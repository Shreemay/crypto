import pymongo.errors
import subprocess
import traceback
import requests
import datetime
import pymongo
import hashlib
import locale
import hmac
import json
import time
import time

mongo_client = pymongo.MongoClient('localhost',27017)
x = mongo_client['crypto']['parameters'].find_one({"exchange":"CoinDCX"})
key = x['api']
secret = x['secret']
secret_bytes = bytes(secret, encoding='utf-8')
buy_price = 100
fees = 0.003
min_fees = 0.002
max_fees = 0.003
locale.setlocale(locale.LC_ALL, 'en_IN')
get_orders_list = []
place_order_list = []
cancel_orders_list = []
fetch_funds_list = []
trade_history_list = []
no_of_orders = x['no_of_orders']
filename = "index.html"


def run_git_command(cmd):
    result = subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,shell=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout

def fetch_funds():
    timeStamp = int(round(time.time() * 1000))
    body = {
        "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    headers = {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': key,
            'X-AUTH-SIGNATURE': signature
        }
    url = "https://api.coindcx.com/exchange/v1/users/balances"
    while len(fetch_funds_list) >= 2000 and fetch_funds_list[-2000] > datetime.datetime.now()-datetime.timedelta(seconds=60):
        pass
    response = requests.post(url, data = json_body, headers = headers)
    data = response.json()
    funds = {}
    for d in data:
        if d["currency"] == "BTC":
            funds["BTC"] = d["balance"]
        elif d["currency"] == "INR":
            funds["INR"] = d["balance"]
    return funds

