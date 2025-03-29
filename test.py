import logging
import os
import asyncpg
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import setup_application
from aiohttp import web

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація змінних оточення
TOKEN = os.getenv("7449909716:AAEzwNAzh85-IwsNgRTB90d6NVl8OoCqB8c")
DATABASE_URL = os.getenv("postgresql://telegrambot_gxyd_user:0YNcGzqKz6D2UCdEQTaLsvuSqDhOatLy@dpg-cvk0cr0gjchc73c6grf0-a/telegrambot_gxyd")
EXCHANGE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Список товарів
tovary = [
    {"name": "Стіл дерев'яний", "price": 2500, "description": "Міцний дубовий стіл."},
    {"name": "Стілець офісний", "price": 1200, "description": "Зручний стілець для роботи."},
    {"name": "Диван кутовий", "price": 8000, "description": "Великий і комфортний диван."}
]

async def create_db():
    """Ініціалізація бази даних"""
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT,
                    item_name TEXT,
                    price INT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

async def on_startup(app: web.Application):
    """Дії при старті сервера"""
    await bot.set_webhook(f"{os.getenv('https://tg-bot-4pr.onrender.com')}/webhook")
    await create_db()

@router.message(F.text.in_({'/start', '/help'}))
async def send_welcome(message: types.Message):
    """Обробка команд /start та /help"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Переглянути товари")],
            [KeyboardButton(text="Конвертація валют")]
        ],
        resize_keyboard=True
    )
    await message.answer("🪑 Ласкаво просимо до магазину меблів!", reply_markup=keyboard)

@router.message(F.text == "Переглянути товари")
async def show_products(message: types.Message):
    """Показ товарів з інлайн кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item['name']} - {item['price']} грн", 
         callback_data=f"buy_{item['name']}")]
        for item in tovary
    ])
    await message.answer("📦 Оберіть товар:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_"))
async def process_purchase(callback: types.CallbackQuery):
    """Обробка покупки товару"""
    item_name = callback.data[4:]
    item = next((x for x in tovary if x['name'] == item_name), None)
    
    if not item:
        return await callback.answer("Товар не знайдено")
    
    try:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO orders (telegram_id, item_name, price) VALUES ($1, $2, $3)",
                callback.from_user.id, item['name'], item['price']
            )
        await callback.message.answer(f"✅ Замовлення прийнято: {item['name']} - {item['price']} грн")
    except Exception as e:
        logger.error(f"Database error: {e}")
        await callback.message.answer("⚠️ Помилка при обробці замовлення")
    finally:
        await pool.close()
        await callback.answer()

@router.message(F.text == "Конвертація валют")
async def convert_currency(message: types.Message):
    """Конвертація валют через API"""
    try:
        response = requests.get(EXCHANGE_API_URL).json()
        usd_rate = response['rates']['UAH']
        eur_rate = response['rates']['UAH'] / response['rates']['EUR']
        await message.answer(
            f"📈 Поточний курс:\n"
            f"🇺🇸 1 USD = {usd_rate:.2f} UAH\n"
            f"🇪🇺 1 EUR = {eur_rate:.2f} UAH"
        )
    except Exception as e:
        logger.error(f"Exchange API error: {e}")
        await message.answer("⚠️ Помилка отримання курсів валют")

@router.message()
async def handle_other_messages(message: types.Message):
    """Обробка інших повідомлень"""
    if message.photo:
        await message.answer("📸 Дякую за фото! Але я обробляю тільки текстові команди.")
    else:
        await message.answer("❌ Незрозуміла команда. Використовуйте кнопки меню!")

async def webhook_handler(request: web.Request):
    """Обробник вебхуків"""
    url = str(request.url)
    update = await request.json()
    await dp.feed_webhook_update(bot, update, drop_pending_updates=True)
    return web.Response()

if __name__ == "__main__":
    # Налаштування веб-додатка
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    setup_application(app, dp, bot=bot)
    
    # Запуск сервера з урахуванням порту Render
    port = int(os.environ.get("PORT", 8000))
    web.run_app(app, host="0.0.0.0", port=port)
