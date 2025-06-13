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

def generate_signature(timestamp, method, request_path, body=None):
    """
    V2 방식 시그니처 생성.
    - body는 POST 시에만 dict로 전달, GET 등은 None으로.
    """
    body_str = json.dumps(body) if body is not None else ''
    message = f'{timestamp}{method.upper()}{request_path}{body_str}'
    digest = hmac.new(API_SECRET.encode('utf-8'),
                      message.encode('utf-8'),
                      hashlib.sha256).digest()
    return base64.b64encode(digest).decode()

def has_open_position(symbol):
    """
    지정 심볼에 대해 현 포지션 보유 여부 조회
    (시그니처 생성 시에 쿼리스트링까지 포함해야 함)
    """
    timestamp = str(int(time.time() * 1000))
    method = 'GET'
    # 쿼리스트링 포함한 request_path
    request_path = f'/api/v2/mix/position/single-position?symbol={symbol}&marginCoin=USDT'
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
        data = response.json().get('data', {})
        # total 필드를 사용해 포지션 수량 확인
        return float(data.get('total', 0)) > 0
    else:
        app.logger.error(f"Position check failed: {response.status_code} {response.text}")
    return False

def place_order(signal):
    """
    마켓 주문 실행: buy 시 long, sell 시 short
    중복 진입 방지 위해 has_open_position() 호출
    """
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
