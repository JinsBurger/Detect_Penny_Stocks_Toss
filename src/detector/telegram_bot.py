import telegram
import requests
import asyncio
import json

TELEGRAM_TOKEN = 'HIDDEN'
CHAT_IDs = [0] #HIDDEN

async def send_all_messages(message):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    for chat_id in CHAT_IDs:
        await bot.sendMessage(chat_id=chat_id, text=message, parse_mode="Markdown")
