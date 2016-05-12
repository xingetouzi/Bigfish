from Bigfish.app.runtime_singal import RuntimeSignal

DEBUG = False

if __name__ == '__main__':
    import sys
    import codecs
    import ujson as json
    import logging
    import os

    if DEBUG:
        file_name = "testcode9.py"
        config = dict(
            user='10032',
            name=file_name.split(".")[0],
            account="mb000004296",
            password="Morrisonwudi520",
            symbols=["EURUSD"],
            time_frame="M1",
        )
        file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test', file_name)


        def set_handle(logger):
            console = logging.StreamHandler(stream=sys.stdout)
            console.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logger.addHandler(console)
            return console

    else:
        config = json.loads(sys.argv[1])
        file = config.pop('file', '')
        log_dir = config.pop('log_dir', '/root/BigfishLog')

        from logging.handlers import RotatingFileHandler


        def set_handle(logger, root=log_dir, user=config.get("user", "non-existent user")):
            path = os.path.join(root, user + ".log")
            rt_handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
            rt_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
            rt_handler.setFormatter(formatter)
            logger.addHandler(rt_handler)
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
        signal.init()
        set_handle(signal.logger)
        signal.start()
