# -*- coding:utf-8 -*-


def init():
    pass


def handle(length=5):
    boll = Bolling(length)
    if boll is not None:
        print(boll.ma, boll.std, boll.up, boll.down)
