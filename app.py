from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import json
import requests

# Flask 애플리케이션 객체 정의
app = Flask(__name__)

API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'

BASE_URL = 'https://api.bitget.com'

def generate_signature(params):
    """ 비트겟 API 요청 시 필요한 서명 생성 함수 """
    query_string = '&'.join([f'{key}={value}' for key, value in sorted(params.items())])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

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

        # 서명 추가
        params['timestamp'] = str(int(time.time() * 1000))  # 타임스탬프 추가
        params['signature'] = generate_signature(params)  # 서명 생성

        # 서명 파라미터 로그 출력
        app.logger.info(f"Params for signature: {params}")
        app.logger.info(f"Generated signature: {params['signature']}")

        # 비트겟 API 주문 요청
        order_url = f'{BASE_URL}/api/v2/mix/order/place-order'  # 수정된 엔드포인트
        response = requests.post(order_url, data=params)

        # API 응답 시 로그 출력
        app.logger.info(f"API Response: {response.status_code} - {response.text}")

        # 비트겟 API 응답 처리
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
