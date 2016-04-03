#!/usr/bin/env python3

import logging
import os
import argparse

import sync
import config


def getConfigPath():
    parser = argparse.ArgumentParser(description="Sync your music the hard way")
    parser.add_argument("-c", "--config", help="Specify config file path", default=("./config.json"))
    parser.parse_args()
    return parser.config

logging.basicConfig(format="[%(asctime)s][%(funcName)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    level=logging.NOTSET)

config = config.Config(getConfigPath)

if not os.path.isdir(config.syncDestination):
    os.mkdir(config.syncDestination)

os.chdir(config.syncDestination)

sync = sync.musicSync(config=config)

for folder in config.syncSource:
    sync.folderTraversal(folder)

sync.prune()

sync.startSync()

sync.shutdown()

logging.shutdown()
