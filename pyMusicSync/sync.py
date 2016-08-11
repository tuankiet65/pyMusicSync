#!/usr/bin/env python3

import concurrent.futures
import logging
import os
import shutil

from tinytag import TinyTag

from pyMusicSync import encoder, objects, utils, cover_art


class musicSync:
    albums = {}
    trackIDList = set()
    progress = objects.Progress()

    def __init__(self, config):
        self.record = objects.Record("record.json", config.autosaveInterval)
        self.config = config
        self.record.startAutosave()

    @staticmethod
    def __detectCoverFile(root):
        possibleNames = ["cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                         "Cover.jpg", "folder.jpeg", "cover.jpeg", "folder.png"]
        for name in possibleNames:
            cover = os.path.join(root, name)
            if os.path.isfile(cover):
                return cover
        return None

    def folderTraversal(self, folderPath):
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
                metadata.album = str(metadata.album)
                self.trackIDList.add(utils.genID(metadata))
                if self.config.filter.check(metadata) and not (metadata in self.record):
                    albumName = metadata.album
                    if albumName not in self.albums:
                        self.albums[albumName] = objects.Album(albumName)
                    newTrack = objects.Track(metadata, fullPath)
                    self.albums[albumName].add(newTrack)
                    hasMusic = True
                    self.progress.incTotal()
            if hasMusic:
                # Handle cover image
                self.albums[albumName].coverFile = self.__detectCoverFile(root)
                logging.info("Album: %s with %d song(s)" %
                             (albumName, len(self.albums[albumName].tracks)))

    def __trackHandle(self, track):
        if not self.config.dryRun:
            if track.lossless:
                track.syncedFilePath = encoder.encode(track.filePath, self.__getFilePath(track),
                                                      self.config.encoderSetting)
            else:
                track.syncedFilePath = self.__getFilePath(track, ext=os.path.splitext(track.filePath)[1])
                shutil.copy(track.filePath, track.syncedFilePath)
        self.record.add(track)
        self.progress.increase()
        logging.info("Processed track {} ({:.2f}%)".format(track.title, self.progress.percent))

    def __createAlbumDirectory(self, album):
        dirName = utils.pathSanitize(album.title)
        if not os.path.isdir(dirName):
            os.mkdir(dirName)
        if album.coverFile is not None:
            cover_art.copy_cover_art(album.coverFile, dirName, self.config.upscaleSetting)

    def startSync(self):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.threadNum)
        for albumName, album in self.albums.items():
            logging.info("Initializing album {}".format(albumName))
            self.__createAlbumDirectory(self.albums[albumName])
            for track in album.tracks:
                executor.submit(self.__trackHandle, track)
        executor.shutdown()

    def prune(self):
        possibleCoverNames = {"cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                              "Cover.jpg", "folder.jpeg", "cover.jpeg", "folder.png"}
        for trackID in self.record.idList():
            if trackID not in self.trackIDList:
                logging.info("Removing old track {}".format(trackID))
                os.remove(self.record.get(trackID))
                fileDir = os.path.split(self.record.get(trackID))[0]
                if set(os.listdir(fileDir)) - possibleCoverNames == set():
                    logging.info("Removing empty folder {}".format(fileDir))
                    shutil.rmtree(fileDir)
                self.record.remove(trackID)

    def shutdown(self):
        self.record.killAutosave()
        self.record.write()

    @staticmethod
    def __getFilePath(track, ext=""):
        directory = utils.pathSanitize(track.album)
        if track.trackNumber is None:
            filename = "{title}{ext}"
        else:
            filename = "{trackNum:02d}. {title}{ext}"
        filename = filename.format(trackNum=track.trackNumber, title=utils.pathSanitize(track.title), ext=ext)

        return os.path.join(directory, filename)
