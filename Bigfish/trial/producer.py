from Bigfish.trial.task import *
import time

if __name__ == '__main__':
    print(add.name)
    r = add.delay(4, 4)
    while not r.ready():
        print('wait')
        time.sleep(0.5)
    print(r.id)
    print(r.get())
    r = running.delay()
    print(r.get())
