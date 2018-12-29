#!/usr/bin/env python3

import hashlib
import logging
import random

import unidecode


def genRandomString(charset, length):
    random.seed()
    return ''.join([random.choice(charset) for i in range(length)])


def pathSanitize(name):
    """ Sanitize path """
    if name is None:
        return genRandomString("0123456789ABCDEF", 5)
    # Convert Unicode character to ASCII (This need to be done first)
    # It doesn't and needn't be accurate
    result = unidecode.unidecode(name)
    # Illegal characters
    ILLEGAL_CHAR = '/?<>:*|"\\^)\0\t'
    for ch in ILLEGAL_CHAR:
        result = result.replace(ch, "_x{:x}_".format(ord(ch)))
    # For some reason creating a directory with trailing space on Linux
    # will cause "Invalid argument"
    result = result.strip()
    # Folder names with trailing spaces like 'e.p.' will become 'e.p'
    # We'd strip the trailing dot
    result = result.strip('.')
    # Also strip trailing and leading spaces
    result = result.strip()
    return result


def genID(metadata):
    mtdID = "{0.album}:{0.title}:{0.duration:.3f}".format(metadata)
    return hashlib.md5(mtdID.encode()).hexdigest()


def getKey(dictionary, key, raiseCheck=False, default=None):
    if key in dictionary:
        return dictionary[key]
    else:
        if raiseCheck:
            raise Exception("{key} not found in dict".format(key=key))
        else:
            logging.warning("{key} not found in dict, returning default value".format(key=key))
            return default
