# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 19:07:00 2015

@author: BurdenBear
"""
import os
import logging
from functools import partial

from contextlib import redirect_stdout
from Bigfish.store.directory import UserDirectory
from Bigfish.models.model import User


class LoggerInterface:
    def __init__(self):
        self._logger = None

    def log(self, message, lvl=logging.NOTSET):
        if self._logger:
            self._logger.log(lvl, message)
        else:
            print("[日志优先级{0}]{1}".format(lvl, message))


class Printer:
    def __init__(self, user, name):
        self.__user = user
        self.__name = name

    # 用于重载的方法
    def _get_redirector(self):
        raise NotImplementedError

    def __print_generator(self):
        with self.__stdout_redirector:
            while True:
                args = yield
                print(args)

    def get_print(self):
        send = self.__gene_instance.send

        def wrapper(*args):
            send(args)

        return wrapper

    def start(self):
        self.__stdout_redirector = self._get_redirector()
        self.__gene_instance = self.__print_generator()

    def stop(self):
        if self.__gene_instance is not None:
            self.__gene_instance.close()
            self.__gene_instance = None


class FilePrinter:
    def __init__(self, user, name, engine):
        self.__user = user
        self.__name = name
        self.__engine = engine
        self.__file_path = os.path.join(UserDirectory(User(user)).get_temp_dir(), name + '.log')
        self.__file = None

    def get_path(self):
        return self.__file_path

    def start(self):
        self.__file = open(self.__file_path, 'w+')
        self.__engine.add_file(self.__file)

    def print(self, *args):
        print(*args, file=self.__file)

    def stop(self):
        if self.__file and not self.__file.closed:
            self.__file.flush()
            self.__file.close()
        self.__file = None
