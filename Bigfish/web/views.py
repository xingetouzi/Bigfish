import os
import pickle
import sys
import datetime
from multiprocessing import Pipe, Process

import tornado.gen
import tornado.ioloop
import tornado.web

from Bigfish.app.backtest import Backtesting
from Bigfish.models.model import User
from Bigfish.performance.performance_cache import StrategyPerformanceCache
from Bigfish.store import UserDirectory
from Bigfish.utils.common import string_to_html
from Bigfish.utils.error import SlaverThreadError, get_user_friendly_traceback


def backtest(conn, *args):
    try:
        user = args[0]
        backtesting = Backtesting(*args)
        backtesting.start()
        performance = backtesting.get_performance()
        cache = StrategyPerformanceCache(user)
        cache.put_object(performance)
        cache.put('setting', pickle.dumps(backtesting.get_setting()))
        conn.write({"stat": "OK"})
    except SlaverThreadError as e:
        tb_message = get_user_friendly_traceback(*e.get_exc())
        conn.write({"stat": "FALSE", "error": string_to_html('\n'.join(tb_message))})
    except Exception:
        tb_message = get_user_friendly_traceback(*sys.exc_info())
        conn.write({"stat": "FALSE", "error": string_to_html('\n'.join(tb_message))})


def run_backtest(*args, callback=None):
    parent_conn, child_conn = Pipe()
    p = Process(target=backtest, args=(child_conn,) + args)
    p.start()
    result = parent_conn.recv()
    p.join()
    callback(result)


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
                result = yield tornado.gen.with_timeout(datetime.timedelta(2),
                                                        tornado.gen.Task(run_backtest, user_id, name, code, [symbols],
                                                                         time_frame, start_time,
                                                                         end_time, commission, slippage),
                                                        tornado.ioloop.IOLoop.instance())
            except TimeoutError:
                self.write({'stat': 'FALSE', 'error': '回测超时'})
                self.finish()
                return
            if result['stat'] == 'OK':
                cache = StrategyPerformanceCache(user_id)
                performance = cache.get_object()
                output = self.get_output(user_id, name)
                self.write({'stat': 'OK', 'result': performance.yield_curve, 'output': string_to_html(output),
                            'performance': performance.info_on_home_page})
            else:
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
