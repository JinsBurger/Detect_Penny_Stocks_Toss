from datetime import datetime
from config import *
import webbrowser
import json
import threading
import logging
import time
import requests
import copy
import os
import sys

sys.path.append(os.path.abspath("../toss"))
sys.path.append(os.path.abspath("../"))
import tossinvest_utils
import db_utils
import tossinvest_sock

requests.packages.urllib3.disable_warnings(
	requests.packages.urllib3.exceptions.InsecureRequestWarning
)

class PennyStocksDectector:
    def __init__(self, stock_db_path, thread_count, sensitive_hooks=None, open_browser=False):
        self.interest_stocks = {}
        self.interest_lock = threading.Lock()

        self.sensitive_stocks = []
        self.sensitive_watcher_cond = threading.Condition()
        self.max_thread_count = thread_count
        self.sensitive_hooks = sensitive_hooks
        self.open_browser = open_browser

        self.sock_queue = []
        self.sock_queue_lock = threading.Lock()

        self.db_path = stock_db_path
        cur, conn =  db_utils.open_sqlite3(stock_db_path)
        self.stock_list = db_utils.read_stocks_from_db(cur)
        for code in self.stock_list:
            self.stock_list[code]["init"] = False

    def trade_sock_hook(self, body):
        """Put body data into queue
        will be proceeded by `process_queue_worker`
        """
        self.sock_queue_lock.acquire()
        self.sock_queue.append(body)
        self.sock_queue_lock.release()
        
    def process_queue_worker(self):
        """Process data in queue from Websockets
          when the packets of the registered stocks upper more than Normal through WebSockets
        """

        while True:
            idx = 0
            for idx in range(len(self.sock_queue)):
                body = json.loads(self.sock_queue[idx])
                stock_code = body["code"]

                self.interest_lock.acquire()
                if stock_code in self.interest_stocks.keys():
                    # tradeType is SELL or BUY
                    self.interest_stocks[stock_code]["price"] = body["close"] #max(self.interest_stocks[stock_code]["price"], body["close"])
                    self.interest_stocks[stock_code]["tick"]["CNT"] += 1
                    self.interest_stocks[stock_code]["tick"][body["tradeType"]] += body["volume"]
                self.interest_lock.release()

            self.sock_queue_lock.acquire()
            self.sock_queue = self.sock_queue[idx+1:]
            self.sock_queue_lock.release()
            time.sleep(1)
        
        #print("WebSocket Received: ", body)

    def prepare_trade_sock(self):
        conn_id, device_id, utk = tossinvest_sock.get_connection_headers()
        self.conn_id = conn_id
        self.device_id = device_id
        self.utk = utk

    ###### SENSITIVE ######
    
    ###### INTEREST-SENSITIVE ######
    def elevate_to_sensitive(self, code):
        print(f"{datetime.fromtimestamp(time.time()).strftime('%Y-%m-%dT%H:%M:%SZ')}: [!!!] [{code}]: SENSITIVE\nhttps://tossinvest.com/stocks/{code}/order")
        if self.open_browser:
            webbrowser.open(f"https://tossinvest.com/stocks/{code}/order")
        self.sensitive_stocks.append(code)
        self.relegate_to_normal(code, self.interest_stocks[code]["price"])


    def is_sensitive(self, code):
        """Check if the stock is raising drastically
        Ensure before the calling this function, `interest_lock` must be locked.
        """
        tick = self.interest_stocks[code]["tick"]

        cnt = tick["CNT"]
        buy = tick["BUY"]
        sell = tick["SELL"]
        if sell != 0:
            strength = (buy / sell)*100
        else:
            strength = 0 

        print(f"[{code}]: TRADE_COUNT: {cnt} | STRENGTH: {strength}", self.interest_stocks[code])
        if cnt >= INTEREST_SENSITIVE_BUY_THRESHOLD and strength >= INTEREST_SENSITIVE_STRENGTH:  
                print(f"[{code}]: TRADE_COUNT: {cnt} | STRENGTH: {strength} | SENSITIVE: ", self.interest_stocks[code], self.interest_stocks[code]["price"])
                return True
        return False

    ###### INTEREST ######
    def interest_watcher_worker(self):
        """Detect the candidate penny stocks and elevate it to SENSITIVE stocks. Level 2
        Meseaure the number of BUY and SELL during `INTEREST_WATCH_SEC`
        """
        timer = 1
        while True:
            self.interest_lock.acquire()
            print(f"-----{timer}\n")
            #print(self.interest_stocks)
            for code in list(self.interest_stocks.keys()):
                if code not in self.sensitive_stocks and self.is_sensitive(code):
                    self.elevate_to_sensitive(code)

                elif time.time() - self.interest_stocks[code]["start_time"] >= INTEREST_TIME_MAX:
                    print(f"[{code}]: Relegate to Normal from Interest")
                    self.relegate_to_normal(code, self.interest_stocks[code]["price"])
                elif timer == 0:
                    self.interest_stocks[code]["tick"] = {
                        "CNT": 0,
                        "BUY": 0,
                        "SELL": 0
                    }

            self.interest_lock.release()
            time.sleep(1)
            timer = (timer+1) % INTEREST_WATCH_SEC
            #time.sleep(INTEREST_WATCH_SEC)


    ###### NORMAL-INTEREST ######
    def relegate_to_normal(self, code, price):
        self.toss_invest_worker.del_watchlist(code)
        self.stock_list[code]["init"] = False
        #self.stock_list[code]["price"] = price
        del self.interest_stocks[code]

    def elevate_to_interest(self, stock_code, info):
        """Elevate a stock to Interest from Normal
        """
        self.interest_lock.acquire()
        self.interest_stocks[stock_code] = {
            "start_time": time.time(),
            "fail": False,
            "price": info["price"],
            "tick": {
                "CNT": 0,
                "BUY": 0,
                "SELL": 0
            }
        }
        if self.toss_invest_worker.add_watchlist(stock_code):
            print(f"[{stock_code}]: Success to elevate to Interest")
        else:
            print(f"[{stock_code}]: Fail to elevate to Interest.")
            self.interest_stocks["fail"] = True
        self.interest_lock.release()

    ###### NORMAL ######
    def normal_watcher_worker(self, target_stock_codes): 
        """ Detect the candidate penny stocks and elevate it to interest stocks from normal stocks. Level 1
        """
        timer = 0
        while True:
            normal_stock_codes = [code for code in target_stock_codes if code not in self.interest_stocks and code not in self.sensitive_stocks]
            try:
                stocks_info = tossinvest_utils.get_current_stocks_info(normal_stock_codes)
            except Exception as e:
                print("[!] Error in get response about current stocks.. Sleep 5", e)
                time.sleep(5)

            for code in normal_stock_codes:
                if code not in stocks_info.keys():
                    continue

                current_info = stocks_info[code]
                base_price = self.stock_list[code]["price"]
                current_price = current_info["price"] # Update base price to last tick

                if timer == 0 or not self.stock_list[code]["init"]: # Update base price
                    self.stock_list[code]["price"] = current_price
                    
                if self.stock_list[code]["init"]:
                    price_diff_pt = (current_price - base_price) / base_price*100
                    if current_info["volume"] > 0 and price_diff_pt >= NORMAL_INTEREST_PRICE_PT:
                        #print(base_price, current_info, stock_name)
                        self.elevate_to_interest(code, current_info)
                self.stock_list[code]["init"] = True

            timer = (timer+1) % NORMAL_DELAY_SEC
            time.sleep(1)

    def start(self):

        interest_wa_th = threading.Thread(target=self.interest_watcher_worker)
        # sen_wa_th = threading.Thread(target=self.sensitive_watcher_worker)
        interest_wa_th.start()
        # sen_wa_th.start()

        self.toss_invest_worker = tossinvest_sock.connect(self.conn_id, self.device_id, self.utk, self.trade_sock_hook)
        self.toss_invest_worker.wait_for_connection()

        queue_worker = threading.Thread(target=self.process_queue_worker)
        queue_worker.start()

        per_stocks_len = (len(self.stock_list.keys()) + self.max_thread_count - 1) // self.max_thread_count
        for idx in range(0, len(self.stock_list.keys()), per_stocks_len):
            th = threading.Thread(target=self.normal_watcher_worker, args=(list(self.stock_list.keys())[idx:idx+per_stocks_len], ) )
            th.start()

        input()
        #wa_th.join()