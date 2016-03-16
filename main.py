#!/usr/bin/env python3

import logging
import os

import sync
import config
import objects

logging.basicConfig(format="[%(asctime)s][%(funcName)s][%(threadName)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    level=logging.NOTSET)

config = config.Config("./config.json")

if not os.path.isdir(config.syncDst):
    os.mkdir(config.syncDst)

sync = sync.musicSync(blacklist=config.blacklistAlbum,
                      recordPath=os.path.join(config.syncDst, "record.json"))

for folder in config.syncSrc:
    sync.folderTraversal(folder)

try:
    sync.albumSync(config.syncDst, config.threadNum)
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt caught, shutting down")
    sync.forceShutdown()
else:
    sync.shutdown()

logging.shutdown()
