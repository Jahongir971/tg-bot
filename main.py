import aiogram, asyncio, random, sqlite3, math, logging, re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta, date
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest 

TOKEN = "7988713798:AAFjobLVOkVsInyMjERsyfNeqxLgiGrpWDc"

bot = Bot(token=TOKEN)
dp = Dispatcher()

admins = [7689058379, 6826046029, 6765230850]
CHANNEL_ID = ["@loyiharobotss", -1002640320474, "@Atomic_MANGA_Uz"]
#CHANNEL_ID = "@loyiharobotss"
ADMIN_USERNAME = "Majidxon008" #---- ADMIN USERNAME KIRITING @ BELGISI BILAN

async def set_bot_commands():
    commands = [
        BotCommand(command='start', description='Botni yangilash'),
        BotCommand(command='help', description='Bot haqida qisqacha yordam'),
        BotCommand(command='cancel', description='Buyruqlarni bekor qilish'),
        BotCommand(command='vip', description='Premium haqida malumot'),
    ]
    await bot.set_my_commands(commands)


sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_converter("DATE", lambda s: date.fromisoformat(s.decode("utf-8")))

def create_database():
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mangas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            translator TEXT,
            genre TEXT,
            type TEXT CHECK(type IN ('oddiy', 'premium', 'gibrid')) NOT NULL DEFAULT 'oddiy',
            genre_type TEXT CHECK(genre_type IN ('manga', 'manhwa', 'manhua', 'novel')) NOT NULL DEFAULT 'manga',
            chapters INTEGER,
            photo_id TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            dislike INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            premium_start INTEGER DEFAULT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manga_pdfs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manga_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            file_name TEXT,
            chapter_number INTEGER,
            is_premium INTEGER DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manga_stats(
            manga_id INTEGER NOT NULL,
            day DATE NOT NULL,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            dislikes INTEGER DEFAULT 0,
            PRIMARY KEY (manga_id, day),
            FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL UNIQUE, 
            channel_username TEXT UNIQUE, 
            required_subs INTEGER DEFAULT 0,
            current_subs INTEGER DEFAULT 0,
            start_date DATE DEFAULT CURRENT_DATE,
            end_date DATE DEFAULT NULL,
            campaign_type TEXT CHECK(campaign_type IN ('limit_based', 'time_based', 'none')) NOT NULL DEFAULT 'none',
            is_active BOOLEAN DEFAULT 0,
            message_id INTEGER DEFAULT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            type TEXT CHECK(type IN ('oddiy', 'premium', 'admin')) NOT NULL DEFAULT 'oddiy',
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            premium_end_date DATE DEFAULT NULL
        )
    ''')

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            value INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (
            user_id INTEGER PRIMARY KEY,
            banned_until DATE,
            reason TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS adminlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT,
            username TEXT,
            added_by INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.close()

@dp.message(Command("cancel"))
async def start(message: types.Message, state: FSMContext):
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 Siz vaqtincha ban qilingansiz. Keyinroq urinib ko'ring.")
        return
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Hech qanday faol buyruq topilmadi")
    else:
        await message.answer("Barcha buyruqlar bekor qilindi")
        await state.clear()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 Siz vaqtincha ban qilingansiz. Keyinroq urinib ko'ring.")
        return 
    user_id = message.from_user.id
    full_name = message.from_user.full_name
    username = message.from_user.username
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, full_name, username, type) VALUES (?, ?, ?, ?)
    """, (user_id, full_name, username, 'oddiy'))
    cursor.execute("""
        UPDATE users SET full_name = ?, username = ? WHERE user_id = ?
    """, (full_name, username, user_id))
    
    conn.commit()

    cursor.execute("SELECT type FROM users WHERE user_id = ?", (user_id,))
    user_type_row = cursor.fetchone()
    user_type = user_type_row[0] if user_type_row else 'oddiy'
    conn.close()

    if message.text and len(message.text.split()) > 1:
        deep_link_payload = message.text.split(maxsplit=1)[1]
        if deep_link_payload.startswith("manga_"):
            manga_id = int(deep_link_payload.replace("manga_", ""))
            await handle_start_from_deeplink(message, manga_id)
            return
        
    if user_type == 'admin' or message.chat.id in admins:
        keyboard_admin = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Qidiruv bo'limi", callback_data="qidiruv"), 
                 InlineKeyboardButton(text="Mangalar ro'yhati", callback_data="royhat")],
                [InlineKeyboardButton(text="Mening profilim", callback_data="profile"), 
                 InlineKeyboardButton(text="ADMIN PANELI", callback_data="admin")],
                [InlineKeyboardButton(text="REKLAMA", callback_data="reklama"),
                 InlineKeyboardButton(text="YORDAM", callback_data="help")],
            ]
        )
        await message.answer("Salom admin! Bugun nima qilamiz?", reply_markup=keyboard_admin)
    else:
        keyboard_user = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Qidiruv bo'limi", callback_data="qidiruv"), 
                 InlineKeyboardButton(text="Mangalar ro'yhati", callback_data="royhat")],
                [InlineKeyboardButton(text="Mening profilim", callback_data="profile"),
                 InlineKeyboardButton(text="REKLAMA", callback_data="reklama"),
                 InlineKeyboardButton(text="YORDAM", callback_data="help")],
            ]
        )
        await message.answer("Botga xush kelibsiz! Qanday yordam bera olaman?", reply_markup=keyboard_user)

@dp.callback_query(F.data == "help")
async def help(callback: types.CallbackQuery):
    text = (
        "✋🏻 <b>Assalomu alaykum, hurmatli foydalanuvchi!</b>\n"
        "‘Анимешник’ botimizga xush kelibsiz! 💫\n\n"
        "📥 <b>Bot orqali barcha animelarni</b> "
        "<a href='https://t.me/Atomic_MANGA_Uz'>@Atomic_MANGA_Uz</a> kanalidan "
        "oson yuklab olib tomosha qilishingiz mumkin.\n\n"
        "🛠 <b>Botdagi foydali buyruqlar:</b>\n"
        "  /help - ☎️ Qo'llab-quvvatlash ma'lumotlari\n"
        "  /vip - 💎 VIP obuna xizmati\n"
        "  /start -  botni qayta ishga tushurish\n"
        "‼️ <b>Eslatma:</b> Anime nomini yoki kodini to'g'ridan-to'g'ri yozishingiz mumkin!"
    )
    await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

@dp.message(Command('help'))
async def help_(message: Message):
    text = (
        "✋🏻 <b>Assalomu alaykum, hurmatli foydalanuvchi!</b>\n"
        "‘Анимешник’ botimizga xush kelibsiz! 💫\n\n"
        "📥 <b>Bot orqali barcha animelarni</b> "
        "<a href='https://t.me/Atomic_MANGA_Uz'>@Atomic_MANGA_Uz</a> kanalidan "
        "oson yuklab olib tomosha qilishingiz mumkin.\n\n"
        "🛠 <b>Botdagi foydali buyruqlar:</b>\n"
        "  /help - ☎️ Qo'llab-quvvatlash ma'lumotlari\n"
        "  /vip - 💎 VIP obuna xizmati\n"
        "  /qollanma - 📚 Botdan foydalanish qo'llanmasi\n"
        "‼️ <b>Eslatma:</b> Anime nomini yoki kodini to'g'ridan-to'g'ri yozishingiz mumkin!"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    await message.answer()

@dp.message(Command('vip'))
async def vip_info(message: Message):
    admin_username = ADMIN_USERNAME if ADMIN_USERNAME else "MAVJUD EMAS"
    vip_message = (
        "💎 *VIP Foydalanuvchi Rejimi* 💎\n\n"
        "'VIP obuna' sizga quyidagi afzalliklarni beradi:\n\n"
        "✅ Kanalga majburiy obuna bo'lmasdan botdan to'liq foydalanish\n"
        "✅ Faqat VIP foydalanuvchilar uchun maxsus 'Premium manga'larga to'liq kirish\n"
        "✅ Yangi qo'shilgan animelarga erta kirish imkoni\n\n"
        "📌 VIP obuna pullik. Agar siz haqiqiy muxlis bo'lsangiz va cheklovlarsiz foydalanishni istasangiz — aynan siz uchun!\n\n"
        f"👤 VIP bo'lish yoki batafsil ma'lumot olish uchun adminga yozing:\n"
        f"'@{admin_username}'"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Adminga yozish", url=f"https://t.me/{admin_username}")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="main_head")]
    ])

    await message.answer(vip_message, reply_markup=keyboard, parse_mode="Markdown")


@dp.callback_query(F.data == 'reklama')
async def show_reklama_info(callback: types.CallbackQuery):
    admin_username = ADMIN_USERNAME if ADMIN_USERNAME else "Mavjud emas"
    
    reklama_message = (
        "<b>📢 Reklama bo'limi</b>\n\n"
        "Botimiz orqali reklama joylashning 2 xil turi mavjud:\n\n"
        
        "<b>1. Kanalni botga ulash (majburiy obuna)</b>\n"
        "Foydalanuvchilar botdan foydalanishdan oldin sizning kanalingizga a'zo bo'lishadi. Bu usul obunachilar sonini tez oshirishga yordam beradi. Uch xil tarif mavjud:\n"
        "  •  <b>KUNLIK:</b> Sizning kanalingiz belgilangan muddat davomida botga ulanadi.\n"
        "  •  <b>OBUNACHI SONIGA:</b> Kanal siz xohlagan miqdorda obunachi yig'ib bo'lguncha botga ulanadi.\n"
        "  •  <b>VIP TARIF:</b> Cheksiz muddatga, doimiy obunachi yig'ish.\n\n"
        
        "<b>2. Kanalga xabar joylash</b>\n"
        "Sizning reklamangiz barcha foydalanuvchilarga alohida xabar ko'rinishida yuboriladi.\n\n"
        
        "Reklama joylash yoki tariflar haqida batafsil ma'lumot olish uchun adminga murojaat qiling:\n"
        f"<b>Admin:</b> <code>{admin_username}</code>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="main_head")]
    ])
    
    await callback.message.edit_text(reklama_message, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

async def handle_start_from_deeplink(message: types.Message, manga_id: int):
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, translator, genre, type, genre_type, chapters, photo_id, views, likes, dislike, added_date, premium_start FROM mangas WHERE id = ?",
        (manga_id,)
    )
    manga = cursor.fetchone()
    conn.close()
    if manga:
        name, translator, genre, m_type, genre_type, chapters, photo_id, views, likes, dislike, added_date, premium_start = manga
        caption = (
            f"📖 <b>{name}</b>\n\n"
            f"👨‍💻 Tarjimon: {translator}\n"
            f"📚 Janrlar: {genre}\n"
            f"🔖 Turi: {genre_type}\n"
            f"🧾 Boblar soni: {chapters}\n"
            f"👥 Auditoriya: {m_type}"
        )
        if m_type == 'gibrid' and premium_start:
            caption += f"\n🔐 Premium qismlar: {premium_start}-qismdan boshlab"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📚 Tomosha qilish", callback_data=f"show_chapters:{manga_id}:1")], 
            ]
        )
        await message.answer_photo(
            photo=photo_id,
            caption=caption,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer("Kechirasiz, ushbu ID bo'yicha manga topilmadi.")

@dp.callback_query(F.data.startswith("show_chapters:"))
async def show_chapters_pagination(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(':')
    manga_id = int(parts[1])
    current_page = int(parts[2])
    user_id = callback.from_user.id
    is_subscribed_to_channels, subscription_keyboard = await check_user_subscription(user_id, bot)
    if not is_subscribed_to_channels:
        try:
            await callback.message.edit_text(
                "Manga boblarini ko'rish uchun avval quyidagi kanallarga obuna bo'lishingiz shart:",
                reply_markup=subscription_keyboard,
                parse_mode='HTML'
            )
        except TelegramBadRequest: 
            await callback.message.answer(
                "Manga boblarini ko'rish uchun avval quyidagi kanallarga obuna bo'lishingiz shart:",
                reply_markup=subscription_keyboard,
                parse_mode='HTML'
            )
        await callback.answer("Obunani tekshiring.", show_alert=True)
        return
    
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, chapters, photo_id FROM mangas WHERE id = ?", (manga_id,))
    manga_info = cursor.fetchone()
    
    if not manga_info:
        await callback.message.edit_text("Kechirasiz, manga topilmadi.")
        await callback.answer()
        conn.close()
        return
    
    manga_name, total_chapters, photo_id = manga_info 
    
    cursor.execute("SELECT chapter_number, is_premium FROM manga_pdfs WHERE manga_id = ? ORDER BY chapter_number ASC", (manga_id,))
    all_chapters_data = cursor.fetchall()
    conn.close()
    
    if not all_chapters_data:
        await callback.message.edit_text("Bu manga uchun boblar hali qo'shilmagan.")
        await callback.answer()
        return
    
    chapters_per_page = 25 
    total_pages = math.ceil(len(all_chapters_data) / chapters_per_page)
    start_index = (current_page - 1) * chapters_per_page
    end_index = start_index + chapters_per_page
    chapters_on_current_page = all_chapters_data[start_index:end_index]
    
    keyboard_buttons = []
    row = []
    
    for i, (chapter_num, is_premium) in enumerate(chapters_on_current_page):
        button_text = f"🔐{chapter_num}" if is_premium else str(chapter_num)
        row.append(InlineKeyboardButton(text=button_text, callback_data=f"get_chapter_pdf:{manga_id}:{chapter_num}"))
        if len(row) == 5: 
            keyboard_buttons.append(row)
            row = []
            
    if row: 
        keyboard_buttons.append(row)
        
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(text="< Avvalgi", callback_data=f"show_chapters:{manga_id}:{current_page - 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text=".", callback_data="ignore")) 

    nav_row.append(InlineKeyboardButton(text=f"📚 {current_page}/{total_pages}", callback_data="ignore"))

    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi >", callback_data=f"show_chapters:{manga_id}:{current_page + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text=".", callback_data="ignore"))
        
    keyboard_buttons.append(nav_row)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    caption = f"<b>📖 {manga_name}</b> - Boblar ({current_page}/{total_pages}-sahifa):"
    
    try:
        await callback.message.edit_media(
            media=types.InputMediaPhoto(media=photo_id, caption=caption, parse_mode='HTML'),
            reply_markup=reply_markup
        )
        
    except TelegramBadRequest as e:
        logging.error(f"Media'ni tahrirlashda xato: {e}. Yangi xabar yuborilmoqda.")
        await callback.message.answer_photo(
            photo=photo_id, 
            caption=caption,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    except Exception as e:
        logging.error(f"Kutilmagan xato: {e}")
        await callback.message.answer_photo(
            photo=photo_id, 
            caption=caption,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

    await callback.answer()

@dp.callback_query(F.data.startswith("get_chapter_pdf:"))
async def get_chapter_pdf(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(':')
    manga_id = int(parts[1])
    chapter_num = int(parts[2])
    user_id = callback.from_user.id
    
    is_subscribed_to_channels, subscription_keyboard = await check_user_subscription(user_id, bot)

    if not is_subscribed_to_channels:
        await callback.message.answer(
            "PDF olish uchun avval quyidagi kanallarga obuna bo'lishingiz shart:",
            reply_markup=subscription_keyboard,
            parse_mode='HTML'
        )
        await callback.answer("Obunani tekshiring.", show_alert=True)
        return

    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT type FROM users WHERE user_id = ?", (user_id,))
    user_type_row = cursor.fetchone()
    user_type = user_type_row[0] if user_type_row else 'oddiy'

    cursor.execute("SELECT type FROM mangas WHERE id = ?", (manga_id,))
    manga_type_row = cursor.fetchone()
    manga_type = manga_type_row[0] if manga_type_row else 'oddiy'

    cursor.execute("SELECT file_id, is_premium FROM manga_pdfs WHERE manga_id = ? AND chapter_number = ?",
                  (manga_id, chapter_num))
    pdf_info = cursor.fetchone()
    conn.close()

    if pdf_info:
        file_id, is_premium_chapter = pdf_info
        if is_premium_chapter and user_type == 'oddiy':
            await callback.answer("Bu bob premium obunachilar uchun. Obuna bo'ling!", show_alert=True)
            return

        try:
            await bot.send_document(
                chat_id=user_id, 
                document=file_id,
                protect_content=True 
            )
            await callback.answer("Bob yuborildi.", show_alert=False) 
            await update_channel_subscriber_count(user_id, bot, admins=[7689058379, 6826046029,]) 
        except Exception as e:
            logging.error(f"PDF yuborishda xato, foydalanuvchi {user_id}: {e}")
            await callback.answer("Faylni yuborishda xatolik yuz berdi.", show_alert=True)
    else:
        await callback.answer("Kechirasiz, bu bob topilmadi.", show_alert=True)


async def check_user_subscription(user_id: int, bot: Bot) -> tuple[bool, InlineKeyboardMarkup | None]:
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT type, premium_end_date FROM users WHERE user_id = ?", (user_id,))
    user_info = cursor.fetchone()
    if user_info:
        user_type, premium_end_date = user_info
        if user_type == 'premium' and premium_end_date and datetime.strptime(premium_end_date, '%Y-%m-%d').date() > datetime.now().date():
            conn.close()
            return True, None
        if user_type == 'premium' and (premium_end_date is None or datetime.strptime(premium_end_date, '%Y-%m-%d').date() <= datetime.now().date()):
            cursor.execute("UPDATE users SET type = 'oddiy' WHERE user_id = ?", (user_id,))
            conn.commit()
    cursor.execute("""
        SELECT channel_id, channel_username, campaign_type
        FROM channels
        WHERE is_active = 1 AND (campaign_type = 'vip' OR end_date IS NULL OR end_date >= CURRENT_DATE)
    """)
    active_channels = cursor.fetchall()
    conn.close()

    if not active_channels:
        return True, None

    all_subscribed = True
    keyboard_buttons = []
    
    for channel_data in active_channels:
        channel_id, channel_username, campaign_type = channel_data
        
        try:
            telegram_channel_id = int(channel_id)
        except ValueError:
            logging.error(f"Xato kanal ID'si bazada: {channel_id}.")
            continue

        is_subscribed = False
        try:
            member = await bot.get_chat_member(telegram_channel_id, user_id)
            if member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                is_subscribed = True
            
        except Exception as e:
            logging.error(f"Foydalanuvchi {user_id} uchun {channel_id} kanalidagi obunani tekshirishda xato: {e}")
            is_subscribed = False

        display_channel_name = channel_username if channel_username else f"Kanal ID: {channel_id}"
        channel_link = f"https://t.me/{channel_username[1:]}" if channel_username else f"https://t.me/c/{channel_id[4:]}"
        
        if not is_subscribed:
            all_subscribed = False
            keyboard_buttons.append(
                [InlineKeyboardButton(text=f"❌ {display_channel_name}", url=channel_link)]
            )
        else:
            keyboard_buttons.append(
                [InlineKeyboardButton(text=f"✅ {display_channel_name}", url=channel_link)]
            )
    
    if all_subscribed:
        return True, None
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="Obunani tekshirish ✅", callback_data="check_subs_again")])
        return False, InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

async def update_channel_subscriber_count(user_id: int, bot: Bot, admins: list):
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_id, required_subs, current_subs
        FROM channels
        WHERE is_active = 1 AND campaign_type = 'limit_based' AND current_subs < required_subs
    """)
    limit_based_channels = cursor.fetchall()

    for channel_id_str, required_subs, current_subs in limit_based_channels:
        try:
            telegram_channel_id = int(channel_id_str)
            member = await bot.get_chat_member(telegram_channel_id, user_id)
            
            if member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
                cursor.execute("""
                    UPDATE channels
                    SET current_subs = current_subs + 1
                    WHERE channel_id = ? AND current_subs < required_subs
                """, (channel_id_str,))
                conn.commit()
                logging.info(f"Foydalanuvchi {user_id} '{channel_id_str}' kanaliga obuna bo'ldi.")
                if current_subs + 1 >= required_subs:
                    cursor.execute("UPDATE channels SET is_active = 0 WHERE channel_id = ?", (channel_id_str,))
                    conn.commit()
                    logging.info(f"Kanal {channel_id_str} kerakli obunachilar soniga yetdi va nofaol qilindi.")
                    
                    for admin_id in admins: 
                        try:
                            channel_chat = await bot.get_chat(telegram_channel_id)
                            channel_name = channel_chat.title if channel_chat.title else "Nomsiz kanal"

                            await bot.send_message(admin_id, 
                                f"🎉 Limit-based kampaniya yakunlandi!\n\n"
                                f"Kanal: <b>{channel_name}</b> (ID: <code>{channel_id_str}</code>)\n"
                                f"Kerakli obunachilar soniga yetdi ({required_subs} ta) va botdan avtomatik olib tashlandi.", 
                                parse_mode='HTML')
                        except Exception as admin_e:
                            logging.error(f"Adminlarga xabar yuborishda xato, kanal {channel_id_str}: {admin_e}")

        except Exception as e:
            logging.error(f"Kanal {channel_id_str} uchun obunachilar sonini yangilashda xato: {e}")
            conn.rollback()
    conn.close()

@dp.callback_query(F.data == "check_subs_again")
async def check_subs_again_handler(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    is_subscribed_to_channels, subscription_keyboard = await check_user_subscription(user_id, bot)

    if is_subscribed_to_channels:
        await callback.message.edit_text(
            "Siz barcha majburiy kanallarga obuna bo'lgansiz. Endi davom etishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Bosh menyuga qaytish", callback_data="main_head")]
            ])
        )
    else:
        await callback.message.edit_text(
            "Siz hali ham quyidagi kanallarga obuna bo'lmagansiz:",
            reply_markup=subscription_keyboard,
            parse_mode='HTML'
        )
    await callback.answer()

@dp.callback_query(F.data == "check_subs_again")
async def check_subs_again_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed_to_channels, subscription_keyboard = await check_user_subscription(user_id, bot)

    if is_subscribed_to_channels:
        await callback.message.edit_text(
            "Siz barcha majburiy kanallarga obuna bo'lgansiz. Endi davom etishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Bosh menyuga qaytish", callback_data="main_head")]
            ])
        )
    else:
        await callback.message.edit_text(
            "Siz hali ham quyidagi kanallarga obuna bo'lmagansiz:",
            reply_markup=subscription_keyboard,
            parse_mode='HTML'
        )
    await callback.answer()

class SearchStates(StatesGroup):
    waiting_for_manga_name = State()
    waiting_for_random_manga = State()

@dp.callback_query(F.data == 'qidiruv')
async def qidiruv_bolimi(callback: types.CallbackQuery):
    keyboard_search = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="NOM orqali qidirish", callback_data='nomtopish'), InlineKeyboardButton(text="TASODIFIY", callback_data='tastopish')],
        ]
    )
    await callback.message.edit_text("Qidiruv bo'limi", reply_markup=keyboard_search)

@dp.callback_query(F.data == 'nomtopish')
async def start_manga_name_search(callback: CallbackQuery, state: FSMContext):
    """Foydalanuvchidan manga nomini kiritishni so'raydi."""
    await callback.message.edit_text("<b>🔎 Manga nomi</b>ni kiriting:", parse_mode='HTML')
    await state.set_state(SearchStates.waiting_for_manga_name)
    await callback.answer()

@dp.message(SearchStates.waiting_for_manga_name)
async def process_manga_name_search(message: Message, state: FSMContext):
    """Kiritilgan nom bo'yicha bazadan mangani izlaydi va natijani yuboradi."""
    manga_name = message.text.strip()
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, translator, genre, type, chapters, photo_id, premium_start FROM mangas WHERE name LIKE ?", (f"%{manga_name}%",))
    manga_data = cursor.fetchone()
    conn.close()
    if manga_data:
        manga_id, name, translator, genre, m_type, chapters, photo_id, premium_start = manga_data
        caption = (
            f"📖 <b>{name}</b>\n\n"
            f"👨‍💻 Tarjimon: {translator}\n"
            f"📚 Janrlar: {genre}\n"
            f"🔖 Turi: {m_type}\n"
            f"🧾 Boblar soni: {chapters}\n"
            f"👥 Auditoriya: {m_type}"
        )
        if m_type == 'gibrid' and premium_start:
            caption += f"\n🔐 Premium qismlar: {premium_start}-qismdan boshlab"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📚 Boblarni ko'rish", callback_data=f"show_chapters:{manga_id}:1")],
            ]
        )
        try:
            await message.answer_photo(
                photo=photo_id,
                caption=caption,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Manga ma'lumotlarini yuborishda xato: {e}")
            await message.answer(
                f"<b>📖 {name}</b>\n\n"
                f"👨‍💻 Tarjimon: {translator}\n"
                f"📚 Janrlar: {genre}\n"
                f"🔖 Turi: {m_type}\n"
                f"🧾 Boblar soni: {chapters}\n"
                f"👥 Auditoriya: {m_type}",
                reply_markup=keyboard,
                parse_mode='HTML'
            )
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Ortga", callback_data="qidiruv")]
            ]
        )
        await message.answer("❌ Kechirasiz, bu nom bo'yicha manga topilmadi.", reply_markup=keyboard)

    await state.clear()

@dp.callback_query(F.data == 'tastopish')
async def find_random_manga(callback: types.CallbackQuery, state: FSMContext):
    """Birinchi tasodifiy mangani topish va yuborish."""
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mangas")
    all_manga_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not all_manga_ids:
        await callback.message.edit_text("❌ Kechirasiz, botda manga mavjud emas.")
        await callback.answer()
        return
    await state.set_state(SearchStates.waiting_for_random_manga)
    random_id = random.choice(all_manga_ids)
    await state.update_data(used_manga_ids=[random_id], all_manga_ids=all_manga_ids)
    await send_manga_by_id(callback.message, random_id, state)
    await callback.answer()

@dp.callback_query(F.data == 'get_another_random_manga', SearchStates.waiting_for_random_manga)
async def get_another_random_manga(callback: types.CallbackQuery, state: FSMContext):
    """Boshqa tasodifiy mangani topish va yuborish."""
    data = await state.get_data()
    all_manga_ids = data.get('all_manga_ids', [])
    used_manga_ids = data.get('used_manga_ids', [])
    available_manga_ids = [m_id for m_id in all_manga_ids if m_id not in used_manga_ids]
    if not available_manga_ids:
        message_text = "<b>🔚 Botda boshqa tasodifiy manga qolmadi.</b>\n\nYangi qidiruvni boshlash uchun bosh menyuga qayting."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="main_head")]
        ])
        
        try:
            await callback.message.edit_text(message_text, parse_mode='HTML', reply_markup=keyboard)
        except TelegramBadRequest as e:
            await callback.message.answer(message_text, parse_mode='HTML', reply_markup=keyboard)

        await state.clear()
        await callback.answer()
        return
    random_id = random.choice(available_manga_ids)
    used_manga_ids.append(random_id)
    await state.update_data(used_manga_ids=used_manga_ids)
    await send_manga_by_id(callback.message, random_id, state)
    await callback.answer()

async def send_manga_by_id(message: types.Message, manga_id: int, state: FSMContext):
    """ID bo'yicha manga ma'lumotlarini topib, uni yuborish."""
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, translator, genre, type, chapters, photo_id, premium_start FROM mangas WHERE id = ?",
        (manga_id,)
    )
    manga = cursor.fetchone()
    conn.close()

    if manga:
        name, translator, genre, m_type, chapters, photo_id, premium_start = manga
        
        caption = (
            f"📖 <b>{name}</b>\n\n"
            f"👨‍💻 Tarjimon: {translator}\n"
            f"📚 Janrlar: {genre}\n"
            f"🔖 Turi: {m_type}\n"
            f"🧾 Boblar soni: {chapters}"
        )
        if m_type == 'gibrid' and premium_start:
            caption += f"\n🔐 Premium qismlar: {premium_start}-qismdan boshlab"

        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📚 Boblarni ko'rish", callback_data=f"show_chapters:{manga_id}:1")],
                [types.InlineKeyboardButton(text="➡️ Boshqa tasodifiy", callback_data="get_another_random_manga")]
            ]
        )
        await message.answer_photo(
            photo=photo_id,
            caption=caption,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    else:
        await message.answer("Kechirasiz, ushbu ID bo'yicha manga topilmadi.")


MANGA_PAGE_SIZE = 10 

@dp.callback_query(F.data.startswith("royhat"))
async def paginated_manga_list(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    page = 0
    filter_type = None
    if len(parts) == 2 and parts[1].isdigit():
        page = int(parts[1])
    elif len(parts) == 2:
        filter_type = parts[1]
    elif len(parts) == 3:
        filter_type = parts[1]
        page = int(parts[2])
    offset = page * MANGA_PAGE_SIZE
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    base_query = "SELECT name, type, chapters, genre FROM mangas"
    order_clause = " ORDER BY added_date DESC "
    if filter_type == "topview":
        order_clause = " ORDER BY views DESC "
    elif filter_type == "goodrating":
        order_clause = " ORDER BY rating DESC "
    elif filter_type == "badrating":
        order_clause = " ORDER BY rating ASC "
    cursor.execute("SELECT COUNT(*) FROM mangas")
    total = cursor.fetchone()[0]

    cursor.execute(f"""
        {base_query}
        {order_clause}
        LIMIT ? OFFSET ?
    """, (MANGA_PAGE_SIZE, offset))
    mangas = cursor.fetchall()
    conn.close()
    if not mangas:
        await callback.message.edit_text("📭 Hozircha hech qanday manga mavjud emas.")
        return
    text = "📚 <b>Mangalar ro'yxati:</b>\n\n"
    for i, (name, mtype, chapters, genre) in enumerate(mangas, start=offset + 1):
        text += (
            f"<b>{i}. {name}</b>\n"
            f"🔖 Turi: {mtype.capitalize()}\n"
            f"🧾 Boblar soni: {chapters}\n"
            f"🎭 Janrlar: {genre or '—'}\n\n"
        )
    total_pages = math.ceil(total / MANGA_PAGE_SIZE)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"royhat:{page - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⛔", callback_data="none"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"royhat:{page + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="⛔", callback_data="none"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        nav_buttons
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == 'profile')
async def show_user_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT full_name, username, type, joined_date, premium_end_date FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            full_name, username, user_type, joined_date, premium_end_date = user_data
            user_role = "Foydalanuvchi"
            cursor.execute("SELECT 1 FROM adminlar WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                user_role = "Admin"
            user_rank = "Oddiy"
            if user_type == 'premium':
                user_rank = "Premium"
            tariff_info_text = "Cheksiz ∞"
            if user_type == 'premium' and premium_end_date:
                try:
                    end_date_obj = datetime.strptime(premium_end_date, '%Y-%m-%d')
                    now_date = datetime.now()
                    time_left = end_date_obj - now_date
                    
                    if time_left.total_seconds() > 0:
                        days = time_left.days
                        hours = time_left.seconds // 3600
                        minutes = (time_left.seconds % 3600) // 60
                        
                        parts = []
                        if days > 0:
                            parts.append(f"{days} kun")
                        if hours > 0:
                            parts.append(f"{hours} soat")
                        if minutes > 0:
                            parts.append(f"{minutes} daqiqa")
                        
                        if not parts:
                            tariff_info_text = "1 daqiqadan kam vaqt qoldi"
                        else:
                            tariff_info_text = ", ".join(parts) + " qoldi."
                    else:
                        tariff_info_text = "Muddati tugagan ❌"
                except (ValueError, TypeError) as e:
                    logging.error(f"user_id: {user_id} uchun premium_end_date formati noto'g'ri: {e}")
                    tariff_info_text = "Mavjud emas"
            joined_date_obj = datetime.strptime(joined_date, '%Y-%m-%d %H:%M:%S').strftime('%Y-yil %d-%b, %H:%M')
            profile_message = (
                f"<b>👤 Sizning profilingiz</b>\n\n"
                f"<b>ID:</b> <code>{user_id}</code>\n"
                f"<b>Hisob turi:</b> <b>{user_role}</b>\n"
                f"<b>Daraja:</b> <b>{user_rank}</b>\n"
                f"<b>Tarif vaqti:</b> <i>{tariff_info_text}</i>\n\n"
                f"<b>To'liq ism:</b> <code>{full_name if full_name else 'Mavjud emas'}</code>\n"
                f"<b>Username:</b> <code>@{username if username else 'Mavjud emas'}</code>\n"
                f"<b>Botga qo'shilgan sana:</b> <code>{joined_date_obj}</code>"
            )
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🎁 Premium sotib olish", callback_data="premium")],
                [types.InlineKeyboardButton(text="🔙 Ortga", callback_data="main_head")]
            ])
            await callback.message.edit_text(profile_message, reply_markup=keyboard, parse_mode='HTML')
        else:
            await callback.message.edit_text("Kechirasiz, sizning profilingiz bazada topilmadi.")
    except sqlite3.Error as e:
        logging.error(f"SQLite xatosi: {e}")
        await callback.message.edit_text("Database bilan ishlashda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
    finally:
        conn.close()
        await callback.answer()

@dp.callback_query(F.data == 'premium')
async def show_premium_info(callback: types.CallbackQuery):
    admin_username = ADMIN_USERNAME if ADMIN_USERNAME else "Mavjud emas"
    
    premium_message = (
        "<b>🎁 Premium hisob sotib olish</b>\n\n"
        "Premium hisob yordamida siz quyidagi imkoniyatlarga ega bo'lasiz:\n"
        "•  Barcha mangalarni mutlaqo **bepul** o'qish.\n"
        "•  Botdan foydalanish uchun majburiy kanallarga a'zo bo'lish shart emas.\n\n"
        "Premiumga ega bo'lish uchun adminga murojaat qiling:\n"
        f"<b>Admin:</b> <code>{admin_username}</code>"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Ortga", callback_data="profile")]
    ])
    
    await callback.message.edit_text(premium_message, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

class form(StatesGroup):
    nom_sorovi = State()
    janr_sorovi = State()
    tarjimon_sorovi = State()
    tur_sorovi = State()
    daraja_sorovi = State()


@dp.callback_query(F.data == 'admin')
async def admin_bolimi(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚  MANGALAR BO'LIMI  📚", callback_data='add_manga'), InlineKeyboardButton(text="🗂  KANALLAR BO'LIMI 🗂", callback_data='hamkor')],
            [InlineKeyboardButton(text="👨‍💻  ADMINLAR BO'LIMI  👨‍💻", callback_data='add_admin'), InlineKeyboardButton(text="💎  PREMIUM BO'LIMI  💎", callback_data='prem')],
            [InlineKeyboardButton(text="🛒  DO'KON BO'LIMI  🛒", callback_data='shop'), InlineKeyboardButton(text="💰  PROMOKOD BO'LIMI  💰", callback_data='promokod')],
            [InlineKeyboardButton(text="👥  OBUNACHILAR BO'LIMI  👥", callback_data='followers'), InlineKeyboardButton(text="📊  STATISTIKA BO'LIMI  📊", callback_data='state')],
            [InlineKeyboardButton(text="🏠 BOSH BO'LIM 🏠", callback_data="main_head"), InlineKeyboardButton(text="🏠 KANAL ULASH 🏠", callback_data="channel_")]
        ]
    )
    await callback.message.edit_text("ADMIN BO'LIMI - QUYIDAGILARDAN BIRINI TANLANG", reply_markup=keyboard)

@dp.callback_query(F.data == 'main_head')
async def start(callback: types.CallbackQuery):
    if callback.from_user.id not in admins:
        keyboard_3 = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Qidiruv bo'limi", callback_data="qidiruv"), InlineKeyboardButton(text="Mangalar ro'yhati", callback_data="royhat")], 
                [InlineKeyboardButton(text="Mening profilim", callback_data="profile")],
            ]
        )
        await callback.message.edit_text("ASOSIY BO'LIM", reply_markup=keyboard_3)
    else:
        keyboard_4 = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Qidiruv bo'limi", callback_data="qidiruv"), InlineKeyboardButton(text="Mangalar ro'yhati", callback_data="royhat")], 
                [InlineKeyboardButton(text="Mening profilim", callback_data="profile"), InlineKeyboardButton(text="ADMIN PANELI", callback_data="admin")],
            ]
        )
        await callback.message.edit_text("ASOSIY BO'LIM", reply_markup=keyboard_4)


@dp.callback_query(F.data == "add_manga")
async def add_manga(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Manga qo'shish ➕", callback_data="add"), InlineKeyboardButton(text="➖ Manga o'chirish ➖", callback_data='remove')],
            [InlineKeyboardButton(text="📜 Mangalar ro'yhati", callback_data="list"), InlineKeyboardButton(text="⚙️ MANGA SOZLAMALARI ⚙️", callback_data='settings_manga')],
            [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data='admin')]
        ]
    )
    await callback.message.edit_text("MANGA BO'LIMI", reply_markup=keyboard)

@dp.callback_query(F.data == "channel_")
async def channel_(callback: types.CallbackQuery):
    text = (
        "Kanal boshqaruvi bo'limi\n\n"
        "- 'Kanal qo'shish' - Yangi kanal qo'shish\n"
        "- 'Kanal o'chirish' - Mavjud kanalni o'chirish\n"
        "- 'Kanallar ro'yxati' - Qo'shilgan barcha kanallar ro'yxatini ko'rish"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kanal qo'shish", callback_data="add_channel_"),
         InlineKeyboardButton(text="Kanal o'chirish", callback_data="delete_channel_")],
        [InlineKeyboardButton(text="Kanallar ro'yxati", callback_data="list_channels_"),
         InlineKeyboardButton(text="Ortga", callback_data="main_head")],
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

class ChannelAdd(StatesGroup):
    waiting_for_channel = State()
@dp.callback_query(F.data == "add_channel_")
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Iltimos, kanal username yoki ID kiriting (masalan: @kanal_nomi yoki -1001234567890):")
    await state.set_state(ChannelAdd.waiting_for_channel)
    await callback.answer()
@dp.message(ChannelAdd.waiting_for_channel)
async def save_channel_id(message: types.Message, state: FSMContext):
    channel_data = message.text.strip()
    CHANNEL_ID.append(channel_data)

    await message.answer(f"Kanal muvaffaqiyatli qo'shildi!\nJoriy ro'yxat: {CHANNEL_ID}")
    await state.clear()

class ChannelDelete(StatesGroup):
    waiting_for_channel = State()
@dp.callback_query(F.data == "delete_channel_")
async def delete_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("O'chirmoqchi bo'lgan kanal username yoki ID sini kiriting:")
    await state.set_state(ChannelDelete.waiting_for_channel)
    await callback.answer()
@dp.message(ChannelDelete.waiting_for_channel)
async def delete_channel_id(message: types.Message, state: FSMContext):
    channel_data = message.text.strip()

    if channel_data in CHANNEL_ID:
        CHANNEL_ID.remove(channel_data)
        await message.answer(f"Kanal '{channel_data}' muvaffaqiyatli o'chirildi!\nJoriy ro'yxat: {CHANNEL_ID}")
    else:
        await message.answer(f"Kanal '{channel_data}' ro'yxatda topilmadi!")

    await state.clear()

@dp.callback_query(F.data == "list_channels_")
async def list_channels(callback: types.CallbackQuery):
    try:
        if not CHANNEL_ID:
            await callback.message.edit_text("📋 Hozircha hech qanday kanal qo'shilmagan.", parse_mode="HTML")
            await callback.answer()
            return

        text = "📋 <b>Kanallar ro'yxati:</b>\n\n"
        buttons = []
        
        for index, channel in enumerate(CHANNEL_ID, start=1):
            try:
                chat = await bot.get_chat(channel)
                channel_name = chat.title or "Noma'lum"
                members_count = await bot.get_chat_members_count(channel) if chat else 0
                text += f"{index}. <b>{channel_name}</b> (@{chat.username})\n👥 Obunachilar: {members_count}\n🆔 ID: <code>{channel}</code>\n\n"
                buttons.append(
                    [InlineKeyboardButton(
                        text=f" {channel_name}",
                        callback_data=f"delete_channel_{channel}"
                    )]
                )
            except Exception as e:
                text += f"{index} {channel} \n\n"
                continue

        buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin")])
        
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Xato yuz berdi: {str(e)}", show_alert=True)

class MangaListForm(StatesGroup):
    waiting_for_manga_name = State()

@dp.callback_query(F.data == 'list')
async def royhat_bolimi(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    page = 0
    filter_type = None
    if len(parts) == 2 and parts[1].isdigit():
        page = int(parts[1])
    elif len(parts) == 2:
        filter_type = parts[1]
    elif len(parts) == 3:
        filter_type = parts[1]
        page = int(parts[2])
    offset = page * MANGA_PAGE_SIZE
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    base_query = "SELECT name, type, chapters, genre FROM mangas"
    order_clause = " ORDER BY added_date DESC "
    if filter_type == "topview":
        order_clause = " ORDER BY views DESC "
    elif filter_type == "goodrating":
        order_clause = " ORDER BY rating DESC "
    elif filter_type == "badrating":
        order_clause = " ORDER BY rating ASC "
    cursor.execute("SELECT COUNT(*) FROM mangas")
    total = cursor.fetchone()[0]

    cursor.execute(f"""
        {base_query}
        {order_clause}
        LIMIT ? OFFSET ?
    """, (MANGA_PAGE_SIZE, offset))
    mangas = cursor.fetchall()
    conn.close()
    if not mangas:
        await callback.message.edit_text("📭 Hozircha hech qanday manga mavjud emas.")
        return
    text = "📚 <b>Mangalar ro'yxati:</b>\n\n"
    for i, (name, mtype, chapters, genre) in enumerate(mangas, start=offset + 1):
        text += (
            f"<b>{i}. {name}</b>\n"
            f"🔖 Turi: {mtype.capitalize()}\n"
            f"🧾 Boblar soni: {chapters}\n"
            f"🎭 Janrlar: {genre or '—'}\n\n"
        )
    total_pages = math.ceil(total / MANGA_PAGE_SIZE)
    filter_buttons = [
        InlineKeyboardButton(text="🔥 Eng ko'p ko'rilganlar", callback_data="royhat_sort:topview:0"),
        InlineKeyboardButton(text="👍 Yaxshi baholanganlar", callback_data="royhat_sort:goodrating:0"),
        InlineKeyboardButton(text="👎 Yomon baholanganlar", callback_data="royhat_sort:badrating:0"),
    ]
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="<-", callback_data=f"royhat:{page - 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="-", callback_data="none"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="->", callback_data=f"royhat:{page + 1}"))
    else:
        nav_buttons.append(InlineKeyboardButton(text="-", callback_data="none"))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        filter_buttons,
        nav_buttons
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)


class MangaDeleteForm(StatesGroup):
    waiting_for_manga_name = State()
    waiting_for_delete_choice = State()
    waiting_for_chapter_number = State()

@dp.callback_query(F.data == 'remove')
async def start_manga_removal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("O'chirmoqchi bo'lgan manga nomini kiriting:")
    await state.set_state(MangaDeleteForm.waiting_for_manga_name)

@dp.message(MangaDeleteForm.waiting_for_manga_name)
async def confirm_manga_deletion(message: types.Message, state: FSMContext):
    manga_name = message.text.strip()
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM mangas WHERE name = ?", (manga_name,))
    manga = cursor.fetchone()
    conn.close()
    if not manga:
        await message.answer(f"❌ '{manga_name}' nomli manga topilmadi.")
        return
    await state.update_data(manga_id=manga[0], manga_name=manga_name)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 BOB O'CHIRISH", callback_data="delete_chapter")],
        [InlineKeyboardButton(text="🗑 BUTKUL O'CHIRISH", callback_data="delete_entire")]
    ])
    await message.answer(f"'{manga_name}' uchun amalni tanlang:", reply_markup=keyboard)
    await state.set_state(MangaDeleteForm.waiting_for_delete_choice)

@dp.callback_query(MangaDeleteForm.waiting_for_delete_choice, F.data == "delete_chapter")
async def ask_chapter_to_delete(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Qaysi bobni o'chirmoqchisiz? (raqam kiriting)")
    await state.set_state(MangaDeleteForm.waiting_for_chapter_number)

@dp.message(MangaDeleteForm.waiting_for_chapter_number)
async def delete_specific_chapter(message: types.Message, state: FSMContext):
    try:
        chapter = int(message.text)
        data = await state.get_data()
        manga_id = data["manga_id"]
        conn = sqlite3.connect('manganest.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM manga_pdfs WHERE manga_id = ? AND chapter_number = ?", (manga_id, chapter))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted:
            await message.answer(f"✅ {data['manga_name']} - {chapter}-bob o'chirildi.")
        else:
            await message.answer(f"❌ {chapter}-bob topilmadi.")
    except ValueError:
        await message.answer("❗ Raqam kiriting.")
    finally:
        await state.clear()

@dp.callback_query(MangaDeleteForm.waiting_for_delete_choice, F.data == "delete_entire")
async def delete_entire_manga(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    manga_id = data["manga_id"]
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mangas WHERE id = ?", (manga_id,))
    conn.commit()
    conn.close()
    await callback.message.answer(f"🗑 '{data['manga_name']}' va barcha ma'lumotlari o'chirildi.")
    await state.clear()

class MangaForm(StatesGroup):
    choosing_audience = State()
    waiting_for_photo = State()
    waiting_for_name = State()
    waiting_for_translator = State()
    waiting_for_chapters = State()
    waiting_for_type = State()
    waiting_for_genres = State()
    waiting_for_pdf = State()

@dp.callback_query(F.data == "add")
async def start_adding_manga(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ODDIY OBUNACHILAR UCHUN", callback_data="audience:oddiy")],
            [InlineKeyboardButton(text="PREMIUM OBUNACHILAR UCHUN", callback_data="audience:premium")],
            [InlineKeyboardButton(text="GIBRID (ARALASH)", callback_data="audience:gibrid")],
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="cancel")]
        ]
    )
    await callback.message.edit_text(
        "Manga turini tanlang:",
        reply_markup=keyboard
    )
    await state.set_state(MangaForm.choosing_audience)
    await callback.answer() 
@dp.callback_query(MangaForm.choosing_audience, F.data.startswith("audience:"))
async def process_audience(callback: CallbackQuery, state: FSMContext):
    audience_type = callback.data.split(":")[1]
    await state.update_data(audience_type=audience_type) 
    await callback.message.answer("Iltimos, manga rasmini yuboring:")
    await state.set_state(MangaForm.waiting_for_photo)
    await callback.answer()

@dp.message(MangaForm.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer("Manga nomini kiriting:")
    await state.set_state(MangaForm.waiting_for_name)

@dp.message(MangaForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Tarjimon nomini kiriting:")
    await state.set_state(MangaForm.waiting_for_translator)

@dp.message(MangaForm.waiting_for_translator)
async def process_translator(message: Message, state: FSMContext):
    await state.update_data(translator=message.text)
    await message.answer("Boblar sonini kiriting:")
    await state.set_state(MangaForm.waiting_for_chapters)

@dp.message(MangaForm.waiting_for_chapters)
async def process_chapters(message: Message, state: FSMContext):
    try:
        chapters_count = int(message.text)
        await state.update_data(chapters=chapters_count)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Manga", callback_data="type:manga"),
                    InlineKeyboardButton(text="Manhwa", callback_data="type:manhwa"),
                    InlineKeyboardButton(text="Manhua", callback_data="type:manhua"),
                    InlineKeyboardButton(text="Novel", callback_data="type:novel") 
                ]
            ]
        )
        await message.answer("Manga turini tanlang:", reply_markup=keyboard)
        await state.set_state(MangaForm.waiting_for_type)
    except ValueError:
        await message.answer("Iltimos, raqam kiriting!")
    except Exception as e:
        logging.error(f"Error in process_chapters: {e}")
        await message.answer("Kutilmagan xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        await state.clear()


@dp.callback_query(MangaForm.waiting_for_type, F.data.startswith("type:"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    manga_genre_type = callback.data.split(":")[1]
    await state.update_data(genre_type=manga_genre_type) 
    await callback.message.answer("Janrlarni vergul bilan ajratib yozing (masalan, Fantastika, Drama, Romantika):")
    await state.set_state(MangaForm.waiting_for_genres)
    await callback.answer()

@dp.message(MangaForm.waiting_for_genres)
async def process_genres(message: Message, state: FSMContext):
    genres = [genre.strip() for genre in message.text.split(",")]
    await state.update_data(genre=", ".join(genres), pdf_files=[], added_chapters_count=0, error_files_count=0) 
    
    await message.answer("Manga uchun PDF fayllarni yuboring:")
    await state.set_state(MangaForm.waiting_for_pdf)

async def send_final_pdf_summary(message: Message, state: FSMContext):
    try:
        await asyncio.sleep(15) 
        data = await state.get_data() 
        manga_name = data.get('name', 'Nomsiz Manga')
        added_count = data.get('added_chapters_count', 0)
        error_count = data.get('error_files_count', 0)
        
        caption_text = (
            f"<b>{manga_name}</b> ga {added_count} ta bob qo'shildi.\n"
            f"Xatoliklar soni: {error_count}"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="JONATISH", callback_data="send"), InlineKeyboardButton(text="TIMER", callback_data="timer")],
            ]
        )
        await message.answer(
            caption_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        await state.update_data(pdf_timeout_task=None)
    except asyncio.CancelledError:
        logging.info("PDF timeout task cancelled (new PDF arrived).")
    except Exception as e:
        logging.error(f"Error in send_final_pdf_summary: {e}")

async def process_single_pdf(message: Message, state: FSMContext):
    """Yuborilgan bitta PDF faylni qayta ishlash funksiyasi."""
    pdf_file_id = message.document.file_id
    pdf_file_name = message.document.file_name
    data = await state.get_data()

    chapter_numbers = re.findall(r'(\d+)', pdf_file_name) 
    chapter_num = None
    if chapter_numbers:
        chapter_num = int(chapter_numbers[0])
    
    if chapter_num is None:
        await message.answer(
            f"❌ Xatolik: '{pdf_file_name}' fayl nomidan bob raqami topilmadi. "
            f"Fayl nomi 'manga nomi 101.pdf' kabi bo'lishi kerak. Ushbu fayl qo'shilmadi."
        )
        await state.update_data(error_files_count=data.get('error_files_count', 0) + 1)
        return False

    existing_chapter_nums = [pdf['chapter_num'] for pdf in data['pdf_files']]
    if chapter_num in existing_chapter_nums:
        await message.answer(
            f"⚠️ '{pdf_file_name}' fayli avval qo'shilgan {chapter_num}-qismga o'xshash. " 
            f"Bu qism qo'shilmadi."
        )
        await state.update_data(error_files_count=data.get('error_files_count', 0) + 1)
        return False

    pdf_data = {
        'file_id': pdf_file_id,
        'file_name': pdf_file_name,
        'chapter_num': chapter_num,
        'is_premium': False
    }  
    if data.get('audience_type') == 'premium':
        pdf_data['is_premium'] = True
    data['pdf_files'].append(pdf_data)
    await state.update_data(pdf_files=data['pdf_files'], added_chapters_count=data.get('added_chapters_count', 0) + 1)
    status = "PREMIUM" if pdf_data['is_premium'] else "ODDIY"
    return True

@dp.message(MangaForm.waiting_for_pdf, F.document)
async def process_pdf(message: Message, state: FSMContext):
    success = await process_single_pdf(message, state)
    data = await state.get_data()
    if 'pdf_timeout_task' in data and data['pdf_timeout_task'] is not None:
        data['pdf_timeout_task'].cancel()
    loop = asyncio.get_event_loop()
    timeout_task = loop.create_task(send_final_pdf_summary(message, state))
    await state.update_data(pdf_timeout_task=timeout_task)

@dp.callback_query(MangaForm.waiting_for_pdf, F.data == "send")
async def send_manga_to_db(callback: CallbackQuery, state: FSMContext):
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    data = await state.get_data()
    if 'pdf_timeout_task' in data and data['pdf_timeout_task'] is not None:
        data['pdf_timeout_task'].cancel()
        await state.update_data(pdf_timeout_task=None)
    required_fields = ['name', 'translator', 'genre', 'audience_type', 'genre_type', 'chapters', 'photo_id', 'pdf_files']
    if not all(data.get(field) is not None for field in required_fields):
        await callback.message.answer("❌ Ma'lumotlar to'liq emas. Qayta urinib ko'ring.")
        await state.clear()
        await callback.answer()
        conn.close()
        return

    try:
        manga_name = data['name']
        translator = data['translator']
        genre = data['genre']
        audience_type = data['audience_type']
        genre_type = data['genre_type']
        chapters = data['chapters']
        photo_id = data['photo_id']
        pdf_files = data['pdf_files']
        premium_start = None
        if audience_type == 'gibrid' and pdf_files:
            premium_chapters = sorted([p['chapter_num'] for p in pdf_files if p['is_premium']])
            if premium_chapters:
                premium_start = premium_chapters[0]
        cursor.execute('''
            INSERT INTO mangas (name, translator, genre, type, genre_type, chapters, photo_id, premium_start)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (manga_name, translator, genre, audience_type, genre_type, chapters, photo_id, premium_start))
        conn.commit()
        manga_id = cursor.lastrowid  
        for pdf in pdf_files:
            cursor.execute('''
                INSERT INTO manga_pdfs (manga_id, file_id, file_name, chapter_number, is_premium)
                VALUES (?, ?, ?, ?, ?)
            ''', (manga_id, pdf['file_id'], pdf['file_name'], pdf['chapter_num'], pdf['is_premium']))
        conn.commit()
        await callback.message.answer("✅ Manga bazaga muvaffaqiyatli saqlandi!")
        manga_info = (manga_name, translator, genre, audience_type, genre_type, chapters, photo_id, premium_start)   
        await state.update_data(
            manga_info=manga_info,
            editing_manga_id=manga_id,  
            channels_to_send=CHANNEL_ID.copy(),
            current_channel_index=0
        )
        first_channel = CHANNEL_ID[0]
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Yuborilsin", callback_data=f"send_to_this_channel_{first_channel}"),
                    InlineKeyboardButton(text="➡️ O'tkazish", callback_data="skip_channel")
                ],
                [
                    InlineKeyboardButton(text="📢 Barchasiga", callback_data="send_to_all_channels")
                ]
            ]
        )
        
        await callback.message.answer(
            f"📤 Xabar quyidagi kanalga yuborilsinmi: {first_channel}?",
            reply_markup=keyboard
        )
        await state.set_state(SendMangaStates.waiting_for_channel_choice)

    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            await callback.message.answer(f"❌ '{manga_name}' nomli manga allaqachon mavjud!")
        else:
            await callback.message.answer("❌ Ma'lumotlarni saqlashda xatolik!")
        logging.error(f"Database error: {e}")
    except Exception as e:
        await callback.message.answer("❌ Kutilmagan xatolik yuz berdi!")
        logging.error(f"Unexpected error: {e}")
    finally:
        conn.close()
    
    await callback.answer()

