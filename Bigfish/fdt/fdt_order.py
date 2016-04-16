import json
import urllib
import urllib.request

fdt_url = "http://61.152.93.136:54321"


def post(req_url, data):
    jdata = json.dumps(data)
    req = urllib.request.Request(req_url, jdata.encode(encoding="UTF8"))
    req.add_header('Content-Type', 'application/json')
    response = urllib.request.urlopen(req)
    return response.read()


class OrderManager:
    def __init__(self):
        self.token = None

    def login(self, fdt_id, pwd):
        data = {"userId": fdt_id, "pwd": pwd}
        # url="http://121.43.71.76:13321/Login"
        login_url = fdt_url + "/Login"
        res = json.loads(post(login_url, data).decode())
        if res["ok"]:
            self.token = res["token"]
            return True, res["token"]
        else:
            return False, res["message"]

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
    om = OrderManager()
    url = "http://61.152.93.136:54321/Login"
    print(om.login("13955133760", "Morrisonwudi520"))

    # print(om.market_order("Buy", 1000, "EURUSD"))
    # print(om.order_status())
    print(om.open_positions())
