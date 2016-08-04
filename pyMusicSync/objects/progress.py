#!/usr/bin/env python3

import threading


class Progress:
    threadLock = threading.Lock()
    finished = 0
    total = 0
    percent = 0.0

    def __init__(self):
        pass

    def increase(self):
        with self.threadLock:
            self.finished += 1
            self.percent = (self.finished / self.total) * 100

    def incTotal(self):
        self.total += 1
