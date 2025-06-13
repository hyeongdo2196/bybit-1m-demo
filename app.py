import time
import hmac
import hashlib
import base64
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# 비트겟 API 관련 정보
API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'  # 본인의 API Key
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'  # 본인의 API Secret
PASSPHRASE = 'Hyeongdo2196'  # 본인의 Passphrase
BASE_URL = 'https://api.bitget.com'

# 서명 생성 함수
def generate_signature(params, timestamp):
    """ 비트겟 API 요청 시 필요한 서명 생성 함수 """
    
    # 타임스탬프 추가
    params['timestamp'] = timestamp
    
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

        # 신호 받기 ('buy' 또는 'sell')
        action = data.get('signal')
        if action not in ['buy', 'sell']:
            app.logger.error(f"Invalid action received: {action}")
            return jsonify({'error': 'Invalid action'}), 400

        # 주문 파라미터 설정
        params = {
            'apiKey': API_KEY,
            'symbol': data.get('symbol', 'ETHUSDT'),  # 기본 ETHUSDT
            'price': data.get('price', '3000'),  # 기본 가격 (예시로 3000)
            'quantity': data.get('quantity', '1.5'),  # 기본 거래량 (1.5 ETH)
            'side': 'buy' if action == 'buy' else 'sell',  # 신호에 따라 'buy' 또는 'sell'
            'type': 'limit',  # 지정가 주문
            'timeInForce': 'GTC'  # 주문 유효 기간 (Good Till Canceled)
        }

        # 타임스탬프 생성 (밀리초 단위)
        timestamp = str(int(time.time() * 1000))
        app.logger.info(f"Timestamp: {timestamp}")

        # 서명 생성
        signature = generate_signature(params, timestamp)
        app.logger.info(f"Generated signature: {signature}")

        params['signature'] = signature

        # 요청 헤더 설정
        headers = {
            'Content-Type': 'application/json',
            'ACCESS-KEY': API_KEY,
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': PASSPHRASE,
            'locale': 'en-US'  # 예시로 'en-US' 로 설정, 원하시는 언어로 변경 가능
        }

        # 비트겟 API 주문 요청
        order_url = f'{BASE_URL}/api/v2/mix/order/place-order'
        response = requests.post(order_url, json=params, headers=headers)

        # 응답 처리
        if response.status_code == 200:
            app.logger.info('Order placed successfully')
            return jsonify({'message': 'Order placed successfully'}), 200
        else:
            app.logger.error(f"Bitget API Error: {response.text}")
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
