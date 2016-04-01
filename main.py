#!/usr/bin/env python3

import logging
import os

import sync
import config

logging.basicConfig(format="[%(asctime)s][%(funcName)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    level=logging.NOTSET)

config = config.Config("./config.json")

if not os.path.isdir(config.syncDestination):
    os.mkdir(config.syncDestination)

sync = sync.musicSync(config=config)

for folder in config.syncDestionation:
    sync.folderTraversal(folder)

sync.prune()

sync.startSync()

sync.shutdown()

logging.shutdown()
