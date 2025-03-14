import requests
import json
import sys
import os

sys.path.append(os.path.abspath("../src/toss"))
import tossinvest_utils




def test_candle():
    utc_time = tossinvest_utils.convert_KST_UTC("2024-12-27 18:59:00")
    candles = tossinvest_utils.get_1min_candles("NAS0230404003", UTC=utc_time, cnt=30)
    #candles = tossinvest.get_1min_candles("US20220128004", cnt=30)
    volumes = {}
    print("DATE(KST)                VOLUME       PRICE")
    for c in candles:
        dt = tossinvest_utils.convert_UTC_KST(c['dt'])
        #volumes['dt'] = c["volume"]
        
        print(f"{dt}   %11.9f     {c['close']}"%(c['volume']))

    print(volumes)



if __name__ == '__main__':
    test_candle()