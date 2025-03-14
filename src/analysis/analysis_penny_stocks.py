from datetime import datetime
import time
import requests
import sys
import json
import os
import sqlite3

sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../toss"))
import tossinvest_utils
import db_utils


requests.packages.urllib3.disable_warnings(
	requests.packages.urllib3.exceptions.InsecureRequestWarning
)

'''

Please run before Premarket

'''


def is_actived_stocks(comments):
    assert(len(comments) <= 20)
    if len(comments) == 0 or (comments[0]["timestamp"] - comments[-1]["timestamp"] >= 60*60*14): # 14 hours
        return False

    # for i in range(len(comments)-1):
    #     if (comments[i]["timestamp"] - comments[i+1]["timestamp"]) >= 60*60*24:
    #         return False
    return True
        
def get_previous_average_volume(code):
    volumes = tossinvest_utils.daily_volume(code, cnt=4)
    return sum([v["volume"] for v in volumes]) // len(volumes)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("USAGE: python3.9 ./analysis_penny_stocks.py [stock_codes.json] [output .sqlite path] ")
        sys.exit(-1)

    stock_codes =  json.load(open(sys.argv[1], "r"))
    db_path = sys.argv[2]
    db_cur, conn = db_utils.open_sqlite3(db_path, create=True)
    db_cur.executescript(open("./suspicious_stocks_init.sql", "r").read())

    for name in stock_codes:
        code = stock_codes[name]
        print(f"==== {name}:{code} ====")
        try:
            stock_info = tossinvest_utils.get_current_stocks_info([code])[code]
            if stock_info:
                price = stock_info["price"]
                comments_info = tossinvest_utils.get_community_comments(code, 20)
                avg_vol = get_previous_average_volume(code)
                #is_actived = is_actived_stocks(comments_info["recent_comments"])
                is_actived = False
                print(f"is_actived: {is_actived}")

                # Currently not active stocks is our target
                if not is_actived:
                    db_cur.execute(
                        "INSERT INTO stocks (stock_code, stock_name, avg_volume, comments_count, recent_comments_json, price)\
                            VALUES (?, ?, ?, ?, ?, ?)"
                    , (code, name, avg_vol, comments_info["count"], json.dumps(comments_info["recent_comments"]), price))
        
        except Exception as e:
            print(e)
            time.sleep(5)
            
    conn.commit()
    db_cur.close()
