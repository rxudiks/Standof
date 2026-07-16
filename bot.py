import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================================================
#  КОНФИГУРАЦИЯ
# ============================================================

BOT_TOKEN = "8995316117:AAEU8xi3HR5oq4VqoGtZ-mbEdKLg0NEqdkY"
ADMIN_ID = 5858391454
MANAGER_LINK = "https://t.me/YourNickname"

# ============================================================
#  ДАННЫЕ О НОЖАХ
# ============================================================

DEFAULT_KNIVES = [
    {"id": "m9", "name": "M9 Bayonet", "emoji": "🗡️", "price": 249},
    {"id": "karambit", "name": "Karambit", "emoji": "🌀", "price": 299},
    {"id": "butterfly", "name": "Butterfly", "emoji": "🦋", "price": 349},
    {"id": "kukri", "name": "Kukri", "emoji": "🏹", "price": 199},
    {"id": "kunai", "name": "Kunai", "emoji": "🔪", "price": 179},
    {"id": "scorpion", "name": "Scorpion", "emoji": "🦂", "price": 279},
    {"id": "flip", "name": "Flip", "emoji": "🔪", "price": 219},
    {"id": "jkomando", "name": "Jkomando", "emoji": "⚔️", "price": 329},
]

# ============================================================
#  РАБОТА С ДАННЫМИ
# ============================================================

DATA_FILE = "shop_dvata.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "admin_nick": "YourNickname",
        "manager_link": MANAGER_LINK,
        "prices": {k["id"]: k["price"] for k in DEFAULT_KNIVES},
        "shop_enabled": True,
        "purchases": [],
        "referrals": {},
        "referral_reward": 10,
        "users": []
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================================
#  FSM
# ============================================================

class AdminStates(StatesGroup):
    waiting_for_nick = State()
    waiting_for_price = State()
    waiting_for_knife_id = State()
    waiting_for_link = State()
    waiting_for_referral_reward = State()
    waiting_for_mailing = State()