@dp.callback_query(MangaForm.waiting_for_pdf, F.data == "timer")
async def timer_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if 'pdf_timeout_task' in data and data['pdf_timeout_task'] is not None:
        data['pdf_timeout_task'].cancel()
        await state.update_data(pdf_timeout_task=None)
    await callback.message.answer("TIMER funksiyasi hali amalga oshirilmagan.")
    await callback.answer()

class setting_manga(StatesGroup):
    main_menu = State() 
    waiting_for_manga_name_for_chapter_edit = State()
    waiting_for_pdf_for_chapter_edit = State() 
    waiting_for_manga_name_for_info_edit = State() 

@dp.callback_query(F.data == 'settings_manga')
async def show_settings_menu(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 BOB tahrirlash", callback_data="edit_chapters")],
            [InlineKeyboardButton(text="📝 Ma'lumot tahrirlash", callback_data="edit_info")],
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="admin")]
        ]
    )
    await callback.message.edit_text(
        "Manga sozlamalari bo'limi:\nQanday tahrirlash turini amalga oshirmoqchisiz?",
        reply_markup=keyboard
    )
    await state.set_state(setting_manga.main_menu)
    await callback.answer()

@dp.callback_query(setting_manga.main_menu, F.data == "edit_chapters")
async def start_chapter_editing(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Qaysi mangani tahrirlamoqchisiz? Iltimos, **manga nomini to'liq** kiriting:")
    await state.set_state(setting_manga.waiting_for_manga_name_for_chapter_edit)
    await callback.answer()

@dp.message(setting_manga.waiting_for_manga_name_for_chapter_edit)
async def process_manga_name_for_chapter_edit(message: Message, state: FSMContext):
    manga_name = message.text.strip()
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, photo_id FROM mangas WHERE name = ?", (manga_name,))
    manga_info = cursor.fetchone()
    conn.close()
    if manga_info:
        manga_id, found_manga_name, photo_id = manga_info
        await state.update_data(
            editing_manga_id=manga_id,
            editing_manga_name=found_manga_name,
            editing_manga_photo_id=photo_id,
            pdf_files_to_update=[],
            added_chapters_count=0, 
            error_files_count=0 
        )
        await message.answer(
            f"<b>'{found_manga_name}'</b> mangasi topildi. Endi boblarni yuborishingiz mumkin.\n"
            "⚠️ Eslatma: Agar yuborgan fayl nomidagi bob raqami mavjud bo'lsa, u yangisi bilan almashtiriladi. "
            "Agar yangi bob bo'lsa, qo'shiladi.",
            parse_mode='HTML'
        )
        await message.answer("Iltimos, PDF fayllarni yuboring:")
        await state.set_state(setting_manga.waiting_for_pdf_for_chapter_edit)
    else:
        await message.answer(
            f"Kechirasiz, '{manga_name}' nomli manga topilmadi. "
            "Iltimos, to'liq va to'g'ri nom kiriting yoki /cancel buyrug'ini bosing."
        )

@dp.message(setting_manga.waiting_for_pdf_for_chapter_edit, F.document)
async def process_pdf_for_chapter_edit(message: Message, state: FSMContext):
    pdf_file_id = message.document.file_id
    pdf_file_name = message.document.file_name
    data = await state.get_data()
    manga_id = data.get('editing_manga_id')
    manga_name = data.get('editing_manga_name')
    chapter_numbers = re.findall(r'(\d+)', pdf_file_name) 
    chapter_num = None
    if chapter_numbers:
        chapter_num = int(chapter_numbers[0])
    
    if chapter_num is None:
        await message.answer(
            f"❌ Xatolik: '{pdf_file_name}' fayl nomidan bob raqami topilmadi. "
            f"Fayl nomi 'manga nomi 101.pdf' kabi bo'lishi kerak. Ushbu fayl qo'shilmadi."
        )
        await state.update_data(error_files_count=data.get('error_files_count', 0) + 1)
        return
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, is_premium FROM manga_pdfs WHERE manga_id = ? AND chapter_number = ?",
        (manga_id, chapter_num)
    )
    existing_pdf = cursor.fetchone()

    is_premium_chapter = False 

    if existing_pdf:
       
        pdf_db_id, old_is_premium = existing_pdf
        cursor.execute(
            "UPDATE manga_pdfs SET file_id = ?, file_name = ?, is_premium = ? WHERE id = ?",
            (pdf_file_id, pdf_file_name, old_is_premium, pdf_db_id) 
        )
        conn.commit()
        await message.answer(
            f"🔄 {chapter_num}-bob yangilandi! ({pdf_file_name})"
        )
        await state.update_data(added_chapters_count=data.get('added_chapters_count', 0) + 1)
    else:
        cursor.execute(
            "INSERT INTO manga_pdfs (manga_id, file_id, file_name, chapter_number, is_premium) VALUES (?, ?, ?, ?, ?)",
            (manga_id, pdf_file_id, pdf_file_name, chapter_num, is_premium_chapter)
        )
        conn.commit()
        await message.answer(
            f"➕ {chapter_num}-bob qo'shildi! ({pdf_file_name})"
        )
        await state.update_data(added_chapters_count=data.get('added_chapters_count', 0) + 1)
        cursor.execute("SELECT chapters FROM mangas WHERE id = ?", (manga_id,))
        current_total_chapters = cursor.fetchone()[0]
        if chapter_num > current_total_chapters:
            cursor.execute("UPDATE mangas SET chapters = ? WHERE id = ?", (chapter_num, manga_id))
            conn.commit()
    conn.close()
    if 'pdf_timeout_task' in data and data['pdf_timeout_task'] is not None:
        data['pdf_timeout_task'].cancel()
    loop = asyncio.get_event_loop()
    timeout_task = loop.create_task(send_chapter_edit_summary(message, state, manga_name))
    await state.update_data(pdf_timeout_task=timeout_task)


