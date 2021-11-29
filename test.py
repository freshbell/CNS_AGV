import threading
import time

temp = 0
def test():
    global temp
    while True:
        ns = time.time_ns()
        time.sleep(0.05)      
        print(ns - temp)
        temp = ns  
    
threa = threading.Thread(target=test)
threa.start()