import ujson as json
import pycurl
import urllib.request
import urllib.parse
from urllib.error import HTTPError
from http.client import IncompleteRead, HTTPConnection
from functools import wraps
from io import BytesIO
from Bigfish.utils.log import LoggerInterface

reconnect_times = 3
retry_times = 3


class HTTP10Connection(HTTPConnection):
    _http_vsn = 10
    _http_vsn_str = "HTTP/1.0"


class HTTP10Handler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(HTTP10Connection, req)


def post_with_urllib(req_url, data):
    j_data = json.dumps(data)
    req = urllib.request.Request(req_url, j_data.encode(encoding="UTF8"))
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as res:
        content = b""
        while True:
            try:
                content += res.read()
                break
            except IncompleteRead as e:
                content += e.partial
    return json.loads(content.decode())


def post_with_curl(req_url, data):
    def get_message(header):
        return ' '.join(header.split('\r\n')[0].split(' ')[2:])

    j_data = json.dumps(data)
    buffer = BytesIO()
    header = BytesIO()
    curl = pycurl.Curl()
    # curl.setopt(pycurl.VERBOSE, 1)
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.HTTPHEADER, ["Content-Type: application/json"])
    curl.setopt(pycurl.URL, req_url)
    curl.setopt(pycurl.POSTFIELDS, j_data)
    curl.setopt(pycurl.WRITEDATA, buffer)
    curl.setopt(pycurl.HEADERFUNCTION, header.write)
    curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    curl.setopt(pycurl.SSL_VERIFYHOST, 0)
    # curl.setopt(pycurl.VERBOSE, 1)
    # curl.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_0)
    curl.perform()
    res_code = curl.getinfo(pycurl.RESPONSE_CODE)
    for field in ["NAMELOOKUP_TIME", "CONNECT_TIME", "PRETRANSFER_TIME", "STARTTRANSFER_TIME", "TOTAL_TIME",
                  "REDIRECT_TIME"]:
        print(field, ": ", curl.getinfo(getattr(pycurl, field)))
    curl.close()
    msg = get_message(header.getvalue().decode())
    if res_code // 100 > 3:
        error = HTTPError(None, res_code, msg, None, None)
        raise error
    else:
        content = buffer.getvalue().decode()
        res = json.loads(content)
        return res


def post_with_http(req_url, data):
    host, req_url = (lambda x: (x[1].replace('/', ''), x[2]))(req_url.split(':'))
    port, url = (lambda x: (int(x[0]), x[1]))(req_url.split('/'))
    j_data = json.dumps(data)
    header = {'Content-Type': 'application/json'}
    conn = HTTPConnection(host, port)
    conn._http_vsn = 10
    conn._http_vsn_str = 'HTTP/1.0'
    conn.request("POST", '/' + url, j_data, header)
    res = conn.getresponse()
    result = res.read()
    conn.close()
    return json.loads(result.decode())


def post_with_urllib_http10(req_url, data):
    opener = urllib.request.build_opener(HTTP10Handler)
    j_data = json.dumps(data)
    req = urllib.request.Request(req_url, j_data.encode(encoding="UTF8"))
    req.add_header('Content-Type', 'application/json')
    with opener.open(req) as res:
        content = res.read()
        print(res.version)
    return json.loads(content.decode())


post = post_with_curl