async def send_chapter_edit_summary(message: Message, state: FSMContext, manga_name: str):
    """Boblarni tahrirlash tugagandan so'ng yakuniy hisobotni yuborish funksiyasi."""
    try:
        await asyncio.sleep(15)
        data = await state.get_data()
        
        added_count = data.get('added_chapters_count', 0)
        error_count = data.get('error_files_count', 0)
        
        caption_text = (
            f"<b>{manga_name}</b> mangasining boblari yangilandi.\n"
            f"Jami yangilangan/qo'shilgan boblar: {added_count}\n"
            f"Xatoliklar soni: {error_count}"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ JONATISH", callback_data="send_edited_manga_to_channel")]
            ]
        )
        await message.answer(
            caption_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        await state.update_data(pdf_timeout_task=None) 
        await state.set_state(setting_manga.main_menu) 
    except asyncio.CancelledError:
        logging.info("Chapter edit timeout task cancelled (new PDF arrived).")
    except Exception as e:
        logging.error(f"Error in send_chapter_edit_summary: {e}")

class SendMangaStates(StatesGroup):
    waiting_for_channel_choice = State()

def create_send_keyboard(channel_identifier: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for sending manga to channels"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborilsin", callback_data=f"send_to_this_channel_{channel_identifier}"),
                InlineKeyboardButton(text="➡️ O'tkazish", callback_data="skip_channel")
            ],
            [
                InlineKeyboardButton(text="📢 Barchasiga", callback_data="send_to_all_channels")
            ]
        ]
    )

