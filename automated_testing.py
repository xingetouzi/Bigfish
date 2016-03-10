import codecs
import logging

from Bigfish.models.model import User
from Bigfish.app.backtest import Backtesting
import time
import random
import threading

log_file = "./basic_logger.log"
logging.basicConfig(filename=log_file, level=logging.DEBUG)


def run(user_id, name, symbol, tf):
    start_time = time.time()
    with codecs.open('./Bigfish/test/testcode7.py', 'r', 'utf-8') as f:
        code = f.read()
    user = User(user_id)
    backtest = Backtesting(user, 'test', code, [symbol], 'M15', '2015-01-01', '2016-01-01')
    backtest.start()
    logging.debug("Run user_id=%s, symbol=%s, timeFrame=%s spend time %f, endtime=%f" % (user_id, symbol, tf, time.time() - start_time, time.time()))


if __name__ == '__main__':
    SYMBOLS = ["EURUSD", "XAUUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDCAD", "USDCHF"]
    TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "D1"]
    # USERIDS = ["10011", "10022", "10033", "10044", "10055", "10066", "10077", "10088"]
    for i in range(2):
        i1 = random.randint(0, len(SYMBOLS) - 1)
        i2 = random.randint(0, len(TIMEFRAMES) - 1)
        name = "test%d" % i
        user_id = name
        print(SYMBOLS[i1], TIMEFRAMES[i2])
        t = threading.Thread(target=run, args=(user_id, name, SYMBOLS[i1], TIMEFRAMES[i2]))
        #t.setDaemon(True)
        t.start()