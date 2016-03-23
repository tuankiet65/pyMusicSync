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
import tempfile
import copy

import objects
import utils


class musicSync():

    albums = {}
    blacklistAlbum = []
    trackIDList = []
    progress = objects.Progress()
    oldRecord = None
    record = None
    forceShutdownFlag = False
    dryRun = False
    syncDst = None
    encodingQuality = None

    def __init__(self, config):
        self.blacklistAlbum = config.blacklistAlbum
        self.record = objects.Record(config.recordPath)
        self.oldRecord = copy.deepcopy(self.record)
        self.dryRun = config.dryRun
        self.syncDst = config.syncDst
        self.encodingQuality = config.encodingQuality

    def losslessToVorbis(self, src, dst):
        ''' Converting lossless track to Vorbis'''
        try:
            subprocess.run(["ffmpeg", "-v", "warning", "-i", src, "-vn", "-c:a", "libvorbis", "-q", str(self.encodingQuality), "-y", dst],
                           check=True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logging.critical("Non-zero exit code occured")
            logging.critical("Return code: %d" % (e.returncode))
            logging.critical("stderr: \n%s" % (e.stderr.decode("utf-8")))
            exit()

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

    def startAlbumSync(self, threadNum):
        threads = []
        for albumName, album in self.albums.items():
            # Start processing album in multiple threads
            # (max number of threads defined in threadNum)
            if self.forceShutdownFlag:
                break
            isRunning = False
            while not(isRunning):
                if len(threads) < threadNum:
                    thread = threading.Thread(
                        target=self.albumHandle, args=(album, ), name=album.title)
                    thread.start()
                    threads.append(thread)
                    isRunning = True
                    continue
                for thread in threads:
                    if not thread.is_alive():
                        threads.remove(thread)
                        thread = threading.Thread(
                            target=self.albumHandle, args=(album, ), name=album.title)
                        thread.start()
                        threads.append(thread)
                        isRunning = True
                        break
                if not self.dryRun:
                    time.sleep(1)
                self.record.write()
                self.progress.printProgress()
        # Wait for all threads to stop
        for thread in threads:
            thread.join()
        self.forceShutdownFlag = False

    def albumHandle(self, album):
        ''' Function for handling an album (converting lossless track and moving files) '''
        dirName = self.returnFilePath(album=album.title, absolute=True)
        if not os.path.isdir(dirName):
            os.mkdir(dirName)
        if album.coverFile is not None:
            shutil.copy(album.coverFile, dirName)
        for track in album.tracks:
            if self.forceShutdownFlag:
                return
            logging.info("Processing track %s" % (track.title))
            if not self.dryRun:
                if track.lossless:
                    track.syncedFilePath = self.returnFilePath(
                        album.title, track.title, suffix=".ogg")
                    tmpFile = tempfile.mkstemp(suffix=".ogg")[1]
                    self.losslessToVorbis(track.filePath, tmpFile)
                    shutil.move(tmpFile, os.path.join(
                        self.syncDst, track.syncedFilePath))
                else:
                    track.syncedFilePath = self.returnFilePath(
                        album.title, track.title, suffix=os.path.splitext(track.filePath)[1])
                    shutil.copy(track.filePath, os.path.join(
                        self.syncDst, track.syncedFilePath))
            self.record.add(track)
            self.progress.increase()

    def prune(self):
        ''' Deleting old tracks'''
        possibleCoverNames = set(["cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                         "Cover.jpg", "folder.jpeg", "cover.jpeg"])
        for trackID, filePath in self.oldRecord.record.items():
            if trackID not in self.trackIDList:
                logging.info("Removing old track {}".format(trackID))
                os.remove(os.path.join(self.syncDst, filePath))
                self.record.remove(trackID)
                fileDir=os.path.join(self.syncDst, os.path.split(filePath)[0])
                if set(os.listdir(fileDir))-possibleCoverNames==set():
                    logging.info("Removing empty folder {}".format(fileDir))
                    shutil.rmtree(fileDir)

    def forceShutdown(self):
        self.forceShutdownFlag = True
        while self.forceShutdownFlag:
            time.sleep(1)
        self.shutdown()

    def shutdown(self):
        self.record.write()

    def returnFilePath(self, album="", title="", suffix="", absolute=False):
        filePath = os.path.join(utils.FAT32Santize(
            album), utils.FAT32Santize(title))
        if absolute:
            filePath = os.path.join(self.syncDst, filePath)
        filePath = filePath + suffix
        return filePath
