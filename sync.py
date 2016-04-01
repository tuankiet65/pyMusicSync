#!/usr/bin/env python3

import os
import logging
import shutil
import threading
import queue
from tinytag import TinyTag

import objects
import utils
import encoder


class musicSync:
    albums = {}
    trackIDList = set()
    progress = objects.Progress()

    def __init__(self, config):
        self.record = objects.Record(config.recordPath)
        self.config = config
        self.trackQueue = queue.Queue(maxsize=self.config.threadNum)

    def __checkValid(self, metadata):
        # Length >=15 minutes => Most probably all-in-one file
        if metadata.duration > 60 * 15:
            return False
        # Album name is in blacklist
        if metadata.album in self.config.blacklistAlbum:
            return False
        # Track is already converted
        if self.record.query(metadata):
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
                    self.albums[albumName].tracks.append(newTrack)
                    hasMusic = True
                    trackCount += 1
            if hasMusic:
                # Handle cover image
                self.albums[albumName].coverFile = self.__detectCoverFile(root)
                logging.info("Album: %s with %d song(s)" %
                             (albumName, len(self.albums[albumName].tracks)))
        self.progress.total = trackCount

    def __trackHandle(self):
        while True:
            albumName, track = self.trackQueue.get()
            if albumName is None and track is None:
                self.trackQueue.task_done()
                return
            logging.info("Processing track {}".format(track.title))
            if not self.config.dryRun:
                if track.lossless:
                    encoder.encode(track.filePath, self.__returnFilePath(albumName, track.title),
                                   self.config.encoderSetting)
                    track.syncedFilePath = self.__returnFilePath(albumName, track.title,
                                                                 ext=self.config.encoderSetting.ext,
                                                                 absolute=False)
                else:
                    track.syncedFilePath = self.__returnFilePath(albumName, track.title,
                                                                 ext=os.path.splitext(track.filePath)[1],
                                                                 absolute=False)
                    shutil.copy(track.filePath, os.path.join(
                        self.config.syncDst, track.syncedFilePath))
            self.record.add(track)
            self.progress.increase()
            self.trackQueue.task_done()

    def startSync(self):
        for i in range(self.config.threadNum):
            threading.Thread(target=self.__trackHandle).start()
        for albumName, album in self.albums.items():
            logging.info("Processing album {}".format(albumName))
            dirName = self.__returnFilePath(album=album.title)
            if not os.path.isdir(dirName):
                os.mkdir(dirName)
            if album.coverFile is not None:
                shutil.copy(album.coverFile, dirName)
            for track in album.tracks:
                self.trackQueue.put((album.title, track))
            self.record.write()
        for i in range(self.config.threadNum):
            self.trackQueue.put((None, None))
        self.trackQueue.join()
        self.record.write()

    def prune(self):
        """ Deleting old tracks"""
        possibleCoverNames = {"cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg", "Cover.jpg", "folder.jpeg",
                              "cover.jpeg"}
        for trackID in self.record.record.keys():
            if trackID not in self.trackIDList:
                logging.info("Removing old track {}".format(trackID))
                os.remove(os.path.join(self.config.syncDst, self.record.record[trackID]))
                fileDir = os.path.join(
                    self.config.syncDst, os.path.split(self.record.record[trackID])[0])
                del self.record.record[trackID]
                if set(os.listdir(fileDir)) - possibleCoverNames == set():
                    logging.info("Removing empty folder {}".format(fileDir))
                    shutil.rmtree(fileDir)

    def shutdown(self):
        self.record.write()

    def __returnFilePath(self, album="", title="", ext="", absolute=True):
        filePath = os.path.join(utils.FAT32Santize(album), utils.FAT32Santize(title))
        if absolute:
            filePath = os.path.join(self.config.syncDst, filePath)
        filePath += ext
        return filePath