async def send_message_to_channel(manga_info: tuple, manga_id: int, channel_identifier, bot) -> bool:
    """Send manga info to specified channel"""
    try:
        # Kanalga kirish huquqini tekshirish
        try:
            chat = await bot.get_chat(channel_identifier)
            if chat.type not in ['channel', 'supergroup']:
                return False
        except Exception as e:
            logging.error(f"Kanalga kirishda xatolik ({channel_identifier}): {e}")
            return False

        # Manga ma'lumotlarini ajratib olish
        name, translator, genre, m_type, genre_type, chapters, photo_id, premium_start = manga_info
        
        caption_text = (
            f"📖 <b>{genre_type.upper()}ga yangi qisim qo'shildi: {name}</b>\n\n"
            f"👨‍💻 Tarjimon: {translator}\n"
            f"📚 Janrlar: {genre}\n"
            f"🔖 Turi: {m_type}\n"
            f"🧾 Boblar soni: {chapters}\n"
            f"📌 Kategoriya: {genre_type}"
        )
        if m_type == 'gibrid' and premium_start:
            caption_text += f"\n🔐 Premium qismlar: {premium_start}-qismdan boshlab"

        bot_username = (await bot.get_me()).username
        download_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="Yuklab olish", 
                    url=f"https://t.me/{bot_username}?start=manga_{manga_id}"
                )]
            ]
        )
        
        await bot.send_photo(
            chat_id=channel_identifier,
            photo=photo_id,
            caption=caption_text,
            parse_mode='HTML',
            reply_markup=download_keyboard
        )
        return True
    except Exception as e:
        logging.error(f"Xabar yuborishda xatolik ({channel_identifier}): {e}")
        return False

