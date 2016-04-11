import sys, getopt
import codecs
import json, pickle
import os

from Bigfish.utils.error import SlaverThreadError, get_user_friendly_traceback
from Bigfish.app.backtest import Backtesting
from Bigfish.performance.performance_cache import StrategyPerformanceJsonCache, StrategyPerformanceCache
from Bigfish.utils.common import string_to_html
from Bigfish.models import User
from Bigfish.store import UserDirectory

DEBUG = False


def get_output(user, name):
    user = User(user)
    user_dir = UserDirectory(user)
    try:
        with codecs.open(os.path.join(user_dir.get_temp_dir(), name + '.log'), 'r', 'utf-8') as f:
            output = f.read()
            f.close()
    except FileNotFoundError:
        output = ''
    except Exception as e:
        raise e
    return output


def run_backtest(user, name, file, symbols, time_frame, start_time, end_time, commission, slippage):
    cache = StrategyPerformanceCache(user)  # TODO 修改为JSON
    try:
        with codecs.open(file, 'r', 'utf-8') as f:
            code = f.read()
            f.close()
        backtesting = Backtesting(user, name, code, symbols, time_frame, start_time, end_time, commission, slippage)
        backtesting.start()
        performance = backtesting.get_performance()
        cache.put_object(performance)
        cache.put('setting', pickle.dumps(backtesting.get_setting()))  # TODO 修改为JSON
        output = get_output(user, name)
        result = {'stat': 'OK', 'result': performance.yield_curve, 'output': string_to_html(output),
                  'performance': performance.info_on_home_page}
    except SlaverThreadError as e:
        tb_message = get_user_friendly_traceback(*e.get_exc())
        result = {"stat": "FALSE", "error": string_to_html('\n'.join(tb_message))}
    except Exception:
        tb_message = get_user_friendly_traceback(*sys.exc_info())
        result = {"stat": "FALSE", "error": string_to_html('\n'.join(tb_message))}
    finally:
        cache.put('response', json.dumps(result))


if __name__ == '__main__':
    process = 16
    if DEBUG:
        user = '10032'
        code = r"E:\Users\BurdenBear\Documents\Github\Bigfish\Bigfish\test\testcode9.py"
        start_time = '2015-01-01'
        end_time = '2015-03-01'
        symbol = "EURUSD"
        time_frame = "M15"
    else:
        user = None
        code = None
        start_time = None
        end_time = None
        symbol = None
        time_frame = None
    name = 'untiled'
    log = None
    slippage = 0
    commission = 0
    opts, args = getopt.getopt(sys.argv[1:], "S:T:C:l:s:e:u:i:c:n:")
    for op, value in opts:
        if op == '-c':
            code = value
        elif op == '-i':
            symbol = value
        elif op == '-T':
            time_frame = value
        elif op == '-s':
            start_time = value.replace('/', ' ')
        elif op == '-e':
            end_time = value.replace('/', ' ')
        elif op == '-l':
            log = value
        elif op == '-u':
            user = value
        elif op == '-S':
            slippage = float(value)
        elif op == '-C':
            commission = float(value)
        elif op == '-n':
            name = value

    run_backtest(user, name, code, [symbol], time_frame, start_time, end_time, commission, slippage)
