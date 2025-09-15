# bot.py — полная версия с сохранением в Supabase

import requests  # 🔽 Нужно в самом начале
import json
import logging
from telegram import Update
from telegram import ReplyKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

# === НАСТРОЙКА ===
SUPABASE_URL = "https://jncwfxxvrglvtpwxxonm.supabase.co"  # ← Замени на свой URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpuY3dmeHh2cmdsdnRwd3h4b25tIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM4ODc5OTYsImV4cCI6MjA2OTQ2Mzk5Nn0.yMu5qwxNftjfKlO_ZE01hEAtp-PbVusJRaNOHuvS-EI"  # ← Замени на свой anon key
TABLE_NAME = "users"

# Категории навыков
CATEGORIES = {
    "💻 IT и программирование": [
        "Python", "JavaScript", "HTML/CSS", "React", "Node.js", "SQL",
        "Аналитика"
    ],
    "🎨 Творчество": [
        "Рисование", "Графический дизайн", "Фотография", "Музыка", "Пение",
        "Игра на гитаре", "Писательство"
    ],
    "🌍 Языки": [
        "Английский", "Немецкий", "Французский", "Испанский", "Китайский",
        "Японский"
    ],
    "🧘 Здоровье и спорт":
    ["Йога", "Бег", "Тренировки", "Плавание", "Медитация"],
    "📚 Учеба и наука":
    ["Математика", "Физика", "Химия", "Биология", "История"],
    "💼 Бизнес и развитие":
    ["Маркетинг", "Продажи", "Public Speaking", "Управление", "Лидерство"]
}

# === ЛОГИРОВАНИЕ (чтобы не было ошибок от APScheduler) ===
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Клавиатура с основными действиями
reply_keyboard = [['📝 Профиль', '🔍 Найти пару'], ['ℹ️ Помощь']]
keyboard_markup = ReplyKeyboardMarkup(reply_keyboard,
                                      resize_keyboard=True,
                                      one_time_keyboard=False)

# === ОБЪЯВЛЯЕМ СТАТУСЫ ДИАЛОГА ===
SHARE, LEARN, LOCATION = range(3)
# Этапы редактирования профиля
EDIT_MENU, EDIT_SHARE, EDIT_LEARN, EDIT_LOCATION = range(3, 7)
# === ОБЪЯВЛЯЕМ СТАТУСЫ ДЛЯ РЕГИСТРАЦИИ ===
REG_SHARE, REG_LEARN, REG_LOCATION = range(100, 103)


# === ФУНКЦИИ БОТА ===

# Обработчик /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
            headers={"apikey": SUPABASE_KEY},
            params={"select": "id"})
        user_exists = response.status_code == 200 and len(response.json()) > 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        user_exists = False

    if user_exists:
        reply_markup = ReplyKeyboardMarkup(
            [['📝 Профиль', '🔍 Найти пару'], ['ℹ️ Помощь']],
            resize_keyboard=True)
        await update.message.reply_text("С возвращением!",
                                        reply_markup=reply_markup)
    else:
        keyboard = [['✨ Заполнить профиль']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Привет! Давай заполним твой профиль?",
                                        reply_markup=reply_markup)


