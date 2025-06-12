# 필요한 라이브러리 임포트
import requests
from flask import Flask, request, jsonify
import hmac
import hashlib
import time

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
    # TradingView에서 보낸 JSON 데이터 받기
    data = request.json
    print("Received data:", data)

    # 신호 (매수 또는 매도) 확인
    action = data.get('action')
    if action not in ['buy', 'sell']:
        return jsonify({'error': 'Invalid action'}), 400

    # 비트겟에 보낼 주문 파라미터 설정
    params = {
        'apiKey': API_KEY,
        'symbol': 'BTCUSDT',  # 거래할 종목 (여기서는 BTC/USDT로 설정)
        'price': '30000',  # 가격은 실제로는 TradingView에서 받을 수 있음
        'quantity': '0.01',  # 수량은 실제로는 TradingView에서 받을 수 있음
        'side': 'buy' if action == 'buy' else 'sell',  # 매수 또는 매도
        'type': 'limit',  # 시장가 주문을 할 경우 'market'으로 변경
        'timeInForce': 'GTC'  # 주문 만료 시간 (Good Till Canceled)
    }

    # 서명 추가
    params['timestamp'] = str(int(time.time() * 1000))
    params['signature'] = generate_signature(params)

    # 비트겟 API 주문 요청
    order_url = f'{BASE_URL}/api/v1/order'
    response = requests.post(order_url, data=params)

    # 비트겟 API 응답 처리
    if response.status_code == 200:
        return jsonify({'message': 'Order placed successfully'}), 200
    else:
        return jsonify({'error': response.json()}), 500

# 루트 엔드포인트 추가
@app.route('/', methods=['GET'])
def home():
    return "Flask Webhook is up and running!"

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)  # host='0.0.0.0'으로 변경
