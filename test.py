import logging
import os
import asyncio
import asyncpg
import requests
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "7449909716:AAEzwNAzh85-IwsNgRTB90d6NVl8OoCqB8c"
DATABASE_URL = "postgresql://telegrambot_gxyd_user:0YNcGzqKz6D2UCdEQTaLsvuSqDhOatLy@dpg-cvk0cr0gjchc73c6grf0-a/telegrambot_gxyd"
EXCHANGE_API_URL = "https://api.exchangerate-api.com/v4/latest/USD"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

logging.basicConfig(level=logging.INFO)

# Приклад списку товарів
tovary = [
    {"name": "Стіл дерев'яний", "price": 2500, "description": "Міцний дубовий стіл."},
    {"name": "Стілець офісний", "price": 1200, "description": "Зручний стілець для роботи."},
    {"name": "Диван кутовий", "price": 8000, "description": "Великий і комфортний диван."}
]

async def create_db():
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                item_name TEXT,
                price INT
            )
        """)
    await pool.close()

@router.message(F.text.in_({'/start', '/help'}))
async def send_welcome(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Переглянути товари")],
            [KeyboardButton(text="Конвертація валют")]
        ],
        resize_keyboard=True
    )
    await message.answer("Ласкаво просимо до магазину меблів!", reply_markup=keyboard)

@router.message(F.text == "Переглянути товари")
async def show_products(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{item['name']} - {item['price']} грн", callback_data=f"buy_{item['name']}")]
        for item in tovary
    ])
    await message.answer("Оберіть товар:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_"))
async def order_product(callback: types.CallbackQuery):
    item_name = callback.data[4:]
    item = next((x for x in tovary if x['name'] == item_name), None)
    if item:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO orders (telegram_id, item_name, price) VALUES ($1, $2, $3)",
                               callback.from_user.id, item['name'], item['price'])
        await pool.close()
        await callback.message.answer(f"Ваше замовлення прийнято: {item['name']} - {item['price']} грн")
        await callback.answer()
    else:
        await callback.answer("Товар не знайдено.")

@router.message(F.text == "Конвертація валют")
async def exchange_rates(message: types.Message):
    response = requests.get(EXCHANGE_API_URL).json()
    usd_to_uah = response['rates']['UAH']
    eur_to_uah = response['rates']['UAH'] / response['rates']['EUR']
    await message.answer(f"Курс валют:\n💵 1 USD = {usd_to_uah:.2f} грн\n💶 1 EUR = {eur_to_uah:.2f} грн")

# Обробка будь-яких інших повідомлень
@router.message()
async def handle_unknown_messages(message: types.Message):
    if message.photo:
        await message.answer("Дякую за фото! Але я обробляю тільки команди, пов'язані з меблями та курсом валют.")
    else:
        await message.answer("Я не знаю, як відповісти на це. Використовуйте кнопки меню або команди!")

async def main():
    await create_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
