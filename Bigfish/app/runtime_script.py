from Bigfish.app.runtime_singal import RuntimeSignal

DEBUG = False

if __name__ == '__main__':
    import sys
    import codecs
    import ujson as json

    if DEBUG:
        user = '10032'
        code = r"E:\Users\BurdenBear\Documents\Github\Bigfish\Bigfish\test\testcode9.py"
        symbol = "EURUSD"
        time_frame = "M15"
    else:
        config = json.loads(sys.argv[1])
        file = config.pop('file', '')
        try:
            with codecs.open(file, 'r', 'utf-8') as f:
                code = f.read()
                f.close()
        except FileNotFoundError:
            code = None
        if code:
            signal = RuntimeSignal()
            signal.code = code
            signal.set_config(**config)
            # print(backtest.progress)
            signal.start()
