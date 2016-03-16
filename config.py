#!/usr/bin/env python

import json


class Config():
    configFile = ""

    def __init__(self, configFile):
        self.configFile = configFile
        self.read()

    def read(self):
        with open(self.configFile) as f:
            data = json.load(f)
        self.syncSrc = self.getKey(data, 'syncSource', raiseCheck=True)
        self.syncDst = self.getKey(data, 'syncDestination', raiseCheck=True)
        self.blacklistAlbum = self.getKey(data, 'blacklistAlbum', default=[])
        self.threadNum = self.getKey(data, 'threadNum', default=1)

    def write(self):
        data = {'syncSource': self.syncSrc, 'syncDestination': self.syncDst,
                'blacklistAlbum': self.blacklistAlbum, 'threadNum': self.threadNum}
        with open(self.configFile, 'w') as f:
            json.dump(data, f, indent=4)

    def getKey(self, dictionary, key, raiseCheck=False, default=None):
        if key in dictionary:
            return dictionary[key]
        else:
            if raiseCheck:
                raise Exception("{key} not found in dict".format(key=key))
            else:
                logging.warning("{key} not found in dict, returning default value".format(key=key))
                return default