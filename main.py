#!/usr/bin/env python3

import argparse
import logging
import os

import pyMusicSync


def getConfigPath():
    parser = argparse.ArgumentParser(description="Sync your music the hard way")
    parser.add_argument("-c", "--config", help="Specify config file path", default="./config.json")
    args = parser.parse_args()
    return args.config


logging.basicConfig(format="[%(asctime)s][%(funcName)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    level=logging.NOTSET)

config = pyMusicSync.config.Config(getConfigPath())

if not os.path.isdir(config.syncDestination):
    os.mkdir(config.syncDestination)

os.chdir(config.syncDestination)

sync = pyMusicSync.sync.musicSync(config=config)

for folder in config.syncSource:
    sync.folderTraversal(folder)

sync.prune()

sync.startSync()

sync.shutdown()

logging.shutdown()
