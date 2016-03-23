#!/usr/bin/env python3

import threading
import logging
import os
import json
import hashlib

import utils

class Progress():
    threadLock = threading.Lock()
    finished = 0
    total = 0
    percent = 0.0

    def __init__(self):
        pass

    def printProgress(self):
        logging.info(
            "Processed {}/{} tracks ({:.2f}%)".format(self.finished, self.total, self.percent))

    def increase(self):
        self.threadLock.acquire()
        self.finished += 1
        self.percent = (self.finished / self.total) * 100
        self.threadLock.release()

    def increaseTotal(self):
        self.threadLock.acquire()
        self.total += 1
        self.threadLock.release()


class Track():
    ''' Class representing a track (in an album) '''
    title = ""
    filePath = ""
    # file path when synced, this is useful when deleting old tracks
    # File path relative to syncDst
    syncedFilePath = ""
    lossless = False
    trackID = ""

    def __init__(self, metadata, filePath):
        self.title = metadata.title
        self.filePath = filePath
        ext = os.path.splitext(filePath)
        self.lossless = ((ext[1] == ".flac") or (ext[1] == ".wma"))
        self.trackID = utils.genID(metadata)


class Album():
    ''' Class representing an album '''
    title = None
    tracks = []
    coverFile = None

    def __init__(self, title):
        self.title = title
        self.tracks = []
        self.coverFile = None


class Record():
    ''' Class representing a record file to keep track of converted and synced file '''
    threadLock = threading.Lock()
    filePath = ""
    record = {} # <trackID>:<filePath>

    def __init__(self, filePath):
        self.filePath = filePath
        if not(os.path.isfile(self.filePath)):
            self.write()
        self.read()

    def read(self):
        with open(self.filePath) as f:
            self.record = json.load(f)

    def add(self, track):
        # Not thread-safe
        self.threadLock.acquire()
        self.record[track.trackID] = track.syncedFilePath
        self.threadLock.release()

    def remove(self, trackID):
        self.threadLock.acquire()
        del self.record[trackID]
        self.threadLock.release()

    def query(self, metadata):
        trackID = utils.genID(metadata)
        return (trackID in self.record)

    def write(self):
        # Threads are crazy, right?
        self.threadLock.acquire()
        with open(self.filePath, "w") as f:
            json.dump(self.record, f, indent=4)
        self.threadLock.release()
