from datetime import datetime
from detector import PennyStocksDectector
import sys
import telegram_bot
import asyncio

DETECTOR_THREAD_COUNT = 7

def telegram_hook(sensitive_stocks, stock_list):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass
    last_stock_name = sensitive_stocks[-1]
    stock_code = stock_list[last_stock_name]['stock_code']
    url = f"Click to Open [TossLink](https://toss.onelink.me/3563614660?pid=referral&c=conversion_securities_performance&af_param_forwarding=false&af_dp=supertoss%3A%2F%2Fsecurities%3Furl%3Dhttps%253A%252F%252Fservice.tossinvest.com%253FnextLandingUrl%253D%25252Fstocks%25252F{stock_code}%26clearHistory%3Dtrue%26swipeRefresh%3Dtrue&af_force_deeplink=true&af_web_dp=https%3A%2F%2Fcontents.tossinvest.com%2Fstocks%2F{stock_code}&af_r=https%3A%2F%2Fcontents.tossinvest.com%2Fstocks%2F{stock_code})"
    timestr = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    asyncio.run(telegram_bot.send_all_messages(f"[{timestr}] New Sensitive Stock!!: {last_stock_name}\n{url}"))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("USAGE: python3.9 ./detect_penny_stocks.py [.sqlite] ")
        sys.exit(-1)

    db_path = sys.argv[1]
    
    detector = PennyStocksDectector(db_path, DETECTOR_THREAD_COUNT, sensitive_hooks=telegram_hook, open_browser=True)
    detector.prepare_trade_sock()

    #detector = PennyStocksDectector(db_path, DETECTOR_THREAD_COUNT, sensitive_hooks=None, open_browser=False)
    detector.start()
