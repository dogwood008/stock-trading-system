import kabusapi
import os
import pprint
pp = pprint.PrettyPrinter()

HOST = os.environ.get('KABU_S_HOST')
PASSWORD = os.environ.get('KABU_S_PASSWORD')
PORT = os.environ.get('KABU_S_API_PORT')
api = kabusapi.Context(HOST, PORT, PASSWORD)

def register_stock():
  # 銘柄登録
  data = {
      "Symbols": [
          {"Symbol": 7974, "Exchange": 1, },
      ]
  }
  response = api.register(**data)
  pp.pprint(response)
register_stock()

exit()
# ---

print('----------------')
@api.websocket
def recieve(msg):
    # ここで処理を行う msgはdict形式である。
    print("{} / {} {} {}".format(
        msg,
        msg['Symbol'],
        msg['SymbolName'],
        msg['CurrentPrice'],
    ))

try:
  # 受信開始
  api.websocket.run()
except KeyboardInterrupt:
  print('Close websocket')
  api.websocket.loop.close()
  #api.websocket.close()
