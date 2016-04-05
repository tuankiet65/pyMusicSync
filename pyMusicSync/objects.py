#!/usr/bin/env python3

import json
import logging
import os
import threading
import time

from pyMusicSync import utils


class Progress:
    threadLock = threading.Lock()
    finished = 0
    total = 0
    percent = 0.0

    def __init__(self):
        pass

    def increase(self):
        with self.threadLock:
            self.finished += 1
            self.percent = (self.finished / self.total) * 100


class Track:
    """ Class representing a track (in an album)
        All file path are relative to syncDst """

    def __init__(self, metadata, filePath):
        self.album = str(metadata.album)
        self.title = str(metadata.title)
        self.filePath = filePath
        ext = os.path.splitext(filePath)
        self.lossless = ((ext[1] == ".flac") or (ext[1] == ".wma"))
        self.trackID = utils.genID(metadata)
        try:
            self.trackNumber = int(metadata.track)
        except (TypeError, ValueError):
            self.trackNumber = None


class Album:
    """ Class representing an album """

    def __init__(self, title):
        self.title = str(title)
        self.tracks = []
        self.coverFile = None

    def add(self, track):
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
        self.killed = False
        self.hasUnsavedChanges = False
        self.autosaveInterval = interval
        self.autosaveThread = threading.Thread(target=self.__autosave)

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
        lastTime = time.monotonic()
        while True:
            if self.killed:
                return
            currTime = time.monotonic()
            if self.hasUnsavedChanges and (currTime - lastTime >= self.autosaveInterval):
                logging.debug("writing changes")
                self.write()
                self.hasUnsavedChanges = False
                lastTime = currTime
            time.sleep(0.1)

    def startAutosave(self):
        self.autosaveThread.start()

    def killAutosave(self):
        self.killed = True
