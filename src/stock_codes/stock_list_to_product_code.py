import requests
import time
import json

requests.packages.urllib3.disable_warnings(
	requests.packages.urllib3.exceptions.InsecureRequestWarning
)

def get_product_code_by_name(keyword):
    url = "https://wts-info-api.tossinvest.com/api/v3/search-all/wts-auto-complete"
    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh;q=0.5,ja;q=0.4",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "origin": "https://tossinvest.com",
        "referer": "https://tossinvest.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }
    data = {
        "query": keyword,
        "sections": [
            {
                "type": "PRODUCT",
                "option":{
                    "addIntegratedSearchResult": True
                }
            },
        ]
    }

    try:
        r = requests.post(url, headers=headers, data=json.dumps(data), allow_redirects=True, verify=False)
        query_result = json.loads(r.content)['result']
        if query_result[0]['type'] == 'PRODUCT':
            product_code = query_result[0]['data']['items'][0]['productCode']
        else:
            product_code = None
    except:
        product_code = None

    return product_code


def get_new_stocks():
    data = json.loads(requests.get("https://tr-cdn.tipranks.com/research/prod/data/penny-stocks/payload.json?ver=28869366").text)["data"]
    return [s["ticker"] for s in data]
    
if __name__ == '__main__':
    stocks_map = json.load(open("./stock_codes.json", "r"))
    new_stocks = get_new_stocks()

    #Exclude already exists
    new_stocks = set(new_stocks) - (set(new_stocks) & set(stocks_map.keys()))

    for stock_name in list(new_stocks):
        for i in range(3):
            product_code = get_product_code_by_name(stock_name)
            if product_code:
                break
            else:
                time.sleep(5)
            
        if product_code:
            print(f"{stock_name}: {product_code}")
            stocks_map[stock_name] = product_code
        else:
            print(f"{stock_name}: Fail")
        time.sleep(0.3)

    open("./stock_codes.json", "w").write(json.dumps(stocks_map))

