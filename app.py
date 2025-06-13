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

# 서명 생성 함수
def generate_signature(params, timestamp):
    """ 비트겟 API 요청 시 필요한 서명 생성 함수 """
    # 파라미터들을 알파벳 순으로 정렬
    sorted_params = sorted(params.items())

    # 정렬된 파라미터들로 쿼리 문자열 생성
    query_string = '&'.join([f'{key}={value}' for key, value in sorted_params])

    # 서명용 문자열 생성 (timestamp + 쿼리 문자열)
    message = f'{timestamp}{query_string}'

    # HMAC-SHA256 서명 생성
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).digest()

    # Base64 인코딩
    return base64.b64encode(signature).decode()

# 포지션 확인 함수
def check_existing_position(symbol):
    """ 이미 포지션이 존재하는지 확인하는 함수 """
    url = f"{BASE_URL}/api/mix/v1/position"
    timestamp = str(int(time.time() * 1000))
    params = {
        'apiKey': API_KEY,
        'timestamp': timestamp
    }

    signature = generate_signature(params, timestamp)
    params['signature'] = signature

    headers = {
        'Content-Type': 'application/json',
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': PASSPHRASE
    }

    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        positions = response.json().get("data", [])
        for position in positions:
            if position['symbol'] == symbol and float(position['size']) > 0:
                return True
    return False

# 주문 실행 함수
def place_order(symbol, side, price, quantity):
    """ 비트겟에서 실제로 주문을 실행하는 함수 """
    url = f'{BASE_URL}/api/v2/mix/order/place-order'
    timestamp = str(int(time.time() * 1000))

    params = {
        'apiKey': API_KEY,
        'symbol': symbol,
        'price': price,
        'quantity': quantity,
        'side': side,
        'type': 'limit',
        'timeInForce': 'GTC',
        'timestamp': timestamp
    }

    signature = generate_signature(params, timestamp)
    params['signature'] = signature

    headers = {
        'Content-Type': 'application/json',
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': PASSPHRASE
    }

    response = requests.post(url, json=params, headers=headers)
    return response

# 익절 및 손절 주문 함수
def set_take_profit_and_stop_loss(symbol, side, entry_price, quantity):
    """ 익절 및 손절 주문 설정 """
    # 익절가 (+5%)
    take_profit_price = entry_price * 1.05
    # 손절가 (-2%)
    stop_loss_price = entry_price * 0.98

    # 익절 주문
    take_profit_order = place_order(symbol, 'sell' if side == 'buy' else 'buy', take_profit_price, quantity)
    if take_profit_order.status_code == 200:
        app.logger.info(f"Take profit set at {take_profit_price}")
    else:
        app.logger.error(f"Failed to set take profit: {take_profit_order.text}")

    # 손절 주문
    stop_loss_order = place_order(symbol, 'sell' if side == 'buy' else 'buy', stop_loss_price, quantity)
    if stop_loss_order.status_code == 200:
        app.logger.info(f"Stop loss set at {stop_loss_price}")
    else:
        app.logger.error(f"Failed to set stop loss: {stop_loss_order.text}")

# 웹훅 엔드포인트
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 요청 헤더와 본문을 로그로 출력하여 확인
        app.logger.info(f"Headers: {request.headers}")
        app.logger.info(f"Raw data: {request.data}")

        # JSON 데이터 받기
        data = request.json

        if not data:
            app.logger.error("No data received")
            return jsonify({'error': 'No data received'}), 400

        # 'action'을 'signal'로 수정
        action = data.get('signal')  # 'action'을 'signal'로 수정
        if action not in ['buy', 'sell']:
            app.logger.error(f"Invalid action received: {action}")
            return jsonify({'error': 'Invalid action'}), 400

        symbol = data.get('symbol', 'ETHUSDT')  # 기본 심볼은 ETHUSDT
        price = data.get('price', '3000')  # 가격
        quantity = data.get('quantity', '1.5')  # 수량 (이더리움 1.5개)

        # 이미 포지션이 있는지 확인
        if check_existing_position(symbol):
            app.logger.error(f"Position already exists for {symbol}. Skipping order.")
            return jsonify({'error': 'Position already exists'}), 400

        # 주문 실행
        side = 'buy' if action == 'buy' else 'sell'
        response = place_order(symbol, side, price, quantity)

        if response.status_code == 200:
            app.logger.info(f"Order placed successfully: {response.json()}")
            # 주문이 성공적으로 이루어졌다면 익절 및 손절 설정
            order_data = response.json()
            entry_price = float(order_data['data']['price'])
            set_take_profit_and_stop_loss(symbol, side, entry_price, quantity)
            return jsonify({'message': 'Order placed successfully'}), 200
        else:
            app.logger.error(f"Failed to place order: {response.text}")
            return jsonify({'error': response.json()}), 500

    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 기본 페이지
@app.route('/')
def home():
    return "Flask TradingBot is running!"

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
