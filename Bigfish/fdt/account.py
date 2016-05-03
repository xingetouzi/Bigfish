import ujson as json
import urllib
import urllib.request

# fdt_url = "http://61.152.93.136:54321"
fdt_url = "http://121.43.71.76:13321"


def post(req_url, data):
    jdata = json.dumps(data)
    req = urllib.request.Request(req_url, jdata.encode(encoding="UTF8"))
    req.add_header('Content-Type', 'application/json')
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode())


class FDTAccount:
    def __init__(self, fdt_id, pwd):
        self.token = None
        self.info = None
        self.fdt_id = fdt_id
        self.pwd = pwd

    def login(self):
        data = {"userId": self.fdt_id, "pwd": self.pwd}
        # url="http://121.43.71.76:13321/Login"
        login_url = fdt_url + "/Login"
        res = post(login_url, data)
        self.info = res
        if res['ok']:
            self.token = res['token']
            return True
        else:
            return False
            # TODO 登录失败的处理

    def market_order(self, order_side, qty, symbol):
        mo_url = fdt_url + "/MarketOrder"
        data = {"orderSide": order_side, "qty": qty, "symbol": symbol, "token": self.token}
        return post(mo_url, data)

    def limit_order(self, order_side, price, qty, symbol):
        lo_url = fdt_url + "/LimitOrder"
        data = {"orderSide": order_side, "price": price, "qty": qty, "symbol": symbol, "token": self.token}
        return post(lo_url, data)

    def order_status(self):
        os_url = fdt_url + "/OrderStatus"
        data = {"token": self.token}
        return post(os_url, data)

    def open_positions(self):
        op_url = fdt_url + "/OpenPositions"
        data = {"token": self.token}
        return post(op_url, data)

    def cancel_order(self):
        co_url = fdt_url + "/CancelOrder"
        data = {"token": self.token}
        return post(co_url, data)


if __name__ == '__main__':
    import time


    def get_id(res):
        return


    def order_status(om, id):
        res = om.order_status()
        for order in res.get('orders', []):
            if order['id'] == id:
                return order


    om = FDTAccount("mb000004296", "Morrisonwudi520")
    url = "http://61.152.93.136:54321/Login"
    print(om.login())
    print(om.info['accounts'])
    res0 = om.market_order("Buy", 100000, "EURUSD")
    buy_id = res0.get('orderId', '')
    print(order_status(om, buy_id))
    print('<P>:%s' % om.open_positions()['openPositions'])
    time.sleep(3)
    res0 = om.market_order("Buy", 100000, "EURUSD")
    buy_id = res0.get('orderId', '')
    print(order_status(om, buy_id))
    print('<P>:%s' % om.open_positions()['openPositions'])
    om.login()
    print(om.info['accounts'])
    time.sleep(60)
    print('<P>:%s' % om.open_positions()['openPositions'])
    om.login()
    print(om.info['accounts'])
    res1 = om.market_order("Sell", 100000, "EURUSD")
    sell_id = res1.get('orderId', '')
    print(order_status(om, sell_id))
    time.sleep(3)
    print('<P>:%s' % om.open_positions()['openPositions'])
    res1 = om.market_order("Sell", 100000, "EURUSD")
    sell_id = res1.get('orderId', '')
    print(order_status(om, sell_id))
    print(om.open_positions())
    om.login()
    print(om.info['accounts'])
    # print(om.order_status())
    # print(om.info)
