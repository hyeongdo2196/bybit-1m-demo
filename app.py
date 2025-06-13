import time
import hmac
import hashlib
import base64
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'
PASSPHRASE = 'Hyeongdo2196'
BASE_URL = 'https://api.bitget.com'

SYMBOL = 'ETHUSDT'
MARGIN_COIN = 'USDT'
PRODUCT_TYPE = 'UMCBL'   # USDT 무기한

def generate_signature(timestamp, method, request_path, body=None):
    body_str = json.dumps(body) if body else ''
    message = f'{timestamp}{method.upper()}{request_path}{body_str}'
    digest = hmac.new(API_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()

def has_open_position(symbol):
    timestamp = str(int(time.time() * 1000))
    method = 'GET'
    request_path = (
        f'/api/v2/mix/position/single-position'
        f'?symbol={symbol}&marginCoin={MARGIN_COIN}&productType={PRODUCT_TYPE}'
    )
    signature = generate_signature(timestamp, method, request_path)

    headers = {
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': PASSPHRASE,
        'locale': 'en-US'
    }
    url = BASE_URL + request_path
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json().get('data', [])
        if isinstance(data, list) and data:
            position = data[0]
            # 비트겟 포지션 응답에서 size 또는 available, open 등 원하는 값으로 수정 가능
            # 여기서는 size 기준
            return float(position.get('total', 0)) > 0
        else:
            return False
    else:
        app.logger.error(f"Position check failed: {response.status_code} {response.text}")
    return False

def place_order(signal):
    size = "1.5"
    leverage = "20"
    margin_mode = "isolated"

    # 헷지모드일 때 side를 open_long/open_short로!
    if signal == 'buy':
        side = 'open_long'
    elif signal == 'sell':
        side = 'open_short'
    else:
        return {'error': 'Invalid signal'}

    timestamp = str(int(time.time() * 1000))
    method = 'POST'
    request_path = '/api/v2/mix/order/place-order'
    body = {
    'symbol': 'ETHUSDT',
    'marginCoin': 'USDT',
    'size': '1.5',
    'side': 'open_long',            # ← buy신호면 open_long, sell이면 open_short
    'orderType': 'market',
    'leverage': '20',
    'marginMode': 'isolated',
    'positionMode': 'hedge_mode',
    'clientOid': 'entry_168XXXXXXX',
    'productType': 'UMCBL'
}
    # <=== 이 부분 추가
    pprint.pprint(body)
    # <===
    
    signature = generate_signature(timestamp, method, request_path, body)
    headers = {
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': PASSPHRASE,
        'Content-Type': 'application/json',
        'locale': 'en-US'
    }
    url = BASE_URL + request_path
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        return {'message': 'Order placed'}
    else:
        error_info = response.json()
        app.logger.error(f"Order placement failed: {response.status_code} {error_info}")
        return {'error': error_info}

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        app.logger.info(f"Webhook received: {data}")

        signal = data.get('signal')
        if signal not in ['buy', 'sell']:
            return jsonify({'error': 'Invalid signal'}), 400

        result = place_order(signal)
        status_code = 200 if 'message' in result else 500
        return jsonify(result), status_code

    except Exception as e:
        app.logger.error(f"Unhandled error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return 'Bitget Flask Trading Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
