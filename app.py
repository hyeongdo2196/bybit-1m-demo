from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import json
import requests
from urllib.parse import urlencode

# Flask 애플리케이션 객체 정의
app = Flask(__name__)

API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'

BASE_URL = 'https://api.bitget.com'

def generate_signature(params):
    """ 비트겟 API 요청 시 필요한 서명 생성 함수 (v2) """
    # 'apiKey'와 'reqTime'을 반드시 포함한 후, 나머지 파라미터를 쿼리 스트링으로 인코딩
    params['apiKey'] = API_KEY
    params['reqTime'] = str(int(time.time() * 1000))  # 현재 시간 (밀리초 단위)
    
    # 쿼리 파라미터 정렬
    query_string = urlencode(sorted(params.items()))
    
    # 서명 생성
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

        # 'signal' 값 확인 (buy 또는 sell)
        action = data.get('signal')
        if action not in ['buy', 'sell']:
            app.logger.error(f"Invalid action received: {action}")
            return jsonify({'error': 'Invalid action'}), 400

        # 주문 파라미터 설정
        params = {
            'symbol': data.get('symbol', 'BTCUSDT'),  # 기본값 BTCUSDT
            'price': data.get('price', '30000'),      # 기본값 30000
            'quantity': data.get('quantity', '0.01'), # 기본값 0.01
            'side': 'buy' if action == 'buy' else 'sell',  # 'buy' 또는 'sell'
            'type': 'limit',  # 한정가 주문
            'timeInForce': 'GTC'  # GTC(지속적 주문)
        }

        # 서명 추가
        params['signature'] = generate_signature(params)  # 서명 생성

        # 비트겟 API 주문 요청
        order_url = f'{BASE_URL}/api/v2/mix/order/place-order'
        response = requests.post(order_url, data=params)

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
