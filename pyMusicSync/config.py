#!/usr/bin/env python

import json

from pyMusicSync import encoder, utils, filter, modifier

class Config:
    configFile = ""
    REQUIRED_OPTIONS = [
        "syncSource",
        "syncDestination"
    ]
    OPTIONAL_OPTIONS = {
        "threadNum": 1,
        "dryRun": False,
        "encoderSetting": {},  # EncoderSetting will handle this instead
        "autosaveInterval": 5,
        "filters": [],
        "modifiers": [],
    }

    def __init__(self, configFile):
        self.configFile = configFile
        self.read()
        self.encoderSetting = encoder.EncoderSetting(self.encoderSetting)
        self.filter = filter.Filter(self.filters)
        self.modifier = modifier.Modifier(self.modifiers)

    def read(self):
        with open(self.configFile) as f:
            data = json.load(f)
        for key in self.REQUIRED_OPTIONS:
            self.__setattr__(key, utils.getKey(data, key, raiseCheck=True))
        for key, default in self.OPTIONAL_OPTIONS.items():
            self.__setattr__(key, utils.getKey(data, key, default=default))

    def write(self):
        data = {}
        for key in self.REQUIRED_OPTIONS:
            data[key] = getattr(self, key)
        for key in self.OPTIONAL_OPTIONS.keys():
            data[key] = getattr(self, key)
        data.encoderSetting = data.encoderSetting.toDict()
        with open(self.configFile, 'w') as f:
            json.dump(data, f, indent=4)
