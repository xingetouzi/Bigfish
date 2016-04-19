#!/usr/bin/env python
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import print_function

from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
import json
from Bigfish.models.quote import Tick


tick_event = dict()
# tick_period = dict()
tick_peroid = 10  # 每隔10秒连接一次


def register_event(symbol, handle):
    if not ("/" in symbol):
        symbol = symbol[:3] + "/" + symbol[3:]
    tick_event[symbol] = handle


def unregister_event(symbol):
    del tick_event[symbol]


class EchoClient(LineReceiver):
    end = "Bye-bye!"
    delimiter = b"\n"

    def __init__(self):
        self.__tict_bar = dict()

    def connectionMade(self):
        self.sendLine(("{\"messageType\":5, \"username\":\"%s\", \"password\":\"%s\"}" % ("Admin", "Xinger520")).encode("utf-8"))
        self.sendLine("{\"messageType\":2}".encode("utf-8"))
        # self.sendLine(self.end)

    def lineReceived(self, line):
        print("receive:", line)
        pd = json.loads(line.decode("utf-8"))
        if "instrument" in pd:  # 忽略非行情消息(如登录消息,是否登录成功)
            symbol = pd["instrument"]
            if symbol in tick_event:  # 如果注册了这个品种的数据事件
                if symbol in self.__tict_bar:
                    bar = self.__tict_bar[symbol]
                    if pd["ctime"] - bar["ctime"] >= tick_peroid:
                        tick = Tick(symbol)
                        tick.highPrice = bar["high"]
                        tick.lowPrice = bar["low"]
                        tick.openPrice = bar["open"]
                        tick.lastPrice = bar["close"]
                        tick.time = pd["ctime"]
                        tick.time_msc = tick_peroid
                        tick_event[symbol](tick)
                        del self.__tict_bar[symbol]
                    else:
                        price = (pd["ask"] + pd["bid"]) / 2
                        bar["close"] = price
                        if price < bar["low"]:
                            bar["low"] = price
                        if price > bar["high"]:
                            bar["high"] = price
                else:
                    price = (pd["ask"] + pd["bid"]) / 2
                    self.__tict_bar[symbol] = {"ctime": pd["ctime"], "open": price, "low": price, "high": price, "close": price}

        if line == self.end:
            self.transport.loseConnection()


class EchoClientFactory(ClientFactory):
    protocol = EchoClient

    def __init__(self):
        self.done = Deferred()

    def clientConnectionFailed(self, connector, reason):
        print('connection failed:', reason.getErrorMessage())
        self.done.errback(reason)

    def clientConnectionLost(self, connector, reason):
        print('connection lost:', reason.getErrorMessage())
        self.done.callback(None)


class Runnable:

    def __init__(self):
        self.factory = EchoClientFactory()

    def connect(self, reactor):
        # factory = EchoClientFactory()
        reactor.connectTCP('112.74.195.144', 9123, self.factory)
        return self.factory.done

    def start(self):
        task.react(self.connect)

    def stop(self):
        self.factory.stopFactory()

if __name__ == '__main__':
    def handle(tick):
        print(tick)
    register_event("EUR/USD", handle)
    runnable = Runnable()
    # task.react(runnable.start)
    runnable.start()