async def get_manga_info(manga_id: int) -> tuple:
    """Get manga info from database"""
    try:
        with sqlite3.connect('manganest.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, translator, genre, type, genre_type, chapters, photo_id, premium_start "
                "FROM mangas WHERE id = ?", 
                (manga_id,)
            )
            return cursor.fetchone()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None

async def finish_sending_process(callback: CallbackQuery):
    """Finish the sending process"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="♻️ Yana tahrirlash", callback_data="settings_manga")]]
    )
    await callback.message.answer("✅ Barcha kanallar ko'rib chiqildi.", reply_markup=keyboard)

@dp.callback_query(F.data == "send_edited_manga_to_channel")
async def start_channel_selection(callback: CallbackQuery, state: FSMContext):
    """Start channel selection process"""
    await callback.answer()
    data = await state.get_data()
    manga_id = data.get('editing_manga_id')
    
    if not manga_id:
        await callback.message.answer("❌ Tahrirlanayotgan manga topilmadi.")
        return

    manga_info = await get_manga_info(manga_id)
    if not manga_info:
        await callback.message.answer("❌ Manga ma'lumotlari topilmadi.")
        return
        
    await state.update_data(
        manga_info=manga_info,
        channels_to_send=CHANNEL_ID.copy(),
        current_channel_index=0
    )
    
    await state.set_state(SendMangaStates.waiting_for_channel_choice)
    first_channel = CHANNEL_ID[0]
    keyboard = create_send_keyboard(str(first_channel))
    await callback.message.answer(
        f"📤 Xabar quyidagi kanalga yuborilsinmi: {first_channel}?",
        reply_markup=keyboard
    )

@dp.callback_query(SendMangaStates.waiting_for_channel_choice, F.data.startswith("send_to_this_channel_"))
async def handle_send_to_this_channel(callback: CallbackQuery, state: FSMContext):
    """Handle sending to specific channel"""
    await callback.answer()
    data = await state.get_data()
    manga_info = data['manga_info']
    channels_to_send = data['channels_to_send']
    current_index = data['current_channel_index']
    manga_id = data.get('editing_manga_id')
    
    if not manga_id:
        await callback.message.answer("❌ Manga IDsi topilmadi.")
        return

    channel_identifier = channels_to_send[current_index]
    success = await send_message_to_channel(
        manga_info=manga_info,
        manga_id=manga_id,
        channel_identifier=channel_identifier,
        bot=bot
    )
    
    if success:
        await callback.message.answer(f"✅ Xabar {channel_identifier} ga muvaffaqiyatli yuborildi.")
    else:
        await callback.message.answer(f"❌ Xabar {channel_identifier} ga yuborishda xatolik yuz berdi.")
    
    next_index = current_index + 1
    if next_index < len(channels_to_send):
        await state.update_data(current_channel_index=next_index)
        next_channel = channels_to_send[next_index]
        keyboard = create_send_keyboard(str(next_channel))
        await callback.message.answer(
            f"Keyingi kanal: {next_channel}. Yuborilsinmi?",
            reply_markup=keyboard
        )
    else:
        await state.clear()
        await finish_sending_process(callback)

@dp.callback_query(SendMangaStates.waiting_for_channel_choice, F.data == "skip_channel")
async def handle_skip_channel(callback: CallbackQuery, state: FSMContext):
    """Handle skipping a channel"""
    await callback.answer()
    data = await state.get_data()
    channels_to_send = data['channels_to_send']
    current_index = data['current_channel_index']
    
    next_index = current_index + 1
    if next_index < len(channels_to_send):
        await state.update_data(current_channel_index=next_index)
        next_channel = channels_to_send[next_index]
        keyboard = create_send_keyboard(str(next_channel))
        await callback.message.answer(
            f"⏭ Keyingi kanal: {next_channel}. Yuborilsinmi?",
            reply_markup=keyboard
        )
    else:
        await state.clear()
        await finish_sending_process(callback)

@dp.callback_query(SendMangaStates.waiting_for_channel_choice, F.data == "send_to_all_channels")
async def handle_send_to_all_channels(callback: CallbackQuery, state: FSMContext):
    """Handle sending to all channels"""
    await callback.answer()
    data = await state.get_data()
    manga_info = data['manga_info']
    channels_to_send = data['channels_to_send']
    manga_id = data.get('editing_manga_id')
    
    if not manga_id:
        await callback.message.answer("❌ Manga IDsi topilmadi.")
        return

    await callback.message.answer("⏳ Barcha kanallarga xabar yuborilmoqda...")
    
    success_count = 0
    for channel_identifier in channels_to_send:
        success = await send_message_to_channel(
            manga_info=manga_info,
            manga_id=manga_id,
            channel_identifier=channel_identifier,
            bot=bot
        )
        if success:
            success_count += 1
        else:
            await callback.message.answer(f"⚠️ {channel_identifier} ga yuborishda xatolik")
    
    await state.clear()
    await callback.message.answer(f"📊 {success_count}/{len(channels_to_send)} kanallarga muvaffaqiyatli yuborildi.")
    await finish_sending_process(callback)

class MangaEditStates(StatesGroup):
    waiting_for_manga_name_for_info_edit = State()
    show_edit_options = State()
    choose_chapter_type = State()
    waiting_for_hybrid_chapter_number = State()
    waiting_for_new_translator = State()
    waiting_for_new_genre = State()
    waiting_for_new_genre_type = State()
    waiting_for_new_manga_type = State()
    waiting_for_new_chapters = State()

@dp.callback_query(F.data == "edit_info") 
async def start_info_editing(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Manga ma'lumotlarini tahrirlash bo'limi.\n\n"
                                     "Iltimos, **tahrirlamoqchi bo'lgan manga nomini** kiriting:",
                                     parse_mode='HTML')
    await state.set_state(MangaEditStates.waiting_for_manga_name_for_info_edit)
    await callback.answer()

@dp.message(MangaEditStates.waiting_for_manga_name_for_info_edit)
async def process_manga_name_for_info_edit(message: Message, state: FSMContext):
    manga_name = message.text.strip()
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM mangas WHERE LOWER(name) = LOWER(?)", (manga_name,))
    manga_info = cursor.fetchone()
    conn.close()

    if manga_info:
        manga_id, found_manga_name = manga_info
        await state.update_data(manga_id=manga_id, manga_name=found_manga_name)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="TUR (Bob turlarini o'zgartirish)", callback_data=f"edit_manga_type:{manga_id}")],
            [InlineKeyboardButton(text="Ma'lumot (boshqa ma'lumotlar)", callback_data=f"edit_manga_details:{manga_id}")],
            [InlineKeyboardButton(text="🔙 Ortga", callback_data="main_head")]
        ])
        await message.answer(f"✅ Manga topildi: **{found_manga_name}**\n\nQuyidagi amallardan birini tanlang:", 
                             reply_markup=keyboard, parse_mode='HTML')
        await state.set_state(MangaEditStates.show_edit_options)
    else:
        await message.answer("❌ Kechirasiz, bunday nomli manga topilmadi. Qayta urinib ko'ring yoki `/cancel` buyrug'i bilan bekor qiling.")

@dp.callback_query(MangaEditStates.show_edit_options, F.data.startswith("edit_manga_type:"))
async def choose_chapter_type_options(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(':')
    manga_id = int(parts[1])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="**ODDIY** (Barcha boblar oddiy)", callback_data=f"set_chapter_type:normal:{manga_id}")],
        [InlineKeyboardButton(text="**PREMIUM** (Barcha boblar premium)", callback_data=f"set_chapter_type:premium:{manga_id}")],
        [InlineKeyboardButton(text="**GIBRID** (Qisman oddiy, qisman premium)", callback_data=f"set_chapter_type:hybrid:{manga_id}")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data=f"show_edit_options_from_type:{manga_id}")]
    ])
    await callback.message.edit_text("**Boblar turini** tanlang:", reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.choose_chapter_type)
    await callback.answer()

@dp.callback_query(F.data.startswith("show_edit_options_from_type:"))
async def return_to_edit_options(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(':')
    manga_id = int(parts[1])
    data = await state.get_data()
    manga_name = data.get('manga_name', "Nomlanmagan manga")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="TUR (Bob turlarini o'zgartirish)", callback_data=f"edit_manga_type:{manga_id}")],
        [InlineKeyboardButton(text="Ma'lumot (boshqa ma'lumotlar)", callback_data=f"edit_manga_details:{manga_id}")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="main_head")]
    ])
    await callback.message.edit_text(f"✅ Manga topildi: **{manga_name}**\n\nQuyidagi amallardan birini tanlang:", 
                             reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.show_edit_options)
    await callback.answer()


@dp.callback_query(MangaEditStates.choose_chapter_type, F.data.startswith("set_chapter_type:"))
async def set_chapter_type(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(':')
    chapter_type = parts[1]
    manga_id = int(parts[2])
    
    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    
    if chapter_type == "normal":
        cursor.execute("UPDATE manga_pdfs SET is_premium = 0 WHERE manga_id = ?", (manga_id,))
        conn.commit()
        await callback.message.edit_text("✅ Barcha boblar **'ODDIY'** turiga o'tkazildi.", parse_mode='HTML')
        await state.clear()
    elif chapter_type == "premium":
        cursor.execute("UPDATE manga_pdfs SET is_premium = 1 WHERE manga_id = ?", (manga_id,))
        conn.commit()
        await callback.message.edit_text("✅ Barcha boblar **'PREMIUM'** turiga o'tkazildi.", parse_mode='HTML')
        await state.clear()
    elif chapter_type == "hybrid":
        await callback.message.edit_text("Gibrid tur tanlandi. Iltimos, **bob raqamini kiriting**. "
                                         "Bu bobdan keyingi qismlar PREMIUM, undan oldingilar ODDIY bo'ladi.\n\n"
                                         "Masalan, '15' kiritsangiz, 15-bobgacha oddiy, 16-bobdan boshlab premium bo'ladi.",
                                         parse_mode='HTML')
        await state.set_state(MangaEditStates.waiting_for_hybrid_chapter_number)
        await callback.answer()
        conn.close()
        return
    
    conn.close()
    
    await callback.message.answer("Asosiy menyuga qaytish uchun:", 
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                      [InlineKeyboardButton(text="🔙 Bosh menyuga qaytish", callback_data="main_head")]
                                  ]))
    await callback.answer()


@dp.message(MangaEditStates.waiting_for_hybrid_chapter_number)
async def process_hybrid_chapter_number(message: Message, state: FSMContext):
    try:
        split_chapter_num = int(message.text.strip())
        if split_chapter_num <= 0:
            raise ValueError

        data = await state.get_data()
        manga_id = data.get('manga_id')

        if manga_id is None:
            await message.answer("Xatolik: Manga ID topilmadi. Iltimos, jarayonni qaytadan boshlang.")
            await state.clear()
            return
        
        conn = sqlite3.connect('manganest.db')
        cursor = conn.cursor()

        cursor.execute("UPDATE manga_pdfs SET is_premium = 0 WHERE manga_id = ? AND chapter_number <= ?", 
                       (manga_id, split_chapter_num))
        cursor.execute("UPDATE manga_pdfs SET is_premium = 1 WHERE manga_id = ? AND chapter_number > ?", 
                       (manga_id, split_chapter_num))
        conn.commit()
        conn.close()

        await message.answer(f"✅ Boblar muvaffaqiyatli **'GIBRID'** turiga o'tkazildi.\n"
                             f"**{split_chapter_num}**-bobgacha ODDIY, **{split_chapter_num+1}**-bobdan boshlab PREMIUM.",
                             parse_mode='HTML')
        await state.clear()
        
        await message.answer("Asosiy menyuga qaytish uchun:", 
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                  [InlineKeyboardButton(text="🔙 Bosh menyuga qaytish", callback_data="main_head")]
                              ]))
    except ValueError:
        await message.answer("❌ Noto'g'ri bob raqami kiritildi. Iltimos, **butun son** kiriting.", parse_mode='HTML')
    except Exception as e:
        logging.error(f"Gibrid bob turini o'rnatishda xato: {e}")
        await message.answer("Boblar turini o'zgartirishda kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

@dp.callback_query(MangaEditStates.show_edit_options, F.data.startswith("edit_manga_details:"))
async def start_manga_details_editing(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    manga_id = data.get('manga_id')

    if manga_id is None:
        await callback.message.edit_text("❌ Xatolik: Tahrirlash uchun manga tanlanmagan. Iltimos, jarayonni qaytadan boshlang.")
        await state.clear()
        await callback.answer()
        return

    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    cursor.execute("SELECT translator, genre, chapters FROM mangas WHERE id = ?", (manga_id,))
    current_info = cursor.fetchone()
    conn.close()

    if not current_info:
        await callback.message.edit_text("❌ Kechirasiz, manga ma'lumotlari topilmadi. Iltimos, qaytadan urinib ko'ring.")
        await state.clear()
        await callback.answer()
        return

    current_translator, current_genre, current_chapters = current_info

    await state.update_data(
        current_translator=current_translator,
        current_genre=current_genre,
        current_chapters=current_chapters
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ⏭️", callback_data="skip_translator")]
    ])

    await callback.message.edit_text(f"**Mavjud Tarjimon:** `{current_translator if current_translator else 'Mavjud emas'}`\n\n"
                                     "Iltimos, yangi **Tarjimon** nomini kiriting:",
                                     reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.waiting_for_new_translator)
    await callback.answer()

@dp.callback_query(MangaEditStates.waiting_for_new_translator, F.data == "skip_translator")
async def skip_new_translator(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(new_translator=data.get('current_translator'))
    await callback.message.edit_text("Tarjimon o'tkazib yuborildi.")
    current_genre = data.get('current_genre')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ⏭️", callback_data="skip_genre")]
    ])
    await callback.message.answer(f"**Mavjud Janrlar:** `{current_genre if current_genre else 'Mavjud emas'}`\n\n"
                                  "Iltimos, yangi **janrlarni** kiriting (vergul bilan ajratib):",
                                  reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.waiting_for_new_genre)
    await callback.answer()

@dp.message(MangaEditStates.waiting_for_new_translator)
async def process_new_translator(message: Message, state: FSMContext):
    await state.update_data(new_translator=message.text.strip())
    
    current_genre = (await state.get_data()).get('current_genre')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ⏭️", callback_data="skip_genre")]
    ])
    await message.answer(f"**Mavjud Janrlar:** `{current_genre if current_genre else 'Mavjud emas'}`\n\n"
                         "Iltimos, yangi **janrlarni** kiriting (vergul bilan ajratib):",
                         reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.waiting_for_new_genre)

@dp.callback_query(MangaEditStates.waiting_for_new_genre, F.data == "skip_genre")
async def skip_new_genre(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(new_genre=data.get('current_genre'))
    await callback.message.edit_text("Janrlar o'tkazib yuborildi.")
    
    current_chapters = data.get('current_chapters')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ⏭️", callback_data="skip_chapters")]
    ])
    await callback.message.answer(f"**Mavjud boblar soni:** `{current_chapters}`\n\n"
                                  "Iltimos, yangi **umumiy boblar sonini** kiriting (faqat raqamda):",
                                  reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.waiting_for_new_chapters)
    await callback.answer()

@dp.message(MangaEditStates.waiting_for_new_genre)
async def process_new_genre(message: Message, state: FSMContext):
    await state.update_data(new_genre=message.text.strip())
    
    current_chapters = (await state.get_data()).get('current_chapters')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="O'tkazib yuborish ⏭️", callback_data="skip_chapters")]
    ])
    await message.answer(f"**Mavjud boblar soni:** `{current_chapters}`\n\n"
                         "Iltimos, yangi **umumiy boblar sonini** kiriting (faqat raqamda):",
                         reply_markup=keyboard, parse_mode='HTML')
    await state.set_state(MangaEditStates.waiting_for_new_chapters)

@dp.callback_query(MangaEditStates.waiting_for_new_chapters, F.data == "skip_chapters")
async def skip_new_chapters(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(new_chapters=data.get('current_chapters'))
    await callback.message.edit_text("Umumiy boblar soni o'tkazib yuborildi.")
    await save_and_finish(callback.message, state)

@dp.message(MangaEditStates.waiting_for_new_chapters)
async def process_new_chapters(message: Message, state: FSMContext):
    try:
        new_chapters = int(message.text.strip())
        if new_chapters <= 0:
            raise ValueError
        await state.update_data(new_chapters=new_chapters)
        await message.answer("Yangi umumiy boblar soni qabul qilindi.")
        await save_and_finish(message, state)
    except ValueError:
        await message.answer("❌ Noto'g'ri boblar soni kiritildi. Iltimos, musbat butun son kiriting.")

async def save_and_finish(message, state: FSMContext):
    data = await state.get_data()
    manga_id = data.get('manga_id')
    final_translator = data.get('new_translator')
    final_genre = data.get('new_genre')
    final_chapters = data.get('new_chapters')

    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE mangas 
            SET translator = ?, genre = ?, chapters = ?
            WHERE id = ?
        """, (final_translator, final_genre, final_chapters, manga_id))
        conn.commit()
        await message.answer("✅ Manga ma'lumotlari muvaffaqiyatli yangilandi!")
    except Exception as e:
        logging.error(f"Manga ma'lumotlarini yangilashda xato: {e}")
        await message.answer("❌ Manga ma'lumotlarini yangilashda kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
    finally:
        conn.close()
        await state.clear()

    await message.answer("Asosiy menyuga qaytish uchun:", 
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                              [InlineKeyboardButton(text="🔙 Bosh menyuga qaytish", callback_data="main_head")]
                          ]))


