import logging
import pymongo
import requests
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token and webhook URL
TOKEN = '8462830033:AAEsXrjKN1CBVIN_wtPezwlhcun6YfQz82U'
WEBHOOK_URL = 'https://your-bot.onrender.com/' + TOKEN
MONGO_URI = 'mongodb+srv://your_username:your_password@cluster.mongodb.net/shopee_bot?retryWrites=true&w=majority'

# MongoDB setup
client = pymongo.MongoClient(MONGO_URI)
db = client['shopee_bot']
tracked_products = db['tracked_products']
jobs = db['jobs']

def init_db():
    # Ensure indexes for faster queries
    tracked_products.create_index([('user_id', 1), ('keyword', 1)], unique=True)
    jobs.create_index([('user_id', 1), ('keyword', 1)], unique=True)

init_db()

# Search Shopee products via scraping
def search_shopee(keyword, category=None, limit=5):
    url = "https://shopee.vn/api/v4/search/search_items"
    params = {
        'by': 'relevancy',
        'keyword': keyword,
        'limit': limit,
        'newest': 0,
        'order': 'desc',
        'page_type': 'search',
        'scenario': 'PAGE_GLOBAL_SEARCH',
        'version': 2
    }
    if category:
        params['categoryids'] = category
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://shopee.vn/search'
    }
    try:
        time.sleep(1)
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('items'):
            products = []
            for item in data['items']:
                product = item['item_basic']
                if product.get('item_rating', {}).get('rating_star', 0) >= 4:
                    price_min = product['price_min'] / 100000
                    price_max = product['price_max'] / 100000
                    discount = product.get('discount_percent', 0) / 100
                    final_price = price_min * (1 - discount)
                    products.append({
                        'name': product['name'],
                        'price': f"{price_min:.0f} - {price_max:.0f} VND (sau giảm: {final_price:.0f} VND)",
                        'link': f"https://shopee.vn/product/{product['shopid']}/{product['itemid']}",
                        'product_id': str(product['itemid']),
                        'image': f"https://down-vn.img.susercontent.com/file/{product['image']}"
                    })
            return sorted(products, key=lambda x: float(x['price'].split('sau giảm: ')[1].replace(' VND', '')))[0] if products else None
        return None
    except Exception as e:
        logger.error(f"Search error: {e}")
        return None

# Save or update product in DB
def save_product(user_id, keyword, product, category):
    count = tracked_products.count_documents({'user_id': user_id, 'bought': False})
    if count >= 10:
        return False, "Bạn đã theo dõi tối đa 10 sản phẩm. Xóa bớt để thêm mới!"
    
    final_price = float(product['price'].split('sau giảm: ')[1].replace(' VND', ''))
    tracked_products.update_one(
        {'user_id': user_id, 'keyword': keyword},
        {'$set': {
            'user_id': user_id,
            'keyword': keyword,
            'best_price': final_price,
            'current_price': final_price,
            'product_id': product['product_id'],
            'image_url': product['image'],
            'category': category,
            'bought': False,
            'last_check': datetime.now().isoformat()
        }},
        upsert=True
    )
    jobs.update_one(
        {'user_id': user_id, 'keyword': keyword},
        {'$set': {
            'user_id': user_id,
            'keyword': keyword,
            'product_id': product['product_id'],
            'category': category
        }},
        upsert=True
    )
    return True, None