# ============================================================
#  ИНИЦИАЛИЗАЦИЯ
# ============================================================

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ============================================================
#  КЛАВИАТУРЫ
# ============================================================

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎁 ПОЛУЧИТЬ ПРОМОКОД", callback_data="get_promo"))
    builder.row(
        InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral_menu"),
        InlineKeyboardButton(text="📊 Мои покупки", callback_data="my_purchases")
    )
    builder.row(InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"))
    return builder.as_markup()

def get_knife_keyboard():
    data = load_data()
    builder = InlineKeyboardBuilder()
    for knife in DEFAULT_KNIVES:
        price = data["prices"].get(knife["id"], knife["price"])
        builder.row(InlineKeyboardButton(
            text=f"{knife['emoji']} {knife['name']} — {price}⭐",
            callback_data=f"knife_{knife['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()

def get_payment_keyboard(knife_id: str):
    data = load_data()
    link = data.get("manager_link", MANAGER_LINK)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 Перейти в аккаунт менеджера", url=link))
    builder.row(InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{knife_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Назад к ножам", callback_data="get_promo"))
    return builder.as_markup()

def get_admin_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить ник", callback_data="admin_nick"),
        InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data="admin_link")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Изменить цену", callback_data="admin_price"),
        InlineKeyboardButton(text="👥 Настройка рефералки", callback_data="admin_referral")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing"),
        InlineKeyboardButton(text="🔒 Магазин", callback_data="admin_toggle_shop")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📋 Все цены", callback_data="admin_prices")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 Выдать промокод", callback_data="admin_give_promo")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()

def get_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()

def get_referral_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Моя реферальная ссылка", callback_data="referral_link"),
        InlineKeyboardButton(text="📊 Мои приглашения", callback_data="referral_stats")
    )
    builder.row(InlineKeyboardButton(text="🎁 Получить бесплатный промокод", callback_data="referral_get_promo"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()

# ============================================================
#  ОБРАБОТЧИКИ КОМАНД
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    data = load_data()
    
    if message.from_user.id not in data["users"]:
        data["users"].append(message.from_user.id)
        save_data(data)
    
    args = message.text.split()
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            if referrer_id != message.from_user.id:
                if str(message.from_user.id) not in data["referrals"]:
                    data["referrals"][str(message.from_user.id)] = {
                        "invited": [],
                        "invited_by": referrer_id,
                        "promo_given": False
                    }
                    if str(referrer_id) in data["referrals"]:
                        data["referrals"][str(referrer_id)]["invited"].append(message.from_user.id)
                    else:
                        data["referrals"][str(referrer_id)] = {
                            "invited": [message.from_user.id],
                            "invited_by": None,
                            "promo_given": False
                        }
                    save_data(data)
                    await message.answer("🎉 *Ты перешёл по реферальной ссылке!*", parse_mode="Markdown")
        except ValueError:
            pass
    
    welcome_text = (
        "🔪 *Добро пожаловать в магазин промокодов Standoff 2!*\n\n"
        "Приветствую тебя, боец! Рады видеть тебя в магазине "
        "эксклюзивных промокодов.\n\n"
        "🔥 *Доступные ножи:* M9, Karambit, Butterfly, Kukri, "
        "Kunai, Scorpion, Flip, Jkomando\n\n"
        "👥 *Реферальная система:* приглашай друзей и получай "
        "промокоды БЕСПЛАТНО!"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён!")
        return
    
    data = load_data()
    text = (
        "⚙️ *Админ-панель*\n\n"
        f"👤 Ник: `{data['admin_nick']}`\n"
        f"🔒 Магазин: {'✅' if data['shop_enabled'] else '❌'}\n"
        f"📊 Покупок: {len(data['purchases'])}\n"
        f"👥 Рефералов: {len(data.get('referrals', {}))}\n"
        f"👤 Пользователей: {len(data.get('users', []))}"
    )
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Нет активных действий.")
        return
    await state.clear()
    await message.answer("✅ Отменено!", reply_markup=get_main_keyboard())

# ============================================================
#  CALLBACK'и
# ============================================================

@dp.callback_query(F.data == "get_promo")
async def callback_get_promo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    data = load_data()
    if not data["shop_enabled"]:
        await callback.answer("⛔ Магазин закрыт!", show_alert=True)
        return
    await callback.message.edit_text(
        "🗡️ *Выбери свой идеальный нож:*",
        reply_markup=get_knife_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🔪 *Главное меню*\n\nВыбери действие:"
    await callback.message.edit_text(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "ℹ️ *Как получить промокод?*\n\n"
        "1️⃣ Нажми «ПОЛУЧИТЬ ПРОМОКОД»\n"
        "2️⃣ Выбери нож\n"
        "3️⃣ Перейди в аккаунт менеджера\n"
        "4️⃣ Переведи звёзды\n"
        "5️⃣ Нажми «✅ Я оплатил»\n"
        "6️⃣ Админ выдаст промокод\n\n"
        "👥 *Реферальная система:*\n"
        "Приглашай друзей и получай промокоды БЕСПЛАТНО!"
    )
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "my_purchases")
async def callback_my_purchases(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    data = load_data()
    user_purchases = [p for p in data["purchases"] if p["user_id"] == callback.from_user.id]
    
    if not user_purchases:
        text = "📊 *История покупок*\n\nУ вас пока нет покупок."
    else:
        text = "📊 *История покупок:*\n\n"
        for purchase in user_purchases[-5:]:
            status = "✅ Выдан" if purchase.get("promo_given", False) else "⏳ Ожидает"
            text += f"🗡️ {purchase['knife_name']}\n💰 {purchase['price']} ⭐\n📌 {status}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

# ============================================================
#  ВЫБОР НОЖА
# ============================================================

@dp.callback_query(F.data.startswith("knife_"))
async def callback_knife_selected(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    knife_id = callback.data.replace("knife_", "")
    knife = next((k for k in DEFAULT_KNIVES if k["id"] == knife_id), None)
    
    if not knife:
        await callback.answer("❌ Нож не найден!", show_alert=True)
        return
    
    data = load_data()
    price = data["prices"].get(knife_id, knife["price"])
    nick = data["admin_nick"]
    
    text = (
        f"{knife['emoji']} *{knife['name']}*\n\n"
        "🔥 *Отличный выбор!*\n\n"
        f"💰 Цена: *{price} ⭐*\n\n"
        f"📤 *Переведи {price} ⭐ на аккаунт менеджера:*\n"
        f"`{nick}`\n\n"
        "👇 Нажми на кнопку ниже, чтобы перейти в аккаунт менеджера.\n"
        "После перевода нажми «✅ Я оплатил»."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_payment_keyboard(knife_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("paid_"))
async def callback_paid(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    knife_id = callback.data.replace("paid_", "")
    knife = next((k for k in DEFAULT_KNIVES if k["id"] == knife_id), None)
    
    if not knife:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    
    user = callback.from_user
    data = load_data()
    price = data["prices"].get(knife_id, knife["price"])
    
    purchase = {
        "user_id": user.id,
        "user_name": user.full_name,
        "user_username": user.username,
        "knife_id": knife_id,
        "knife_name": knife["name"],
        "knife_emoji": knife["emoji"],
        "price": price,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "promo_given": False
    }
    data["purchases"].append(purchase)
    save_data(data)
    
    await bot.send_message(
        ADMIN_ID,
        f"🆕 *НОВАЯ ОПЛАТА!*\n\n"
        f"👤 [{user.full_name}](tg://user?id={user.id})\n"
        f"🗡️ {knife['emoji']} {knife['name']}\n"
        f"💰 {price} ⭐",
        parse_mode="Markdown"
    )
    
    await callback.message.edit_text(
        f"✅ *Заявка отправлена!*\n\n"
        f"🗡️ {knife['emoji']} {knife['name']}\n"
        f"💰 {price} ⭐\n\n"
        "⏳ Админ проверит оплату и выдаст промокод.",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer("✅ Заявка отправлена!")

# ============================================================
#  РЕФЕРАЛЬНАЯ СИСТЕМА
# ============================================================

@dp.callback_query(F.data == "referral_menu")
async def referral_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    data = load_data()
    text = (
        "👥 *Реферальная система*\n\n"
        "Приглашай друзей по своей реферальной ссылке!\n"
        f"🎁 За каждые *{data.get('referral_reward', 10)}* приглашений "
        "ты получаешь БЕСПЛАТНЫЙ промокод!"
    )
    await callback.message.edit_text(text, reply_markup=get_referral_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "referral_link")
async def referral_link(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    
    data = load_data()
    ref_data = data["referrals"].get(str(user_id), {"invited": []})
    invited_count = len(ref_data.get("invited", []))
    
    text = (
        "🔗 *Твоя реферальная ссылка:*\n\n"
        f"`{link}`\n\n"
        f"👥 Приглашено: *{invited_count}* человек\n"
        f"🎯 Нужно: *{data.get('referral_reward', 10)}*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="referral_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "referral_stats")
async def referral_stats(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    data = load_data()
    
    ref_data = data["referrals"].get(str(user_id), {"invited": [], "promo_given": False})
    invited = ref_data.get("invited", [])
    invited_count = len(invited)
    needed = data.get("referral_reward", 10)
    
    text = (
        "📊 *Мои приглашения*\n\n"
        f"👥 Приглашено: *{invited_count}* человек\n"
        f"🎯 Нужно: *{needed}*\n"
        f"📌 Осталось: *{max(0, needed - invited_count)}*\n\n"
    )
    
    if invited:
        for i, inv in enumerate(invited[-5:], 1):
            text += f"{i}. ID: `{inv}`\n"
    else:
        text += "Пока нет приглашённых."
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "referral_get_promo")
async def referral_get_promo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    data = load_data()
    
    ref_data = data["referrals"].get(str(user_id), {"invited": [], "promo_given": False})
    invited_count = len(ref_data.get("invited", []))
    needed = data.get("referral_reward", 10)
    
    if ref_data.get("promo_given", False):
        await callback.answer("❌ Ты уже получил промокод!", show_alert=True)
        return
    
    if invited_count < needed:
        await callback.answer(f"❌ Нужно ещё {needed - invited_count} приглашений!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for knife in DEFAULT_KNIVES:
        builder.row(InlineKeyboardButton(
            text=f"{knife['emoji']} {knife['name']}",
            callback_data=f"ref_promo_{knife['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="referral_menu"))
    
    await callback.message.edit_text(
        "🎁 *Выбери нож для бесплатного промокода:*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("ref_promo_"))
async def referral_promo_give(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    knife_id = callback.data.replace("ref_promo_", "")
    knife = next((k for k in DEFAULT_KNIVES if k["id"] == knife_id), None)
    
    if not knife:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    data = load_data()
    
    ref_data = data["referrals"].get(str(user_id), {"invited": [], "promo_given": False})
    
    if ref_data.get("promo_given", False):
        await callback.answer("❌ Уже получено!", show_alert=True)
        return
    
    ref_data["promo_given"] = True
    data["referrals"][str(user_id)] = ref_data
    save_data(data)
    
    promo_code = f"REF-{knife_id.upper()}-{user_id % 10000}"
    
    await callback.message.edit_text(
        f"🎉 *БЕСПЛАТНЫЙ ПРОМОКОД!*\n\n"
        f"🗡️ {knife['emoji']} {knife['name']}\n"
        f"🔑 `{promo_code}`",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    
    await bot.send_message(
        ADMIN_ID,
        f"🎁 *БЕСПЛАТНЫЙ ПРОМОКОД ЗА РЕФЕРАЛОВ!*\n\n"
        f"👤 [{callback.from_user.full_name}](tg://user?id={user_id})\n"
        f"🗡️ {knife['emoji']} {knife['name']}",
        parse_mode="Markdown"
    )
    await callback.answer()

# ============================================================
#  РАССЫЛКА
# ============================================================

@dp.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    
    await state.clear()
    
    data = load_data()
    users_count = len(data.get("users", []))
    
    await callback.message.edit_text(
        "📨 *Рассылка*\n\n"
        f"👤 Всего пользователей: *{users_count}*\n\n"
        "✍️ Отправь сообщение для рассылки.\n"
        "📌 Для отмены напиши /cancel",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_mailing)
    await callback.answer()

@dp.message(AdminStates.waiting_for_mailing)
async def admin_mailing_send(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён!")
        await state.clear()
        return
    
    data = load_data()
    users = data.get("users", [])
    
    if not users:
        await message.answer("❌ Нет пользователей для рассылки!")
        await state.clear()
        return
    
    await message.answer(f"📨 Начинаю рассылку для {len(users)} пользователей...")
    
    success = 0
    fail = 0
    
    for user_id in users:
        try:
            if message.photo:
                await bot.send_photo(user_id, photo=message.photo[-1].file_id, caption=message.caption)
            elif message.document:
                await bot.send_document(user_id, document=message.document.file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(user_id, video=message.video.file_id, caption=message.caption)
            else:
                await bot.send_message(user_id, message.text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            fail += 1
            print(f"Ошибка отправки {user_id}: {e}")
    
    await message.answer(
        f"📨 *Рассылка завершена!*\n\n"
        f"✅ Отправлено: *{success}*\n"
        f"❌ Ошибок: *{fail}*",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# ============================================================
#  АДМИН-НАСТРОЙКИ
# ============================================================

@dp.callback_query(F.data == "admin_nick")
async def admin_nick(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "✏️ *Изменить ник*\n\nВведи новый ник:\n📌 /cancel для отмены",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_nick)
    await callback.answer()

@dp.message(AdminStates.waiting_for_nick)
async def admin_nick_set(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён!")
        await state.clear()
        return
    new_nick = message.text.strip()
    if not new_nick:
        await message.answer("❌ Ник не может быть пустым!")
        return
    data = load_data()
    data["admin_nick"] = new_nick
    save_data(data)
    await message.answer(f"✅ Ник изменён: `{new_nick}`", parse_mode="Markdown", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_link")
async def admin_link(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "🔗 *Изменить ссылку*\n\nВведи новую ссылку (https://t.me/...):\n📌 /cancel для отмены",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_link)
    await callback.answer()

@dp.message(AdminStates.waiting_for_link)
async def admin_link_set(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён!")
        await state.clear()
        return
    new_link = message.text.strip()
    if not new_link.startswith("https://t.me/"):
        await message.answer("❌ Ссылка должна начинаться с https://t.me/")
        return
    data = load_data()
    data["manager_link"] = new_link
    save_data(data)
    await message.answer("✅ Ссылка изменена!", reply_markup=get_admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_price")
async def admin_price(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    builder = InlineKeyboardBuilder()
    for knife in DEFAULT_KNIVES:
        price = load_data()["prices"].get(knife["id"], knife["price"])
        builder.row(InlineKeyboardButton(
            text=f"{knife['emoji']} {knife['name']} — {price}⭐",
            callback_data=f"admin_price_set_{knife['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    await callback.message.edit_text(
        "💰 *Выбери нож для изменения цены:*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_price_set_"))
async def admin_price_set(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    knife_id = callback.data.replace("admin_price_set_", "")
    knife = next((k for k in DEFAULT_KNIVES if k["id"] == knife_id), None)
    if not knife:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    await state.update_data(knife_id=knife_id)
    await callback.message.edit_text(
        f"✏️ *Изменить цену для {knife['emoji']} {knife['name']}*\n\n"
        f"Текущая цена: {load_data()['prices'].get(knife_id, knife['price'])} ⭐\n\n"
        "Введи новую цену:\n📌 /cancel для отмены",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_price)
    await callback.answer()

@dp.message(AdminStates.waiting_for_price)
async def admin_price_save(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён!")
        await state.clear()
        return
    try:
        new_price = int(message.text.strip())
        if new_price < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи число больше 0!")
        return
    data_state = await state.get_data()
    knife_id = data_state.get("knife_id")
    if not knife_id:
        await message.answer("❌ Ошибка! Напиши /cancel")
        await state.clear()
        return
    data = load_data()
    data["prices"][knife_id] = new_price
    save_data(data)
    knife = next((k for k in DEFAULT_KNIVES if k["id"] == knife_id), None)
    knife_name = knife["name"] if knife else knife_id
    await message.answer(
        f"✅ Цена для {knife_name}: *{new_price} ⭐*",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_referral")
async def admin_referral(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    data = load_data()
    reward = data.get("referral_reward", 10)
    await callback.message.edit_text(
        f"👥 *Настройка рефералки*\n\n"
        f"🎯 Сейчас нужно: *{reward}* приглашений\n\n"
        "Введи новое количество:\n📌 /cancel для отмены",
        reply_markup=get_back_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_referral_reward)
    await callback.answer()

@dp.message(AdminStates.waiting_for_referral_reward)
async def admin_referral_save(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён!")
        await state.clear()
        return
    try:
        reward = int(message.text.strip())
        if reward < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи число больше 0!")
        return
    data = load_data()
    data["referral_reward"] = reward
    save_data(data)
    await message.answer(
        f"✅ Теперь нужно *{reward}* приглашений!",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "admin_toggle_shop")
async def admin_toggle_shop(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    data = load_data()
    data["shop_enabled"] = not data["shop_enabled"]
    save_data(data)
    status = "✅ открыт" if data["shop_enabled"] else "❌ закрыт"
    await callback.message.edit_text(
        f"🔒 Магазин теперь {status}!",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    data = load_data()
    total_purchases = len(data["purchases"])
    total_stars = sum(p["price"] for p in data["purchases"])
    pending = len([p for p in data["purchases"] if not p.get("promo_given", False)])
    referrals = len(data.get("referrals", {}))
    users = len(data.get("users", []))
    text = (
        "📊 *Статистика*\n\n"
        f"📦 Ножей: {len(DEFAULT_KNIVES)}\n"
        f"📊 Покупок: {total_purchases}\n"
        f"⭐ Заработано: {total_stars} звёзд\n"
        f"⏳ Ожидают: {pending}\n"
        f"👥 Рефералов: {referrals}\n"
        f"👤 Пользователей: {users}\n"
        f"🔒 Магазин: {'✅' if data['shop_enabled'] else '❌'}"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    data = load_data()
    text = "📋 *Все цены:*\n\n"
    for knife in DEFAULT_KNIVES:
        price = data["prices"].get(knife["id"], knife["price"])
        text += f"{knife['emoji']} {knife['name']}: `{price} ⭐`\n"
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_give_promo")
async def admin_give_promo(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    data = load_data()
    pending = [p for p in data["purchases"] if not p.get("promo_given", False)]
    if not pending:
        await callback.message.edit_text("✅ Все промокоды выданы!", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
        await callback.answer()
        return
    builder = InlineKeyboardBuilder()
    for i, purchase in enumerate(pending[-10:], 1):
        builder.row(InlineKeyboardButton(
            text=f"#{i} {purchase['knife_emoji']} {purchase['knife_name']}",
            callback_data=f"give_promo_{purchase['user_id']}_{purchase['knife_id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    await callback.message.edit_text("🎁 *Выдача промокодов*", reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("give_promo_"))
async def admin_give_promo_selected(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Доступ запрещён!", show_alert=True)
        return
    await state.clear()
    parts = callback.data.split("_")
    if len(parts) >= 3:
        user_id = int(parts[2])
        knife_id = parts[3] if len(parts) > 3 else "unknown"
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    data = load_data()
    purchases = [p for p in data["purchases"] 
                if p["user_id"] == user_id and p["knife_id"] == knife_id and not p.get("promo_given", False)]
    if not purchases:
        await callback.answer("❌ Уже выдано!", show_alert=True)
        return
    purchase = purchases[-1]
    purchase["promo_given"] = True
    save_data(data)
    promo_code = f"STANDOFF2-{knife_id.upper()}-{user_id % 10000}"
    try:
        await bot.send_message(
            user_id,
            f"🎉 *Промокод получен!*\n\n"
            f"🗡️ {purchase['knife_emoji']} {purchase['knife_name']}\n"
            f"🔑 `{promo_code}`",
            parse_mode="Markdown"
        )
        await callback.message.edit_text(
            f"✅ Промокод выдан!\n👤 ID: {user_id}",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка: {e}",
            reply_markup=get_admin_keyboard(),
            parse_mode="Markdown"
        )
    await callback.answer()

# ============================================================
#  ЗАПУСК
# ============================================================

async def main():
    print("=" * 50)
    print("🤖 БОТ ЗАПУЩЕН!")
    print(f"👤 Админ ID: {ADMIN_ID}")
    print("✅ Магазин промокодов Standoff 2")
    print("👥 Реферальная система: ДА")
    print("📨 Рассылка: ДА")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())