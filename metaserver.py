#!/usr/bin/env python3

import os, time

while True:
    start_time = time.time()
    
    os.system("./server.py pre")
    os.system("git pull origin master")
    os.system("./server.py post")
    
    elapsed_time = time.time() - start_time
    time.sleep(60 - elapsed_time)
