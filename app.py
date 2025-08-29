import json
import time
import threading
import requests
from flask import Flask, render_template, request, jsonify
from pywebpush import webpush, WebPushException
from pushbullet import Pushbullet  # <-- Import Pushbullet

app = Flask(__name__)

# --- CONFIGURATION ---
# 1. VAPID keys for web push (from 'vapid --gen --json')
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
# 2. Pushbullet API Key for your personal notifications
PUSHBULLET_API_KEY = "o.ebw7nrnJadssASuelll5czivZqvo9Gdw" 

# 3. List of shops you want to receive PERSONAL Pushbullet notifications for
PUSHBULLET_TARGET_SHOPS = ["TheAymane", ".AymaneGaming579"]

# --- INITIALIZATION ---
pb = Pushbullet(PUSHBULLET_API_KEY) if PUSHBULLET_API_KEY != os.environ.get("PUSHBULLET_API_KEY") else None

# Safely load shop subscriptions from file
def load_subscriptions():
    try:
        with open("shop_subscriptions.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_subscriptions(subscriptions):
    with open("shop_subscriptions.json", "w") as f:
        json.dump(subscriptions, f, indent=4)

# --- FLASK ROUTES ---
@app.route("/")
def index():
    return render_template("index.html", vapid_key=VAPID_PUBLIC_KEY)

@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.json
    shop_name = data.get("shopName")
    subscription_info = data.get("subscription")

    if not shop_name or not subscription_info:
        return jsonify({"error": "Shop name and subscription info are required."}), 400

    subscriptions = load_subscriptions()
    
    # Add the new subscriber to the list for that shop
    if shop_name not in subscriptions:
        subscriptions[shop_name] = []
    
    # Avoid adding duplicate subscriptions for the same shop
    if subscription_info not in subscriptions[shop_name]:
        subscriptions[shop_name].append(subscription_info)
        save_subscriptions(subscriptions)
        print(f"New subscriber for shop: {shop_name}")

    return jsonify({"status": "subscribed", "shop": shop_name})

# --- NOTIFICATION LOGIC ---
def send_web_push_notification(sub, message):
    try:
        webpush(
            subscription_info=sub,
            data=message,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": "mailto:eloirdiwi@gmail.com"} # Update this email
        )
    except WebPushException as ex:
        print(f"Push failed for {sub.get('endpoint', 'N/A')}: {ex}")
        # If the subscription is expired or invalid, we could remove it here
        # For example, if ex.response.status_code == 410 (Gone)

def send_pushbullet_notification(title, body):
    if pb:
        try:
            print(f"Sending Pushbullet notification: {title}")
            pb.push_note(title, body)
        except Exception as e:
            print(f"Failed to send Pushbullet notification: {e}")
    else:
        print("Pushbullet not configured. Skipping notification.")

# --- BACKGROUND WORKER ---
def poll_trades():
    url = "https://web.peacefulvanilla.club/shops/data.json"
    prev_stocks = {}

    while True:
        try:
            shop_subscriptions = load_subscriptions() # Load the latest subscriptions
            data = requests.get(url, timeout=10).json()["data"]

            for shop in data:
                owner = shop["shopOwner"]
                for recipe in shop["recipes"]:
                    key = f"{owner}|{recipe['resultItem']['type']}"
                    stock = recipe["stock"]
                    old_stock = prev_stocks.get(key, stock)
                    
                    # Check for a change in stock
                    if stock != old_stock:
                        msg = None
                        if stock < old_stock:  # SALE
                            msg = f"SALE at {owner}: {recipe['resultItem']['type']} stock {old_stock} -> {stock}"
                        elif stock == 0 and old_stock > 0:  # OUT OF STOCK
                            msg = f"OUT OF STOCK at {owner}: {recipe['resultItem']['type']}"

                        if msg:
                            print(msg)
                            # 1. Send personal Pushbullet alert if it's a shop you follow
                            if owner in PUSHBULLET_TARGET_SHOPS:
                                send_pushbullet_notification(f"PVC Alert: {owner}", msg)

                            # 2. Send web push notifications to all users subscribed to this shop
                            if owner in shop_subscriptions:
                                for sub in shop_subscriptions[owner]:
                                    send_web_push_notification(sub, msg)
                    
                    prev_stocks[key] = stock

        except Exception as e:
            print(f"Error polling trades: {e}")

        time.sleep(30)

# --- START APPLICATION ---
if __name__ == "__main__":
    threading.Thread(target=poll_trades, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
