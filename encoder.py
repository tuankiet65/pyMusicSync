#!/usr/bin/env python3

import subprocess
import queue
import threading
import tempfile
import shutil
import logging


class EncoderSetting():

    def __init__(self, codec, bitrate):
        codecMap = {
            "mp3": ("libmp3lame", ".mp3"),
            "opus": ("libopus", ".mkv"),  # Android compability
            "ogg": ("libvorbis", ".ogg"),
            "aac": (self.detect_fdkaac(), ".mp4")
        }
        self.encoder, self.ext = codecMap[codec]
        self.bitrate = bitrate

    def detect_fdkaac(self):
        ffmpegOutput = subprocess.check_output(
            ["ffmpeg", "-codecs"], stderr=subprocess.DEVNULL).decode("utf-8")
        if "libfdk_aac" in ffmpegOutput:
            return "libfdk_aac"
        else:
            print(
                "If your encoding setting is AAC, please consider\ncompiling FFmpeg with libfdk_aac for better audio quality\ncompared to FFmpeg's native AAC encoder")
            return "aac"


def encode(src, dst, setting):
    tmpFile = tempfile.mkstemp(suffix=setting.ext)[1]
    dst = dst + setting.ext

    subprocess.run(["ffmpeg", "-v", "warning",
                    "-i", src, "-vn",
                    "-c:a", setting.encoder, "-b:a", setting.bitrate,
                    "-y", tmpFile],
                   check=True,
                   stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)

    shutil.move(tmpFile, dst)