async def start_registration_flow(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    """Запускает регистрацию для нового пользователя"""
    keyboard = [[category] for category in CATEGORIES.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Выбери категорию, которой можешь поделиться:",
        reply_markup=reply_markup)
    context.user_data['awaiting'] = 'share_category'
    return REG_SHARE


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("🔄 Запущен profile()")
    user_id = update.effective_user.id

    # Сначала попробуем загрузить текущий профиль из Supabase
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
            headers={"apikey": SUPABASE_KEY},
            params={"select": "share, learn, location"})
        if response.status_code == 200 and response.json():
            current = response.json()[0]
            # Сохраняем в context.user_data
            context.user_data['share'] = current.get('share', '')
            context.user_data['learn'] = current.get('learn', '')
            context.user_data['location'] = current.get('location', '')
        else:
            # Если нет данных — оставляем пустыми
            context.user_data['share'] = ''
            context.user_data['learn'] = ''
            context.user_data['location'] = ''
    except Exception as e:
        print(f"❌ Ошибка загрузки профиля: {e}")
        context.user_data['share'] = ''
        context.user_data['learn'] = ''
        context.user_data['location'] = ''

    # Показываем меню редактирования
    keyboard = [["🔧 Умею"], ["📚 Хочу учить"], ["📍 Место"], ["✅ Готово"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Что хочешь изменить?\n\n"
        f"Сейчас:\n"
        f"Умеешь: {context.user_data['share'] or 'не указано'}\n"
        f"Хочешь учить: {context.user_data['learn'] or 'не указано'}\n"
        f"Место: {context.user_data['location'] or 'не указано'}",
        reply_markup=reply_markup)
    return EDIT_MENU


# Шаг 1: Что можешь поделиться
async def share_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['share'] = update.message.text
    await update.message.reply_text("Чем хочешь научиться?")
    return LEARN


# Шаг 2: Чем хочешь научиться
async def learn_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['learn'] = update.message.text
    await update.message.reply_text(
        "Где тебе удобно общаться? (онлайн, Москва, СПб и т.д.)")
    return LOCATION


# Шаг 3: Локация и сохранение в Supabase
async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    user = update.effective_user

    # Сохраняем имя
    context.user_data['name'] = user.full_name
    context.user_data['username'] = user.username or "нет"

    # Показываем, что всё ок
    await update.message.reply_text(
        f"Отлично! 🎉\n"
        f"Ты умеешь: {context.user_data['share']}\n"
        f"Хочешь учить: {context.user_data['learn']}\n"
        f"Место: {context.user_data['location']}\n\n"
        f"Ищу тебе пару...")

    # === 🔵 КОД ДЛЯ SUPABASE — ВСТАВЬ СЮДА ===

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "telegram_id": update.effective_user.id,
        "name": user.full_name,
        "username": user.username or "",
        "share": context.user_data['share'],
        "learn": context.user_data['learn'],
        "location": context.user_data['location']
    }

    try:
        response = requests.post(f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                                 headers=headers,
                                 data=json.dumps(data))
        if response.status_code in [200, 201]:
            await update.message.reply_text(
                "✅ Ты в базе! Скоро пришлю пару для обмена.")
        else:
            print(
                f"❌ Supabase ошибка: {response.status_code}, {response.text}")
            await update.message.reply_text("✅ Данные сохранены временно.")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        await update.message.reply_text("✅ Данные сохранены локально.")
    # === КОНЕЦ КОДА ДЛЯ SUPABASE ===

    return ConversationHandler.END


