import sys
import codecs
import ujson as json
import logging
import os
import traceback
from logging.handlers import RotatingFileHandler
from Bigfish.app.runtime_singal import RuntimeSignal
from Bigfish.models.model import User
from Bigfish.store.directory import UserDirectory


def main():
    code_file = sys.argv[1]
    config_file = sys.argv[2]
    with codecs.open(code_file, "r", "utf-8") as f:
        code = f.read()
        f.close()
    with codecs.open(config_file, "r", "utf-8") as f:
        config = json.loads(f.read())
        f.close()

    def set_handle(logger, user=config.get("user", "non-existent user")):
        path = os.path.join(UserDirectory(User(user)).get_temp_dir(), "runtime.log")
        rt_handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
        rt_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
        rt_handler.setFormatter(formatter)
        logger.addHandler(rt_handler)

    if code:
        signal = RuntimeSignal()
        signal.code = code
        signal.set_config(**config)
        signal.init()
        set_handle(signal.logger)
        signal.start()


if __name__ == '__main__':
    try:
        main()
    except:
        path = os.path.join(UserDirectory.__get_root__(), "runtime.log")
        logger = logging.getLogger("RuntimeScript")
        rt_handler = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5)
        rt_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s %(filename)-20s[line:%(lineno)-3d] %(levelname)-8s %(message)s')
        rt_handler.setFormatter(formatter)
        logger.addHandler(rt_handler)
        logger.warning("\n%s" % traceback.format_exc())
