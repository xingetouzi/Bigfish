import sys
import getopt
import codecs
import operator
import time
import logging
import pandas as pd
import json
import traceback
from multiprocessing import Pool

from Bigfish.app.backtest import Backtesting


def run_backest(kwargs):
    try:
        file = kwargs.pop('code')
        with codecs.open(file, 'r', 'utf-8') as f:
            code = f.read()
            f.close()
        user = '10032'
        parameters = kwargs.pop('paras')
        start_time = kwargs.pop('start_time')
        end_time = kwargs.pop('end_time')
        symbol = kwargs.pop('symbol')
        time_frame = kwargs.pop('time_frame')
        log = kwargs.pop('log')
        backtest = Backtesting(user, 'test', code, [symbol], time_frame, start_time, end_time)
        if log:
            handle = logging.FileHandler(log, encoding='utf-8')
            logger = logging.getLogger('backtest')
            logger.addHandler(handle)
            logger.setLevel(logging.INFO)
            backtest.set_logger(logger)
        backtest.start(paras=parameters)
        performance = backtest.get_performance()
        result = performance.optimize_info
        temp = pd.Series({signal + '.' + k: v for signal, paras in parameters.items() for k, v in paras.items()})
        result = pd.concat([temp, result])
        backtest.log(backtest.time("绩效计算完毕，耗时:{0}"), logging.INFO)
        return result
    except Exception as e:
        print("Error: {0}, Para: {1}".format(e, parameters))
        print(traceback.format_exc())
        return None


def get_para(file, out=None):
    with codecs.open(file, 'r', 'utf-8') as f:
        code = f.read()
        f.close()
    user = '10032'
    backtest = Backtesting(user, 'test', code, ['EURUSD'], 'M30', '2015-01-01', '2015-01-02')
    backtest.init()
    result = backtest.get_parameters()
    if out:
        with codecs.open(out, 'w', 'utf-8') as f:
            f.write(json.dumps(result))
        f.close()
    else:
        print(json.dumps(result))


def read_para(file):
    if file:
        with codecs.open(file, 'r', 'utf-8') as f:
            result = json.loads(f.read())
            f.close()
        return result

    else:
        n = 8
        m = 8
        t = 50
        s = 100
        return [{'handle': dict(TakeProfit=t - n // 2 + i, StopLoss=s - m // 2 + j)} for i in range(n) for j in
                range(m)]


if __name__ == '__main__':
    process = 16
    code = r"E:\Users\BurdenBear\Documents\Github\Bigfish\Bigfish\test\testcode9.py"
    input_ = None
    output = None
    start_time = '2015-01-01'
    end_time = '2015-03-01'
    target = '净利($)'
    symbol = "EURUSD"
    time_frame = "M15"
    cal = True
    log = None
    opts, args = getopt.getopt(sys.argv[1:], "S:T:l:c:n:i:o:s:e:t:g")
    for op, value in opts:
        if op == '-n':
            process = value
        elif op == '-c':
            code = value
        elif op == '-i':
            input_ = value
        elif op == '-o':
            output = value
        elif op == '-S':
            symbol = value
        elif op == '-T':
            time_frame = value
        elif op == '-s':
            start_time = value.replace('/', ' ')
        elif op == '-e':
            end_time = value.replace('/', ' ')
        elif op == '-t':
            target = value
        elif op == '-l':
            log = value
        elif op == '-g':
            cal = False
    # print(run_backest(**{'handle': dict(TakeProfit=T, StopLoss=S)}))
    print(start_time, end_time)
    if cal:
        t1 = time.time()
        p = Pool(processes=process)
        result = []
        paras = read_para(input_)
        print(paras)
        kwds = [dict(paras=para,
                     code=code,
                     output=output,
                     start_time=start_time,
                     end_time=end_time,
                     symbol=symbol,
                     time_frame=time_frame,
                     log=log,
                     ) for para in paras]
        task = p.map_async(run_backest, kwds)
        # for para in paras:
        #     result.append(
        #         p.apply_async(func=run_backest,
        #                       kwds=dict(paras=para,
        #                                 code=code,
        #                                 output=output,
        #                                 start_time=start_time,
        #                                 end_time=end_time,
        #                                 )
        #                       )
        #
        #     )
        t2 = time.time()
        print('进程池创建完毕，大小:<%s>，总耗时:%s seconds' % (process, t2 - t1))
        # prints "[42, None, 'hello']"
        # p.join()
        # temp = list(map(operator.methodcaller('get'), result))
        temp = task.get(timeout=None)
        p.close()
        # temp = list(map(lambda x: pd.Series(x), temp))
        # print(temp)
        temp = [item for item in temp if item is not None]
        outputs = pd.DataFrame(temp)
        if not outputs.empty:
            outputs = outputs.sort_values(target, ascending=False).iloc[:50]
        if output:
            with codecs.open(output, 'w', 'utf-8') as f:
                outputs.to_csv(f, index=False)
                f.close()
        else:
            print(outputs)
        t3 = time.time()
        print('运行完毕，总耗时:%s seconds' % (t3 - t1))
    else:
        get_para(code, out=output)
