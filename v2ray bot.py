import logging
import asyncio
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '8156768081:AAGFhf3ME1jggGjBNl2HraCPSImCPLS8pww'
ADMIN_ID = 694246194

# تنظیمات لاگ‌ها
logging.basicConfig(level=logging.INFO)

# قیمت‌ها و کشورها
PRICES = {
    "vmess": lambda gb: gb * 3000,
    "vless": lambda gb: gb * 3000 + 20000
}

LOCATIONS = {
    "france": "\U0001F1EB\U0001F1F7 فرانسه",
    "sweden": "\U0001F1F8\U0001F1EA سوئد",
    "austria": "\U0001F1E6\U0001F1F9 اتریش",
    "netherlands": "\U0001F1F3\U0001F1F1 هلند"
}

user_orders = {}

# ساخت ربات بدون پروکسی
from aiogram.client.default import DefaultBotProperties

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

@router.message(CommandStart())
async def send_welcome(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ خرید اشتراک", callback_data="buy")],
        [InlineKeyboardButton(text="ℹ مشخصات اشتراک", callback_data="info")]
    ])
    await message.answer(
        "به ربات فروش کانفیگ‌های پرسرعت ویتوری خوش آمدید\n\n⚡ پشتیبانی 24 ساعته \n📱 مناسب برای انواع دستگاه‌ها\n\nیکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "info")
async def info_request(callback_query: CallbackQuery):
    await bot.send_message(ADMIN_ID, f"درخواست مشخصات اشتراک از طرف کاربر: {callback_query.from_user.id}")
    await callback_query.answer()
    await bot.send_message(callback_query.from_user.id, "درخواست شما ثبت شد، منتظر پاسخ مدیر باشید.", reply_markup=back_to_main())

@router.callback_query(F.data == "buy")
async def buy_subscription(callback_query: CallbackQuery):
    user_orders[callback_query.from_user.id] = {}
    keyboard = InlineKeyboardBuilder()
    for key, name in LOCATIONS.items():
        keyboard.button(text=name, callback_data=f"loc:{key}")
    keyboard.button(text="بازگشت", callback_data="main")
    keyboard.adjust(2)
    await callback_query.message.answer("کشور مورد نظر را انتخاب کنید:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("loc:"))
async def choose_service(callback_query: CallbackQuery):
    loc = callback_query.data.split(":")[1]
    user_orders[callback_query.from_user.id]['location'] = loc
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="vmess", callback_data="srv:vmess"), InlineKeyboardButton(text="vless", callback_data="srv:vless")],
        [InlineKeyboardButton(text="بازگشت", callback_data="buy")]
    ])
    await callback_query.message.answer("نوع سرویس را انتخاب کنید:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("srv:"))
async def choose_duration(callback_query: CallbackQuery):
    srv = callback_query.data.split(":")[1]
    user_orders[callback_query.from_user.id]['service'] = srv
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 ماهه", callback_data="dur:1"), InlineKeyboardButton(text="3 ماهه", callback_data="dur:3")],
        [InlineKeyboardButton(text="بازگشت", callback_data="buy")]
    ])
    await callback_query.message.answer("بازه زمانی را انتخاب کنید:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("dur:"))
async def choose_volume(callback_query: CallbackQuery):
    duration = int(callback_query.data.split(":")[1])
    user_orders[callback_query.from_user.id]['duration'] = duration
    volumes = [20, 30, 50, 80, 100] if duration == 1 else [50, 100, 200]
    keyboard = InlineKeyboardBuilder()
    for v in volumes:
        keyboard.button(text=f"{v} گیگ", callback_data=f"vol:{v}")
    keyboard.button(text="بازگشت", callback_data="buy")
    keyboard.adjust(2)
    await callback_query.message.answer("حجم مورد نظر را انتخاب کنید:", reply_markup=keyboard.as_markup())

@router.callback_query(F.data.startswith("vol:"))
async def final_step(callback_query: CallbackQuery):
    volume = int(callback_query.data.split(":")[1])
    uid = callback_query.from_user.id
    user_orders[uid]['volume'] = volume
    service = user_orders[uid]['service']
    price = PRICES[service](volume)
    user_orders[uid]['price'] = price

    summary = f"✉ مشخصات سفارش شما:\n"
    summary += f"کشور: {LOCATIONS[user_orders[uid]['location']]}\n"
    summary += f"نوع سرویس: {service}\n"
    summary += f"مدت زمان: {user_orders[uid]['duration']} ماهه\n"
    summary += f"حجم: {volume} گیگ\n"
    summary += f"مبلغ: {price:,} تومان\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ارسال فیش واریزی", callback_data="paid")],
        [InlineKeyboardButton(text="بازگشت", callback_data="buy")]
    ])

    await callback_query.message.answer(
        summary + "\nلطفا مبلغ را به شماره کارت زیر واریز کرده و سپس گزینه ارسال فیش را انتخاب کنید:\n\n6037-9918-7450-3889\nبه نام احمدرضا اله دادی",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "paid")
async def wait_for_confirm(callback_query: CallbackQuery):
    await callback_query.message.answer("لطفا فیش واریزی را ارسال کنید:")

@router.message(F.content_type == ContentType.PHOTO)
async def handle_receipt(message: Message):
    if message.from_user.id in user_orders:
        await message.forward(ADMIN_ID)
        await message.answer("فیش شما ارسال شد. لطفا منتظر تایید مدیر بمانید.")

@router.message(Command("send_config"))
async def send_config(message: Message):
    if message.from_user.id == ADMIN_ID:
        parts = message.text.split(' ', 2)
        if len(parts) == 3:
            target_user = int(parts[1])
            config = parts[2]
            await bot.send_message(target_user, f"✅ کانفیگ شما آماده است:\n\n{config}\n\nبا تشکر از خرید شما")
        else:
            await message.answer("فرمت استفاده: /send_config user_id کانفیگ")

def back_to_main():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="بازگشت به منو", callback_data="main")]])

@router.callback_query(F.data == "main")
async def back_to_main_callback(callback_query: CallbackQuery):
    await send_welcome(callback_query.message)
    await callback_query.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
