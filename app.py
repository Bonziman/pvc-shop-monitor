import os
import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

PB_API_TOKEN = os.getenv("PB_API_TOKEN")  # set in Render dashboard
TARGET_OWNERS = ["TheAymane", ".AymaneGaming579"]
DATA_URL = "https://web.peacefulvanilla.club/shops/data.json"

# track stock between loops
previous_stock = {}

def send_push(title, body):
    if not PB_API_TOKEN:
        print("[WARN] PB_API_TOKEN not set")
        return
    requests.post(
        "https://api.pushbullet.com/v2/pushes",
        headers={"Access-Token": PB_API_TOKEN},
        json={"type": "note", "title": title, "body": body}
    )

def monitor_loop():
    global previous_stock
    while True:
        try:
            r = requests.get(DATA_URL, timeout=15)
            data = r.json()["data"]

            for shop in data:
                if shop["shopOwner"] not in TARGET_OWNERS:
                    continue
                shop_name = shop.get("shopName") or "Unnamed Shop"
                for recipe in shop["recipes"]:
                    result = recipe["resultItem"]["type"]
                    stock = recipe.get("stock", 0)
                    key = f"{shop['shopOwner']}::{shop_name}::{result}"

                    if key in previous_stock:
                        delta = stock - previous_stock[key]
                        if delta < 0:
                            send_push("SALE 💸",
                                      f"{shop['shopOwner']} sold {abs(delta)}x {result} at {shop_name}\nNew stock: {stock}")
                        if stock == 0 and previous_stock[key] > 0:
                            send_push("OUT OF STOCK ❌",
                                      f"{shop['shopOwner']} ran out of {result} at {shop_name}")
                    previous_stock[key] = stock

        except Exception as e:
            print("Error:", e)

        time.sleep(30)  # check every 30s

# Start monitoring in background
threading.Thread(target=monitor_loop, daemon=True).start()

@app.route("/")
def home():
    return "PVC Notifier is running ✅"


