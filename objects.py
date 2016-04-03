#!/usr/bin/env python3

import threading
import os
import json
import time

import utils


class Progress:
    threadLock = threading.Lock()
    finished = 0
    total = 0
    percent = 0.0

    def __init__(self):
        pass

    def increase(self):
        self.threadLock.acquire()
        self.finished += 1
        self.percent = (self.finished / self.total) * 100
        self.threadLock.release()


class Track:
    """ Class representing a track (in an album)
        All file path are relative to syncDst """

    def __init__(self, metadata, filePath):
        self.title = metadata.title
        self.filePath = filePath
        ext = os.path.splitext(filePath)
        self.lossless = ((ext[1] == ".flac") or (ext[1] == ".wma"))
        self.trackID = utils.genID(metadata)


class Album:
    """ Class representing an album """

    def __init__(self, title):
        self.title = title
        self.tracks = []
        self.coverFile = None

    def addTrack(self, track):
        self.tracks.append(track)


class Record:
    """ Class representing a record file to keep track of converted and synced file """
    threadLock = threading.Lock()
    filePath = ""
    record = {}  # <trackID>:<filePath>

    def __init__(self, filePath, interval):
        self.filePath = filePath
        if not (os.path.isfile(self.filePath)):
            self.write()
        self.read()
        self.autosave = False
        self.hasUnsavedChanges = False
        self.autosaveInterval = interval
        threading.Thread(target=self.__autosave).start()

    def read(self):
        with open(self.filePath) as f:
            self.record = json.load(f)

    def add(self, track):
        # Not thread-safe
        with self.threadLock:
            self.record[track.trackID] = track.syncedFilePath
            self.hasUnsavedChanges = True

    def remove(self, item):
        with self.threadLock:
            del self.record[item]
            self.hasUnsavedChanges = True

    def __contains__(self, item):
        with self.threadLock:
            trackID = utils.genID(item)
            return trackID in self.record

    def get(self, item):
        return self.record[item]

    def write(self):
        with self.threadLock:
            with open(self.filePath, "w") as f:
                json.dump(self.record, f, indent=4)

    def idList(self):
        return list(self.record.keys())

    def __autosave(self):
        while True:
            if self.autosave and self.hasUnsavedChanges:
                self.write()
                self.hasUnsavedChanges = False
            time.sleep(self.autosaveInterval)

    def startAutosave(self):
        self.autosave = True

    def stopAutosave(self):
        self.autosave = False
