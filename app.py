import requests
from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import json

# Flask 애플리케이션 생성
app = Flask(__name__)

# 비트겟 API 키와 시크릿 키 (여기서는 더미 데이터로 설정, 실제 값을 입력해야 함)
API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'  # 비트겟에서 제공하는 실제 API Key를 여기에 입력하세요
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'  # 비트겟에서 제공하는 실제 API Secret을 여기에 입력하세요

# 비트겟 API URL
BASE_URL = 'https://api.bitget.com'

# 서명 생성 함수
def generate_signature(params):
    """ 비트겟 API 요청 시 필요한 서명 생성 함수 """
    query_string = '&'.join([f'{key}={value}' for key, value in sorted(params.items())])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# 웹훅 엔드포인트 설정
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 요청 헤더와 본문을 로그로 출력하여 확인
        print("Headers:", request.headers)
        print("Raw data:", request.data)

        # JSON 데이터 받기
        data = request.json

        # 데이터가 제대로 파싱되지 않은 경우 수동으로 파싱
        if not data:
            try:
                data = json.loads(request.data)  # 수동으로 JSON 파싱
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format'}), 400

        print("Received data:", data)  # 수신된 데이터 로그 출력

        # 데이터가 제대로 왔는지 확인
        if not data:
            return jsonify({'error': 'No data received'}), 400

        # 신호 (매수 또는 매도) 확인
        action = data.get('action')
        if action not in ['buy', 'sell']:
            return jsonify({'error': 'Invalid action'}), 400

        # 비트겟에 보낼 주문 파라미터 설정
        params = {
            'apiKey': API_KEY,
            'symbol': data.get('symbol', 'BTCUSDT'),  # 기본값 BTC/USDT
            'price': data.get('price', '30000'),  # 기본 가격 설정
            'quantity': data.get('quantity', '0.01'),  # 기본 수량 설정
            'side': 'buy' if action == 'buy' else 'sell',  # 매수 또는 매도
            'type': 'limit',  # 시장가 주문을 할 경우 'market'으로 변경
            'timeInForce': 'GTC'  # 주문 만료 시간 (Good Till Canceled)
        }

        # 서명 추가
        params['timestamp'] = str(int(time.time() * 1000))
        params['signature'] = generate_signature(params)

        # 서명과 파라미터 로그 출력
        print("Generated signature:", params['signature'])
        print("Sending order with params:", params)  # 주문 파라미터 로그 출력

        # 비트겟 API 주문 요청
        order_url = f'{BASE_URL}/api/v1/order'
        response = requests.post(order_url, data=params)

        # 비트겟 API 응답 처리
        print("Response status code:", response.status_code)
        print("Response text:", response.text)

        if response.status_code == 200:
            return jsonify({'message': 'Order placed successfully'}), 200
        else:
            return jsonify({'error': response.json()}), 500

    except Exception as e:
        print(f"Error: {str(e)}")  # 오류 로그 출력
        return jsonify({'error': str(e)}), 500

# 기본 페이지 (테스트용)
@app.route('/')
def home():
    return "Flask TradingBot is running!"

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # 외부에서 접근 가능하도록 host를 0.0.0.0으로 설정
