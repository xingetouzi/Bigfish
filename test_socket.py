# -*- coding:utf-8 -*-
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientCreator


class Greeter(Protocol):
    def sendMessage(self, msg):
        self.transport.write(msg.encode('utf-8'))

    def dataReceived(self, data):
        print(data.decode("utf-8"))


def gotProtocol(p):
    p.sendMessage("{\"opt\":\"GETDATA\", \"query_id\":\"test4\", \"symbols\":[\"EURUSD\"], \"tf\":\"M15\", \"start_time\":\"2015-11-03\",\"end_time\":\"2015-11-04\",\"size\":90}\r\n")
    # reactor.callLater(1, p.sendMessage, u"This is sent in a second\r\n")
    # reactor.callLater(2, p.transport.loseConnection)


if __name__ == '__main__':
    c = ClientCreator(reactor, Greeter)
    c.connectTCP("127.0.0.1", 10011).addCallback(gotProtocol)
    reactor.run()