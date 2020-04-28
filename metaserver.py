#!/usr/bin/env python3

import os

while True:
    os.system("git pull origin master")
    os.system("./server.py")
