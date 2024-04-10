import subprocess
import threading
import os
import time


def run_in_thread():
    j = 0
    while j < 10:
        print(j)
        time.sleep(1)
        j += 1

thread = threading.Thread(target=run_in_thread)
thread.start()

i = 0
while True:
    print(str(i) + " second")
    time.sleep(1)
    i += 1
