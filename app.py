from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import json

# Flask 애플리케이션 객체 정의
app = Flask(__name__)

API_KEY = 'bg_9e4ab5c0a0c427406bba98473752269c'
API_SECRET = '47a27700c5488fa7fddf508dac0f49472b8cad971087e58503a889d0c3bd3c59'

BASE_URL = 'https://api.bitget.com'

def generate_signature(params):
    query_string = '&'.join([f'{key}={value}' for key, value in sorted(params.items())])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# 웹훅 엔드포인트
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json

        if not data:
            return jsonify({'error': 'No data received'}), 400

        action = data.get('action')
        if action not in ['buy', 'sell']:
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

        params['timestamp'] = str(int(time.time() * 1000))
        params['signature'] = generate_signature(params)

        order_url = f'{BASE_URL}/api/v1/order'
        response = requests.post(order_url, data=params)

        if response.status_code == 200:
            return jsonify({'message': 'Order placed successfully'}), 200
        else:
            return jsonify({'error': response.json()}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 기본 페이지
@app.route('/')
def home():
    return "Flask TradingBot is running!"

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
