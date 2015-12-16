# -*- coding: utf-8 -*-

from datetime import *
import time
import socket
import json
import struct

SERVER_HOST = '112.74.195.144'
PORT = 6666

class DatetimeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        else:
            return json.JSONEncoder.default(self, obj)
            
def send(channel, *args):
    buffer_ = json.dumps(args, separators= (',', ':'), cls= DatetimeJsonEncoder)
    value = socket.htonl(len(buffer_))
    size = struct.pack('L', value)
    channel.send(size)
    channel.send(buffer_.encode())

def receive(channel):
    size = struct.calcsize('L')
    size = channel.recv(size)
    try:
        size = socket.ntohl(struct.unpack('L', size)[0])
    except struct.error as e:
        print(e)
        return None
    buf = ''
    while len(buf) < size:
        buf += channel.recv(size - len(buf)).decode()
    return json.loads(buf)[0]

def getBarData(symbol, startTime, endTime, barType, host= SERVER_HOST, port= PORT):
    request = {}    
    request['symbol'] = symbol
    request['start_time'] = startTime
    request['end_time'] = endTime
    request['bar_type'] = barType
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    send(sock, request)
    try:
        return receive(sock)
    except Exception as e:
        return e
        
if __name__ == '__main__':
    symbol = '000002.SZ'
    startTime = datetime(2015,8,15,9,00,00)
    endTime = datetime.fromtimestamp(int(time.time()))  
    data = getBarData(symbol,startTime,endTime,'1')
    print (data)