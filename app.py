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
            # 포지션 보유 여부 판단: open, size 등 상황에 맞게!
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
    side = 'open_long' if signal == 'buy' else 'open_short'

    if has_open_position(SYMBOL):
        return {'error': 'Already in position'}

    timestamp = str(int(time.time() * 1000))
    method = 'POST'
    request_path = '/api/v2/mix/order/place-order'
    body = {
        'symbol': SYMBOL,
        'marginCoin': MARGIN_COIN,
        'size': size,
        'side': side,
        'orderType': 'market',
        'leverage': leverage,
        'marginMode': margin_mode,
        'clientOid': f'entry_{timestamp}',
        'productType': PRODUCT_TYPE
    }
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