@dp.callback_query(F.data == "hamkor")
async def hamkor_kanallar(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ KANAL QO'SHISH ➕", callback_data="add_chanel"), InlineKeyboardButton(text="➖ KANAL O'CHIRISH ➖", callback_data="remove_chanel")],
            [InlineKeyboardButton(text="📜 KANALLAR RO'YHATI 📜", callback_data="list_chanel"), InlineKeyboardButton(text="⚙️ KANAL SOZLAMALARI ⚙️", callback_data="settings_chanel")],
            [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data="admin")]
        ]
    )
    await callback.message.edit_text("KANALLAR BO'LIMI", reply_markup=keyboard)

class ChannelForm(StatesGroup):
    choosing_add_method = State()
    choosing_campaign_type = State() 
    waiting_for_channel_id = State() 
    waiting_for_channel_username = State() 
    waiting_for_subs_count = State() 
    waiting_for_days_count = State()
    confirm_channel_data = State() 

@dp.callback_query(F.data == "add_chanel")
async def ask_add_channel_method(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="ID orqali", callback_data="channel_by_id"),
                InlineKeyboardButton(text="USERNAME orqali", callback_data="channel_by_username")
            ],
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="hamkor")] 
        ]
    )
    await callback.message.edit_text("Qaysi usulda kanal qo'shmoqchisiz?", reply_markup=keyboard)
    await state.set_state(ChannelForm.choosing_add_method)
    await callback.answer()

@dp.callback_query(ChannelForm.choosing_add_method, F.data.in_({"channel_by_id", "channel_by_username"}))
async def ask_campaign_type(callback: types.CallbackQuery, state: FSMContext):
    selected_method = callback.data
    await state.update_data(add_method=selected_method)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 KUNLIK", callback_data="campaign_time_based")],
            [InlineKeyboardButton(text="👥 OBUNACHI SONI", callback_data="campaign_limit_based")],
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="add_chanel")] 
        ]
    )
    await callback.message.edit_text("Iltimos, kampaniya turini tanlang:", reply_markup=keyboard)
    await state.set_state(ChannelForm.choosing_campaign_type)
    await callback.answer()

@dp.callback_query(ChannelForm.choosing_campaign_type, F.data.in_({"campaign_time_based", "campaign_limit_based", "campaign_vip"}))
async def process_campaign_type(callback: types.CallbackQuery, state: FSMContext):
    campaign_type = callback.data.replace("campaign_", "") 
    await state.update_data(campaign_type=campaign_type) 

    data = await state.get_data()
    add_method = data.get('add_method')

    if add_method == "channel_by_id":
        await callback.message.edit_text("Iltimos, kanalning **ID raqamini** kiriting (masalan, `-1001234567890`):")
        await state.set_state(ChannelForm.waiting_for_channel_id)
    elif add_method == "channel_by_username":
        await callback.message.edit_text("Iltimos, kanalning **USERNAME'ini** kiriting (masalan, `@mychannel`):")
        await state.set_state(ChannelForm.waiting_for_channel_username)
    
    await callback.answer()

@dp.message(ChannelForm.waiting_for_channel_id)
async def process_channel_id(message: types.Message, state: FSMContext):
    try:
        channel_id_int = int(message.text.strip())
        if not str(channel_id_int).startswith('-100'):
            await message.answer("Xato kanal ID! Kanal IDsi odatda '-100' bilan boshlanadi. Qayta kiriting.")
            return
        await state.update_data(channel_id=str(channel_id_int))
        await proceed_to_campaign_details(message, state)
    except ValueError:
        await message.answer("Noto'g'ri ID format. Iltimos, faqat raqamlardan iborat ID kiriting (masalan, `-1001234567890`).")
    
@dp.message(ChannelForm.waiting_for_channel_username)
async def process_channel_username(message: Message, state: FSMContext): 
    channel_username = message.text.strip()
    if not channel_username.startswith('@'):
        channel_username = "@" + channel_username
    
    try:
        chat = await bot.get_chat(channel_username)
        if chat.type != "channel":
            await message.answer("Siz kiritgan username kanalga tegishli emas. Iltimos, kanal username'ini kiriting.")
            return

        try:
            bot_member = await bot.get_chat_member(chat.id, bot.id)
            if bot_member.status not in ["administrator", "creator"]: 
                await message.answer(
                    "Bot bu kanalda admin emas. Iltimos, botni kanalda admin qiling va unga "
                    "'Foydalanuvchilarni taklif qilish havolalari' va 'Administratorlar ro'yxati' huquqlarini bering."
                )
                return
        except aiogram.exceptions.TelegramForbiddenError:
            await message.answer(
                "Bot bu kanalda topilmadi yoki unga ruxsat berilmagan. "
                "Iltimos, botni kanalda admin qiling va qayta urinib ko'ring."
            )
            return
        except Exception as e:
            logging.error(f"Botning kanaldagi adminligini tekshirishda xato: {e}")
            await message.answer(
                "Kanalni tekshirishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring yoki botni qayta ishga tushiring."
            )
            return

        await state.update_data(channel_id=chat.id, channel_username=channel_username)
        await proceed_to_campaign_details(message, state)

    except aiogram.exceptions.TelegramBadRequest as e:
        await message.answer(
            "Kanal topilmadi. Username to'g'riligini (masalan, `@mychannel`) tekshiring va "
            "kanalning umumiy (public) ekanligiga ishonch hosil qiling, yoki botni avval kanalda admin qiling."
        )
        logging.error(f"TelegramBadRequest in process_channel_username: {e}")
    except Exception as e:
        await message.answer("Kanalni qo'shishda kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
        logging.error(f"Unexpected error in process_channel_username: {e}")

async def proceed_to_campaign_details(message: types.Message, state: FSMContext):
    data = await state.get_data()
    campaign_type = data.get('campaign_type')

    if campaign_type == "time_based":
        await message.answer("Kanal necha kunga ulanadi? Iltimos, kunlar sonini kiriting (faqat butun son):")
        await state.set_state(ChannelForm.waiting_for_days_count)
    elif campaign_type == "limit_based":
        await message.answer("Kanalga nechta obunachi qo'shish kerak? Iltimos, obunachilar sonini kiriting (faqat butun son):")
        await state.set_state(ChannelForm.waiting_for_subs_count)
    elif campaign_type == "vip":
        await message.answer("Siz VIP kanal qo'shmoqchisiz. Bu kanal admin o'chirmaguncha botda faol bo'ladi.")
        await confirm_channel_addition(message, state) 

@dp.message(ChannelForm.waiting_for_subs_count)
async def process_subs_count(message: types.Message, state: FSMContext):
    try:
        subs_count = int(message.text.strip())
        if subs_count <= 0:
            await message.answer("Obunachilar soni musbat son bo'lishi kerak. Qayta kiriting.")
            return
        await state.update_data(required_subs=subs_count)
        await confirm_channel_addition(message, state)
    except ValueError:
        await message.answer("Noto'g'ri format. Iltimos, obunachilar sonini butun son sifatida kiriting.")

@dp.message(ChannelForm.waiting_for_days_count)
async def process_days_count(message: types.Message, state: FSMContext):
    try:
        days_count = int(message.text.strip())
        if days_count <= 0:
            await message.answer("Kunlar soni musbat son bo'lishi kerak. Qayta kiriting.")
            return
        end_date = date.today() + timedelta(days=days_count)
        await state.update_data(end_date=end_date.strftime('%Y-%m-%d'))
        await confirm_channel_addition(message, state)
    except ValueError:
        await message.answer("Noto'g'ri format. Iltimos, kunlar sonini butun son sifatida kiriting.")

async def confirm_channel_addition(message: types.Message, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get('channel_id')
    channel_username = data.get('channel_username')
    campaign_type = data.get('campaign_type')
    required_subs = data.get('required_subs')
    end_date_str = data.get('end_date')
    summary_text = f"<b>Kanal qo'shish tasdiqlash:</b>\n"
    summary_text += f"Kanal ID: <code>{channel_id}</code>\n"
    summary_text += f"Kanal USERNAME: {channel_username}\n"
    summary_text += f"Kampaniya turi: <b>{campaign_type.upper()}</b>\n"

    if campaign_type == "limit_based":
        summary_text += f"Kerakli obunachilar: {required_subs} ta\n"
    elif campaign_type == "time_based":
        summary_text += f"Tugash sanasi: {end_date_str}\n"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ TASDIQLASH", callback_data="add_channel_to_db")],
            [InlineKeyboardButton(text="❌ BEKOR QILISH", callback_data="cancel_channel_addition")]
        ]
    )
    await message.answer(summary_text, parse_mode='HTML', reply_markup=keyboard)
    await state.set_state(ChannelForm.confirm_channel_data)

