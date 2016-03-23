#!/usr/bin/env python3

import random
import unidecode
import re
import hashlib

def genRandomString(charset, length):
    random.seed()
    return ''.join([random.choice(charset) for i in range(length)])

def FAT32Santize(name):
    ''' Santize name to be compatible with FAT32 system '''
    if name is None:
        return genRandomString("0123456789ABCDEF", 5)
    # Convert Unicode character to ASCII (This need to be done first)
    # It doesn't and needn't be accurate
    result = unidecode.unidecode(name)
    # FAT32 invalid characters
    ILLEGAL_CHAR = '[' + re.escape("/?<>\:*|\"\\^") + ']'
    result = re.sub(ILLEGAL_CHAR, '', result)
    # For some reason creating a directory with trailing space on Linux
    # will cause "Invalid argument"
    # \t (tabs character) also causes trouble
    result = result.strip().replace("\t", "")
    return result

def genID(metadata):
    mtdID = "{0.album}:{0.title}:{0.duration:.3f}".format(metadata)
    return hashlib.md5(mtdID.encode()).hexdigest()