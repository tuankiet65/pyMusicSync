#!/usr/bin/env python3

import shutil
import subprocess
import tempfile

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
            "ogg": ("libvorbis", ".ogg"),
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
            print(
                "If your encoding setting is AAC, please consider\n"
                "compiling FFmpeg with libfdk_aac for better audio quality\n"
                "compared to FFmpeg's native AAC encoder")
            return "aac"


def encode(src, dst, setting):
    tmpFile = tempfile.mkstemp(suffix=setting.ext)[1]
    dst = dst + setting.ext

    param = ["ffmpeg", "-v", "warning", "-i", src, "-vn", "-c:a", setting.encoder]
    if setting.bitrateControl == "vbr":
        param.extend(["-q:a", setting.quality])
    elif setting.bitrateControl == "cbr":
        param.extend(["-b:a", setting.quality])
    param.extend(["-y", tmpFile])

    subprocess.run(param,
                   check=True,
                   stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)

    shutil.move(tmpFile, dst)
    return dst