@dp.callback_query(ChannelForm.confirm_channel_data, F.data == "add_channel_to_db")
async def add_channel_to_db(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    channel_id = data.get('channel_id') 
    channel_username = data.get('channel_username')
    campaign_type = data.get('campaign_type')
    required_subs = data.get('required_subs', 0)
    end_date_str = data.get('end_date') 

    conn = sqlite3.connect('manganest.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM channels WHERE channel_id = ? OR channel_username = ?", 
                       (channel_id, channel_username))
        existing_channel = cursor.fetchone()
        if existing_channel:
            await callback.message.edit_text("❌ Xatolik: Ushbu kanal allaqachon botda mavjud. Boshqa kanal qo'shing yoki bekor qiling.",
                                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin paneliga", callback_data="admin")]]))
            await state.clear()
            await callback.answer()
            return 
        start_date = date.today().strftime('%Y-%m-%d')
        final_end_date = end_date_str if campaign_type == "time_based" else None

        is_active = 1

        cursor.execute(
            """
            INSERT INTO channels 
            (channel_id, channel_username, required_subs, current_subs, start_date, end_date, campaign_type, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (channel_id, channel_username, required_subs, 0, start_date, final_end_date, campaign_type, is_active)
        )
        conn.commit()
        await callback.message.edit_text("✅ Kanal muvaffaqiyatli qo'shildi! Admin paneliga qaytishingiz mumkin.",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin paneliga", callback_data="admin")]]))
    except Exception as e:
        logging.error(f"Kanalni bazaga qo'shishda kutilmagan xatolik yuz berdi: {e}")
        await callback.message.edit_text(f"❌ Kanalni qo'shishda kutilmagan xatolik yuz berdi: {e}",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin paneliga", callback_data="admin")]]))
    finally:
        conn.close()
        await state.clear()
    await callback.answer()

@dp.callback_query(ChannelForm.confirm_channel_data, F.data == "cancel_channel_addition")
async def cancel_channel_addition(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Kanal qo'shish jarayoni bekor qilindi. Admin paneliga qaytishingiz mumkin.",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin paneliga", callback_data="admin")]]))
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "remove_chanel")
async def remove_channel_list(callback: types.CallbackQuery):
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_id, channel_username FROM channels")
    channels = cursor.fetchall()
    conn.close()
    if not channels:
        await callback.message.answer("❌ Hozircha hech qanday kanal mavjud emas.")
        return
    buttons = []
    for ch in channels:
        ch_id, channel_id, username = ch
        label = username if username else channel_id
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"delete_channel:{ch_id}")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("🗑 O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("delete_channel:"))
async def delete_selected_channel(callback: types.CallbackQuery):
    channel_db_id = callback.data.split(":")[1]
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE id = ?", (channel_db_id,))
    conn.commit()
    conn.close()
    await callback.message.answer("✅ Kanal muvaffaqiyatli o'chirildi.")
    await callback.answer()

@dp.callback_query(F.data == "list_chanel")
async def list_channels(callback: types.CallbackQuery):
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_id, channel_username FROM channels")
    channels = cursor.fetchall()
    conn.close()
    if not channels:
        await callback.message.answer("📭 Hech qanday kanal topilmadi.")
        return
    buttons = []
    for ch_id, ch_id_val, username in channels:
        label = username if username else ch_id_val
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"channel_info:{ch_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("📋 Kanallar ro'yxati. Kanal ustiga bosib ma'lumot oling:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("channel_info:"))
async def show_channel_info(callback: types.CallbackQuery):
    channel_db_id = callback.data.split(":")[1]
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_id, channel_username, required_subs, current_subs, 
               start_date, end_date, campaign_type, is_active 
        FROM channels 
        WHERE id = ?
    """, (channel_db_id,))
    
    channel_data = cursor.fetchone()
    conn.close()

    if not channel_data:
        await callback.message.edit_text("❌ Kanal topilmadi yoki bazadan o'chirilgan.")
        await callback.answer()
        return
    db_channel_id, db_channel_username, required_subs, current_subs, \
    start_date_str, end_date_str, campaign_type, is_active = channel_data
    try:
        chat_ref = db_channel_username if db_channel_username else db_channel_id
        
        chat = await bot.get_chat(chat_ref)
        member_count = await bot.get_chat_member_count(chat.id)
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        is_bot_admin = bot_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
        bot_status_text = "ADMIN" if is_bot_admin else "Oddiy a'zo yoki yo'q"
        display_telegram_username = f"@{chat.username}" if chat.username else "mavjud emas"
        display_campaign_type = ""
        if campaign_type == "limit_based":
            display_campaign_type = f"Obunachi soni bo'yicha ({current_subs}/{required_subs})"
        elif campaign_type == "time_based":
            display_end_date = "Noma'lum"
            if end_date_str:
                end_date_obj = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                display_end_date = end_date_obj.strftime('%Y-%m-%d')
                if end_date_obj < date.today():
                    display_end_date += " (Muddati tugagan)"
            display_campaign_type = f"Kunlik (Tugash sanasi: {display_end_date})"
        elif campaign_type == "vip":
            display_campaign_type = "VIP (Admin o'chirmaguncha)"
        else:
            display_campaign_type = "Noma'lum"
        status_emoji = "✅ Faol" if is_active else "❌ Nofaol"
        text = (
            f"📡 <b>Kanal nomi:</b> {chat.title}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"🔗 <b>Username:</b> {display_telegram_username}\n"
            f"👥 <b>Obunachilar soni:</b> {member_count}\n"
            f"🔐 <b>Bot holati:</b> {bot_status_text}\n"
            f"--- Kampaniya ma'lumotlari ---\n"
            f"📊 <b>Turi:</b> {display_campaign_type}\n"
            f"📈 <b>Holat:</b> {status_emoji}\n"
            f"➕ <b>Qo'shilgan sana:</b> {start_date_str}\n" 
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin paneliga", callback_data="admin")]
            ]
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Kanal ma'lumotlarini olishda xatolik: {e} (Channel ID: {db_channel_id}, Username: {db_channel_username})")
        await callback.message.edit_text(f"❌ Kanal ma'lumotlarini olishda xatolik yuz berdi. "
                                         f"Sabab: {e}\n"
                                         f"Kanal mavjudligini va bot kanalda admin ekanligini tekshiring."
                                         f"Username mavjud bo'lmasa, ID orqali ham urinib ko'rishingiz mumkin.")
    finally:
        await callback.answer()



@dp.callback_query(F.data == "add_admin")
async def adminlar_bolimi(callback: types.CallbackQuery):
    if callback.from_user.id not in admins:
        await callback.message.answer("Siz bosh admin emassiz, bu yerga faqat bosh admin kira oladi.")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ ADMIN QO'SHISH ➕", callback_data="add_admin_id"), InlineKeyboardButton(text="➖ ADMIN O'CHIRISH ➖", callback_data="remove_admin")],
                [InlineKeyboardButton(text="📜 ADMINLAR RO'YHATI 📜", callback_data="list_admin"), InlineKeyboardButton(text="⚙️ ADMIN SOZLAMALARI ⚙️", callback_data="settings_admin")],
                [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data="admin")]
            ]
        )
        await callback.message.edit_text("ADMINLAR BO'LIMI", reply_markup=keyboard)

@dp.callback_query(F.data == "list_admin")
async def show_admin_list(callback: types.CallbackQuery):
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, full_name, username, joined_date
        FROM users
        WHERE type = 'admin'
        ORDER BY joined_date DESC
    """)
    admins = cursor.fetchall()
    conn.close()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="admin")]
        ]
    )
    if not admins:
        await callback.message.answer("📭 Hozircha hech qanday admin mavjud emas.", reply_markup=keyboard)
        return
    text = "👨‍💻 <b>Adminlar ro'yxati:</b>\n\n"
    for user_id, full_name, username, joined in admins:
        text += (
            f"🆔 <code>{user_id}</code>\n"
            f"👤 {full_name}\n"
            f"🔗 @{username or 'username yo‘q'}\n"
            f"📅 Qo'shilgan: {joined}\n\n"
        )
    await callback.message.answer(text[:4096], parse_mode="HTML", reply_markup=keyboard)


class AdminForm(StatesGroup):
    waiting_for_admin_id = State()

@dp.callback_query(F.data == "remove_admin")
async def ask_admin_id_to_remove(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🗑 Adminlikdan olib tashlamoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminForm.waiting_for_admin_id)
    await state.update_data(mode="remove")

@dp.message(AdminForm.waiting_for_admin_id)
async def process_admin_action(message: types.Message, state: FSMContext):
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="admin")]
        ]
    )

    try:
        user_id = int(message.text.strip())
        data = await state.get_data()
        mode = data.get("mode", "add")  
        conn = sqlite3.connect("manganest.db")
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, type FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            await message.answer("❌ Bu ID bo'yicha foydalanuvchi topilmadi. Qaytadan urinib ko'ring:", reply_markup=back_button)
            return

        full_name, current_type = result

        if mode == "add":
            if current_type == "admin":
                await message.answer(f"✅ {full_name} allaqachon admin!", reply_markup=back_button)
            else:
                cursor.execute("UPDATE users SET type = 'admin' WHERE user_id = ?", (user_id,))
                conn.commit()
                await message.answer(f"✅ {full_name} endi yordamchi admin qilindi.", reply_markup=back_button)

        elif mode == "remove":
            if current_type != "admin":
                await message.answer(f"ℹ️ {full_name} hozirda admin emas.", reply_markup=back_button)
            else:
                cursor.execute("UPDATE users SET type = 'oddiy' WHERE user_id = ?", (user_id,))
                conn.commit()
                await message.answer(f"🗑 {full_name} endi admin emas.", reply_markup=back_button)

        await state.clear()

    except ValueError:
        await message.answer("❗ Iltimos, faqat raqamli ID kiriting.", reply_markup=back_button)
    finally:
        conn.close()

@dp.callback_query(F.data == "add_admin_id")
async def ask_for_admin_id(callback: types.CallbackQuery, state: FSMContext):
    """Admin qilish uchun ID so'raydi."""
    await callback.message.answer("🆔 Admin qilmoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(AdminForm.waiting_for_admin_id)

@dp.message(AdminForm.waiting_for_admin_id)
async def promote_to_admin(message: types.Message, state: FSMContext):
    """Kiritilgan IDni adminlar jadvaliga qo'shadi."""
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="admin")]
        ]
    ) 
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    try:
        user_id = int(message.text.strip())
        cursor.execute("SELECT 1 FROM adminlar WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            await message.answer(f"✅ Ushbu ID ({user_id}) allaqachon admin!", reply_markup=back_button)
        else:
            cursor.execute("SELECT full_name, username FROM users WHERE user_id = ?", (user_id,))
            user_data = cursor.fetchone()

            if user_data:
                full_name, username = user_data
                added_by = message.from_user.id
                cursor.execute("""
                    INSERT INTO adminlar (user_id, full_name, username, added_by) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, full_name, username, added_by))
                conn.commit()
                
                await message.answer(f"✅ {full_name if full_name else 'Foydalanuvchi'} endi yordamchi admin qilindi.", reply_markup=back_button)
            else:
                await message.answer("❌ Bu ID bo'yicha foydalanuvchi botda mavjud emas.", reply_markup=back_button)

    except ValueError:
        await message.answer("❗ Iltimos, faqat raqamli ID kiriting.", reply_markup=back_button)
    except sqlite3.Error as e:
        await message.answer(f"Database xatosi yuz berdi: {e}", reply_markup=back_button)
    finally:
        conn.close()
        await state.clear()


@dp.callback_query(F.data == "prem")
async def premium(callback: types.CallbackQuery):
    if callback.from_user.id not in admins:
        await callback.message.answer("Siz bosh admin emassiz, bu yerga faqat bosh admin kira oladi.")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ PREMIUM QO'SHISH ➕", callback_data="add_premium"), InlineKeyboardButton(text="➖ PREMIUM O'CHIRISH ➖", callback_data="remove_premium")],
                [InlineKeyboardButton(text="📜 PREMIUMLAR RO'YHATI 📜", callback_data="list_premium"), InlineKeyboardButton(text="⚙️ PREMIUM SOZLAMALARI ⚙️", callback_data="settings_premium")],
                [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data="admin")]
            ]
        )
        await callback.message.edit_text("PREMIUM BO'LIMI", reply_markup=keyboard)

class PremiumForm(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_user_id2 = State()
    waiting_for_days = State()
    waiting_for_confirm = State()

@dp.callback_query(F.data == "add_premium")
async def ask_premium_user_id(callback: types.CallbackQuery, state: FSMContext,):
    await callback.message.answer(
        "👤 Premium qilish uchun foydalanuvchi ID sini kiriting:\n\n",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="prem")]
            ]
        )
    )
    await state.set_state(PremiumForm.waiting_for_user_id)
@dp.message(PremiumForm.waiting_for_user_id)
async def get_premium_days(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("SELECT full_name, type, premium_end_date FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await message.answer("❌ Bunday foydalanuvchi topilmadi. Qayta urinib ko'ring:")
            return
        full_name, user_type, current_end_date = user_data
        await state.update_data(user_id=user_id, full_name=full_name, current_type=user_type, current_end_date=current_end_date)
        if user_type == 'premium' and current_end_date:
            await message.answer(
                f"ℹ️ {full_name} allaqachon premium foydalanuvchi.\n"
                f"⏳ Joriy premium muddati: {current_end_date}\n\n"
                "Yangi muddat qo'shish uchun kunlar sonini kiriting:",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="prem")]
                    ]
                )
            )
        else:
            await message.answer(
                f"📆 {full_name} uchun necha kunga premium berilsin?\n"
                "(Faqat raqam kiriting, masalan: 30):",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="prem")]
                    ]
                )
            )
        
        await state.set_state(PremiumForm.waiting_for_days)
        conn.close()     
    except ValueError:
        await message.answer(
            "❗ Noto'g'ri format! Faqat raqam kiriting.\n"
            "Foydalanuvchi ID sini qayta kiriting:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="prem")]
                ]
            )
        )

@dp.message(PremiumForm.waiting_for_days)
async def confirm_premium_addition(message: types.Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError     
        data = await state.get_data()
        user_id = data["user_id"]
        full_name = data["full_name"]
        current_type = data["current_type"]
        current_end_date = data.get("current_end_date")
        new_end_date = datetime.now().date() + timedelta(days=days)
        if current_type == 'premium' and current_end_date and current_end_date > datetime.now().date():
            new_end_date = current_end_date + timedelta(days=days)
        
        await state.update_data(days=days, new_end_date=new_end_date)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_premium")],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_premium")]
            ]
        )
        
        await message.answer(
            f"🔄 Premiumni tasdiqlang:\n\n"
            f"👤 Foydalanuvchi: {full_name}\n"
            f"🆔 ID: {user_id}\n"
            f"📆 Kunlar soni: {days}\n"
            f"⏳ Yangi premium muddati: {new_end_date}\n\n"
            "Ushbu amalni tasdiqlaysizmi?",
            reply_markup=keyboard
        )
        await state.set_state(PremiumForm.waiting_for_confirm)
        
    except ValueError:
        await message.answer(
            "❗ Noto'g'ri format! Iltimos, musbat butun son kiriting:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="prem")]
                ]
            )
        )

@dp.callback_query(PremiumForm.waiting_for_confirm, F.data == "confirm_premium")
async def process_premium_confirmation(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    full_name = data["full_name"]
    days = data["days"]
    new_end_date = data["new_end_date"] 
    try:
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET type = 'premium', premium_end_date = ?
            WHERE user_id = ?
        """, (new_end_date, user_id))
        
        conn.commit()
        conn.close()
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🎉 Tabriklaymiz! Sizga {days} kunlik premium berildi.\n"
                     f"⏳ Premium muddati: {new_end_date}\n\n"
                     f"Premium imkoniyatlaridan foydalanish uchun /start buyrug'ini bosing."
            )
        except Exception as e:
            print(f"Foydalanuvchiga xabar yuborishda xato: {e}")
        
        await callback.message.edit_text(
            f"✅ {full_name} uchun {days} kunlik premium muvaffaqiyatli qo'shildi.\n"
            f"⏳ Premium muddati: {new_end_date}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Premium bo'limiga qaytish", callback_data="prem")]
                ]
            )
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Premium bo'limiga qaytish", callback_data="prem")]
                ]
            )
        )
    finally:
        await state.clear()

