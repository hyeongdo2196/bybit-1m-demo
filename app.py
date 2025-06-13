import time
import hmac
import hashlib
import json
import base64
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
    # 파라미터 문자열 생성
    query_string = '&'.join([f'{key}={value}' for key, value in sorted(params.items())])
    
    # 서명용 문자열 생성
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

        # 'action'을 'signal'로 수정
        action = data.get('signal')  # 'action'을 'signal'로 수정
        if action not in ['buy', 'sell']:
            app.logger.error(f"Invalid action received: {action}")
            return jsonify({'error': 'Invalid action'}), 400

        params = {
            'apiKey': API_KEY,
            'symbol': data.get('symbol', 'BTCUSDT'),
            'price': data.get('price', '30000'),
            'quantity': data.get('quantity', '0.01'),
            'side': 'buy' if action == 'buy' else 'sell',
            'type': 'limit',
            'timeInForce': 'GTC'
        }

        # 타임스탬프 생성 (밀리초 단위)
        timestamp = str(int(time.time() * 1000))
        params['timestamp'] = timestamp
        
        # 서명 생성
        signature = generate_signature(params, timestamp)
        params['signature'] = signature

        # 헤더 추가
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
        
        # 로그로 API 요청 파라미터와 헤더를 출력하여 디버깅
        app.logger.info(f"Params for signature: {params}")
        app.logger.info(f"Generated signature: {signature}")
        app.logger.info(f"Request Headers: {headers}")

        response = requests.post(order_url, json=params, headers=headers)

        # 비트겟 API 응답 처리
        app.logger.info(f"API Response: {response.status_code} - {response.text}")
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
