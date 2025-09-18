Shopee Discount Bot
A Telegram bot that searches for discounted products on Shopee Vietnam, tracks prices, and notifies users about price changes. Built with Python, it uses python-telegram-bot for Telegram integration, requests for scraping Shopee, pymongo for MongoDB Atlas storage, and is deployed on Render.
Features

Search Products: Users can search for products by keyword (e.g., "điện thoại iPhone 13") and optionally specify a category (e.g., "điện thoại iPhone 13: điện tử").
Price Tracking: Automatically tracks the best price for searched products and stores them in MongoDB.
Interactive Buttons: Inline keyboard with "Đã mua" (Mark as bought) and "Xóa theo dõi" (Remove tracking) options.
Commands:
/start: Welcome message with instructions.
/list: Show all tracked products for the user.
/bought <keyword>: Mark a product as bought.


Webhook Support: Runs 24/7 on Render using Telegram webhooks for instant responses.

Prerequisites

Python: 3.10+ (Render uses Python 3.13 by default).
MongoDB Atlas: Free tier cluster for storing product data.
Render Account: For deploying the bot (Free plan works, but sleeps after 15 minutes of inactivity).
Telegram Bot: Created via @BotFather to get a bot token.
GitHub Repository: Code hosted at https://github.com/thnguyendinh/shopee-discount-bot.

Installation

Clone Repository (optional, for local development):
git clone https://github.com/thnguyendinh/shopee-discount-bot.git
cd shopee-discount-bot


Install Dependencies:

Ensure requirements.txt contains:python-telegram-bot[webhooks]==21.4
requests==2.31.0
pymongo==4.6.0
python-dotenv==1.0.0


Run locally (if needed):pip install -r requirements.txt




Set Up MongoDB Atlas:

Create a free cluster at https://cloud.mongodb.com.
Add a database user (e.g., shopee_bot_user) with "Read and write to any database" permissions.
Allow network access from anywhere (0.0.0.0/0) in Network Access settings.
Get the connection string (MONGO_URI), e.g.:mongodb+srv://shopee_bot_user:<password>@ac-ft2pkci.swqvcex.mongodb.net/shopee_bot?retryWrites=true&w=majority




Set Up Telegram Bot:

Create a bot via @BotFather on Telegram.
Copy the bot token (e.g., 1234567890:AAH...).



Deployment on Render

Create Render Web Service:

Go to https://dashboard.render.com > New > Web Service.
Connect to GitHub repo thnguyendinh/shopee-discount-bot.
Configure:
Name: shopee-discount-bot.
Environment: Python.
Region: Singapore (or closest).
Branch: main.
Build Command: pip install -r requirements.txt.
Start Command: python shopee_discount_bot.py.
Instance Type: Free (512MB RAM, sufficient for bot).




Set Environment Variables:

In Render dashboard > Environment, add:
TOKEN: Your Telegram bot token.
WEBHOOK_URL: https://shopee-discount-bot.onrender.com/<TOKEN>.
MONGO_URI: MongoDB Atlas connection string (encode special characters in password, e.g., ! to %21).


Save and redeploy.


Set Webhook:

Open browser and visit:https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://shopee-discount-bot.onrender.com/<TOKEN>


Verify with:https://api.telegram.org/bot<TOKEN>/getWebhookInfo


Expected: {"ok":true,"result":{"url":"https://shopee-discount-bot.onrender.com/..."}}.



Usage

Start Bot:

Message /start to the bot on Telegram to see welcome message and instructions.


Search Products:

Send a keyword, e.g., "điện thoại iPhone 13".
Optional: Add category, e.g., "điện thoại iPhone 13: điện tử".
Bot returns the best-priced product (rating ≥ 4 stars) with image, price, and link.


Track Prices:

Products are automatically tracked and stored in MongoDB (shopee_bot.tracked_products).
Use /list to view all tracked products.


Manage Tracking:

Inline buttons: "Đã mua" (mark as bought), "Xóa theo dõi" (stop tracking).
Command: /bought <keyword> to mark a product as bought.



Troubleshooting

MongoDB Errors:
bad auth: Check username/password in MONGO_URI, ensure user has "Read and write" permissions.
SSL handshake failed: Verify Network Access allows 0.0.0.0/0 in MongoDB Atlas.


Webhook Errors:
Bad webhook: HTTPS URL required: Ensure WEBHOOK_URL starts with https:// and matches token.
502 Bad Gateway: Check Render logs for crashes (e.g., missing dependencies).


Shopee Scraping Errors:
403 Forbidden: Update headers/cookies in search_shopee function or use a proxy.
Edit shopee_discount_bot.py to increase time.sleep(3) or add cookies from browser (F12 > Application > Cookies > shopee.vn).
Consider proxy for stable scraping (contact for code).




Render Deploy Issues:
See https://render.com/docs/troubleshooting-deploys.
Clear build cache in Render Settings > Advanced.
Redeploy manually: Manual Deploy > Deploy latest commit.



Notes

Token Security: Generate a new token via @BotFather and update Render.
Render Free Plan: Bot sleeps after 15 minutes of inactivity but wakes on webhook requests. Upgrade to Starter ($7/month) for 24/7 uptime.
Shopee Scraping: Unofficial API may return 403 errors due to anti-bot measures. Future improvements may include proxy rotation or Shopee Open API (https://affiliate.shopee.vn/).

Contributing

Fork the repository, make changes, and submit a pull request.
Report issues or suggest features via GitHub Issues.

License
MIT License. See LICENSE for details.
