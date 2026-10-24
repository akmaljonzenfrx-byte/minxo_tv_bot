import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from config import ADMIN_IDS, setup_logger
from database import (
    get_stats,
    get_top_searches,
    create_db_backup,
    add_movie,
    add_series,
    add_episode,
    delete_movie,
    delete_series,
    get_all_users,
    set_user_block,
    get_required_channels,
    add_channel,
    remove_channel,
    get_movie,
    get_series,
)
from keyboards import admin_panel_keyboard, admin_cancel_keyboard

logger = setup_logger()

(
    M_TITLE,
    M_ALT_TITLE,
    M_DESC,
    M_POSTER,
    M_YEAR,
    M_GENRE,
    M_COUNTRY,
    M_LANG,
    M_DURATION,
    M_RATING,
    M_WATCH_URL,
    M_CONFIRM,
) = range(12)

(
    S_TITLE,
    S_ALT_TITLE,
    S_DESC,
    S_POSTER,
    S_YEAR,
    S_GENRE,
    S_COUNTRY,
    S_LANG,
    S_RATING,
    S_STATUS,
    S_CONFIRM,
) = range(12, 23)

(
    EP_SERIES_ID,
    EP_SEASON,
    EP_NUMBER,
    EP_TITLE,
    EP_URL,
    EP_CONFIRM,
) = range(23, 29)

BC_MESSAGE, BC_CONFIRM = range(29, 31)

CH_ACTION, CH_INPUT = range(31, 33)

DEL_TYPE, DEL_ID, DEL_CONFIRM = range(33, 36)

BLOCK_ACTION, BLOCK_USER_ID = range(36, 38)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    msg_text = "❌ Amal bekor qilindi."
    keyboard = admin_panel_keyboard()
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(msg_text, reply_markup=keyboard)
        except Exception:
            await update.callback_query.message.reply_text(msg_text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(msg_text, reply_markup=keyboard)
    return ConversationHandler.END


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        text = "⛔ Ushbu bo'lim faqat bot ma'murlari uchun mo'ljallangan."
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
        elif update.message:
            await update.message.reply_text(text)
        return

    text = (
        "👑 *MINXO TV — Ma'muriyat Boshqaruv Paneli*\n\n"
        "Quyidagi bo'limlardan birini tanlang:"
    )
    keyboard = admin_panel_keyboard()

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            await update.callback_query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    stats = get_stats()
    top_searches = get_top_searches(5)

    searches_text = ""
    if top_searches:
        for idx, (term, count) in enumerate(top_searches, 1):
            searches_text += f"  {idx}. {term} — {count} marta\n"
    else:
        searches_text = "  Hozircha qidiruvlar mavjud emas.\n"

    msg = (
        "📊 *MINXO TV Tizim Statistikasi*\n\n"
        f"👥 Jami foydalanuvchilar: *{stats['total_users']}*\n"
        f"🆕 Bugun qo'shilganlar: *{stats['new_today']}*\n"
        f"🚫 Bloklanganlar: *{stats['blocked_users']}*\n\n"
        f"🎬 Jami kinolar: *{stats['total_movies']}*\n"
        f"📺 Jami seriallar: *{stats['total_series']}*\n"
        f"🎞 Jami serial qismlari: *{stats['total_episodes']}*\n"
        f"⭐ Sevimlilarga qo'shishlar: *{stats['total_favorites']}*\n"
        f"🔍 Jami qidiruvlar: *{stats['total_searches']}*\n\n"
        f"🔥 *Eng ko'p qidirilganlar:*\n{searches_text}"
    )

    back_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Admin panelga qaytish", callback_data="admin_home")]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_kb)
    elif update.message:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=back_kb)


async def admin_backup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if update.callback_query:
        await update.callback_query.answer("Zaxira nusxa tayyorlanmoqda...")

    try:
        backup_path = create_db_backup()
        with open(backup_path, "rb") as backup_file:
            caption = "🗃 *Baza zaxira nusxasi muvaffaqiyatli yaratildi.*"
            if update.callback_query:
                await update.callback_query.message.reply_document(
                    document=backup_file,
                    caption=caption,
                    parse_mode="Markdown"
                )
            elif update.message:
                await update.message.reply_document(
                    document=backup_file,
                    caption=caption,
                    parse_mode="Markdown"
                )
    except Exception as e:
        logger.error(f"Zaxira nusxa yaratishda xato: {e}")
        err_msg = f"❌ Zaxira nusxa olishda xatolik yuz berdi: {e}"
        if update.callback_query:
            await update.callback_query.message.reply_text(err_msg)
        elif update.message:
            await update.message.reply_text(err_msg)


