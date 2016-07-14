import sys
import logging
import os
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

log_format = "%(asctime)s %(filename)-20s[line:%(lineno)-4d] %(levelname)-8s %(message)s"
log_root = os.path.join(os.path.expanduser("~"), "BigfishLog")
if not os.path.exists(log_root):
    os.mkdir(log_root)


def namer(name):
    return os.path.join(log_root, os.path.basename(name))


def set_handler(logger_name, user, file, level=logging.DEBUG):
    dir_name = os.path.join(log_root, user)
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
    path = os.path.join(log_root, user, "%s.log" % file)
    logger = logging.getLogger(logger_name)
    rt_handler = TimedRotatingFileHandler(path, when='m', interval=2, backupCount=100, encoding='utf-8')
    rt_handler.setLevel(level)
    rt_handler.namer = namer
    formatter = logging.Formatter(log_format)
    rt_handler.setFormatter(formatter)
    logger.addHandler(rt_handler)


def main():
    userid = sys.argv[1]

    if not userid:
        name = "Total"
    else:
        name = userid
    set_handler("Script", name, name)
    if not userid:
        logging.getLogger("Script").fatal("no userid input!!!")
        return
    try:
        from Bigfish.store.directory import UserDirectory
        import ujson as json
        from Bigfish.app.runtime_singal import RuntimeSignal
        from Bigfish.app.tracebacksignal import TracebackSignal
        from Bigfish.models.model import User
        from Bigfish.models.config import BfConfig
        from Bigfish.web_utils.runtime_data_man import runtime_data
        rd = runtime_data(userid)
        config = rd.get_config()
        config['symbols'] = [config['symbols']]
        code = rd.get_code()
        time_start = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if code:
            if config.get("start_time", None) is not None:
                signal = TracebackSignal()
            else:
                signal = RuntimeSignal()
            signal.code = code
            signal.set_config(BfConfig(**config))
            signal.init()
            set_handler(signal.logger.name, userid, userid + '.' + time_start)
            signal.start()
    except:
        logging.getLogger("Script").error("%s\n" % traceback.format_exc())

if __name__ == '__main__':
    main()
