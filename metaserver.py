#!/usr/bin/env python3

import os, time

while True:
    os.system("./server.py pre")
    os.system("git pull origin master")
    os.system("./server.py post")
    time.sleep(22)