# TODO pycurl.error
def reconnect(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        connect_count = 0
        need_login = False
        while connect_count <= reconnect_times:
            try:
                if need_login:
                    self.login()
                    need_login = False
                return func(self, *args, **kwargs)
            except HTTPError as e:
                if e.code == 400:
                    self.logger.warning("Login failed, in %s, message:%s" % (
                        func.__name__, '|'.join([str(e.code), e.reason, e.msg])))
                    need_login = True
                    connect_count += 1
                else:
                    return {"ok": False, "message": "%s %s" % (type(e), e.msg)}
            except pycurl.error as e:
                return {"ok": False, "message": "%s %s" % (type(e), str(e.args))}
        return {"ok": False, "message": "Login Failed"}

    return wrapper


def retry(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        retry_count = 0
        while retry_count <= retry_times:
            res = func(self, *args, **kwargs)
            if not res['ok']:
                self.logger.warning("Connection failed, in %s, message:%s" % (func.__name__, res.get("message", "")))
                retry_count += 1
            else:
                return res
        return {"ok": False, "message": "Connection failed"}

    return wrapper


class FDTAccount(LoggerInterface):
    url = "http://121.43.71.76:13321"

    def __init__(self, fdt_id, pwd, parent=None):
        LoggerInterface.__init__(self, parent=parent)
        self.token = None
        self.info = None
        self.fdt_id = fdt_id
        self.pwd = pwd

    def login(self):
        try:
            data = {"userId": self.fdt_id, "pwd": self.pwd}
            login_url = self.url + "/Login"
            res = post(login_url, data)
            self.info = res
            if res['ok']:
                self.token = res['token']
                return True
            else:
                return False
                # TODO 登录失败的处理
        except HTTPError as e:
            self.info = {'ok': False, 'message': e.msg}
            return False

    @retry
    @reconnect
    def market_order(self, order_side, qty, symbol):
        mo_url = self.url + "/MarketOrder"
        data = {"orderSide": order_side, "qty": qty, "symbol": symbol, "token": self.token}
        return post(mo_url, data)

    @retry
    @reconnect
    def limit_order(self, order_side, price, qty, symbol):
        lo_url = self.url + "/LimitOrder"
        data = {"orderSide": order_side, "price": price, "qty": qty, "symbol": symbol, "token": self.token}
        return post(lo_url, data)

    @retry
    @reconnect
    def order_status(self, order_id):
        os_url = self.url + "/OrderStatus"
        data = {"token": self.token, "orderId": order_id}
        return post(os_url, data)

    @retry
    @reconnect
    def open_positions(self):
        op_url = self.url + "/OpenPositions"
        data = {"token": self.token}
        return post(op_url, data)

    @retry
    @reconnect
    def account_status(self):
        as_url = self.url + "/AccountStatus"
        data = {"token": self.token}
        return post(as_url, data)

    @retry
    @reconnect
    def cancel_order(self):
        co_url = self.url + "/CancelOrder"
        data = {"token": self.token}
        return post(co_url, data)


class FDTRealAccount(FDTAccount):
    url = "https://quantbowl.investmaster.cn:443"

if __name__ == '__main__':
    import time


    def get_id(res):
        return


    def order_status(om, id):
        return om.order_status(id)


    def timeit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            st = time.time()
            result = func()
            print(time.time() - st)
            return result

        return wrapper
    om = FDTAccount("mb000004296", "Morrisonwudi520")
    om = FDTRealAccount("hztest2", "123456")
    st = time.time()
    print(om.login())
    print(time.time() - st)
    # print(om.info)
    st = time.time()
    print(om.account_status())
    print(time.time() - st)
    st = time.time()
    print(om.open_positions())
    print(time.time() - st)
    # time.sleep(20)
    # res0 = om.market_order("Buy", 100000, "EURUSD")
    # buy_id = res0.get('orderId', '')
    # print(order_status(om, buy_id))
    # print('<P>:%s' % om.open_positions()['openPositions'])
    # time.sleep(3)
    # res0 = om.market_order("Buy", 100000, "EURUSD")
    # buy_id = res0.get('orderId', '')
    # print(order_status(om, buy_id))
    # print('<P>:%s' % om.open_positions()['openPositions'])
    # om.login()
    # print(om.info['accounts'])
    # time.sleep(10)
    # print('<P>:%s' % om.open_positions()['openPositions'])
    # om.login()
    # print(om.info['accounts'])
    # res1 = om.market_order("Sell", 100000, "EURUSD")
    # sell_id = res1.get('orderId', '')
    # print(order_status(om, sell_id))
    # time.sleep(3)
    # print('<P>:%s' % om.open_positions()['openPositions'])
    # res1 = om.market_order("Sell", 100000, "EURUSD")
    # sell_id = res1.get('orderId', '')
    # print(order_status(om, sell_id))
    # print(om.open_positions())
    # om.login()
    # print(om.info['accounts'])
    # # print(om.order_status())
    # # print(om.info)