@dp.callback_query(PremiumForm.waiting_for_confirm, F.data == "cancel_premium")
async def cancel_premium_addition(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "⚠️ Premium qo'shish bekor qilindi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Premium bo'limiga qaytish", callback_data="prem")]
            ]
        )
    )

PREMIUM_PAGE_SIZE = 10

@dp.callback_query(F.data.startswith("list_premium"))
async def show_premium_list(callback: types.CallbackQuery):
    try:
        parts = callback.data.split(":")
        page = int(parts[1]) if len(parts) == 2 else 0
        offset = page * PREMIUM_PAGE_SIZE
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE type = 'premium' AND (premium_end_date IS NULL OR premium_end_date >= ?)
        """, (datetime.now().date(),))
        total_count = cursor.fetchone()[0]
        cursor.execute("""
            SELECT user_id, full_name, username, premium_end_date 
            FROM users 
            WHERE type = 'premium' AND (premium_end_date IS NULL OR premium_end_date >= ?)
            ORDER BY premium_end_date DESC
            LIMIT ? OFFSET ?
        """, (datetime.now().date(), PREMIUM_PAGE_SIZE, offset))
        premium_users = cursor.fetchall()
        conn.close()
        if not premium_users:
            await callback.message.edit_text(
                "📭 Hozircha premium foydalanuvchilar mavjud emas.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Orqaga", callback_data="prem")]
                ])
            )
            return
        text = f"🌟 Premium Foydalanuvchilar Ro'yxati (sahifa {page+1}):\n\n"
        for user_id, full_name, username, end_date in premium_users:
            remaining = (end_date - datetime.now().date()).days if end_date else "∞"
            text += (
                f"👤 {full_name}\n"
                f"🆔 {user_id} | @{username or '---'}\n"
                f"⏳ Premium muddati: {end_date or 'Cheksiz'}\n"
                f"📅 Qolgan kunlar: {remaining}\n"
                f"────────────────\n"
            )
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"list_premium:{page-1}"))
        if offset + PREMIUM_PAGE_SIZE < total_count:
            buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"list_premium:{page+1}"))

        nav_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                buttons if buttons else [InlineKeyboardButton(text="🚫 Hech narsa yo'q", callback_data="none")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="prem")]
            ]
        )
        await callback.message.edit_text(text, reply_markup=nav_markup)
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Orqaga", callback_data="prem")]
                ]
            )
        )

@dp.callback_query(F.data == "remove_premium")
async def ask_premium_user_to_remove(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🗑 Premiumdan olib tashlamoqchi bo'lgan foydalanuvchi ID sini kiriting:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="prem")]
            ]
        )
    )
    await state.set_state(PremiumForm.waiting_for_user_id2)
    await state.update_data(mode="remove")

@dp.message(PremiumForm.waiting_for_user_id2)
async def confirm_premium_removal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("mode") != "remove":
        return
    try:
        user_id = int(message.text.strip())
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        
        cursor.execute("SELECT full_name, type FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await message.answer("❌ Bunday foydalanuvchi topilmadi.")
            return
        
        full_name, user_type = user_data
        
        if user_type != 'premium':
            await message.answer(f"ℹ️ {full_name} hozirda premium emas.")
            return
        
        await state.update_data(user_id=user_id, full_name=full_name)
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_remove_premium")],
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_remove_premium")]
            ]
        )
        
        await message.answer(
            f"⚠️ {full_name} ni premiumdan olib tashlashni tasdiqlaysizmi?\n"
            "Bu foydalanuvchining premium imkoniyatlarini bekor qiladi.",
            reply_markup=keyboard
        )
        
        await state.set_state(PremiumForm.waiting_for_confirm)
        conn.close()
        
    except ValueError:
        await message.answer("❗ Noto'g'ri format! Faqat raqam kiriting.")

@dp.callback_query(PremiumForm.waiting_for_confirm, F.data == "confirm_remove_premium")
async def process_premium_removal(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data["user_id"]
    full_name = data["full_name"]
    try:
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET type = 'oddiy', premium_end_date = NULL 
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        conn.close()
        try:
            await bot.send_message(
                chat_id=user_id,
                text="⚠️ Sizning premium obunangiz bekor qilindi.\n\n"
                     "Agar bu xato bo'lsa, administratorlar bilan bog'laning."
            )
        except Exception as e:
            print(f"Foydalanuvchiga xabar yuborishda xato: {e}")
        
        await callback.message.edit_text(
            f"✅ {full_name} premiumdan muvaffaqiyatli olib tashlandi.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Premium bo'limiga qaytish", callback_data="prem")]
                ]
            )
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Premium bo'limiga qaytish", callback_data="prem")]
                ]
            )
        )
    finally:
        await state.clear()

@dp.callback_query(PremiumForm.waiting_for_confirm, F.data == "cancel_remove_premium")
async def cancel_premium_removal(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "⚠️ Premiumdan olib tashlash bekor qilindi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Premium bo'limiga qaytish", callback_data="prem")]
            ]
        )
    )

@dp.callback_query(F.data == "shop")
async def shop_bolimi(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ TOVAR QO'SHISH ➕", callback_data="add_product"), InlineKeyboardButton(text="➖ TOVAR O'CHIRISH ➖", callback_data="remove_product")],
            [InlineKeyboardButton(text="📜 TOVARLAR RO'YHATI 📜", callback_data="list_products"), InlineKeyboardButton(text="⚙️ TOVAR SOZLAMALARI ⚙️", callback_data="settings_products")],
            [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data="admin")]
        ]
    )
    await callback.message.edit_text("DO'KON BO'LIMI tamirlanmoqda...", reply_markup=keyboard)

@dp.callback_query(F.data == "promokod")
async def promokod_bolimi(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ PROMOKOD QO'SHISH ➕", callback_data="add_promo"), InlineKeyboardButton(text="➖ PROMOKOD O'CHIRISH ➖", callback_data="remove_promo")],
            [InlineKeyboardButton(text="📜 PROMOKODLAR RO'YHATI 📜", callback_data="list_promo"), InlineKeyboardButton(text="⚙️ PROMOKOD SOZLAMALARI ⚙️", callback_data="settings_promo")],
            [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data="admin")]
        ]
    )
    await callback.message.edit_text("PROMOKOD BO'LIMI", reply_markup=keyboard)

class PromoForm(StatesGroup):
    waiting_for_code = State()
    waiting_for_value = State()
    waiting_for_code_to_delete = State()

@dp.callback_query(F.data == "add_promo")
async def ask_promo_code(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Yangi promokod nomini kiriting (masalan: `nfd345`):")
    await state.set_state(PromoForm.waiting_for_code)

@dp.message(PromoForm.waiting_for_code)
async def ask_promo_value(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if len(code) < 3:
        await message.answer("❗ Promokod nomi juda qisqa. Qayta kiriting:")
        return
    await state.update_data(code=code)
    await message.answer("🎯 Ushbu promokodga necha ball biriktiriladi? (Masalan: 100):")
    await state.set_state(PromoForm.waiting_for_value)

@dp.message(PromoForm.waiting_for_value)
async def save_promo(message: types.Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value <= 0:
            raise ValueError
        data = await state.get_data()
        code = data["code"]
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO promocodes (code, value) VALUES (?, ?)", (code, value))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Promokod '{code}' {value} ball bilan muvaffaqiyatli qo'shildi!")
    except ValueError:
        await message.answer("❗ Noto'g'ri raqam! Ballni butun son sifatida kiriting.")
        return
    except sqlite3.IntegrityError:
        await message.answer("⚠️ Bu promokod allaqachon mavjud!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    finally:
        await state.clear()

@dp.callback_query(F.data == "remove_promo")
async def ask_promo_to_delete(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🗑 O'chirmoqchi bo'lgan promokod nomini kiriting:")
    await state.set_state(PromoForm.waiting_for_code_to_delete)

@dp.message(PromoForm.waiting_for_code_to_delete)
async def delete_promo(message: types.Message, state: FSMContext):
    code = message.text.strip()
    conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected:
        await message.answer(f"✅ Promokod '{code}' muvaffaqiyatli o'chirildi.")
    else:
        await message.answer(f"❌ '{code}' nomli promokod topilmadi.")

    await state.clear()

@dp.callback_query(F.data == "list_promo")
async def list_promocodes(callback: types.CallbackQuery):
    conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("SELECT code, value, created_at FROM promocodes ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await callback.message.edit_text(
            "📭 Hech qanday promokod mavjud emas.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="promokod")]
                ]
            )
        )
        return
    text = "🎁 <b>Promokodlar ro'yxati:</b>\n\n"
    for code, value, created_at in rows:
        text += (
            f"🔑 <b>Promokod:</b> <code>{code}</code>\n"
            f"🎯 Ball: {value}\n"
            f"🕓 Yaralgan: {created_at}\n"
            f"──────────────\n"
        )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="promokod")]
        ]
    )

    await callback.message.edit_text(text[:4096], parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "followers")
async def obunachilar_bolimi(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ BANGA TASHLASH ➕", callback_data="ban_user"), InlineKeyboardButton(text="➖ BANDAN O'CHIRISH ➖", callback_data="unban_user")],
            [InlineKeyboardButton(text="📜 OBUNACHILAR RO'YHATI 📜", callback_data="list_users"), InlineKeyboardButton(text="⚙️ OBUNACHI SOZLAMALARI ⚙️", callback_data="settings_users")],
            [InlineKeyboardButton(text="🔙 ORQAGA 🔙", callback_data="admin")]
        ]
    )
    await callback.message.edit_text("OBUNACHILAR BO'LIMI", reply_markup=keyboard)

class BanForm(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_days = State()
    waiting_for_unban_id = State()

@dp.callback_query(F.data == "ban_user")
async def start_banning(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🚫 Ban qilmoqchi bo'lgan foydalanuvchi ID sini kiriting:")
    await state.set_state(BanForm.waiting_for_user_id)

@dp.message(BanForm.waiting_for_user_id)
async def ask_ban_duration(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        await state.update_data(user_id=user_id)
        await message.answer("⏳ Necha kunga ban qilinsin? (Masalan: 7)")
        await state.set_state(BanForm.waiting_for_days)
    except ValueError:
        await message.answer("❗ Noto'g'ri ID! Faqat raqam kiriting:")

@dp.message(BanForm.waiting_for_days)
async def save_ban(message: types.Message, state: FSMContext):
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
        data = await state.get_data()
        user_id = data["user_id"]
        banned_until = datetime.now().date() + timedelta(days=days)
        conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO bans (user_id, banned_until) VALUES (?, ?)
        """, (user_id, banned_until))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Foydalanuvchi {user_id} {days} kunga ban qilindi (⏳ {banned_until} gacha).")
    except ValueError:
        await message.answer("❗ Iltimos, musbat butun son kiriting:")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()

@dp.callback_query(F.data == "unban_user")
async def ask_user_id_to_unban(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("🔓 Bandan chiqariladigan foydalanuvchi ID sini kiriting:")
    await state.set_state(BanForm.waiting_for_unban_id)

@dp.message(BanForm.waiting_for_unban_id)
async def unban_user(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        conn = sqlite3.connect('manganest.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted:
            await message.answer(f"✅ Foydalanuvchi {user_id} bandan chiqarildi.")
        else:
            await message.answer("❗ Bu foydalanuvchi ban holatida emas edi.")
    except ValueError:
        await message.answer("❗ Iltimos, faqat raqamli ID kiriting.")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()


def is_user_banned(user_id: int) -> bool:
    if user_id in admins:
        return False
    conn = sqlite3.connect('manganest.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM adminlar")
    adminlar = [row[0] for row in cursor.fetchall()]

    if user_id in adminlar:
        conn.close()
        return False
    cursor.execute("SELECT banned_until FROM bans WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        banned_until = row[0]
        return banned_until >= datetime.now().date()

    return False


@dp.callback_query(F.data == "list_users")
async def list_all_users(callback: types.CallbackQuery):
    try:
        conn = sqlite3.connect("manganest.db", detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, full_name, username, type, joined_date, premium_end_date 
            FROM users 
            ORDER BY joined_date DESC
            LIMIT 100
        """)
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            await callback.message.edit_text(
                "📭 Hozircha hech qanday foydalanuvchi mavjud emas.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="followers")]
                    ]
                )
            )
            return
        text = "👥 <b>Foydalanuvchilar ro'yxati:</b>\n\n"
        for user in users:
            user_id, full_name, username, user_type, joined_date, premium_end = user
            premium_status = ""
            if user_type == 'premium' and premium_end:
                days_left = (premium_end - datetime.now().date()).days
                premium_status = f" | 💎 Premium ({days_left} kun qoldi)"
            elif user_type == 'admin':
                premium_status = " | 👑 Admin"
            text += (
                f"🆔 <code>{user_id}</code>\n"
                f"👤 {full_name or 'Nomalum'}\n"
                f"🔗 @{username or '—'}\n"
                f"📅 Qo'shilgan: {joined_date}{premium_status}\n"
                f"────────────────\n"
            )
        if len(text) > 4000:
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await callback.message.answer(part, parse_mode="HTML")
        else:
            await callback.message.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="followers")]
                    ]
                )
            )
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="followers")]
                ]
            )
        )

@dp.callback_query(F.data == "state")
async def show_statistics(callback: types.CallbackQuery):
    conn = sqlite3.connect("manganest.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mangas WHERE type = 'premium'")
    premium_manga = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM mangas WHERE type = 'oddiy'")
    oddiy_manga = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM mangas WHERE type = 'gibrid'")
    gibrid_manga = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    jami_foydalanuvchilar = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE type = 'premium'")
    premium_foydalanuvchilar = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE type = 'oddiy'")
    oddiy_foydalanuvchilar = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM promocodes")
    promokodlar_soni = cursor.fetchone()[0]
    conn.close()
    text = (
        "<b>📊 BOT STATISTIKASI</b>\n\n"
        f"📚 Premium mangalar: <b>{premium_manga}</b>\n"
        f"📖 Oddiy mangalar: <b>{oddiy_manga}</b>\n"
        f"🔀 Gibrid mangalar: <b>{gibrid_manga}</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{jami_foydalanuvchilar}</b>\n"
        f"💎 Premium foydalanuvchilar: <b>{premium_foydalanuvchilar}</b>\n"
        f"🙋 Oddiy foydalanuvchilar: <b>{oddiy_foydalanuvchilar}</b>\n\n"
        f"🎁 Promokodlar soni: <b>{promokodlar_soni}</b>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 ORQAGA", callback_data="admin")]
        ]
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)



async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("BOT ISHGA TUSHDI")
    create_database()
    asyncio.run(main())
