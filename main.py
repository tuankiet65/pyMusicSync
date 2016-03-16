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

sync = sync.musicSync(config=config)

for folder in config.syncSrc:
    sync.folderTraversal(config.blacklistAlbum, folder)


try:
    sync.startAlbumSync(config.threadNum)
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt caught, shutting down")
    sync.forceShutdown()
else:
    sync.shutdown()

logging.shutdown()
