import time
import hmac
import hashlib
import base64
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 비트겟 API 정보
API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'
PASSPHRASE = 'Hyeongdo2196'
BASE_URL = 'https://api.bitget.com'

# 서명 생성 함수 (v2 방식)
def generate_signature(timestamp, method, request_path, body):
    body_str = json.dumps(body) if body else ''
    message = f'{timestamp}{method.upper()}{request_path}{body_str}'
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

# 포지션 확인 (중복 진입 방지)
def has_open_position(symbol):
    timestamp = str(int(time.time() * 1000))
    method = 'GET'
    request_path = f'/api/v2/mix/position/single-position?symbol={symbol}&marginCoin=USDT'
    signature = generate_signature(timestamp, method, '/api/v2/mix/position/single-position', '')

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
        data = response.json().get('data', {})
        return float(data.get('total', 0)) > 0
    return False

# 주문 실행
def place_order(signal):
    symbol = 'ETHUSDT'
    size = "1.5"
    leverage = "20"
    margin_mode = "isolated"
    side = 'open_long' if signal == 'buy' else 'open_short'

    if has_open_position(symbol):
        return {'error': 'Already in position'}

    timestamp = str(int(time.time() * 1000))
    method = 'POST'
    request_path = '/api/v2/mix/order/place-order'

    body = {
        'symbol': symbol,
        'marginCoin': 'USDT',
        'size': size,
        'side': side,
        'orderType': 'market',
        'leverage': leverage,
        'marginMode': margin_mode,
        'clientOid': f'entry_{timestamp}'
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
        return {'error': response.json()}

# 웹훅 처리
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        app.logger.info(f"Webhook received: {data}")

        signal = data.get('signal')
        if signal not in ['buy', 'sell']:
            return jsonify({'error': 'Invalid signal'}), 400

        result = place_order(signal)
        return jsonify(result), 200 if 'message' in result else 500

    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return 'Bitget Flask Trading Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
