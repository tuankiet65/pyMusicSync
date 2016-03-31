#!/usr/bin/env python3

import os
import logging
import shutil
import threading
import time
import re
from tinytag import TinyTag
import unidecode
import subprocess
import hashlib
import copy
import queue

import objects
import utils
import encoder


class musicSync():

    albums = {}
    blacklistAlbum = []
    trackIDList = []
    progress = objects.Progress()
    oldRecord = None
    record = None
    dryRun = False
    syncDst = None
    encoderQuality = None

    def __init__(self, config):
        self.blacklistAlbum = config.blacklistAlbum
        self.record = objects.Record(config.recordPath)
        self.oldRecord = copy.deepcopy(self.record)
        self.dryRun = config.dryRun
        self.syncDst = config.syncDst
        self.encoderSetting = config.encoderSetting
        self.threadNum = config.threadNum
        self.trackQueue = queue.Queue(maxsize=self.threadNum)

    def checkValid(self, metadata):
        # Length >=15 minutes => Most probably all-in-one file
        if metadata.duration > 60 * 15:
            return False
        # Album name is in blacklist
        if metadata.album in self.blacklistAlbum:
            return False
        # Track is already converted
        if self.record.query(metadata):
            return False
        return True

    def detectCoverFile(self, root):
        possibleNames = ["cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                         "Cover.jpg", "folder.jpeg", "cover.jpeg"]
        for name in possibleNames:
            cover = os.path.join(root, name)
            if os.path.isfile(cover):
                return cover
        return None

    def folderTraversal(self, blacklistAlbum, folderPath):
        for root, subdir, files in os.walk(folderPath):
            hasMusic = False
            albumName = ""
            for f in files:
                fullPath = os.path.join(root, f)
                try:
                    metadata = TinyTag.get(fullPath)
                except LookupError as e:
                    # File is not a valid audio file, skip
                    continue
                self.trackIDList.append(utils.genID(metadata))
                if self.checkValid(metadata):
                    albumName = metadata.album
                    if not albumName in self.albums:
                        self.albums[albumName] = objects.Album(albumName)
                    newTrack = objects.Track(metadata, fullPath)
                    self.albums[albumName].tracks.append(newTrack)
                    hasMusic = True
                    self.progress.increaseTotal()
            if hasMusic:
                # Handle cover image
                self.albums[albumName].coverFile = self.detectCoverFile(root)
                logging.info("Album: %s with %d song(s)" %
                             (albumName, len(self.albums[albumName].tracks)))

    def trackHandle(self):
        while True:
            albumName, track = self.trackQueue.get()
            if albumName is None and track is None:
                self.trackQueue.task_done()
                return
            logging.info("Processing track {}".format(track.title))
            if track.lossless:
                encoder.encode(track.filePath, self.returnFilePath(
                    albumName, track.title), self.encoderSetting)
                track.syncedFilePath = self.returnFilePath(
                    albumName, track.title, ext=self.encoderSetting.ext, absolute=False)
            else:
                track.syncedFilePath = self.returnFilePath(
                    albumName, track.title, ext=os.path.splitext(track.filePath)[1], absolute=False)
                shutil.copy(track.filePath, os.path.join(
                    self.syncDst, track.syncedFilePath))
            self.record.add(track)
            self.progress.increase()
            self.trackQueue.task_done()

    def startSync(self):
        for i in range(self.threadNum):
            threading.Thread(target=self.trackHandle).start()
        for albumName, album in self.albums.items():
            logging.info("Processing album {}".format(albumName))
            dirName = self.returnFilePath(album=album.title)
            if not os.path.isdir(dirName):
                os.mkdir(dirName)
            if album.coverFile is not None:
                shutil.copy(album.coverFile, dirName)
            for track in album.tracks:
                self.trackQueue.put((album.title, track))
        for i in range(self.threadNum):
            self.trackQueue.put((None, None))
        self.trackQueue.join()

    def prune(self):
        ''' Deleting old tracks'''
        possibleCoverNames = set(["cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                                  "Cover.jpg", "folder.jpeg", "cover.jpeg"])
        for trackID, filePath in self.oldRecord.record.items():
            if trackID not in self.trackIDList:
                logging.info("Removing old track {}".format(trackID))
                os.remove(os.path.join(self.syncDst, filePath))
                self.record.remove(trackID)
                fileDir = os.path.join(
                    self.syncDst, os.path.split(filePath)[0])
                if set(os.listdir(fileDir)) - possibleCoverNames == set():
                    logging.info("Removing empty folder {}".format(fileDir))
                    shutil.rmtree(fileDir)

    def shutdown(self):
        self.record.write()

    def returnFilePath(self, album="", title="", ext="", absolute=True):
        filePath = os.path.join(utils.FAT32Santize(
            album), utils.FAT32Santize(title))
        if absolute:
            filePath = os.path.join(self.syncDst, filePath)
        filePath = filePath + ext
        return filePath
