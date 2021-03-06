#!/usr/bin/env python3

import os
import shutil
import subprocess
import tempfile
import logging

from pyMusicSync import utils


class EncoderSetting:
    OPTIONAL_OPTIONS = {
        "codec": "mp3",
        "bitrateControl": "vbr",
        "quality": "0"
    }

    def __init__(self, config):
        codecMap = {
            "mp3": ("libmp3lame", ".mp3"),
            "opus": ("libopus", ".ogg"),
            "vorbis": ("libvorbis", ".ogg"),
            "aac": (self.detect_fdkaac(), ".mp4")
        }
        for key, default in self.OPTIONAL_OPTIONS.items():
            self.__setattr__(key, utils.getKey(config, key, default=default))
        self.encoder, self.ext = codecMap[self.codec]

    def toDict(self):
        result = {}
        for key in self.OPTIONAL_OPTIONS.keys():
            result[key] = getattr(self, key)
        return result

    @staticmethod
    def detect_fdkaac():
        ffmpegOutput = subprocess.check_output(
            ["ffmpeg", "-codecs"], stderr=subprocess.DEVNULL).decode("utf-8")
        if "libfdk_aac" in ffmpegOutput:
            return "libfdk_aac"
        else:
            logging.info(
                "If your encoding setting is AAC, please consider\n"
                "compiling FFmpeg with libfdk_aac for better audio quality\n"
                "compared to FFmpeg's native AAC encoder")
            return "aac"


def encode(src, dst, setting):
    tmpFile = tempfile.mkstemp(suffix=setting.ext, prefix="pmsync_")[1]
    dst = dst + setting.ext

    param = ["ffmpeg", "-v", "warning", "-i", src, "-vn", "-c:a", setting.encoder]
    if setting.bitrateControl == "vbr":
        param.extend(["-q:a", setting.quality])
    elif setting.bitrateControl == "cbr":
        param.extend(["-b:a", "{}k".format(setting.quality)])
    param.extend(["-threads", "1", "-y", tmpFile])
    success = False

    while not success:
        try:
            subprocess.run(param,
                           check=True,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logging.debug("=== CalledProcessError ===")
            logging.debug("cmd: {}".format(e.cmd))
            logging.debug("output: {}".format(e.stdout.decode()))
            logging.debug("stderr: {}".format(e.stderr.decode()))
            logging.debug("=== CalledProcessError ===")
            os.remove(tmpFile)
        else:
            shutil.move(tmpFile, dst)
            success = True

    return dst