async def admin_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    args = context.args
    if not args or len(args) < 2:
        msg = "Foydalanish: `/block <tg_id> <1 yoki 0>`\n1 - bloklash, 0 - blokdan chiqarish"
        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        return

    try:
        target_id = int(args[0])
        block_status = int(args[1])
        set_user_block(target_id, block_status)
        status_word = "bloklandi" if block_status == 1 else "blokdan chiqarildi"
        await update.message.reply_text(f"✅ Foydalanuvchi {target_id} muvaffaqiyatli {status_word}.")
    except ValueError:
        await update.message.reply_text("❌ Foydalanuvchi ID va holat faqat son bo'lishi kerak.")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {e}")


# --- KINO QO'SHISH BOSQICHLARI ---

async def movie_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data["movie_data"] = {}
    text = "🎬 *Yangi kino qo'shish*\n\n1. Kino nomini kiriting:"
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_cancel_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=admin_cancel_keyboard())
    return M_TITLE


async def movie_add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["movie_data"]["title"] = update.message.text.strip()
    await update.message.reply_text(
        "2. Muqobil nomlarini kiriting (yoki bo'sh qoldirish uchun '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_ALT_TITLE


async def movie_add_alt_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["movie_data"]["alt_title"] = "" if text == "-" else text
    await update.message.reply_text(
        "3. Kino tavsifini (syujetini) kiriting (yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_DESC


async def movie_add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["movie_data"]["description"] = "" if text == "-" else text
    await update.message.reply_text(
        "4. Poster rasm URL manzilini yoki Telegram rasm file_id sini kiriting (yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_POSTER


async def movie_add_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["movie_data"]["poster_url"] = "" if text == "-" else text
    await update.message.reply_text(
        "5. Chiqqan yilini kiriting (masalan, 2024):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_YEAR


async def movie_add_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        year = int(text)
        context.user_data["movie_data"]["release_year"] = year
    except ValueError:
        context.user_data["movie_data"]["release_year"] = None

    await update.message.reply_text(
        "6. Janrini kiriting (masalan: Jangari, Komediya, Drama):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_GENRE


async def movie_add_genre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["movie_data"]["genre"] = update.message.text.strip()
    await update.message.reply_text(
        "7. Ishlab chiqarilgan mamlakatni kiriting (masalan: AQSH, O'zbekiston):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_COUNTRY


async def movie_add_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["movie_data"]["country"] = update.message.text.strip()
    await update.message.reply_text(
        "8. Ovoz berilgan tilni kiriting (masalan: O'zbekcha, Ruscha):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_LANG


async def movie_add_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["movie_data"]["language"] = update.message.text.strip()
    await update.message.reply_text(
        "9. Davomiyligini kiriting (masalan: 1 soat 45 daqiqa yoki 105 daq):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_DURATION


async def movie_add_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["movie_data"]["duration"] = update.message.text.strip()
    await update.message.reply_text(
        "10. Reytingini kiriting (masalan: 8.5 yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return M_RATING


async def movie_add_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        context.user_data["movie_data"]["rating"] = float(text)
    except ValueError:
        context.user_data["movie_data"]["rating"] = 0.0

    await update.message.reply_text(
        "11. Tomosha qilish havolasi yoki ruxsat etilgan media URL sini kiriting:",
        reply_markup=admin_cancel_keyboard()
    )
    return M_WATCH_URL


async def movie_add_watch_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["movie_data"]["watch_url"] = update.message.text.strip()
    d = context.user_data["movie_data"]

    summary = (
        "🎬 *Kiritilgan ma'lumotlarni tasdiqlaysizmi?*\n\n"
        f"📌 *Nomi:* {d.get('title')}\n"
        f"📝 *Muqobil:* {d.get('alt_title') or 'Yo`q'}\n"
        f"📅 *Yil:* {d.get('release_year') or 'Noma`lum'}\n"
        f"🎭 *Janr:* {d.get('genre') or 'Noma`lum'}\n"
        f"🌍 *Mamlakat:* {d.get('country') or 'Noma`lum'}\n"
        f"🌐 *Til:* {d.get('language') or 'Noma`lum'}\n"
        f"⏱ *Davomiyligi:* {d.get('duration') or 'Noma`lum'}\n"
        f"⭐ *Reyting:* {d.get('rating')}\n"
        f"🔗 *Havola:* {d.get('watch_url')}\n"
        f"🖼 *Poster:* {d.get('poster_url') or 'Mavjud emas'}"
    )

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Saqlash", callback_data="movie_save_confirm")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel_conv")]
    ])

    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=confirm_keyboard)
    return M_CONFIRM


async def movie_add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "movie_save_confirm":
        data = context.user_data.get("movie_data", {})
        new_id = add_movie(data)
        context.user_data.pop("movie_data", None)
        await query.edit_message_text(
            f"✅ *Kino muvaffaqiyatli saqlandi!* (ID: {new_id})",
            parse_mode="Markdown",
            reply_markup=admin_panel_keyboard()
        )
        return ConversationHandler.END

    return await cancel_admin_action(update, context)


def get_movie_add_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(movie_add_start, pattern="^adm_add_movie$")],
        states={
            M_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_title)],
            M_ALT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_alt_title)],
            M_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_desc)],
            M_POSTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_poster)],
            M_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_year)],
            M_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_genre)],
            M_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_country)],
            M_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_lang)],
            M_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_duration)],
            M_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_rating)],
            M_WATCH_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, movie_add_watch_url)],
            M_CONFIRM: [CallbackQueryHandler(movie_add_confirm, pattern="^movie_save_confirm$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern="^admin_cancel_conv$")],
        allow_reentry=True
    )


# --- SERIAL QO'SHISH BOSQICHLARI ---

async def series_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data["series_data"] = {}
    text = "📺 *Yangi serial qo'shish*\n\n1. Serial nomini kiriting:"
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_cancel_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=admin_cancel_keyboard())
    return S_TITLE


