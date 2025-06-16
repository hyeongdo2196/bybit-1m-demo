import time, hmac, hashlib, requests, json, uuid
from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 Bybit Demo API 키 (하드코딩 방식)
API_KEY = 'Xzb5U5mCE44WSB3ExX'
API_SECRET = 'mFTkRe7AAQDvqrkjr1agwysit4SpW3Cpw62A'
BASE_URL = 'https://api-demo.bybit.com'

SYMBOL = 'MNTUSDT'
FIXED_QTY = 200
LEVERAGE = 10

def get_timestamp():
    return str(int(time.time() * 1000))

def generate_signature(params, secret):
    sorted_params = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(secret.encode(), sorted_params.encode(), hashlib.sha256).hexdigest()

def http_request(method, endpoint, params):
    ts = get_timestamp()
    params['api_key'] = API_KEY
    params['timestamp'] = ts
    params['recvWindow'] = 5000
    sign = generate_signature(params, API_SECRET)
    params['sign'] = sign

    url = BASE_URL + endpoint
    if method == 'GET':
        return requests.get(url, params=params)
    return requests.post(url, data=params)

def get_position(symbol):
    endpoint = '/v5/position/list'
    params = {"category": "linear", "symbol": symbol}
    resp = http_request('GET', endpoint, params)
    try:
        data = resp.json()
        if data['retCode'] == 0:
            for pos in data['result']['list']:
                side = pos['side'].upper()
                size = float(pos['size'])
                if size > 0:
                    return {
                        'side': side,
                        'size': size,
                        'avg_price': float(pos['avgPrice'])
                    }
        return None
    except Exception as e:
        app.logger.error(f"Position check error: {str(e)} - {resp.text}")
        return None

def set_leverage(symbol, buy_leverage, sell_leverage):
    endpoint = '/v5/position/set-leverage'
    params = {
        "category": "linear",
        "symbol": symbol,
        "buyLeverage": str(buy_leverage),
        "sellLeverage": str(sell_leverage)
    }
    return http_request('POST', endpoint, params)

def close_position(symbol, side):
    close_side = 'Sell' if side == 'BUY' else 'Buy'
    position_idx = 1 if side == 'BUY' else 2
    endpoint = '/v5/order/create'
    params = {
        'category': 'linear',
        'symbol': symbol,
        'side': close_side,
        'orderType': 'Market',
        'qty': FIXED_QTY,
        'positionIdx': position_idx,
        'reduceOnly': True,
        'timeInForce': 'IOC',
        'orderLinkId': f"close_{uuid.uuid4().hex[:10]}"
    }
    return http_request('POST', endpoint, params)

def place_order(signal):
    side = 'Buy' if signal == 'buy' else 'Sell'
    position_idx = 1 if signal == 'buy' else 2
    opposite_side = 'SELL' if side == 'Buy' else 'BUY'

    set_leverage(SYMBOL, LEVERAGE, LEVERAGE)

    position = get_position(SYMBOL)

    if position and position['side'] == opposite_side:
        app.logger.info("🔁 반대 포지션 존재 → 청산 중...")
        close_position(SYMBOL, position['side'])

    position = get_position(SYMBOL)
    if not position:
        entry = http_request('POST', '/v5/order/create', {
            'category': 'linear',
            'symbol': SYMBOL,
            'side': side,
            'orderType': 'Market',
            'qty': FIXED_QTY,
            'positionIdx': position_idx,
            'reduceOnly': False,
            'timeInForce': 'IOC',
            'orderLinkId': f"entry_{uuid.uuid4().hex[:10]}"
        })

        try:
            entry_data = entry.json()
            if entry_data['retCode'] == 0:
                time.sleep(1.2)
                new_pos = get_position(SYMBOL)
                if not new_pos:
                    return {'error': '포지션 확인 실패'}

                avg_price = new_pos['avg_price']
                tp_price = avg_price * (1.07 if signal == 'buy' else 0.93)
                sl_price = avg_price * (0.98 if signal == 'buy' else 1.02)

                http_request('POST', '/v5/order/create', {
                    'category': 'linear',
                    'symbol': SYMBOL,
                    'side': 'Sell' if signal == 'buy' else 'Buy',
                    'orderType': 'Limit',
                    'qty': FIXED_QTY,
                    'price': round(tp_price, 4),
                    'positionIdx': position_idx,
                    'reduceOnly': True,
                    'timeInForce': 'GTC',
                    'orderLinkId': f"tp_{uuid.uuid4().hex[:8]}"
                })

                http_request('POST', '/v5/order/create', {
                    'category': 'linear',
                    'symbol': SYMBOL,
                    'side': 'Sell' if signal == 'buy' else 'Buy',
                    'orderType': 'Stop',
                    'qty': FIXED_QTY,
                    'stopPx': round(sl_price, 4),
                    'positionIdx': position_idx,
                    'reduceOnly': True,
                    'timeInForce': 'GTC',
                    'orderLinkId': f"sl_{uuid.uuid4().hex[:8]}"
                })

                return {'message': f'{side} 진입 + TP/SL 완료'}

            return {'error': entry_data.get("retMsg", "Unknown order error")}
        except Exception as e:
            return {'error': f'TP/SL 설정 실패: {str(e)}'}

    return {'message': '이미 동일 방향 포지션 존재'}

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        app.logger.info(f"📨 Webhook received: {data}")
        signal = data.get('signal')
        if signal not in ['buy', 'sell']:
            return jsonify({'error': 'Invalid signal'}), 400

        result = place_order(signal)
        status_code = 200 if 'message' in result else 500
        return jsonify(result), status_code

    except Exception as e:
        app.logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return '✅ Bybit MNTUSDT 1m Trading Bot is live!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
