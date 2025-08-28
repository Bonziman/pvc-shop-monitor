import json
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify
from pywebpush import webpush, WebPushException

app = Flask(__name__)

# VAPID keys (generate with: `pywebpush generateVAPIDKeys`)
VAPID_PUBLIC_KEY = "YOUR_PUBLIC_KEY"
VAPID_PRIVATE_KEY = "YOUR_PRIVATE_KEY"

with open("subscriptions.json", "r") as f:
    subscriptions = json.load(f)

TARGET_SHOPS = ["TheAymane", ".AymaneGaming579"]  # Only monitor these owners


@app.route("/")
def index():
    return render_template("index.html", vapid_key=VAPID_PUBLIC_KEY)


@app.route("/subscribe", methods=["POST"])
def subscribe():
    sub = request.json
    subscriptions[sub["endpoint"]] = sub
    with open("subscriptions.json", "w") as f:
        json.dump(subscriptions, f)
    return jsonify({"status": "subscribed"})


def send_notification(sub, message):
    try:
        webpush(
            subscription_info=sub,
            data=message,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": "mailto:example@yourdomain.com"}
        )
    except WebPushException as ex:
        print("Push failed:", repr(ex))


def poll_trades():
    url = "https://web.peacefulvanilla.club/shops/data.json"
    prev_stocks = {}

    while True:
        try:
            data = requests.get(url, timeout=10).json()["data"]

            for shop in data:
                if shop["shopOwner"] not in TARGET_SHOPS:
                    continue

                for recipe in shop["recipes"]:
                    key = f"{shop['shopOwner']}|{recipe['resultItem']['type']}"
                    stock = recipe["stock"]
                    old_stock = prev_stocks.get(key, stock)

                    if stock < old_stock:  # SALE
                        msg = f"SALE at {shop['shopOwner']}: {recipe['resultItem']['type']} stock {old_stock}->{stock}"
                        print(msg)
                        for sub in subscriptions.values():
                            send_notification(sub, msg)

                    if stock == 0 and old_stock > 0:  # OUT OF STOCK
                        msg = f"OUT OF STOCK at {shop['shopOwner']}: {recipe['resultItem']['type']}"
                        print(msg)
                        for sub in subscriptions.values():
                            send_notification(sub, msg)

                    prev_stocks[key] = stock

        except Exception as e:
            print("Error polling:", e)

        time.sleep(30)


# Background worker
threading.Thread(target=poll_trades, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