async def series_add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["series_data"]["title"] = update.message.text.strip()
    await update.message.reply_text(
        "2. Muqobil nomini kiriting (yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_ALT_TITLE


async def series_add_alt_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["series_data"]["alt_title"] = "" if text == "-" else text
    await update.message.reply_text(
        "3. Serial tavsifini kiriting (yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_DESC


async def series_add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["series_data"]["description"] = "" if text == "-" else text
    await update.message.reply_text(
        "4. Poster rasmi URL yoki Telegram file_id (yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_POSTER


async def series_add_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["series_data"]["poster_url"] = "" if text == "-" else text
    await update.message.reply_text(
        "5. Chiqqan yilini kiriting (masalan: 2023):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_YEAR


async def series_add_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        context.user_data["series_data"]["release_year"] = int(text)
    except ValueError:
        context.user_data["series_data"]["release_year"] = None
    await update.message.reply_text(
        "6. Janrini kiriting (masalan: Fantastika, Triller):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_GENRE


async def series_add_genre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["series_data"]["genre"] = update.message.text.strip()
    await update.message.reply_text(
        "7. Mamlakatini kiriting (masalan: Janubiy Koreya, Turkiya):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_COUNTRY


async def series_add_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["series_data"]["country"] = update.message.text.strip()
    await update.message.reply_text(
        "8. Tilini kiriting (masalan: O'zbekcha):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_LANG


async def series_add_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["series_data"]["language"] = update.message.text.strip()
    await update.message.reply_text(
        "9. Reytingini kiriting (masalan: 9.1 yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return S_RATING


async def series_add_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        context.user_data["series_data"]["rating"] = float(text)
    except ValueError:
        context.user_data["series_data"]["rating"] = 0.0
    await update.message.reply_text(
        "10. Holati: 'Davom etmoqda' yoki 'Yakunlangan' deb yozing:",
        reply_markup=admin_cancel_keyboard()
    )
    return S_STATUS


async def series_add_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    status_text = update.message.text.strip()
    context.user_data["series_data"]["status"] = status_text
    d = context.user_data["series_data"]

    summary = (
        "📺 *Serial ma'lumotlarini tasdiqlaysizmi?*\n\n"
        f"📌 *Nomi:* {d.get('title')}\n"
        f"📝 *Muqobil:* {d.get('alt_title') or 'Yo`q'}\n"
        f"📅 *Yil:* {d.get('release_year') or 'Noma`lum'}\n"
        f"🎭 *Janr:* {d.get('genre') or 'Noma`lum'}\n"
        f"🌍 *Mamlakat:* {d.get('country') or 'Noma`lum'}\n"
        f"🌐 *Til:* {d.get('language') or 'Noma`lum'}\n"
        f"⭐ *Reyting:* {d.get('rating')}\n"
        f"🔄 *Holati:* {d.get('status')}"
    )

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Saqlash", callback_data="series_save_confirm")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel_conv")]
    ])

    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=confirm_keyboard)
    return S_CONFIRM


async def series_add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "series_save_confirm":
        data = context.user_data.get("series_data", {})
        new_id = add_series(data)
        context.user_data.pop("series_data", None)
        await query.edit_message_text(
            f"✅ *Serial muvaffaqiyatli saqlandi!* (ID: {new_id})\n\nEndi '🎞 Qism qo'shish' tugmasi orqali qismlarni biriktirishingiz mumkin.",
            parse_mode="Markdown",
            reply_markup=admin_panel_keyboard()
        )
        return ConversationHandler.END

    return await cancel_admin_action(update, context)


def get_series_add_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(series_add_start, pattern="^adm_add_series$")],
        states={
            S_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_title)],
            S_ALT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_alt_title)],
            S_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_desc)],
            S_POSTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_poster)],
            S_YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_year)],
            S_GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_genre)],
            S_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_country)],
            S_LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_lang)],
            S_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_rating)],
            S_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, series_add_status)],
            S_CONFIRM: [CallbackQueryHandler(series_add_confirm, pattern="^series_save_confirm$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern="^admin_cancel_conv$")],
        allow_reentry=True
    )


# --- SERIAL QISMINI QO'SHISH BOSQICHLARI ---

async def episode_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data["ep_data"] = {}
    text = "🎞 *Serialga qism qo'shish*\n\n1. Qaysi serialga tegishli? Serial ID sini kiriting:"
    if query:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_cancel_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=admin_cancel_keyboard())
    return EP_SERIES_ID


