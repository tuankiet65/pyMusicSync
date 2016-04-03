#!/usr/bin/env python3

import os
import logging
import shutil
import concurrent.futures
from tinytag import TinyTag

import objects
import utils
import encoder


class musicSync:
    albums = {}
    trackIDList = set()
    progress = objects.Progress()

    def __init__(self, config):
        self.record = objects.Record(config.recordPath, config.autosaveDuration)
        self.config = config
        self.record.startAutosave()

    def __checkValid(self, metadata):
        # Length >=15 minutes => Most probably all-in-one file
        if metadata.duration > 60 * 15:
            return False
        # Album name is in blacklist
        if metadata.album in self.config.blacklistAlbum:
            return False
        # Track is already converted
        if metadata in self.record:
            return False
        return True

    @staticmethod
    def __detectCoverFile(root):
        possibleNames = ["cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                         "Cover.jpg", "folder.jpeg", "cover.jpeg"]
        for name in possibleNames:
            cover = os.path.join(root, name)
            if os.path.isfile(cover):
                return cover
        return None

    def folderTraversal(self, folderPath):
        trackCount = 0
        for root, subdir, files in os.walk(folderPath):
            hasMusic = False
            albumName = ""
            for f in files:
                fullPath = os.path.join(root, f)
                try:
                    metadata = TinyTag.get(fullPath)
                except LookupError:
                    # File is not a valid audio file, skip
                    continue
                self.trackIDList.add(utils.genID(metadata))
                if self.__checkValid(metadata):
                    albumName = metadata.album
                    if albumName not in self.albums:
                        self.albums[albumName] = objects.Album(albumName)
                    newTrack = objects.Track(metadata, fullPath)
                    self.albums[albumName].addTrack(newTrack)
                    hasMusic = True
                    trackCount += 1
            if hasMusic:
                # Handle cover image
                self.albums[albumName].coverFile = self.__detectCoverFile(root)
                logging.info("Album: %s with %d song(s)" %
                             (albumName, len(self.albums[albumName].tracks)))
        self.progress.total = trackCount

    def __trackHandle(self, albumName, track):
        logging.info("Processing track {}".format(track.title))
        if not self.config.dryRun:
            if track.lossless:
                track.syncedFilePath = encoder.encode(track.filePath, self.__getFilePath(albumName, track.title),
                                                      self.config.encoderSetting)
            else:
                track.syncedFilePath = self.__getFilePath(albumName, track.title,
                                                          ext=os.path.splitext(track.filePath)[1])
                shutil.copy(track.filePath, track.syncedFilePath)
        self.record.add(track)
        self.progress.increase()

    def startSync(self):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.threadNum)
        for albumName, album in self.albums.items():
            logging.info("Processing album {}".format(albumName))
            dirName = self.__getFilePath(album=albumName)
            if not os.path.isdir(dirName):
                os.mkdir(dirName)
            if album.coverFile is not None:
                shutil.copy(album.coverFile, dirName)
            for track in album.tracks:
                executor.submit(self.__trackHandle, albumName, track)
        executor.shutdown()

    def prune(self):
        possibleCoverNames = {"cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg", "Cover.jpg", "folder.jpeg",
                              "cover.jpeg"}
        for trackID in self.record.idList():
            if trackID not in self.trackIDList:
                logging.info("Removing old track {}".format(trackID))
                os.remove(self.record.get(trackID))
                self.record.remove(trackID)
                fileDir = os.path.split(self.record.get(trackID))[0]
                if set(os.listdir(fileDir)) - possibleCoverNames == set():
                    logging.info("Removing empty folder {}".format(fileDir))
                    shutil.rmtree(fileDir)

    def shutdown(self):
        self.record.stopAutosave()
        self.record.write()

    @staticmethod
    def __getFilePath(album="", title="", ext=""):
        return os.path.join(utils.FAT32Santize(album), utils.FAT32Santize(title)) + ext
