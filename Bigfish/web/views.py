import os
import pickle, ujson as json
import sys
import time
import multiprocessing as mp
from queue import Empty

import tornado.gen
import tornado.ioloop
import tornado.web

from Bigfish.app.backtest import Backtesting
from Bigfish.models.base import TradingMode, BfConfig
from Bigfish.models.model import User
from Bigfish.performance.cache import StrategyPerformanceJsonCache
from Bigfish.store import UserDirectory
from Bigfish.utils.common import string_to_html
from Bigfish.utils.error import SlaverThreadError, get_user_friendly_traceback


def backtest(conn, *args):
    try:
        code = args[0]
        config = BfConfig(**{v[0]: v[1] for v in zip(["user", "name", "symbols", "time_frame", "start_time",
                                                      "end_time", "commission", "slippage"], args[1:])})
        config.trading_mode = TradingMode.on_tick
        user = config.user
        backtesting = Backtesting()
        backtesting.set_code(code)
        backtesting.set_config(config)
        backtesting.start()
        performance = backtesting.get_performance()
        cache = StrategyPerformanceJsonCache(user)
        cache.put_performance(performance)
        cache.put('setting', json.dumps(backtesting.get_setting()))
        conn.put({"stat": "OK"})
    except SlaverThreadError as e:
        tb_message = get_user_friendly_traceback(*e.get_exc())
        conn.put({"stat": "FALSE", "error": string_to_html('\n'.join(tb_message))})
    except Exception:
        tb_message = get_user_friendly_traceback(*sys.exc_info())
        conn.put({"stat": "FALSE", "error": string_to_html('\n'.join(tb_message))})


def run_backtest(*args, callback=None):
    ctx = mp.get_context('spawn')
    q = ctx.Queue()
    p = ctx.Process(target=backtest, args=(q,) + args)
    p.start()
    while True:
        try:
            result = q.get(timeout=10)
            callback(result)
            break
        except Empty:
            continue


class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, *argc, **argkw):
        super(BaseHandler, self).__init__(*argc, **argkw)

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        code = self.get_argument('code', '').replace('\t', '    ')
        name = self.get_argument('name', 'untitled')
        symbols = self.get_argument('symbols', None)
        time_frame = self.get_argument('time_frame', None)
        start_time = self.get_argument('start_time', None)
        end_time = self.get_argument('end_time', None)
        commission = int(self.get_argument('commission', 0))
        slippage = int(self.get_argument('slippage', 0))
        user_id = self.get_argument('user_id', None)
        if user_id:
            self.write('callback(')
            try:
                result = yield tornado.gen.Task(run_backtest, code, user_id, name, [symbols],
                                                time_frame, start_time,
                                                end_time, commission, slippage)
            except TimeoutError:
                self.write({'stat': 'FALSE', 'error': '回测超时'})
                self.finish()
                return
            if result['stat'] == 'OK':
                cache = StrategyPerformanceJsonCache(user_id)
                performance = cache.get_performance()
                output = self.get_output(user_id, name)
                self.write({'stat': 'OK', 'result': performance.yield_curve, 'output': string_to_html(output),
                            'performance': performance.info_on_home_page})
            else:
                output = self.get_output(user_id, name)
                result['output'] = string_to_html(output)
                self.write(result)
            self.write(')')
        self.flush()
        self.finish()

    @staticmethod
    def get_output(user_id, name):
        user_dir = UserDirectory(User(user_id))
        try:
            with open(os.path.join(user_dir.get_temp_dir(), name + '.log'), 'r') as f:
                output = f.read()
                f.close()
        except FileNotFoundError:
            output = ''
        except Exception as e:
            raise e
        return output