async def episode_add_series_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        series_id = int(text)
        series = get_series(series_id)
        if not series:
            await update.message.reply_text(
                "❌ Bunday ID ga ega serial topilmadi. Qaytadan ID kiriting:",
                reply_markup=admin_cancel_keyboard()
            )
            return EP_SERIES_ID
        context.user_data["ep_data"]["series_id"] = series_id
        context.user_data["ep_data"]["series_title"] = series["title"]
    except ValueError:
        await update.message.reply_text("❌ Serial ID faqat son bo'lishi kerak. Qayta kiriting:")
        return EP_SERIES_ID

    await update.message.reply_text(
        f"Topildi: *{context.user_data['ep_data']['series_title']}*\n\n2. Mavsum raqamini kiriting (masalan: 1):",
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard()
    )
    return EP_SEASON


async def episode_add_season(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        season = int(text)
        context.user_data["ep_data"]["season"] = season
    except ValueError:
        await update.message.reply_text("❌ Mavsum son bo'lishi kerak. Qayta kiriting:")
        return EP_SEASON

    await update.message.reply_text(
        "3. Qism raqamini kiriting (masalan: 1):",
        reply_markup=admin_cancel_keyboard()
    )
    return EP_NUMBER


async def episode_add_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        ep_num = int(text)
        context.user_data["ep_data"]["episode_num"] = ep_num
    except ValueError:
        await update.message.reply_text("❌ Qism raqami faqat son bo'lishi kerak. Qayta kiriting:")
        return EP_NUMBER

    await update.message.reply_text(
        "4. Qism nomini kiriting (yoki '-' yuboring):",
        reply_markup=admin_cancel_keyboard()
    )
    return EP_TITLE


async def episode_add_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["ep_data"]["title"] = "" if text == "-" else text
    await update.message.reply_text(
        "5. Tomosha qilish manzili yoki Telegram post havolasini kiriting:",
        reply_markup=admin_cancel_keyboard()
    )
    return EP_URL


async def episode_add_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ep_data"]["watch_url"] = update.message.text.strip()
    ep = context.user_data["ep_data"]

    summary = (
        "🎞 *Qism ma'lumotlarini tasdiqlaysizmi?*\n\n"
        f"📺 *Serial:* {ep.get('series_title')} (ID: {ep.get('series_id')})\n"
        f"📅 *Mavsum:* {ep.get('season')}\n"
        f"🔢 *Qism:* {ep.get('episode_num')}\n"
        f"📝 *Nomi:* {ep.get('title') or 'Nomsiz'}\n"
        f"🔗 *Havola:* {ep.get('watch_url')}"
    )

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Saqlash", callback_data="ep_save_confirm")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel_conv")]
    ])

    await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=confirm_keyboard)
    return EP_CONFIRM


async def episode_add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "ep_save_confirm":
        ep = context.user_data.get("ep_data", {})
        add_episode(
            series_id=ep["series_id"],
            season=ep["season"],
            episode_num=ep["episode_num"],
            title=ep.get("title", ""),
            watch_url=ep["watch_url"]
        )
        context.user_data.pop("ep_data", None)
        await query.edit_message_text(
            "✅ *Serial qismi muvaffaqiyatli saqlandi!*",
            parse_mode="Markdown",
            reply_markup=admin_panel_keyboard()
        )
        return ConversationHandler.END

    return await cancel_admin_action(update, context)


