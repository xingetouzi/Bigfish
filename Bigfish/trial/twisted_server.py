import time
import json
from twisted.internet.protocol import ClientCreator, Protocol
from twisted.internet import reactor
from Bigfish.core import AsyncDataGenerator
from Bigfish.models.quote import Bar
from threading import Thread

HOST = '192.168.0.106'
PORT = 10011

"""
测试用,实际Bigfish并未用到
"""
class DataFetcher(Protocol):
    delimiter = b'\r\n'
    _buffer = b''

    def __init__(self, *args, **kwargs):
        super(DataFetcher, self).__init__(*args, **kwargs)
        self.__message = None
        self.__callback = {}
        self.__finish_callback = {}

    def setMessage(self, msg):
        self.__message = msg

    def addCallback(self, key, callback):
        self.__callback[key] = callback

    def dataReceived(self, data):
        try:
            self._buffer += data
            while True:
                index = self._buffer.find(self.delimiter)
                if index == -1:
                    break
                block = json.loads(self._buffer[:index].decode())
                self._buffer = self._buffer[index + len(self.delimiter):]
                query_id = block.pop('queryId')
                state = block.pop('stat')
                if state == 'IN_REQ':
                    callback = self.__callback.get(query_id, None)
                    if callback:
                        callback(block.pop('results'))
                elif state == 'END_REQ':
                    self.sendJson({'opt': "GETDATA", 'query_id': query_id})
                elif state == 'END_QUERY':
                    self.__callback.pop(query_id, None)
                    finish_callback = self.__finish_callback.get(query_id, None)
                    if finish_callback:
                        finish_callback()
        except Exception as e:
            raise e

    def sendJson(self, msg):
        self.transport.write(json.dumps(msg).encode() + self.delimiter)

    def subscribe(self, message, callback=None):
        self.__finish_callback[message['query_id']] = callback
        self.sendJson(message)


class TwistAsyncDataGenerator(AsyncDataGenerator):
    @classmethod
    def run_reactor(cls):
        cls._c.connectTCP(HOST, PORT).addCallback(cls.get_protocol)
        cls._thread = Thread(target=cls._reactor.run, name='twisted')
        cls._thread.start()
        cls._is_running = True

    @classmethod
    def stop_reactor(cls):
        cls._reactor.stop()
        cls._thread = None
        cls._is_running = False

    @classmethod
    def get_protocol(cls, p):
        cls._protocol = p

    _c = ClientCreator(reactor, DataFetcher)
    _reactor = reactor
    _thread = None
    _protocol = None  # 用factory可以改成多protocol的模式
    _is_running = False

    def __init__(self, *args, **kwargs):
        super(TwistAsyncDataGenerator, self).__init__(*args, **kwargs)
        if not self._is_running:
            self.run_reactor()
        self.__message = None

    def subscribe_data(self, **options):
        query_id = '.'.join([options['user'].user_id, options['name'], str(time.time())])
        self.__message = {'opt': 'GETDATA', 'query_id': query_id, 'symbols': options['symbols'],
                          'tf': options['time_frame'],
                          'start_time': options['start_time'], 'end_time': options['end_time']}
        self._protocol.addCallback(query_id, self.receive_data)
        self._protocol.subscribe(self.__message, self.stop)

    def get_bars(self, data):
        def dict_to_bar(dict_):
            dict_['time_frame'] = dict_.pop('timeFrame')
            dict_['time'] = dict_.pop('ctime')
            bar = Bar(dict_['symbol'])
            for field in ['open', 'high', 'low', 'close', 'time_frame', 'volume']:
                setattr(bar, field, dict_[field])
            return bar

        return map(data, dict_to_bar)

    def stop(self):
        self.__engine.stop()
        super(TwistAsyncDataGenerator, self).stop()


def getProtocol(p):
    query_id = str(time.time())
    message = {'opt': "GETDATA", 'query_id': query_id, 'symbols': ["EURUSD"], 'tf': "M1",
               'start_time': "2015-11-01", 'end_time': "2015-11-04 ", 'size': 1000}

    def write(data):
        print(len(data))
        print(data)

    p.addCallback(query_id, write)
    p.subscribe(message, reactor.stop)


if __name__ == '__main__':
    c = ClientCreator(reactor, DataFetcher)
    # c = ClientCreator(reactor, LineFetcher)
    c.connectTCP('192.168.0.106', 10011).addCallback(getProtocol)
    reactor.run()