# Check price update
def check_price(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id, keyword, product_id, category = job.data['user_id'], job.data['keyword'], job.data['product_id'], job.data['category']
    
    new_product = search_shopee(keyword, category)
    if new_product and new_product['product_id'] == product_id:
        new_price_str = new_product['price'].split('sau giảm: ')[1].replace(' VND', '')
        new_price = float(new_price_str)
        
        old_best = tracked_products.find_one({'user_id': user_id, 'keyword': keyword, 'product_id': product_id, 'bought': False})
        if old_best:
            old_best_price = old_best['best_price']
            if new_price < old_best_price * 0.95:
                keyboard = [[InlineKeyboardButton("Xóa theo dõi", callback_data=f"delete_{keyword}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.bot.send_photo(
                    chat_id=user_id,
                    photo=new_product['image'],
                    caption=f"Giá hời hơn cho '{keyword}'! Giá mới: {new_product['price']}\nLink: {new_product['link']}",
                    reply_markup=reply_markup
                )
                tracked_products.update_one(
                    {'user_id': user_id, 'keyword': keyword, 'product_id': product_id},
                    {'$set': {'current_price': new_price_str, 'best_price': new_price_str}}
                )

# Load jobs from DB
def load_jobs(application: Application):
    job_list = list(jobs.find())
    for job_doc in job_list:
        application.job_queue.run_repeating(
            check_price, interval=3600, first=10,
            data={'user_id': job_doc['user_id'], 'keyword': job_doc['keyword'], 'product_id': job_doc['product_id'], 'category': job_doc.get('category')}
        )

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Chào! Gõ sản phẩm bạn muốn săn, ví dụ: "điện thoại iPhone 15 category:điện tử". Tôi sẽ tìm giá tốt nhất và theo dõi!')

# Handle message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    category = None
    if 'category:' in text:
        parts = text.split('category:')
        keyword = parts[0].strip()
        category = parts[1].strip()
    else:
        keyword = text
    
    product = search_shopee(keyword, category)
    if product:
        success, error = save_product(user_id, keyword, product, category)
        if not success:
            await update.message.reply_text(error)
            return
        
        keyboard = [
            [InlineKeyboardButton("Đã mua", callback_data=f"bought_{keyword}"),
             InlineKeyboardButton("Xóa theo dõi", callback_data=f"delete_{keyword}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(
            photo=product['image'],
            caption=f"Sản phẩm tốt nhất cho '{keyword}':\nTên: {product['name']}\nGiá: {product['price']}\nLink: {product['link']}\n\nĐã lưu để theo dõi!",
            reply_markup=reply_markup
        )
        context.job_queue.run_repeating(
            check_price, interval=3600, first=10,
            data={'user_id': user_id, 'keyword': keyword, 'product_id': product['product_id'], 'category': category}
        )
    else:
        await update.message.reply_text("Không tìm thấy sản phẩm. Thử từ khóa hoặc danh mục khác!")

# List tracked products
async def list_tracked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    results = list(tracked_products.find({'user_id': user_id}))
    
    if results:
        text = "Sản phẩm đang theo dõi:\n"
        for row in results:
            status = "Đã mua" if row['bought'] else "Chưa mua"
            category = f" (Danh mục: {row['category']})" if row.get('category') else ""
            text += f"- {row['keyword']}{category}: {row['best_price']} VND ({status})\n"
    else:
        text = "Chưa theo dõi sản phẩm nào."
    await update.message.reply_text(text)

# Mark as bought
async def bought(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.args:
        keyword = ' '.join(context.args)
        tracked_products.update_one({'user_id': user_id, 'keyword': keyword}, {'$set': {'bought': True}})
        jobs.delete_one({'user_id': user_id, 'keyword': keyword})
        await update.message.reply_text(f"Đã đánh dấu '{keyword}' là đã mua.")
    else:
        await update.message.reply_text("Sử dụng: /bought <tên sản phẩm>")

# Handle button clicks
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith('bought_'):
        keyword = data.replace('bought_', '')
        tracked_products.update_one({'user_id': user_id, 'keyword': keyword}, {'$set': {'bought': True}})
        jobs.delete_one({'user_id': user_id, 'keyword': keyword})
        await query.message.reply_text(f"Đã đánh dấu '{keyword}' là đã mua.")
    elif data.startswith('delete_'):
        keyword = data.replace('delete_', '')
        tracked_products.delete_one({'user_id': user_id, 'keyword': keyword})
        jobs.delete_one({'user_id': user_id, 'keyword': keyword})
        await query.message.reply_text(f"Đã xóa '{keyword}' khỏi danh sách theo dõi.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_tracked))
    application.add_handler(CommandHandler("bought", bought))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button))
    
    load_jobs(application)
    
    application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()