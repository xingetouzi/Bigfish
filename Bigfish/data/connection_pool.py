import socket
import json
from socketpool import ConnectionPool, TcpConnector
import time

HOST = '192.168.0.106'
PORT = 10010
SIZE = 1024
POOL = ConnectionPool(factory=TcpConnector, backend="thread", timeout=10)

"""
测试用,实际Bigfish并未用到
"""
def socket_test():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect((HOST, PORT))
    query_id = time.time()
    message = {'opt': "GETDATA", 'query_id': query_id, 'symbols': ["XAUUSD"], 'tf': "M1", 'start_time': "2015-11-03",
               'end_time': "2015-11-04", 'size': 90}
    try:
        data = {query_id: []}
        times = 0
        while True:
            block = ''.encode()
            sock.send((json.dumps(message) + '\r\n').encode('utf-8'))
            while True:
                temp = sock.recv(SIZE)
                print(len(temp))
                if not len(temp):
                    break
                else:
                    block += temp
                    if temp.endswith('\n'.encode()):
                        break
            if block == '\n'.encode():
                break
            times += 1
            print('times<%s>:%s' %(times, len(json.loads(block.decode())[query_id])))
            data[query_id].extend(json.loads(block.decode()))
    except Exception as e:
        print('error:', e)
    finally:
        sock.close()
    print(data)


def connection_test(pool):
    message = {'opt': "GETDATA", 'query_id': time.time(), 'symbols': ["XAUUSD"], 'tf': "M1", 'start_time': "2015-11-03",
               'end_time': "2015-11-04", 'size': 90}
    options = {'host': HOST, 'port': PORT}
    with pool.connection(**options) as conn:
        data = None
        try:
            conn.send((json.dumps(message) + '\r\n').encode('utf-8'))
            while True:
                temp = conn.recv(SIZE)
                print(len(temp))
                if len(temp) == 0:
                    print(123)
                    break
                else:
                    print(len(temp))
                    if data is None:
                        data = temp
                    else:
                        data += temp
        except Exception as e:
            print('error:', e)
        print(json.loads(data.decode('utf-8')))
    print('Done')


if __name__ == '__main__':
    socket_test()
    connection_test(POOL)
    options = {'host': HOST, 'port': PORT}
    message = {'opt': "GETDATA", 'query_id': time.time(), 'symbols': ["XAUUSD"], 'tf': "M1", 'start_time': "2015-11-03",
               'end_time': "2015-11-04", 'size': 90}
    pool = POOL
    times = 0
    with pool.connection(**options) as conn:
        while True:
            try:
                data = None
                conn.send((json.dumps(message) + '\r\n').encode('utf-8'))
                print('nima')
                while True:
                    print(';')
                    temp = conn.recv(SIZE)
                    print(1)
                    if not temp:
                        break
                    else:
                        if temp is None:
                            data = temp
                        else:
                            data += temp
            except Exception as e:
                print('error:', e)
                break
            if data is None:
                break
            else:
                times += 1
                print('receive in time<%s>:\n%s' % (times, data.decode('utf-8')))
    print('Done')
