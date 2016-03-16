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

import objects
import utils


class musicSync():

    albums = {}
    progress = objects.Progress()
    record = None
    forceShutdownFlag = False
    dryRun = False
    syncDst = None
    encodingQuality = None

    def __init__(self, config):
        self.record = objects.Record(config.recordPath)
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

    def checkValid(self, metadata, blacklistAlbum):
        # Length >=15 minutes => Most probably all-in-one file
        if metadata.duration > 60 * 15:
            return False
        # Album name is in blacklist
        if metadata.album in blacklistAlbum:
            return False
        # Track is already converted
        if self.record.queryMetadata(metadata):
            return False
        return True

    def detectCoverFile(self, root):
        possibleName = ["cover_override.jpg", "cover.png", "cover.jpg", "folder.jpg",
                        "Cover.jpg", "folder.jpeg", "cover.jpeg"]
        for name in possibleName:
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
                if self.checkValid(metadata, blacklistAlbum):
                    albumName = metadata.album
                    if not albumName in self.albums:
                        self.albums[albumName] = objects.Album(albumName)
                    self.albums[albumName].tracks.append(
                        objects.Track(metadata, fullPath))
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
        dirName = os.path.join(self.syncDst, utils.FAT32Santize(album.title))
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
                    tmpPath = os.path.join(
                        "/tmp/", utils.FAT32Santize(track.title)) + ".ogg"
                    self.losslessToVorbis(track.filePath, tmpPath)
                    shutil.copy(tmpPath, dirName)
                else:
                    shutil.move(track.filePath, os.path.join(dirName, utils.FAT32Santize(
                        track.title)) + os.path.splitext(track.filePath)[1])
            self.record.add(track.trackID)
            self.progress.increase()

    def forceShutdown(self):
        self.forceShutdownFlag = True
        while self.forceShutdownFlag:
            time.sleep(1)
        self.shutdown()

    def shutdown(self):
        self.record.write()
