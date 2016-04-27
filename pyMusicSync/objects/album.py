#!/usr/bin/env python3

class Album:
    """ Class representing an album """

    def __init__(self, title):
        self.title = str(title)
        self.tracks = []
        self.coverFile = None

    def add(self, track):
        self.tracks.append(track)
