import uuid
import time
import requests
import hashlib
import random
import string
import websockets
import threading
import asyncio

TOSSINVEST_WS_URL = "wss://realtime-socket.tossinvest.com/ws"

class TossStomper():
    def __init__(self, conn_id, device_id, utk):
        self.utk = utk
        self.conn_id = conn_id
        self.device_id = device_id
        self.id = 0
        self.stock_id_maps = {}
        self.id_subscribe_status = {} # Subscribe status for each id

    def connect(self):
        return f"CONNECT\ndevice-id:{self.device_id}\nconnection-id:{self.conn_id}\nauthorization:{self.utk}\naccept-version:1.2,1.1,1.0\nheart-beat:5000,5000\n\n\x00\n"
    
    def subscribe(self, stock_code, id=None):
        destination = f"/topic/quote/stock/{stock_code}"
        if id == None:
            id = self.id
            self.stock_id_maps[stock_code] = self.id
            self.id_subscribe_status[self.id] = False
            self.id += 1

        res = f"SUBSCRIBE\nid:{id}\nreceipt:{id}-sub_receipt\ndestination:{destination}\n\n\x00\n"
        return res
    
    def server_allowed_subscribe(self, id):
        self.id_subscribe_status[id] = True
    
    def unsubscribe(self, stock_code):
        id = self.stock_id_maps[stock_code]
        res = f"UNSUBSCRIBE\nreceipt:{id}-sub_receipt\nid:{id}\n\n\x00\n"
        del self.stock_id_maps[stock_code]
        del self.id_subscribe_status[id]
        return res

    def parse_message(self, data):
        body = data.split("\n\n")[1][:-1] # Eliminate the last \n
        lines = data[:-(len(body)+2)].split("\n")[1:] # After MESSAGE
        subscription = None

        # Parse header
        # for l in lines:
        #     h_name = l.split(":")[0]
        #     h_value = l[len(h_name)+1:]
        #     if h_name == "subscription":
        #         subscription = int(h_value)
                
        return body            
    

class TossInvestWorker(threading.Thread):
    def __init__(self, ws_url, conn_id, device_id, utk, message_hook):
        threading.Thread.__init__(self)
        self.ws = None
        self.is_initialized = False
        self.ws_url = ws_url
        self.stomper = TossStomper(conn_id, device_id, utk)
        self.message_hook = message_hook
        self._ws_lock = threading.Lock()
        
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        asyncio.run(self.ws_recv_handler())

    def wait_for_connection(self):
        while not self.is_initialized:
            time.sleep(3)
        
    def add_watchlist(self, stock_code):
        """Subscribe a stock
        """
        self._ws_lock.acquire()
        asyncio.run(self.ws.send(self.stomper.subscribe(stock_code, id=None)))
        id = self.stomper.stock_id_maps[stock_code]
        while True:
            if self.stomper.id_subscribe_status[id] == True:
                break
            time.sleep(0.03)
        self._ws_lock.release()
        return self.stomper.id_subscribe_status[id]
    
    def del_watchlist(self, stock_code):
        self._ws_lock.acquire()
        asyncio.run(self.ws.send(self.stomper.unsubscribe(stock_code)))
        time.sleep(0.4)
        self._ws_lock.release()


    async def ws_recv_handler(self):
        """WebSocket Handlers
            1. Process messages from Toss server.
            2. Send message to Toss server to subscribe and unsubscribe stocks.
        """

        async with websockets.connect(self.ws_url, subprotocols=["v12.stomp", "v11.stomp", "v10.stomp"], ping_interval=500) as ws:

            #Initialize Connection
            await ws.send(self.stomper.connect())
            assert("CONNECTED" in await ws.recv())
            print("[*] Success to connect TossInvest websocket")
            self.ws = ws
            self.is_initialized = True

            while True:
                try:
                    data = await ws.recv()

                    if len(data) == 1: # Ping-Pong Heartbeat
                        await ws.send("\n")

                    elif data[:len("MESSAGE")] == "MESSAGE":
                        self.message_hook(self.stomper.parse_message(data))

                    elif data[:len("RECEIPT")] == "RECEIPT":
                        receipt_id = int(data.split("receipt-id:")[1].split("-")[0])
                        if "unsubscribe" in data:
                            pass
                        else: #subscribe
                            self.stomper.id_subscribe_status[receipt_id] = True
                    else:
                        print("[!!] Unexpected Packet: ", data)
                        

                except websockets.exceptions.ConnectionClosed as e:
                    print("TossInvestWorker Closed", e)
                    break

                except Exception as e:
                    print("TossInvestWorker: ", e)
                    break


def get_connection_headers():
    """Get connection for initializing socket connection
        Returns
            - Generated uuid
            - Generated Device Id
            - UTK (used for authorization)
    """

    url = "https://wts-api.tossinvest.com/api/v3/init"
    device_id = "WTS-"+hashlib.md5(''.join([random.choice(string.ascii_letters) for _ in range(35)]).encode()).hexdigest()
    connection_id = str(uuid.uuid4())

    headers = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ko-KR,ko;q=0.9",
        "app-version": "2024-12-26 18:33:54",
        "connection": "keep-alive",
        f"cookie": "x-toss-distribution-id=53; deviceId={device_id}",
        "host": "wts-api.tossinvest.com",
        "origin": "https://tossinvest.com",
        "referer": "https://tossinvest.com/",
        "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    r = requests.get(url, headers=headers)
    return connection_id, device_id, r.cookies["UTK"]


def connect(conn_id, device_id, utk, hook):
    """Create and connect Toss invest websockets
        Parameters
            - connection_id
            - device_id
            - UTK
        Returns
            - TossInvestWorker
    """

    worker = TossInvestWorker(TOSSINVEST_WS_URL, conn_id, device_id, utk, hook)
    worker.start()
    return worker