import sys
import json
import os
from datetime import datetime

sys.path.append(os.path.abspath("../src/toss"))
import tossinvest_sock
import tossinvest_utils


trade_strength = {}

def calculate_1min_tradestrength(body):
    body = json.loads(body)
    stock_code = body["code"]
    date       = body["dt"] # i.e 2024-12-27T10:50:16Z
    price      = body["close"]
    trade_vol  = body["volume"]
    trade_type = body["tradeType"] # SELL or BUY
    
    sliced_time = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M")
    if stock_code not in trade_strength.keys():
        trade_strength[stock_code] = {}
    if sliced_time not in trade_strength[stock_code].keys():
        trade_strength[stock_code][sliced_time] = [1, 1, 0]
    
    
    quantity = trade_vol#*price
    trade_strength[stock_code][sliced_time][2] += 1
    if trade_type == "SELL":
        #quantity = -quantity        
        trade_strength[stock_code][sliced_time][1] += quantity
    else:
        trade_strength[stock_code][sliced_time][0] += quantity

    print(datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"), f"CNT: {trade_strength[stock_code][sliced_time][2]}, BUY: {trade_strength[stock_code][sliced_time][0]}     SELL: {trade_strength[stock_code][sliced_time][1]},  STRENGTH: {(trade_strength[stock_code][sliced_time][0]/trade_strength[stock_code][sliced_time][1])*100}")

#    trade_strength[stock_code][sliced_time]
    #print(sliced_time, quantity, "%.2f"%trade_strength[stock_code][sliced_time])

def connect_sock():
    conn_id, device_id, utk = tossinvest_sock.get_connection_headers()
    toss_invest_worker = tossinvest_sock.connect(conn_id, device_id, utk, calculate_1min_tradestrength)
    toss_invest_worker.wait_for_connection()
    toss_invest_worker.add_watchlist("US20211005002")
    input()
    # toss_invest_worker.del_watchlist("US20220919001")
    # input()
    # toss_invest_worker.add_watchlist("US20210326005")
    # input()



def get_stock_info():
    stocks_info = tossinvest_utils.get_current_stocks_info(["US20201001014", "NAS0231011003", "US20150209001"])
    print(stocks_info)

if __name__ == '__main__':
    connect_sock()
    #get_stock_info()