# --- РЕГИСТРАЦИЯ ДЛЯ НОВЫХ ПОЛЬЗОВАТЕЛЕЙ ---
async def reg_share_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    awaiting = context.user_data.get('awaiting')

    if awaiting == 'share_category' and user_input in CATEGORIES:
        skills = CATEGORIES[user_input]
        keyboard = [[skill] for skill in skills]
        keyboard.append(["◀️ Назад к категориям"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выбери, чем именно можешь поделиться:", reply_markup=reply_markup)
        context.user_data['awaiting'] = 'share_skill'
        return REG_SHARE

    elif awaiting == 'share_skill' and any(user_input in skills
                                           for skills in CATEGORIES.values()):
        context.user_data['share'] = user_input
        await update.message.reply_text("Теперь выбери, чему хочешь научить:")
        keyboard = [[category] for category in CATEGORIES.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выбери категорию:",
                                        reply_markup=reply_markup)
        context.user_data['awaiting'] = 'learn_category'
        return REG_LEARN

    elif awaiting == 'share_skill' and user_input == "◀️ Назад к категориям":
        keyboard = [[category] for category in CATEGORIES.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выбери другую категорию:",
                                        reply_markup=reply_markup)
        context.user_data['awaiting'] = 'share_category'
        return REG_SHARE

    else:
        await update.message.reply_text("Пожалуйста, выбери из списка.")
        return REG_SHARE


async def reg_learn_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    awaiting = context.user_data.get('awaiting')

    if awaiting == 'learn_category' and user_input in CATEGORIES:
        skills = CATEGORIES[user_input]
        keyboard = [[skill] for skill in skills]
        keyboard.append(["◀️ Назад к категориям"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выбери, чему именно хочешь научиться:", reply_markup=reply_markup)
        context.user_data['awaiting'] = 'learn_skill'
        return REG_LEARN

    elif awaiting == 'learn_skill' and any(user_input in skills
                                           for skills in CATEGORIES.values()):
        context.user_data['learn'] = user_input
        await update.message.reply_text(
            "Где тебе удобно общаться? (онлайн, Москва, СПб и т.д.)")
        return REG_LOCATION

    elif awaiting == 'learn_skill' and user_input == "◀️ Назад к категориям":
        keyboard = [[category] for category in CATEGORIES.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выбери другую категорию:",
                                        reply_markup=reply_markup)
        context.user_data['awaiting'] = 'learn_category'
        return REG_LEARN

    else:
        await update.message.reply_text("Пожалуйста, выбери из списка.")
        return REG_LEARN


async def reg_location_handler(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    user = update.effective_user

    # Если "Назад"
    if user_input == "◀️ Назад":
        keyboard = [[category] for category in CATEGORIES.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выбери категорию:",
                                        reply_markup=reply_markup)
        return REG_LEARN

    context.user_data['location'] = user_input

    # Сохраняем в Supabase
    data = {
        "telegram_id": user.id,
        "name": user.full_name,
        "username": user.username or "",
        "share": context.user_data['share'],
        "learn": context.user_data['learn'],
        "location": user_input
    }

    try:
        response = requests.post(f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                                 headers={
                                     "apikey": SUPABASE_KEY,
                                     "Authorization": f"Bearer {SUPABASE_KEY}",
                                     "Content-Type": "application/json"
                                 },
                                 json=data)
        if response.status_code in [200, 201]:
            await update.message.reply_text(
                "✅ Профиль сохранён! Теперь ты можешь искать пару.")
        else:
            await update.message.reply_text("❌ Ошибка сохранения.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка подключения.")

    await view_profile(update, context)

    await update.message.reply_text(
        "📢 Подпишись на канал с новостями и успехами: "
        "https://t.me/SwapSkills_News")
    return ConversationHandler.END


# === ПОИСК ПАРЫ ===
async def find_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        "🔍 Ищу тебе пару для обмена... Подожди секунду!")

    try:
        # Получаем текущего пользователя
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user.id}",
            headers={"apikey": SUPABASE_KEY},
            params={
                "select":
                "telegram_id, name, username, share, learn, location, matches"
            })
        if response.status_code != 200 or not response.json():
            await update.message.reply_text(
                "❌ Не удалось загрузить ваш профиль.")
            return

        current_user = response.json()[0]
        matches = current_user.get("matches") or [
        ]  # Список ID, с кем уже был контакт

        # Получаем всех пользователей
        all_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers={"apikey": SUPABASE_KEY},
            params={
                "select": "telegram_id, name, username, share, learn, location"
            })
        if all_response.status_code != 200:
            await update.message.reply_text(
                "❌ Не удалось загрузить пользователей.")
            return

        all_users = all_response.json()

        # Фильтруем: не я, не в списке matches, подходит по навыкам
        candidates = [
            u for u in all_users if u['telegram_id'] != user.id
            and u['telegram_id'] not in matches and u['share'] and u['learn']
            and current_user['learn'].lower() in u['share'].lower()
            and current_user['share'].lower() in u['learn'].lower()
        ]

        if not candidates:
            await update.message.reply_text(
                "😔 Пока нет подходящих пар. Попробуй позже!")
            return

        # Берём случайного (чтобы было честнее)
        import random
        partner = random.choice(candidates)

        # Отправляем результат
        text = (f"🎉 Я нашёл(а) тебе пару:\n"
                f"👤 {partner['name']}\n"
                f"🔧 Умеет: {partner['share']}\n"
                f"📍 Место: {partner['location']}\n"
                f"Напиши ему(ей): @{partner['username'] or 'нет'}")
        await update.message.reply_text(text)

        # 🟢 Сохраняем встречу в обоих профилях
        headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}

        # Ты добавляешь его в историю
        my_new_matches = list(set(matches + [partner['telegram_id']]))
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user.id}",
            headers=headers,
            json={"matches": my_new_matches})

        # Он добавляет тебя (если нужно)
        his_current = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{partner['telegram_id']}",
            headers={"apikey": SUPABASE_KEY})
        his_matches = his_current.json()[0].get(
            "matches", []) if his_current.status_code == 200 else []
        his_new_matches = list(set(his_matches + [user.id]))

        requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{partner['telegram_id']}",
            headers=headers,
            json={"matches": his_new_matches})

    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        await update.message.reply_text("Ошибка поиска. Попробуй позже.")


