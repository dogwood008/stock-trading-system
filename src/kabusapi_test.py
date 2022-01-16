# coding: utf-8

import pprint
pp = pprint.PrettyPrinter()

import sys
import os
import pathlib
path_to_kabusapi = '../python-kabusapi/src'
sys.path.append(str(pathlib.Path(path_to_kabusapi).resolve()))

import kabusapi
from requests.auth import HTTPBasicAuth

HOST = os.environ.get('KABU_S_HOST')
PASSWORD = os.environ.get('KABU_S_PASSWORD')
PORT = os.environ.get('KABU_S_PORT')
USE_TLS = os.environ.get('KABU_S_TLS') == 'true'
BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PW = os.environ.get('BASIC_AUTH_PW')

if BASIC_AUTH_USER:
  auth = HTTPBasicAuth(BASIC_AUTH_USER, BASIC_AUTH_PW)
else:
  auth = None

api = kabusapi.Context(HOST, PORT, PASSWORD,
  auth=auth,
  tls=USE_TLS,
)

def register_stock():
  # 銘柄登録
  data = {
      "Symbols": [
          {"Symbol": 7974, "Exchange": 1, },
      ]
  }
  response = api.register(**data)
  pp.pprint(response)
#register_stock()

# exit()
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
