import html
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from database import (
    register_user,
    get_user,
    get_movie,
    get_movies,
    get_series,
    get_all_series,
    get_seasons,
    get_episodes,
    toggle_favorite,
    is_favorite,
    get_favorites,
    log_search,
    search_movies_and_series,
    get_required_channels,
)
from keyboards import (
    main_menu_keyboard,
    movies_list_keyboard,
    movie_detail_keyboard,
    series_detail_keyboard,
    episodes_keyboard,
    episode_detail_keyboard,
    categories_keyboard,
    language_keyboard,
    sub_check_keyboard,
)

logger = logging.getLogger("MINXO_TV")


async def check_user_channels(user_id: int, bot) -> tuple[bool, list[str]]:
    channels = get_required_channels()
    if not channels:
        return True, []

    unsubscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                unsubscribed.append(ch)
        except Exception as e:
            logger.warning("Kanal a'zoligini tekshirishda xato (%s): %s", ch, e)
            unsubscribed.append(ch)

    if unsubscribed:
        return False, unsubscribed
    return True, []


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    register_user(
        tg_id=user.id,
        username=user.username or "",
        full_name=user.full_name or ""
    )

    db_user = get_user(user.id)
    if db_user and db_user.get("is_blocked"):
        if update.message:
            await update.message.reply_text("Siz botdan foydalanishdan bloklangansiz.")
        return

    is_sub, unsubs = await check_user_channels(user.id, context.bot)
    if not is_sub:
        text = (
            "Assalomu alaykum! MINXO TV botidan to'liq foydalanish uchun "
            "quyidagi homiy kanallarga a'zo bo'ling va «✅ Obunani tekshirish» tugmasini bosing:"
        )
        keyboard = sub_check_keyboard(unsubs)
        if update.message:
            await update.message.reply_text(text, reply_markup=keyboard)
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=keyboard)
        return

    is_admin = user.id in ADMIN_IDS
    greeting = (
        f"Assalomu alaykum, <b>{html.escape(user.first_name)}</b>!\n\n"
        "🎬 <b>MINXO TV</b> rasmiy kino va seriallar platformasiga xush kelibsiz!\n\n"
        "Biz orqali eng sara filmlar, mashhur seriallar va premyerlarni topishingiz mumkin. "
        "Quyidagi menyudan kerakli bo'limni tanlang:"
    )

    keyboard = main_menu_keyboard(is_admin=is_admin)
    if update.message:
        await update.message.reply_text(greeting, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(greeting, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def check_subscription_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user = update.effective_user
    if not user:
        return

    is_sub, unsubs = await check_user_channels(user.id, context.bot)
    if not is_sub:
        await query.answer("Siz hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)
        text = (
            "Iltimos, botdan foydalanish uchun barcha majburiy kanallarga a'zo bo'ling:"
        )
        await query.edit_message_text(text, reply_markup=sub_check_keyboard(unsubs))
        return

    await query.answer("Obuna tasdiqlandi! Xush kelibsiz!", show_alert=False)
    is_admin = user.id in ADMIN_IDS
    text = (
        f"Assalomu alaykum, <b>{html.escape(user.first_name)}</b>!\n\n"
        "🎬 <b>MINXO TV</b> ga muvaffaqiyatli obuna bo'ldingiz.\n"
        "O'zingizga yoqqan film yoki serialni tanlang:"
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(is_admin=is_admin))


async def menu_navigation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    data = query.data
    user = update.effective_user
    if not user:
        return

    db_user = get_user(user.id)
    if db_user and db_user.get("is_blocked"):
        await query.answer("Siz bloklangansiz!", show_alert=True)
        return

    await query.answer()
    is_admin = user.id in ADMIN_IDS

    if data == "menu_main":
        text = (
            f"🎬 <b>MINXO TV Asosiy Menyusi</b>\n\n"
            f"Marhamat, bo'limlardan birini tanlang:"
        )
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(is_admin=is_admin))
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(is_admin=is_admin))

    elif data == "menu_movies" or data.startswith("mov_pg_"):
        page = 1
        if data.startswith("mov_pg_"):
            try:
                page = int(data.replace("mov_pg_", ""))
            except ValueError:
                page = 1

        movies, total_pages = get_movies(page=page, per_page=6, order_by="created_at")
        if not movies:
            await query.edit_message_text(
                "🎬 Hozircha kinolar bazada mavjud emas.",
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return

        text = f"🎬 <b>Barcha Kinolar Katalogi</b> (Sahifa: {page}/{total_pages}):\n\nFilm tanlang:"
        keyboard = movies_list_keyboard(movies, current_page=page, total_pages=total_pages, prefix="mov_pg")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "menu_series" or data.startswith("ser_pg_"):
        page = 1
        if data.startswith("ser_pg_"):
            try:
                page = int(data.replace("ser_pg_", ""))
            except ValueError:
                page = 1

        series_list, total_pages = get_all_series(page=page, per_page=6)
        if not series_list:
            await query.edit_message_text(
                "📺 Hozircha seriallar bazada mavjud emas.",
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return

        text = f"📺 <b>Barcha Seriallar Katalogi</b> (Sahifa: {page}/{total_pages}):\n\nSerial tanlang:"
        keyboard = movies_list_keyboard(series_list, current_page=page, total_pages=total_pages, prefix="ser_pg")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "menu_popular":
        movies, total_pages = get_movies(page=1, per_page=10, order_by="views")
        if not movies:
            await query.edit_message_text(
                "🔥 Hozircha eng mashhur kinolar ro'yxati shakllanmagan.",
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return

        text = "🔥 <b>Eng Mashhur Kinolar:</b>\n\nKo'rish uchun kinoni tanlang:"
        keyboard = movies_list_keyboard(movies, current_page=1, total_pages=1, prefix="pop_pg")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "menu_new":
        movies, total_pages = get_movies(page=1, per_page=10, order_by="id")
        if not movies:
            await query.edit_message_text(
                "🆕 Hozircha yangi qo'shilgan filmlar yo'q.",
                reply_markup=main_menu_keyboard(is_admin=is_admin)
            )
            return

        text = "🆕 <b>Yangi Qo'shilgan Kinolar:</b>\n\nKo'rish uchun kinoni tanlang:"
        keyboard = movies_list_keyboard(movies, current_page=1, total_pages=1, prefix="new_pg")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "menu_search":
        context.user_data["awaiting_search"] = True
        text = (
            "🔍 <b>Kino yoki Serial Qidirish</b>\n\n"
            "Film yoki serial nomini matn sifatida yuboring (masalan: <i>Forsaj</i> yoki <i>Avatar</i>):"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=categories_keyboard("cancel_search"))

    elif data == "menu_categories":
        text = "📂 <b>Janr bo'yicha saralash</b>:\n\nQaysi janrdagi kinolarni ko'rmoqchisiz?"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=categories_keyboard("genre"))

    elif data.startswith("genre_"):
        genre_name = data.replace("genre_", "")
        movies, total_pages = get_movies(page=1, per_page=8, genre=genre_name)
        if not movies:
            await query.edit_message_text(
                f"📂 <b>{genre_name}</b> janrida hozircha kinolar topilmadi.",
                parse_mode=ParseMode.HTML,
                reply_markup=categories_keyboard("genre")
            )
            return

        text = f"📂 <b>{genre_name}</b> janridagi kinolar:\n\nKino tanlang:"
        keyboard = movies_list_keyboard(movies, current_page=1, total_pages=total_pages, prefix=f"g_{genre_name}")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "menu_language":
        text = "🌐 <b>Til bo'yicha saralash</b>:\n\nQaysi tildagi kinolarni ko'rmoqchisiz?"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=language_keyboard())

    elif data.startswith("lang_"):
        lang_code = data.replace("lang_", "")
        movies, total_pages = get_movies(page=1, per_page=8, lang=lang_code)
        if not movies:
            await query.edit_message_text(
                f"🌐 <b>{lang_code}</b> tilida hozircha kinolar topilmadi.",
                parse_mode=ParseMode.HTML,
                reply_markup=language_keyboard()
            )
            return

        text = f"🌐 <b>{lang_code}</b> tilidagi kinolar:\n\nKino tanlang:"
        keyboard = movies_list_keyboard(movies, current_page=1, total_pages=total_pages, prefix=f"l_{lang_code}")
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data == "menu_profile":
        await profile_handler(update, context)

    elif data == "menu_help":
        await help_handler(update, context)


async def movie_view_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    data = query.data
    user = update.effective_user
    if not user:
        return

    await query.answer()

    try:
        movie_id = int(data.replace("view_movie_", ""))
    except ValueError:
        return

    movie = get_movie(movie_id)
    if not movie:
        await query.answer("Kino topilmadi yoki o'chirilgan!", show_alert=True)
        return

    is_fav = is_favorite(user.id, "movie", movie_id)
    fav_btn_text = "❤️ Sevimlilardan o'chirish" if is_fav else "🤍 Sevimlilarga qo'shish"

    title = html.escape(movie.get("title") or "Noma'lum")
    genre = html.escape(movie.get("genre") or "Ma'lumot mavjud emas")
    year = movie.get("year") or "—"
    country = html.escape(movie.get("country") or "Ma'lumot mavjud emas")
    duration = html.escape(movie.get("duration") or "—")
    rating = movie.get("rating") or "—"
    desc = html.escape(movie.get("description") or "Tavsif mavjud emas.")
    views = movie.get("views", 0)

    caption = (
        f"🎬 <b>{title}</b>\n\n"
        f"📅 <b>Yili:</b> {year}\n"
        f"🎭 <b>Janri:</b> {genre}\n"
        f"🌍 <b>Mamlakat:</b> {country}\n"
        f"⏱ <b>Davomiyligi:</b> {duration}\n"
        f"⭐ <b>Reyting:</b> {rating}\n"
        f"👁 <b>Ko'rishlar:</b> {views}\n\n"
        f"📝 <b>Tavsif:</b>\n{desc}"
    )

    keyboard = movie_detail_keyboard(movie_id, is_fav, movie.get("watch_url") or "")
    poster = movie.get("poster")

    try:
        if poster and (poster.startswith("http://") or poster.startswith("https://") or len(poster) > 20):
            try:
                await query.message.delete()
            except Exception:
                pass
            await query.message.reply_photo(
                photo=poster,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            return
    except Exception as e:
        logger.warning("Poster yuborishda xatolik, oddiy matn chiqarilmoqda: %s", e)

    try:
        await query.edit_message_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except Exception:
        await query.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def series_view_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    data = query.data
    user = update.effective_user
    if not user:
        return

    await query.answer()

    if data.startswith("view_series_"):
        series_id = int(data.replace("view_series_", ""))
        series = get_series(series_id)
        if not series:
            await query.answer("Serial topilmadi!", show_alert=True)
            return

        seasons = get_seasons(series_id)
        is_fav = is_favorite(user.id, "series", series_id)

        title = html.escape(series.get("title") or "Noma'lum")
        genre = html.escape(series.get("genre") or "Ma'lumot mavjud emas")
        year = series.get("year") or "—"
        country = html.escape(series.get("country") or "Ma'lumot mavjud emas")
        status = html.escape(series.get("status") or "davom etmoqda")
        desc = html.escape(series.get("description") or "Tavsif mavjud emas.")

        caption = (
            f"📺 <b>{title}</b>\n\n"
            f"📅 <b>Yili:</b> {year}\n"
            f"🎭 <b>Janri:</b> {genre}\n"
            f"🌍 <b>Mamlakat:</b> {country}\n"
            f"📌 <b>Holati:</b> {status}\n\n"
            f"📝 <b>Tavsif:</b>\n{desc}\n\n"
            f"Kerakli mavsum va qismni pastdan tanlang:"
        )

        keyboard = series_detail_keyboard(series_id, is_fav, seasons)
        poster = series.get("poster")

        try:
            if poster and (poster.startswith("http://") or poster.startswith("https://") or len(poster) > 20):
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await query.message.reply_photo(
                    photo=poster,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                return
        except Exception as e:
            logger.warning("Serial posterini yuborishda xato: %s", e)

        try:
            await query.edit_message_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception:
            await query.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data.startswith("season_"):
        parts = data.split("_")
        series_id = int(parts[1])
        season_num = int(parts[2])

        episodes = get_episodes(series_id, season_num)
        series = get_series(series_id)
        series_title = series.get("title") if series else "Serial"

        text = (
            f"📺 <b>{html.escape(series_title)}</b>\n"
            f"📌 <b>{season_num}-mavsum qismlari:</b>\n\n"
            f"Tomosha qilmoqchi bo'lgan qismingizni tanlang:"
        )
        keyboard = episodes_keyboard(series_id, season_num, episodes)
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    elif data.startswith("ep_"):
        parts = data.split("_")
        series_id = int(parts[1])
        season_num = int(parts[2])
        ep_id = int(parts[3])

        episodes = get_episodes(series_id, season_num)
        curr_ep = None
        for ep in episodes:
            if ep["id"] == ep_id:
                curr_ep = ep
                break

        if not curr_ep:
            await query.answer("Qism topilmadi!", show_alert=True)
            return

        series = get_series(series_id)
        series_title = series.get("title") if series else "Serial"
        title = html.escape(curr_ep.get("title") or f"{curr_ep.get('episode_num')}-qism")
        watch_url = curr_ep.get("watch_url") or ""

        text = (
            f"📺 <b>{html.escape(series_title)}</b>\n"
            f"🔹 <b>{season_num}-mavsum, {curr_ep.get('episode_num')}-qism</b>\n"
            f"🎬 <b>Nomi:</b> {title}\n\n"
            f"Quyidagi tugma orqali qismni tomosha qilishingiz mumkin:"
        )
        keyboard = episode_detail_keyboard(series_id, season_num, watch_url)
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception:
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def favorite_toggle_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    data = query.data
    user = update.effective_user
    if not user:
        return

    parts = data.split("_")
    item_type = parts[1]
    item_id = int(parts[2])

    is_now_fav = toggle_favorite(user.id, item_type, item_id)
    if is_now_fav:
        await query.answer("⭐️ Sevimlilar ro'yxatiga qo'shildi!", show_alert=False)
    else:
        await query.answer("❌ Sevimlilar ro'yxatidan olib tashlandi!", show_alert=False)

    if item_type == "movie":
        movie = get_movie(item_id)
        if movie:
            keyboard = movie_detail_keyboard(item_id, is_now_fav, movie.get("watch_url") or "")
            try:
                await query.edit_message_reply_markup(reply_markup=keyboard)
            except Exception:
                pass
    elif item_type == "series":
        seasons = get_seasons(item_id)
        keyboard = series_detail_keyboard(item_id, is_now_fav, seasons)
        try:
            await query.edit_message_reply_markup(reply_markup=keyboard)
        except Exception:
            pass


async def my_favorites_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not user:
        return

    if query:
        await query.answer()

    favs = get_favorites(user.id)
    if not favs:
        text = "⭐ <b>Sevimlilar ro'yxatingiz bo'sh.</b>\n\nO'zingizga yoqqan kinolarni saqlash uchun «Sevimlilarga qo'shish» tugmasidan foydalaning."
        if query:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS))
        elif update.message:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS))
        return

    text = "⭐ <b>Sizning Sevimli Kontentlaringiz:</b>\n\nKo'rish uchun ustiga bosing:"
    keyboard = movies_list_keyboard(favs, current_page=1, total_pages=1, prefix="fav_pg")
    if query:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def search_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return

    query_text = update.message.text.strip()
    if query_text.startswith("/"):
        return

    log_search(user.id, query_text)
    results, total_pages = search_movies_and_series(query_text, page=1, per_page=8)

    if not results:
        text = (
            f"🔍 «<b>{html.escape(query_text)}</b>» so'rovi bo'yicha hech narsa topilmadi.\n\n"
            "Kino nomini to'g'ri yozganingizga ishonch hosil qiling yoki boshqa nom bilan qidirib ko'ring."
        )
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS)
        )
        return

    text = (
        f"🔍 «<b>{html.escape(query_text)}</b>» bo'yicha qidiruv natijalari:\n\n"
        "Batafsil ma'lumot olish uchun tanlang:"
    )
    keyboard = movies_list_keyboard(results, current_page=1, total_pages=total_pages, prefix="search_pg")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    db_user = get_user(user.id)
    if not db_user:
        register_user(user.id, user.username or "", user.full_name or "")
        db_user = get_user(user.id)

    favs = get_favorites(user.id)
    fav_count = len(favs)
    created_at = db_user.get("created_at", "—") if db_user else "—"

    text = (
        f"📊 <b>Foydalanuvchi Profili</b>\n\n"
        f"👤 <b>Ism:</b> {html.escape(user.full_name or 'Noma\'lum')}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n"
        f"🌐 <b>Username:</b> @{user.username or 'mavjud emas'}\n"
        f"📅 <b>Ro'yxatdan o'tgan:</b> {created_at}\n"
        f"⭐ <b>Sevimlilar soni:</b> {fav_count} ta\n"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS)
        )
    elif update.message:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS)
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = (
        "💬 <b>MINXO TV Yordam va Qo'llanma</b>\n\n"
        "• <b>Qidiruv:</b> Botga kino yoki serialning nomini to'g'ridan-to'g'ri yozib yuboring.\n"
        "• <b>Seriallar:</b> Serial sahifasida mavsum va qismlarni bosqichma-bosqich tanlang.\n"
        "• <b>Sevimlilar:</b> O'zingizga ma'qul bo'lgan kinolarni «Sevimlilarga qo'shish» orqali saqlang.\n"
        "• <b>Katalog:</b> Janrlar va tillar orqali oson saralash imkoniyati mavjud.\n\n"
        "Savol va takliflar uchun administrator bilan bog'lanishingiz mumkin."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS if user else False)
        )
    elif update.message:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(is_admin=user.id in ADMIN_IDS if user else False)
        )