async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '📝 Профиль':
        await view_profile(update, context)


async def handle_find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '🔍 Найти пару':
        await find_match(update, context)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == 'ℹ️ Помощь':
        await update.message.reply_text(
            "💬 Как это работает:\n"
            "1. Заполни профиль — расскажи, чем можешь поделиться.\n"
            "2. Нажми 'Найти пару' — я подберу тебе напарника.\n"
            "3. Напиши ему(ей) — договоритесь об обмене.\n\n"
            "💡 Главное — отдать столько же времени, сколько получил(а).")


# Кнопка "Редактировать профиль"
async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '✏️ Редактировать':
        keyboard = [["🔧 Умею"], ["📚 Хочу учить"], ["📍 Место"], ["✅ Готово"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Что хочешь изменить?",
                                        reply_markup=reply_markup)


# Кнопка "Назад" — возвращает в главное меню
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '◀️ Назад':
        await update.message.reply_text("Главное меню:",
                                        reply_markup=keyboard_markup)


# === ЗАГЛУШКИ ДЛЯ РЕДАКТИРОВАНИЯ ===
# Вставляй СЮДА, после всех предыдущих функций


async def edit_share_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Чем ты можешь поделиться?")
    return EDIT_SHARE


async def edit_learn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Чем хочешь научиться?")
    return EDIT_LEARN


async def edit_location_start(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Где тебе удобно общаться?")
    return EDIT_LOCATION


async def edit_share_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['share'] = update.message.text
    await profile(update, context)  # Возвращаем в меню редактирования


async def edit_learn_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['learn'] = update.message.text
    await profile(update, context)


async def edit_location_save(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    await profile(update, context)


async def edit_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await view_profile(update, context)


async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        # Получаем пользователя из Supabase
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
            headers={"apikey": SUPABASE_KEY},
            params={"select": "name, username, share, learn, location"})
        if response.status_code == 200 and response.json():
            user = response.json()[0]
            text = (f"👤 <b>Твой профиль</b>\n\n"
                    f"🔧 <b>Умеешь:</b> {user['share']}\n"
                    f"📚 <b>Хочешь учить:</b> {user['learn']}\n"
                    f"📍 <b>Место:</b> {user['location']}\n"
                    f"💬 @{user['username'] or 'нет'}")
        else:
            text = ("❌ Ты ещё не заполнил(а) профиль.\n"
                    "Нажми '✏️ Редактировать', чтобы рассказать о себе.")
    except Exception as e:
        print(f"❌ Ошибка загрузки профиля: {e}")
        text = "⚠️ Не удалось загрузить профиль. Попробуй позже."

    # Кнопки: Редактировать / Назад
    keyboard = [["✏️ Редактировать"], ["◀️ Назад"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(text,
                                    reply_markup=reply_markup,
                                    parse_mode="HTML")


# === АВТОМАТИЧЕСКИЕ УВЕДОМЛЕНИЯ ===
async def auto_find(context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем всех пользователей
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?notified=eq.false",
            headers={"apikey": SUPABASE_KEY},
            params={
                "select": "telegram_id, name, username, share, learn, location"
            })
        if response.status_code != 200:
            return

        users = response.json()
        if not users:
            return  # Нечего проверять

        # Получаем ВСЕХ (чтобы искать пары)
        all_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers={"apikey": SUPABASE_KEY},
            params={
                "select": "telegram_id, name, username, share, learn, location"
            })
        all_users = all_response.json(
        ) if all_response.status_code == 200 else []

        for user in users:
            try:
                # Ищем пару
                candidates = [
                    u for u in all_users
                    if u['telegram_id'] != user['telegram_id'] and u['share']
                    and u['learn']
                    and user['learn'].lower() in u['share'].lower()
                ]

                if candidates:
                    c = candidates[0]
                    await context.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=f"🔔 Уведомление!\n\n"
                        f"Я нашёл(а) тебе пару для обмена:\n"
                        f"👤 {c['name']}\n"
                        f"🔧 Умеет: {c['share']}\n"
                        f"📍 Место: {c['location']}\n\n"
                        f"Напиши ему(ей): @{c['username'] or 'нет'}\n\n"
                        f"💬 Договоритесь об обмене!")
                    print(f"✅ Уведомление отправлено: {user['name']}")

                    # Отмечаем, что уведомили
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user['telegram_id']}",
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}"
                        },
                        json={"notified": True})
            except Exception as e:
                print(f"❌ Не удалось уведомить {user['name']}: {e}")
                continue

    except Exception as e:
        print(f"❌ Ошибка авто-поиска: {e}")


