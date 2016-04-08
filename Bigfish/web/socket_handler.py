import urllib

import tornado.websocket


class SocketHandler(tornado.websocket.WebSocketHandler):
    # clients = set()

    def open(self):
        print("Open")
        self.write_message('Welcome to WebSocket')
        # SocketHandler.clients.add(self)

    def on_message(self, message):
        print(message)
        if message == "1":
            import time
            while True:
                print("a")
                time.sleep(1)


    def on_close(self):
        # SocketHandler.clients.remove(self)
        print("Close")

    def check_origin(self, origin):
        # parsed_origin = urllib.parse.urlparse(origin)
        # return parsed_origin.netloc.endswith(".fxdayu.com")
        return True
