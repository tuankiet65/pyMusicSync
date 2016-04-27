#!/usr/bin/env python3

import os

from pyMusicSync import utils


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