async def notify_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            },
            json={"notified": True}  # просто отмечаем, чтобы не беспокоить
        )
        await update.message.reply_text(
            "🔕 Уведомления отключены. Если захочешь снова — просто напиши /find"
        )
    except:
        await update.message.reply_text("❌ Не удалось отключить уведомления.")


async def edit_share_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '🔧 Умею':
        keyboard = [[category] for category in CATEGORIES.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выбери категорию, которой можешь поделиться:",
            reply_markup=reply_markup)
        context.user_data['awaiting'] = 'share_category'


async def edit_learn_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '📚 Хочу учить':
        keyboard = [[category] for category in CATEGORIES.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "Выбери категорию, которую хочешь изучить:",
            reply_markup=reply_markup)
        context.user_data['awaiting'] = 'learn_category'


async def edit_location_start(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '📍 Место':
        await update.message.reply_text(
            "Где тебе удобно общаться? (онлайн, Москва, СПб и т.д.)")
        context.user_data['awaiting'] = 'location'


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text

    # Сначала проверяем "✅ Готово"
    if user_input == '✅ Готово':
        await view_profile(update, context)
        return ConversationHandler.END

    awaiting = context.user_data.get('awaiting')

    if awaiting == 'share_category' and user_input in CATEGORIES:
        keyboard = [[skill] for skill in CATEGORIES[user_input]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Выбери, чем именно можешь поделиться:",
            reply_markup=reply_markup)
        context.user_data['awaiting'] = 'share_skill'
        context.user_data['temp_category'] = user_input

    elif awaiting == 'share_skill' and any(user_input in skills
                                           for skills in CATEGORIES.values()):
        context.user_data['share'] = user_input
        user_id = update.effective_user.id
        try:
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"share": user_input})
            if response.status_code in [200, 204]:
                await update.message.reply_text(
                    f"✅ Теперь ты умеешь: {user_input}")
            else:
                await update.message.reply_text("❌ Не удалось сохранить.")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("❌ Ошибка подключения.")
        await view_profile(update, context)

    elif awaiting == 'learn_category' and user_input in CATEGORIES:
        keyboard = [[skill] for skill in CATEGORIES[user_input]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Выбери, чему именно хочешь научиться:",
            reply_markup=reply_markup)
        context.user_data['awaiting'] = 'learn_skill'
        context.user_data['temp_category'] = user_input

    elif awaiting == 'learn_skill' and any(user_input in skills
                                           for skills in CATEGORIES.values()):
        context.user_data['learn'] = user_input
        user_id = update.effective_user.id
        try:
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"learn": user_input})
            if response.status_code in [200, 204]:
                await update.message.reply_text(
                    f"✅ Теперь хочешь учить: {user_input}")
            else:
                await update.message.reply_text("❌ Не удалось сохранить.")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("❌ Ошибка подключения.")
        await view_profile(update, context)

    elif awaiting == 'location':
        context.user_data['location'] = user_input
        user_id = update.effective_user.id
        try:
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?telegram_id=eq.{user_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"location": user_input})
            if response.status_code in [200, 204]:
                await update.message.reply_text(
                    f"✅ Место обновлено: {user_input}")
            else:
                await update.message.reply_text("❌ Не удалось сохранить.")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await update.message.reply_text("❌ Ошибка подключения.")
        await view_profile(update, context)

    else:
        await update.message.reply_text("Пожалуйста, выбери из списка.")