def get_episode_add_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(episode_add_start, pattern="^adm_add_ep$")],
        states={
            EP_SERIES_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_add_series_id)],
            EP_SEASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_add_season)],
            EP_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_add_number)],
            EP_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_add_title)],
            EP_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, episode_add_url)],
            EP_CONFIRM: [CallbackQueryHandler(episode_add_confirm, pattern="^ep_save_confirm$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern="^admin_cancel_conv$")],
        allow_reentry=True
    )


# --- OMMAVIY XABAR YUBORISH (BROADCAST) ---

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📢 *Ommaviy xabar yuborish bo'limi*\n\nBarcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:",
            parse_mode="Markdown",
            reply_markup=admin_cancel_keyboard()
        )
    return BC_MESSAGE


async def admin_broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["broadcast_text"] = update.message.text
    text = (
        "📢 *Quyidagi xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?*\n\n"
        f"{update.message.text}"
    )
    confirm_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Yuborish", callback_data="bc_send_now")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel_conv")]
    ])
    await update.message.reply_text(text, reply_markup=confirm_kb)
    return BC_CONFIRM


async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data != "bc_send_now":
        return await cancel_admin_action(update, context)

    bc_text = context.user_data.get("broadcast_text", "")
    if not bc_text:
        await query.edit_message_text("❌ Xabar matni topilmadi.", reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    users = get_all_users()
    await query.edit_message_text("⏳ Xabar tarqatilmoqda, kuting...")

    sent_count = 0
    blocked_count = 0

    for u in users:
        tg_id = u["tg_id"]
        try:
            await context.bot.send_message(chat_id=tg_id, text=bc_text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked_count += 1

    result_text = (
        "✅ *Xabar tarqatish yakunlandi!*\n\n"
        f"📨 Yuborildi: *{sent_count}* ta foydalanuvchiga\n"
        f"🚫 Yetib bormadi (bloklagan): *{blocked_count}* ta"
    )
    context.user_data.pop("broadcast_text", None)
    await query.message.reply_text(result_text, parse_mode="Markdown", reply_markup=admin_panel_keyboard())
    return ConversationHandler.END


def get_broadcast_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern="^adm_broadcast$")],
        states={
            BC_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_receive)],
            BC_CONFIRM: [CallbackQueryHandler(admin_broadcast_send, pattern="^bc_send_now$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern="^admin_cancel_conv$")],
        allow_reentry=True
    )


# --- KANALLARNI BOSHQARISH ---

async def manage_channels_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    channels = get_required_channels()
    ch_list_str = "\n".join([f"• {c}" for c in channels]) if channels else "Majburiy kanallar ro'yxati bo'sh."

    text = (
        "📢 *Majburiy obuna kanallari boshqaruvi*\n\n"
        f"Hozirgi kanallar:\n{ch_list_str}\n\n"
        "Kerakli amalni tanlang:"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kanal qo'shish", callback_data="ch_add")],
        [InlineKeyboardButton("➖ Kanal o'chirish", callback_data="ch_del")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_cancel_conv")]
    ])

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    return CH_ACTION


async def manage_channels_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    action = query.data
    if action == "ch_add":
        context.user_data["ch_action"] = "add"
        await query.edit_message_text(
            "Kanal username sini kiriting (masalan: @minxotv yoki -100123456789):",
            reply_markup=admin_cancel_keyboard()
        )
        return CH_INPUT
    elif action == "ch_del":
        context.user_data["ch_action"] = "del"
        await query.edit_message_text(
            "O'chirmoqchi bo'lgan kanal username sini kiriting:",
            reply_markup=admin_cancel_keyboard()
        )
        return CH_INPUT

    return await cancel_admin_action(update, context)


async def manage_channels_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    val = update.message.text.strip()
    action = context.user_data.get("ch_action")

    if action == "add":
        add_channel(val)
        await update.message.reply_text(
            f"✅ Kanal qo'shildi: {val}",
            reply_markup=admin_panel_keyboard()
        )
    elif action == "del":
        remove_channel(val)
        await update.message.reply_text(
            f"✅ Kanal o'chirildi: {val}",
            reply_markup=admin_panel_keyboard()
        )

    context.user_data.pop("ch_action", None)
    return ConversationHandler.END


def get_manage_channels_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(manage_channels_start, pattern="^adm_channels$")],
        states={
            CH_ACTION: [CallbackQueryHandler(manage_channels_action, pattern="^(ch_add|ch_del)$")],
            CH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, manage_channels_input)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern="^admin_cancel_conv$")],
        allow_reentry=True
    )