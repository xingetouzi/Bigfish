# -*- coding: utf-8 -*-
"""
Created on Mon Nov  2 19:07:00 2015

@author: BurdenBear
"""
import os

from contextlib import redirect_stdout
from Bigfish.store.directory import UserDirectory

class Printer():
    def __init__(self, user, name):
        self.__user = user
        self.__name = name
        self.__gene_instance = None

    def _get_redirector(self, user, name):
        raise NotImplementedError

    def __print_generator(self, user, name):
        with self.__stdout_redirector:
            while True:
                args = yield
                print(args)

    def get_print(self):
        send = self.__print_generator.send
        def wrapper(*args):
            send(args)
        return wrapper

    def start(self):
        self.__stdout_redirector = self._get_redirector()
        self.__gene_instance = self.__print_generator()

    def stop(self):
        self.__gene_instance.stop()
        self.__gene_instance = None

class FilePrinter(Printer):
    def __init__(self,user,name):
        super(FilePrinter, self).__init__(user, name)
        self.__file_path = os.path.join(UserDirectory(user).get_temp_dir(), name+'.log')

    def _get_redirector(self):
        return redirect_stdout(self.__file)

    def start(self):
        self.__file = open(self.__file_path,'w')
        self.__stdout_redirector = self._get_redirector()
        self.__gene_instance = self.__print_generator()

    def stop(self):
        self.__gene_instance.stop()
        self.__gene_instance = None
        self.__file.close()

