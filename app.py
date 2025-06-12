@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 요청 헤더와 본문을 로그로 출력하여 확인
        print("Headers:", request.headers)
        print("Raw data:", request.data)

        # JSON 데이터 받기
        data = request.json
        if not data:
            print("No JSON parsed. Attempting manual JSON parsing.")
            try:
                data = json.loads(request.data)  # 수동으로 JSON 파싱
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
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