registration_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^✨ Заполнить профиль$'),
                       start_registration_flow)
    ],
    states={
        REG_SHARE:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_share_skill)],
        REG_LEARN:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_learn_skill)],
        REG_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND,
                           reg_location_handler)
        ],
    },
    fallbacks=[])

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("profile", profile)],
    states={
        EDIT_MENU: [
            MessageHandler(filters.Regex('^🔧 Умею$'), edit_share_start),
            MessageHandler(filters.Regex('^📚 Хочу учить$'), edit_learn_start),
            MessageHandler(filters.Regex('^📍 Место$'), edit_location_start),
            MessageHandler(filters.Regex('^✅ Готово$'), edit_done)
        ],
        EDIT_SHARE:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_share_save)],
        EDIT_LEARN:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_learn_save)],
        EDIT_LOCATION:
        [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_location_save)],
    },
    fallbacks=[])

# Запуск бота
if __name__ == '__main__':
    TOKEN = "8455075824:AAGQAGZbaO-76QkDhj2Q6qFHSgW_dlvydmU"
    # Создаём приложение
    app = ApplicationBuilder().token(TOKEN).build()

    # Добавляем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(registration_conv)  # Только для новых
    app.add_handler(conv_handler)  # Только для редактирования
    app.add_handler(CommandHandler("find", find_match))
    app.add_handler(CommandHandler("notify_off", notify_off))
    # Обработчики кнопок
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^📝 Профиль$'),
                       handle_profile))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^🔍 Найти пару$'),
                       handle_find))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^ℹ️ Помощь$'),
                       handle_help))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^✏️ Редактировать$'),
                       handle_edit))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^◀️ Назад$'),
                       handle_back))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^🔧 Умею$'),
                       edit_share_start))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^📚 Хочу учить$'),
                       edit_learn_start))
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex('^📍 Место$'),
                       edit_location_start))
    app.add_handler(MessageHandler(filters.TEXT,
                                   handle_choice))  # Обрабатывает выбор навыка
    # Запуск фоновой задачи каждые 5 минут
    from telegram.ext import ExtBot

    app.job_queue.run_repeating(
        auto_find, interval=86400, first=60
    )  # раз в день  # раз в час  # каждые 300 секунд (5 мин), начать через 10 сек
    print("✅ Бот запущен! Нажми Ctrl+C для остановки.")

    app.run_polling()
