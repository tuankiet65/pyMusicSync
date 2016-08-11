import subprocess
import os
import tempfile
import shutil
import logging
import math
from PIL import Image
from . import utils


def PILResize(src, width, height, targetWidth, targetHeight):
    aspect_ratio = width / height
    if (targetHeight * aspect_ratio >= targetWidth):
        size = (math.ceil(targetHeight * aspect_ratio), targetHeight)
    else:
        size = (targetWidth, math.ceil(targetWidth * aspect_ratio))

    tmp = tempfile.mkstemp(suffix=".jpg", prefix="pmsync_cover_")
    img = Image.open(src, "r")
    img = img.resize(size, Image.LANCZOS)
    if img.mode == "P":
        img = img.convert(mode = "RGB")
    img.save(tmp[1], "jpeg", quality=95, optimize=True)
    return tmp[1]


def Waifu2xResize(src, width, height, targetWidth, targetHeight):
    resize_factor = 2 ** math.ceil(max(math.log2(targetHeight / height), math.log2(targetWidth / targetWidth)))
    logging.debug("w: {} h: {} tw: {} th: {} rf: {}".format(width, height, targetWidth, targetHeight, resize_factor))
    tmp = tempfile.mkstemp(suffix=".png", prefix="pmsync_cover_")
    try:
        subprocess.run(["waifu2x-converter-cpp",
                        "--scale_ratio", str(resize_factor),
                        "-m", "scale",
                        "-i", src,
                        "-o", tmp[1]],
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
        os.remove(tmp[1])
    return PILResize(tmp[1], width*resize_factor, height*resize_factor, targetWidth, targetHeight)

class UpscaleSetting:
    # All cover art will be resize so that the aspect ratio stays the same
    OPTIONAL_OPTIONS = {
        "enabled": False,
        "engine": "PIL",
        "targetHeight": 720,
        "targetWidth": 1280,
        "ignoreIfLarger": False
    }

    def __init__(self, config):
        for key, default in self.OPTIONAL_OPTIONS.items():
            self.__setattr__(key, utils.getKey(config, key, default=default))
        if self.engine == "waifu2x":
            self.upscale = Waifu2xResize
            pass
        elif self.engine == "PIL":
            self.upscale = PILResize
            pass
        else:
            logging.debug("Invalid upscale engine: {}. Choosing PIL".format(self.engine))
            self.upscale = PILResize
            pass

    def toDict(self):
        result = {}
        for key in self.OPTIONAL_OPTIONS.keys():
            result[key] = getattr(self, key)
        return result


def copy_cover_art(src, dst, setting):
    try:
        img = Image.open(src, "r")
    except IOError:
        logging.debug("Error loading cover art {}, ignoring".format(src))
        return
    width, height = img.size
    if (width >= setting.targetWidth) or (height >= setting.targetHeight):
        if setting.ignoreIfLarger:
            shutil.copy(src, dst)
        else:
            # Just downscale, PIL/Lanczos is enough
            src = PILResize(src, width, height, setting.targetWidth, setting.targetHeight)
            shutil.copy(src, os.path.join(dst, "cover.jpg"))
    else:
        src = setting.upscale(src, width, height, setting.targetWidth, setting.targetHeight)
        shutil.copy(src, os.path.join(dst, "cover.jpg"))