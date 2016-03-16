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


class musicSync():

    albums = {}
    progress = objects.Progress()
    trackCount = 0
    blacklist = []
    record = None
    forceShutdownFlag = False

    def __init__(self, blacklist, recordPath):
        self.blacklist = blacklist
        self.record = objects.Record(recordPath)

    def losslessToVorbis(self, src, dst):
        ''' Converting lossless track to Vorbis Q4 '''
        try:
            subprocess.run(["ffmpeg", "-v", "warning", "-i", src, "-vn", "-c:a", "libvorbis", "-q", "7", "-y", dst],
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
        if metadata.album in self.blacklist:
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

    def folderTraversal(self, folderPath):
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
                if not(self.checkValid(metadata)):
                    continue
                albumName = metadata.album
                if not albumName in self.albums:
                    self.albums[albumName] = objects.Album(albumName)
                self.albums[albumName].tracks.append(
                    objects.Track(metadata, fullPath))
                hasMusic = True
                self.trackCount += 1
            if hasMusic:
                # Handle cover image
                self.albums[albumName].coverFile = self.detectCoverFile(root)
                logging.info("Album: %s with %d song(s)" %
                             (albumName, len(self.albums[albumName].tracks)))
        self.progress.setTotal(self.trackCount)

    def startAlbumThread(self, syncFolder, album):
        thread = threading.Thread(target=self.albumHandle, args=(
            syncFolder, album), name=album.title)
        thread.start()
        return thread

    def albumSync(self, syncFolder, threadNum):
        threads = []
        for albumName, album in self.albums.items():
            # Start processing album in multiple threads
            # (max number of threads defined in THREAD_NUM
            if self.forceShutdownFlag:
                break
            isRunning = False
            while not(isRunning):
                if len(threads) < threadNum:
                    threads.append(self.startAlbumThread(syncFolder, album))
                    isRunning = True
                    continue
                for thread in threads:
                    if not thread.is_alive():
                        threads.remove(thread)
                        threads.append(
                            self.startAlbumThread(syncFolder, album))
                        isRunning = True
                        break
                time.sleep(1)
                self.progress.printProgress()
        # Wait for all threads to stop
        for thread in threads:
            thread.join()
        self.forceShutdownFlag = False

    def albumHandle(self, syncFolder, album):
        ''' Function for handling an album (converting lossless track and moving files) '''
        dirName = os.path.join(syncFolder, self.santizeName(album.title))
        if not os.path.isdir(dirName):
            os.mkdir(dirName)
        if album.coverFile is not None:
            shutil.copy(album.coverFile, dirName)
        for track in album.tracks:
            if self.forceShutdownFlag:
                return
            logging.info("Processing track %s" % (track.title))
            if track.lossless:
                tmpPath = os.path.join(
                    "/tmp/", self.santizeName(track.title)) + ".ogg"
                self.losslessToVorbis(track.filePath, tmpPath)
                shutil.copy(tmpPath, dirName)
            else:
                shutil.move(track.filePath, os.path.join(dirName, self.santizeName(
                    track.title)) + os.path.splitext(track.filePath)[1])
            self.record.add(track.trackID)
            self.progress.increase()
            if self.progress.finished%10==0:
                self.record.write()
    
    def genRandomString(self, charset, length):
        random.join()
        return ''.join([random.choice(charset) for i in range(length)])

    def santizeName(self, name):
        ''' Santize name to be compatible with FAT32 system '''
        if name is None:
            return genRandomString("0123456789ABCDEF", 5)
        # Convert Unicode character to ASCII (This need to be done first)
        # It doesn't and needn't be accurate
        result = unidecode.unidecode(name)
        # FAT32 invalid characters
        ILLEGAL_CHAR = '[' + re.escape("/?<>\:*|\"\\^") + ']'
        result = re.sub(ILLEGAL_CHAR, '', result)
        # For some reason creating a directory with trailing space on Linux
        # will cause "Invalid argument"
        # \t (tabs character) also causes trouble
        result = result.strip().replace("\t", "")
        return result

    def forceShutdown(self):
        self.forceShutdownFlag = True
        while self.forceShutdownFlag:
            time.sleep(1)
        self.shutdown()

    def shutdown(self):
        self.record.write()
