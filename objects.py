#!/usr/bin/env python3

import threading
import logging
import os
import json
import hashlib


class Progress():
    threadLock = threading.Lock()
    finished = 0
    total = 0
    percent = 0.0

    def __init__(self):
        pass

    def setTotal(self, total):
        self.total = total

    def printProgress(self):
        logging.info(
            "Processed {}/{} tracks ({:.2f}%)".format(self.finished, self.total, self.percent))

    def increase(self):
        self.threadLock.acquire()
        self.finished += 1
        self.percent = (self.finished / self.total) * 100
        self.threadLock.release()


class Track():
    ''' Class representing a track (in an album) '''
    title = ""
    filePath = ""
    lossless = False
    trackID = ""

    def __init__(self, metadata, filePath):
        self.title = metadata.title
        self.filePath = filePath
        ext = os.path.splitext(filePath)
        self.lossless = ((ext[1] == ".flac") or (ext[1] == ".wma"))
        self.trackID = self.genID(metadata)

    def genID(self, metadata):
        mtdID = "{0.album}:{0.title}:{0.duration:.3f}".format(metadata)
        return mtdID
        # return hashlib.md5(mtdID.encode()).hexdigest()


class Album():
    ''' Class representing an album '''
    title = ""
    tracks = []
    coverFile = ""

    def __init__(self, title):
        self.title = title
        self.tracks = []
        self.coverFile = ""


class Record():
    ''' Class representing a record file to keep track of converted and synced file '''
    filePath = ""
    record = []

    def __init__(self, filePath):
        self.filePath = filePath
        record = []
        if not(os.path.isfile(self.filePath)):
            self.write()
        self.read()

    def read(self):
        with open(self.filePath) as f:
            self.record = json.load(f)

    def add(self, trackID):
        # list.append is thread-safe
        self.record.append(trackID)

    def query(self, trackID):
        return (trackID in self.record)

    def queryMetadata(self, metadata):
        trackID = self.genID(metadata)
        return trackID in self.record

    def genID(self, metadata):
        mtdID = "{0.album}:{0.title}:{0.duration:.3f}".format(metadata)
        return mtdID
        # return hashlib.md5(mtdID.encode()).hexdigest()

    def write(self):
        with open(self.filePath, "w") as f:
            json.dump(self.record, f, indent=4)
