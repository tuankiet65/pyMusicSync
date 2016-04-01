#!/usr/bin/env python

import json
import os
import encoder

class Config():
    configFile = ""
    REQUIRED_OPTIONS = [
        "syncSource",
        "syncDestination"
    ]
    OPTIONAL_OPTIONS = {
        "blacklistAlbum": [],
        "threadNum": 1,
        "dryRun": False,
        "encoderSetting": {
            "codec": "mp3",
            "bitrateControl": "vbr",
            "quality": "0"
        }
    }

    def __init__(self, configFile):
        self.configFile = configFile
        self.read()

    def read(self):
        with open(self.configFile) as f:
            data = json.load(f)
        for v in REQUIRES_VARIABLES:
            self.__setattr__(v, self.__getKey(data, v, raiseCheck=True))
        for v, default in self.OPTIONAL_OPTIONS.items():
            self.__setattr__(v, self.__getKey(data, v, default=default))
        self.encoderSetting = encoder.EncoderSetting(self.encoderSetting)

    def write(self):
        data = {}
        for v in self.REQUIRED_OPTIONS:
            data[v] = self.__getattr__(v)
        for v in self.OPTIONAL_OPTIONS.keys():
            data[v] = self.__getattr__(v)
        with open(self.configFile, 'w') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def __getKey(dictionary, key, raiseCheck=False, default=None):
        if key in dictionary:
            return dictionary[key]
        else:
            if raiseCheck:
                raise Exception("{key} not found in dict".format(key=key))
            else:
                logging.warning("{key} not found in dict, returning default value".format(key=key))
                return default