def place_order(side, price_per_unit, qty):
    url = "https://api.coindcx.com/exchange/v1/markets_details"
    timeStamp = int(round(time.time() * 1000))
    body = {
      "side": side,
      "order_type": "limit_order",
      "market": "BTCINR",
      "price_per_unit": price_per_unit,
      "total_quantity": qty,
      "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    url = "https://api.coindcx.com/exchange/v1/orders/create"
    while len(place_order_list) >= 2000 and place_order_list[-2000] > datetime.datetime.now()-datetime.timedelta(seconds=60):
        pass
    response = requests.post(url, data = json_body, headers = headers)
    data = response.json()

def get_orders():
    secret_bytes = bytes(secret, encoding='utf-8')
    timeStamp = int(round(time.time() * 1000))
    body = {
        "market": "BTCINR",
        "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    url = "https://api.coindcx.com/exchange/v1/orders/active_orders"
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    while len(get_orders_list) >= 2000 and get_orders_list[-2000] > datetime.datetime.now()-datetime.timedelta(seconds=60):
        pass
    response = requests.post(url, data = json_body, headers = headers)
    data = response.json()
    return data["orders"]

def cancel_order_by_id(id):
    secret_bytes = bytes(secret, encoding='utf-8')
    timeStamp = int(round(time.time() * 1000))
    body = {
        'id':id,
        'timestamp':timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    url = "https://api.coindcx.com/exchange/v1/orders/cancel"
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    while len(cancel_orders_list) >= 30 and cancel_orders_list[-30] > datetime.datetime.now()-datetime.timedelta(seconds=60):
        pass
    response = requests.post(url, data = json_body, headers = headers)
    cancel_orders_list.append(datetime.datetime.now())
    data = response.json()
    if data['code'] == 400:
        print(data)
        return False
    return True

def cancel_orders():
    secret_bytes = bytes(secret, encoding='utf-8')
    timeStamp = int(round(time.time() * 1000))
    body = {
    "market": "BTCINR", # Replace 'SNTBTC' with your desired market pair.
    "timestamp": timeStamp
    }
    json_body = json.dumps(body, separators = (',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    url = "https://api.coindcx.com/exchange/v1/orders/cancel_all"
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    while len(cancel_orders_list) >= 30 and cancel_orders_list[-30] > datetime.datetime.now()-datetime.timedelta(seconds=60):
        pass
    response = requests.post(url, data = json_body, headers = headers)
    cancel_orders_list.append(datetime.datetime.now())
    data = response.json()

def get_profit(current_price):
    sell_amt = 0
    sell_total = 0
    trades = {'buy':{'qty':0,'price':0,'fee':0},'sell':{'qty':0,'price':0,'fee':0}}
    count = 0
    for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","timestamp":{"$gte":datetime.datetime(2025,9,1).timestamp()*1000}},{"quantity":1,"price":1,"fee_amount":1,"side":1}):
        count += 1
        trades[x['side']]['qty'] += float(x['quantity'])
        trades[x['side']]['price'] += float(x["price"])*float(x["quantity"])
        trades[x['side']]['fee'] += float(x['fee_amount'])
    for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","side":"sell","timestamp":{"$gte":datetime.datetime(2025,9,1).timestamp()*1000}},{"quantity":1,"price":1,"fee_amount":1}):
        sell_amt += float(x["quantity"])
        sell_total += (float(x["price"])*float(x["quantity"])-float(x["fee_amount"]))
    buy_amt = 0
    buy_total = 0
    for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","side":"buy","timestamp":{"$gte":datetime.datetime(2025,9,1).timestamp()*1000}},{"quantity":1,"price":1,"fee_amount":1}):
        buy_amt += float(x["quantity"])
        buy_total += (float(x["price"])*float(x["quantity"])+float(x["fee_amount"]))
        if buy_amt >= sell_amt:
            break
    return sell_total-buy_total+current_price*(sell_amt-buy_amt)

def generate_html(lowest, reserve, volume_30,inr):
    last_price = get_price()
    reserve_price = reserve*last_price/100000000
    hour_1 = datetime.datetime.now()-datetime.timedelta(hours=1)
    day_1 = datetime.datetime.now()-datetime.timedelta(days=1)
    day_14 = datetime.datetime.now()-datetime.timedelta(days=14)
    day_30 = datetime.datetime.now()-datetime.timedelta(days=30)
    volume_1h = round(sum([float(x['price'])*float(x["quantity"]) for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","timestamp":{"$gte":hour_1.timestamp()*1000}},{"price":1,"quantity":1})]),2)
    d = datetime.datetime(2020,1,1)
    tds = round(sum([float(x['price'])*float(x["quantity"])*0.01 for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","side":"sell","timestamp":{"$gte":d.timestamp()*1000}},{"price":1,"quantity":1})]),2)
    d = datetime.datetime.now()
    d = datetime.datetime(d.year,4,1)
    if d > datetime.datetime.now():
        d = datetime.datetime(d.year-1,4,1)
    tds_1y = round(sum([float(x['price'])*float(x["quantity"])*0.01 for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","side":"sell","timestamp":{"$gte":d.timestamp()*1000}},{"price":1,"quantity":1})]),2)
    tds_14 = round(sum([float(x['price'])*float(x["quantity"])*0.01 for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","side":"sell","timestamp":{"$gte":day_14.timestamp()*1000}},{"price":1,"quantity":1})]),2)
    tds_1m = round(sum([float(x['price'])*float(x["quantity"])*0.01 for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","side":"sell","timestamp":{"$gte":day_30.timestamp()*1000}},{"price":1,"quantity":1})]),2)
    profit = get_profit(last_price)
    orders = []
    for x in mongo_client['crypto']['trades'].find({"exchange":"CoinDCX"}).sort("timestamp",-1).limit(5):
        orders.append(x)
    with open(filename,'w',encoding='utf8') as f:
        text = """
            <html>
            <head>
            <meta http-equiv="refresh" content="5">
            <title>Portfolio</title>
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Portfolio Dashboard</title>
            <style>
                body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background: #f5f7fa;
                color: #333;
                }

                header {
                background: #2d3436;
                color: #fff;
                padding: 15px;
                text-align: center;
                font-size: 1.5rem;
                }

                .dashboard {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                padding: 20px;
                }

                .card {
                background: #fff;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.2s ease-in-out;
                }

                .card:hover {
                transform: translateY(-5px);
                }

                .card img {
                width: 75px;
                height: 75px;
                margin-bottom: 10px;
                }

                .title {
                font-size: 1.1rem;
                font-weight: bold;
                margin-bottom: 10px;
                }

                .value {
                font-size: 1.5rem;
                color: #0984e3;
                }

                .positive {
                color: #00b894;
                }

                .negative {
                color: #d63031;
                }

                table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
                }

                table th, table td {
                padding: 6px 8px;
                text-align: center;
                }

                table th {
                background: #f1f2f6;
                font-weight: bold;
                }

                .buy {
                color: #00b894;
                font-weight: bold;
                }

                .sell {
                color: #d63031;
                font-weight: bold;
                }
            </style>
            </head>
            <body>
            <div class="dashboard">
        """
        text += """
                <div class="card">
                <img src="https://www.shutterstock.com/image-vector/bitcoin-icon-sign-payment-symbol-600nw-1938997753.jpg" alt="Current Price">
                <div class="title">Current Price</div>
        """
        text += """
            <div class="value" id="vol-1-h">₹{}</div>
        """.format(locale.format_string("%d", last_price, grouping=True))
        text += """
            </div>
            <div class="card">
            <img src="https://www.shutterstock.com/image-vector/1-hour-clock-icon-vector-260nw-2302434205.jpg" alt="1 Hour">
            <div class="title">1H Volume</div>
        """
        text += """
            <div class="value" id="vol-1-h">₹{}</div>
        """.format(locale.format_string("%d", volume_1h, grouping=True))
        text += """
            </div>
            <div class="card">
            <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTgxPkLvLr2bB8by3p8l3oIR5cesJ77S4phow&s" alt="1 Month">
            <div class="title">30D Volume</div>
        """
        text += """
            <div class="value" id="vol-30-d">₹{}</div>
            </div>
        """.format(locale.format_string("%d", volume_30, grouping=True))
        text += """
            <div class="card">
                    <img src="https://cdn-icons-png.flaticon.com/512/10771/10771391.png" alt="Lowest">
                    <div class="title">Fees</div>
                    <div class="value" id="fees">{}%</div>
                </div>
        """.format(fees)
        text += """
            
            <div class="card">
            <img src="https://cdn.iconscout.com/icon/free/png-256/free-tds-icon-svg-png-download-1538212.png" alt="Total TDS">
            <div class="title">Total TDS</div>
        """
        text += """
            <div class="value" id="tds-total">₹{}</div>
            <div class="value" id="tds-total">₹{}</div>
            </div>
        """.format(locale.format_string("%d", tds, grouping=True),locale.format_string("%d", tds_1y, grouping=True))
        text += """
            <div class="card">
            <img src="https://cdn.iconscout.com/icon/free/png-256/free-tds-icon-svg-png-download-1538212.png" alt="24 Hour TDS">
            <div class="title">14D TDS</div>
            <div class="value" id="tds-24-h">₹{}</div>
            </div>
        """.format(locale.format_string("%d", tds_14, grouping=True))
        text += """
            <div class="card">
            <img src="https://cdn.iconscout.com/icon/free/png-256/free-tds-icon-svg-png-download-1538212.png" alt="1 Month TDS">
            <div class="title">1M TDS</div>
            <div class="value" id="tds-1-m">₹{}</div>
            </div>
        """.format(locale.format_string("%d", tds_1m, grouping=True))
        
        text += """
            <div class="card">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Bitcoin.svg/1200px-Bitcoin.svg.png" alt="Sats">
            <div class="title">Reserve Sats</div>
            <div class="value" id="reserve">{}</div>
            <div class="value" id="reserve-price">₹{}</div>
            </div>
        """.format(locale.format_string("%.2f", round(reserve,2), grouping=True),locale.format_string("%.2f", round(reserve_price,2), grouping=True))
        text += """
            <div class="card">
                    <img src="https://thumbs.dreamstime.com/b/low-price-bitcoin-icon-isolated-low-price-bitcoin-346991232.jpg" alt="Lowest">
                    <div class="title">Lowest Buy</div>
                    <div class="value" id="lowest-buy">₹{} ({}%)</div>
                </div>
        """.format(locale.format_string("%d", lowest, grouping=True), round(lowest*100/base_price,2))
        text += """
            <div class="card">
                    <img src="https://www.shutterstock.com/image-vector/profit-loss-icon-trendy-flat-260nw-1811004328.jpg" alt="PNL">
                    <div class="title">PNL</div>
                    <div class="value" id="profit">₹{}</div>
                </div>
        """.format(locale.format_string("%d", profit, grouping=True))
        text += """
            <div class="card">
                    <div class="title">Orders</div>
                    <table>
                    <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Price</th>
                        <th>Side</th>
                    </tr>
                    </thead>
                    <tbody id="orders-body">
        """
        for o in orders:
            t = datetime.datetime.fromtimestamp(float(o["timestamp"])/1000)
            hour = "0"+str(t.hour)
            minute = "0"+str(t.minute)
            second = "0"+str(t.second)
            text += "<tr><td class=\"title\">{}:{}:{}</td><td class=\"title\">{}</td><td class=\"{}\">{}</td></tr>".format(hour[-2:],minute[-2:],second[-2:],int(float(o["price"])),o["side"],o["side"])
        text += """
                    </tbody>
                </table>
                </div>
        """.format(locale.format_string("%d", lowest, grouping=True), round(lowest*100/base_price,2))
        text += """
            <div class="card">
            <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSiaRL_ColqSIPDHvgPgdw1DBr9nbyjFLbFtQ&s" alt="Total INR">
            <div class="title">Total INR</div>
            <div class="value" id="total-inr">₹{}</div>
            </div>
        """.format(locale.format_string("%d", inr, grouping=True))
        text += """
            </div>
            </body>
            </html>
        """
        f.write(text)
    
    if filename in run_git_command("git status"):
        run_git_command("git add .")
        run_git_command('git commit -m "{} {}"'.format('HTML file updated at',datetime.datetime.now()))
        run_git_command("git push")
        print('File pushed')
        

def get_coin_qty(current_price):
    ret = 0.000001
    while ret*current_price < buy_price:
        ret = round(ret+0.000001,6)
    ret = max(0.00001,ret)
    return ret

def get_lowest(funds, difference):
    current_price = base_price
    btc_qty = funds["BTC"]
    while True:
        qty = get_coin_qty(current_price)
        current_price -= difference
        btc_qty -= qty
        if btc_qty < get_coin_qty(current_price):
            break
    inr = funds["INR"]
    while True:
        if inr < (current_price-difference)*get_coin_qty(current_price-difference):
            break
        inr -= current_price*get_coin_qty(current_price)
        current_price -= difference
    return current_price

def get_inr(funds):
    current_price = base_price
    inr = 0
    btc_qty = funds["BTC"]
    while True:
        qty = get_coin_qty(current_price)
        inr += qty*current_price*(1-2*fees*1.18)
        btc_qty -= qty
        if btc_qty < get_coin_qty(current_price):
            break
    inr += funds["INR"]
    return inr

def get_trade_orders(funds,difference):
    current_price = base_price
    btc_qty = funds["BTC"]
    while True:
        qty = get_coin_qty(current_price)
        current_price -= difference
        btc_qty -= qty
        if btc_qty < get_coin_qty(current_price):
            break
    if funds["INR"] < current_price*get_coin_qty(current_price):
        time.sleep(100)
        exit()
    current_price -= difference
    orders = []
    for i in range(no_of_orders):
        orders.append([get_coin_qty(current_price-difference*i), current_price-difference*i, get_coin_qty(current_price+difference*(i+1)), int((current_price+difference*(i+1))*(1+fees*2*1.18))])
    return orders

def get_trade_history():
    timestamp = 0
    for x in mongo_client['crypto']['trades'].find({"exchange":"CoinDCX"}):
        timestamp = max(timestamp,x['timestamp'])
    secret_bytes = bytes(secret, encoding='utf-8')
    timeStamp = int(round(time.time() * 1000))
    body = {
    "timestamp": timeStamp,
    "symbol": "BTCINR"
    }
    if timestamp:
        body["from_timestamp"] = timestamp
    json_body = json.dumps(body, separators = (',', ':'))
    signature = hmac.new(secret_bytes, json_body.encode(), hashlib.sha256).hexdigest()
    url = "https://api.coindcx.com/exchange/v1/orders/trade_history"
    headers = {
        'Content-Type': 'application/json',
        'X-AUTH-APIKEY': key,
        'X-AUTH-SIGNATURE': signature
    }
    while len(trade_history_list) >= 2000 and trade_history_list[-2000] > datetime.datetime.now()-datetime.timedelta(seconds=60):
        pass
    response = requests.post(url, data = json_body, headers = headers)
    data = response.json()
    for t in data:
        t["exchange"] = "CoinDCX"
        t['fee_amount'] = float(t['fee_amount'])
        t['quantity'] = float(t['quantity'])
        t['price'] = float(t['price'])
        try:
            mongo_client['crypto']['trades'].insert_one(t)
            print('{} Order executed: {}'.format(t['side'].title(),t['price']))
        except pymongo.errors.DuplicateKeyError:
            pass

def update_reserve():
    reserve = 0
    fees = 0
    for x in mongo_client['crypto']['trades'].find({"exchange":"CoinDCX"}):
        reserve += float(x['fee_amount'])*0.01/float(x['price'])
        fees += float(x['fee_amount'])
    mongo_client['crypto']['parameters'].update_one({"exchange":"CoinDCX"},{"$set":{"reserve":reserve*100000000}})
    last = 0
    for x in mongo_client['crypto']['reserve'].find():
        last = max(last,x['reserve'])
    if reserve > last:
        mongo_client['crypto']['reserve'].insert_one({"time":datetime.datetime.now(),"reserve":reserve})

def get_price():
    url = "https://api.coindcx.com/exchange/ticker"
    response = requests.get(url)
    data = response.json()
    for d in data:
        if d['market'] == 'BTCINR':
            return int(float(d['last_price']))

def get_fees(volume_30):
    if volume_30 < 29000000:
        return 0.0014
    elif volume_30 < 29500000:
        return 0.0015
    elif volume_30 < 30500000:
        return 0.0016
    elif volume_30 < 31500000:
        return 0.0017
    elif volume_30 < 32500000:
        return 0.0018
    elif volume_30 < 33500000:
        return 0.0019
    elif volume_30 < 35000000:
        return 0.002
    elif volume_30 < 36000000:
        return 0.0021
    elif volume_30 < 37500000:
        return 0.0022
    elif volume_30 < 39000000:
        return 0.0023
    elif volume_30 < 40500000:
        return 0.0024
    elif volume_30 < 42000000:
        return 0.0025
    elif volume_30 < 44000000:
        return 0.0026
    elif volume_30 < 46000000:
        return 0.0027
    elif volume_30 < 48000000:
        return 0.0028
    elif volume_30 < 54000000:
        return 0.0029
    elif volume_30 < 57000000:
        return 0.003
    elif volume_30 < 61000000:
        return 0.0031
    elif volume_30 < 65000000:
        return 0.0032
    elif volume_30 < 69000000:
        return 0.0033
    elif volume_30 < 74000000:
        return 0.0034
    


while True:
    try:
        x = mongo_client['crypto']['parameters'].find_one({"exchange":"CoinDCX"},{"base_price":1,"difference":1})
        base_price = x['base_price']
        difference = x['difference']
        current_price = get_price()
        if current_price > base_price:
            mongo_client['crypto']['parameters'].update_one({"exchange":"CoinDCX"},{"$set":{"base_price":int(current_price)}})
            continue
        reserve = mongo_client['crypto']['parameters'].find_one({"exchange":"CoinDCX"})['reserve']
        funds = fetch_funds()
        lowest = get_lowest(funds, difference)
        day_30 = datetime.datetime.now()-datetime.timedelta(days=30)
        volume_30 = round(sum([float(x['price'])*float(x["quantity"]) for x in mongo_client['crypto']['trades'].find({"symbol":"BTCINR","timestamp":{"$gte":day_30.timestamp()*1000}},{"price":1,"quantity":1})]),2)
        inr = get_inr(funds)
        generate_html(lowest, reserve, volume_30,inr)
        orders = get_orders()
        orders = [o for o in orders if o["id"] != "44c9d322-8d4f-11f0-9f72-4fc3e565f7cc"]
        fees = get_fees(volume_30)
        if len(orders) == 2*no_of_orders:
            sides = {"buy":0,"sell":0}
            for o in orders:
                sides[o["side"]] += 1
            if sides["buy"] != sides["sell"]:
                cancel_orders()
            else:
                update_reserve()
                get_trade_history()
                print(datetime.datetime.now(),sides["buy"],'orders intact')
                continue
        print("Placing orders: {}".format(datetime.datetime.now()))
        funds = fetch_funds()
        orders_to_place = get_trade_orders(funds,difference)
        orders = get_orders()
        orders = [o for o in orders if o["id"] != "44c9d322-8d4f-11f0-9f72-4fc3e565f7cc"]
        present_orders = {int(o['price_per_unit']):o['id'] for o in orders}
        orders_to_be_placed_list = []
        for o in orders_to_place:
            orders_to_be_placed_list.append(o[1])
            orders_to_be_placed_list.append(o[3])
        continue_flag = False
        spread = ((max(orders_to_be_placed_list)/min(orders_to_be_placed_list))-1)*100
        if spread > 1:
            no_of_orders -= 1
            mongo_client['crypto']['parameters'].update_one({"exchange":"CoinDCX"},{"$set":{"no_of_orders":no_of_orders}})
        elif spread < 0.9:
            no_of_orders += 1
            mongo_client['crypto']['parameters'].update_one({"exchange":"CoinDCX"},{"$set":{"no_of_orders":no_of_orders}})
        for p in present_orders:
            if p in orders_to_be_placed_list:
                pass
            else:
                status = cancel_order_by_id(present_orders[p])
                if not status:
                    continue_flag = True
                    break
        if continue_flag:
            continue
        for o in orders_to_place:
            if o[1] not in present_orders:
                place_order("buy", o[1], o[0])
            if o[3] not in present_orders:
                place_order("sell", o[3], o[2])
        print(datetime.datetime.now(),orders_to_place[0][1],orders_to_place[0][3])
    except:
        print(traceback.format_exc())
        time.sleep(10)
