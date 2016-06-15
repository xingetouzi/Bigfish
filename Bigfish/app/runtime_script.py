import sys
import codecs
import logging
import os
import traceback
from logging.handlers import RotatingFileHandler


def main():
    # code_file = sys.argv[1]
    # config_file = sys.argv[2]
    # with codecs.open(code_file, "r", "utf-8") as f:
    #     code = f.read()
    #     f.close()
    # with codecs.open(config_file, "r", "utf-8") as f:
    #     config = json.loads(f.read())
    #     f.close()
    userid = sys.argv[1]
    rd = runtime_data(userid)
    config = rd.get_config()
    config['symbols'] = [config['symbols']]
    code = rd.get_code()

    def set_handle(logger, user=config.get("user", "non-existent user")):
        path = os.path.join(UserDirectory(User(user)).get_temp_dir(), "runtime.log")
        rt_handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
        rt_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
        rt_handler.setFormatter(formatter)
        logger.addHandler(rt_handler)

    if code:
        if config.get("start_time", None) is not None:
            signal = TracebackSignal()
        else:
            signal = RuntimeSignal()
        signal.code = code
        signal.set_config(BfConfig(**config))
        signal.init()
        set_handle(signal.logger)
        signal.start()


if __name__ == '__main__':
    try:
        from Bigfish.store.directory import UserDirectory
        import ujson as json
        from Bigfish.app.runtime_singal import RuntimeSignal
        from Bigfish.app.tracebacksignal import TracebackSignal
        from Bigfish.models.model import User
        from Bigfish.models.config import BfConfig
        from Bigfish.web_utils.runtime_data_man import runtime_data
        main()
    except:
        if len(sys.argv) > 1:
            user_id = sys.argv[1]
            path = os.path.join(UserDirectory(User(user_id)).get_temp_dir(), "runtime.log")
        else:
            path = os.path.join(UserDirectory.__get_root__(), "runtime.log")
        logger = logging.getLogger("RuntimeScript")
        rt_handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
        rt_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
        rt_handler.setFormatter(formatter)
        logger.addHandler(rt_handler)
        logger.warning("\n%s" % traceback.format_exc())
