import time
import hmac
import hashlib
import requests
import json
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

# !!! 여기에 본인의 Bybit API 정보를 넣으세요 !!!
API_KEY = 'YOUR_BYBIT_API_KEY'
API_SECRET = 'YOUR_BYBIT_API_SECRET'
BASE_URL = 'https://api.bybit.com'

# 심볼별 최소 주문 수량 (Bybit 기준, 필요시 추가)
SYMBOL_MIN_QTY = {
    'BTCUSDT': 0.001,
    'ETHUSDT': 0.01,
    'SOLUSDT': 0.1,
    # 추가 원할 경우 여기에...
}

def get_timestamp():
    # Bybit는 millisecond timestamp 사용
    return str(int(time.time() * 1000))

def generate_signature(params, api_secret):
    # Bybit V5 REST API 시그니처
    sorted_params = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(api_secret.encode('utf-8'), sorted_params.encode('utf-8'), hashlib.sha256).hexdigest()

def http_request(method, endpoint, params):
    ts = get_timestamp()
    params['api_key'] = API_KEY
    params['timestamp'] = ts
    params['recvWindow'] = 5000  # 5초
    sign = generate_signature(params, API_SECRET)
    params['sign'] = sign

    if method == "GET":
        resp = requests.get(BASE_URL + endpoint, params=params)
    else:
        resp = requests.post(BASE_URL + endpoint, data=params)
    return resp

def has_open_position(symbol):
    # Bybit 포지션 조회 (0이 아니면 포지션 있음)
    endpoint = '/v5/position/list'
    params = {
        "category": "linear",  # USDT Perp
        "symbol": symbol,
    }
    resp = http_request('GET', endpoint, params)
    try:
        data = resp.json()
        if data['retCode'] == 0:
            pos_list = data['result']['list']
            for pos in pos_list:
                size = float(pos.get('size', 0))
                if size != 0:
                    return True
        return False
    except Exception as e:
        app.logger.error(f"Position check error: {str(e)} - {resp.text}")
        return False

def place_order(signal, symbol='BTCUSDT'):
    qty = SYMBOL_MIN_QTY.get(symbol, 0.01)
    side = 'Buy' if signal == 'buy' else 'Sell'
    order_type = 'Market'
    client_order_id = f"entry_{uuid.uuid4().hex}"

    if has_open_position(symbol):
        return {'error': 'Already in position'}

    endpoint = '/v5/order/create'
    params = {
        'category': 'linear',
        'symbol': symbol,
        'side': side,
        'orderType': order_type,
        'qty': qty,
        'positionIdx': 0,  # 0: BOTH, 1: LONG, 2: SHORT
        'reduceOnly': False,
        'closeOnTrigger': False,
        'timeInForce': 'IOC',  # 즉시체결
        'orderLinkId': client_order_id
        # 필요시 leverage, takeProfit 등 추가 가능
    }
    resp = http_request('POST', endpoint, params)
    try:
        data = resp.json()
        if data['retCode'] == 0:
            return {'message': 'Order placed'}
        else:
            return {'error': data}
    except Exception as e:
        return {'error': str(e)}

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        app.logger.info(f"Webhook received: {data}")

        signal = data.get('signal')
        symbol = data.get('symbol', 'BTCUSDT')
        if signal not in ['buy', 'sell']:
            return jsonify({'error': 'Invalid signal'}), 400

        result = place_order(signal, symbol)
        status_code = 200 if 'message' in result else 500
        return jsonify(result), status_code
    except Exception as e:
        app.logger.error(f"Unhandled error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return 'Bybit Flask Trading Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
