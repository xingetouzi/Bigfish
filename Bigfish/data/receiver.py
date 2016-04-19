from __future__ import print_function

from twisted.internet import reactor
from twisted.internet.defer import Deferred
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
import json
from Bigfish.models.quote import Tick

# tick_period = dict()

tick_period = 10  # 每隔10秒连接一次


class DataClient(LineReceiver):
    end = "Bye-bye!"
    delimiter = b"\n"

    def __init__(self):
        self.__tict_bar = dict()
        self.factory = None

    @property
    def _tick_event(self):
        return self.factory._tick_event

    def connectionMade(self):
        self.sendLine(
            ("{\"messageType\":5, \"username\":\"%s\", \"password\":\"%s\"}" % ("Admin", "Xinger520")).encode("utf-8"))
        self.sendLine("{\"messageType\":2}".encode("utf-8"))
        # self.sendLine(self.end)

    def lineReceived(self, line):
        # print("receive:", line)
        pd = json.loads(line.decode("utf-8"))
        if "instrument" in pd:  # 忽略非行情消息(如登录消息,是否登录成功)
            symbol = pd["instrument"]
            if symbol in self._tick_event:  # 如果注册了这个品种的数据事件
                if symbol in self.__tict_bar:
                    print(pd)
                    bar = self.__tict_bar[symbol]
                    if pd["ctime"] - bar["start"] >= tick_period:
                        tick = Tick(symbol)
                        tick.highPrice = bar["high"]
                        tick.lowPrice = bar["low"]
                        tick.openPrice = bar["open"]
                        tick.lastPrice = bar["close"]
                        tick.time = bar["ctime"]
                        self._tick_event[symbol](tick)
                        del self.__tict_bar[symbol]
                        price = (pd["ask"] + pd["bid"]) / 2
                        self.__tict_bar[symbol] = {"start": bar["ctime"] +
                                                           (pd["ctime"] - bar["ctime"]) // tick_period * tick_period,
                                                  "ctime": pd["ctime"], "open": price, "low": price,
                                                  "high": price, "close": price}
                    else:
                        price = (pd["ask"] + pd["bid"]) / 2
                        bar["close"] = price
                        bar["ctime"] = pd["ctime"]
                        if price < bar["low"]:
                            bar["low"] = price
                        if price > bar["high"]:
                            bar["high"] = price
                else:
                    price = (pd["ask"] + pd["bid"]) / 2
                    self.__tict_bar[symbol] = {"start": pd["ctime"], "ctime": pd["ctime"], "open": price, "low": price,
                                              "high": price, "close": price}

        if line == self.end:
            self.transport.loseConnection()


class DataClientFactory(ClientFactory):
    protocol = DataClient

    def __init__(self):
        self.done = Deferred()
        self._tick_event = dict()

    def clientConnectionFailed(self, connector, reason):
        print('connection failed:', reason.getErrorMessage())
        self.done.errback(reason)

    def clientConnectionLost(self, connector, reason):
        print('connection lost:', reason.getErrorMessage())
        self.done.callback(None)

    def register_event(self, symbol, handle):
        if not ("/" in symbol):
            symbol = symbol[:3] + "/" + symbol[3:]
        self._tick_event[symbol] = handle

    def unregister_event(self, symbol):
        del self._tick_event[symbol]


class TickDataReceiver:
    def __init__(self):
        self.factory = DataClientFactory()

    def start(self):
        reactor.connectTCP('112.74.195.144', 9123, self.factory)
        reactor.run(installSignalHandlers=0)
        return self.factory.done

    def stop(self):
        self.factory.stopFactory()
        reactor.stop()

    def register_event(self, symbol, handle):
        self.factory.register_event(symbol, handle)

    def unregister_event(self, symbol):
        self.factory.unregister_event(symbol)


if __name__ == '__main__':
    import time
    import threading


    def handle(tick):
        print(tick.lastPrice, tick.time)


    runnable = TickDataReceiver()
    runnable.register_event("EUR/USD", handle)
    thread = threading.Thread(target=runnable.start)
    thread.start()
    time.sleep(10)
    thread.join()
