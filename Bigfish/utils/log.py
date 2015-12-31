# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 19:07:00 2015

@author: BurdenBear
"""
import os

from contextlib import redirect_stdout
from Bigfish.store.directory import UserDirectory


class Printer:
    def __init__(self, user, name):
        self.__user = user
        self.__name = name
        self.__gene_instance = None
        self.__stdout_redirector = None

    #用于重载的方法
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


class FilePrinter(Printer):
    def __init__(self, user, name):
        super(FilePrinter, self).__init__(user, name)
        self.__file_path = os.path.join(UserDirectory(user).get_temp_dir(), name + '.log')
        self.__file = None

    def _get_redirector(self):
        return redirect_stdout(self.__file)

    def start(self):
        self.__file = open(self.__file_path, 'w')
        super(FilePrinter, self).start()

    def stop(self):
        super(FilePrinter, self).stop()
        self.__file.close()