from datetime import datetime, timedelta
import json
import requests
import time


requests.packages.urllib3.disable_warnings(
	requests.packages.urllib3.exceptions.InsecureRequestWarning
)


def convert_KST_UTC(time_str):
    """Convert KST to UTC format
    Paramteters:
        - time_str: i.e 2024-12-19 06:34:00
    Returns:
        - UTC Time, i.e 2024-12-19T06:34:00Z
    """
    kst_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    utc_time = kst_time - timedelta(hours=9)
    utc_iso = utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_iso

def convert_UTC_KST(time_str):
    """Convert UTC to KST format
    Paramteters:
        - time_str: i.e 2024-12-19T06:34:00Z
    Returns:
        - UTC Time, i.e 2024-12-19 06:34:00
    """
    utc_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
    kst_time = utc_time + timedelta(hours=9)
    kst_iso = kst_time.strftime("%Y-%m-%d %H:%M:%S")
    return kst_iso


def convert_ts_UTC(timestamp):
    """Convert timestamp to KST(UTC) format
    Paramteters:
        - timestamp
    Returns:
        - UTC Time, i.e 2024-12-19T06:34:00Z
    """
    kst_time = datetime.fromtimestamp(timestamp)
    utc_time = kst_time - timedelta(hours=9)
    utc_iso = utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return utc_iso


def get_1min_candles(stock_code, kst_ts=None, UTC="", cnt=10):
    """Get candles 
        Parameters:
            - stock_code
            - time: timestamp
            - cnt: The number of candles
        Returns:
            - Candles json string
    """
    
    if kst_ts != None and UTC != "":
        UTC = convert_ts_UTC(kst_ts)

    res = json.loads(requests.get(f"https://wts-info-api.tossinvest.com/api/v2/stock-prices/{stock_code}/period-candles/min:1?count={cnt}&to={UTC}").text)
    candles = res["result"]["candles"]

    return candles

    
def get_community_comments(stock_code, cnt=20):
    """ Get toss community comments of a specific stock.
    Returns:
        - Community comments
    """

    post_data = {
            "subjectId": stock_code,
            "subjectType": "STOCK",
            "commentSortType": "RECENT"
    }

    result = {"recent_comments": []}
    for _ in range((cnt+19) // 20):
        r = None
        for __ in range(5):
            try:
                r = requests.post("https://wts-cert-api.tossinvest.com/api/v3/comments", data=json.dumps(post_data), headers={
                    "content-type": "application/json",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                })
                break
            except:
                pass

        comments_data = json.loads(r.content)["result"]

        if "count" not in result.keys():
            result["count"] = comments_data["commentCount"]

        result["recent_comments"] += [ {
            "msg": c["message"], 
            "timestamp":  int(datetime.strptime(c["updatedAt"], "%Y-%m-%dT%H:%M:%S+09:00").timestamp())
            }  for c in comments_data["comments"]["body"]
        ]

        try:
            if len(comments_data["comments"]["body"]) == 0:
                break
            post_data["commentId"] = comments_data["comments"]["body"][-1]["id"]
        except Exception as e:
            print("tossinvest_utils.py", e)
            break


    return result
    
def get_current_stocks_info(stock_codes: list):
    """ Get stocks information
    Note:
        Delisted stocks doesn't have "result" keys
    Returns:
        - stocks_info
    """
    concated_stock_codes = ','.join(stock_codes)
    result = {}
    with requests.get(f'https://wts-info-api.tossinvest.com/api/v2/stock-prices/wts?codes={concated_stock_codes}') as r:
        res = json.loads(r.text)
        if "result" in res.keys():
            stocks = res["result"]["prices"]
            for info in stocks:
                result[info["code"]] = {
                    "base": info["base"],
                    "price": info["close"],
                    "is_raising": info["changeType"] == "UP", # UP or DOWN
                    "volume": info["volume"]
                }

        else:
            return None
    return result


def daily_volume(stock_code, cnt=1):
    volume_info = json.loads(requests.get(f"https://wts-info-api.tossinvest.com/api/v1/stock-prices/{stock_code}/candle-daily?count={cnt}").text)["result"]["prices"]
    result = []

    for vol in volume_info:
        result.append({
            "date": vol["dt"],
            "volume": vol["volume"]
        })

    return result

    