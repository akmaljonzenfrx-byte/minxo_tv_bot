from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def pagination_buttons(current_page: int, total_pages: int, prefix: str) -> list[InlineKeyboardButton]:
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"{prefix}:{current_page - 1}"))
    buttons.append(InlineKeyboardButton(f"📄 {current_page}/{max(1, total_pages)}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"{prefix}:{current_page + 1}"))
    return buttons


def main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🎬 Kinolar", callback_data="nav:movies"),
            InlineKeyboardButton("📺 Seriallar", callback_data="nav:series")
        ],
        [
            InlineKeyboardButton("🔍 Kino qidirish", callback_data="nav:search"),
            InlineKeyboardButton("🔥 Mashhur kinolar", callback_data="nav:popular")
        ],
        [
            InlineKeyboardButton("🆕 Yangi qo‘shilganlar", callback_data="nav:latest"),
            InlineKeyboardButton("⭐ Sevimlilarim", callback_data="nav:favorites")
        ],
        [
            InlineKeyboardButton("📂 Kategoriyalar", callback_data="nav:categories"),
            InlineKeyboardButton("🌐 Til bo‘yicha", callback_data="nav:languages")
        ],
        [
            InlineKeyboardButton("📊 Mening profilim", callback_data="nav:profile"),
            InlineKeyboardButton("💬 Yordam", callback_data="nav:help")
        ]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin:main")])
    return InlineKeyboardMarkup(keyboard)


def movies_list_keyboard(movies: list[dict], current_page: int, total_pages: int, prefix: str = 'mov_pg') -> InlineKeyboardMarkup:
    keyboard = []
    for item in movies:
        item_id = item.get("id")
        title = item.get("title", "Nomsiz")
        item_type = item.get("type", "movie")
        cb_prefix = "view_series" if item_type == "series" else "view_movie"
        keyboard.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"{cb_prefix}:{item_id}")])

    if total_pages > 1:
        pag_row = pagination_buttons(current_page, total_pages, prefix)
        keyboard.append(pag_row)

    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")])
    return InlineKeyboardMarkup(keyboard)


def movie_detail_keyboard(movie_id: int, is_fav: bool, watch_url: str) -> InlineKeyboardMarkup:
    fav_text = "❤️ Sevimlilardan o'chirish" if is_fav else "🤍 Sevimlilarga qo'shish"
    fav_action = "fav_rem" if is_fav else "fav_add"
    
    keyboard = []
    if watch_url and (watch_url.startswith("http://") or watch_url.startswith("https://") or watch_url.startswith("tg://")):
        keyboard.append([InlineKeyboardButton("▶️ Tomosha qilish", url=watch_url)])
    elif watch_url:
        keyboard.append([InlineKeyboardButton("▶️ Tomosha qilish", callback_data=f"show_content:movie:{movie_id}")])

    keyboard.append([InlineKeyboardButton(fav_text, callback_data=f"{fav_action}:movie:{movie_id}")])
    keyboard.append([
        InlineKeyboardButton("🎬 Kinolarga qaytish", callback_data="nav:movies"),
        InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")
    ])
    return InlineKeyboardMarkup(keyboard)


def series_detail_keyboard(series_id: int, is_fav: bool, seasons: list[int]) -> InlineKeyboardMarkup:
    fav_text = "❤️ Sevimlilardan o'chirish" if is_fav else "🤍 Sevimlilarga qo'shish"
    fav_action = "fav_rem" if is_fav else "fav_add"
    keyboard = []

    season_buttons = []
    for s in seasons:
        season_buttons.append(InlineKeyboardButton(f"{s}-mavsum", callback_data=f"series_season:{series_id}:{s}"))
        if len(season_buttons) == 3:
            keyboard.append(season_buttons)
            season_buttons = []
    if season_buttons:
        keyboard.append(season_buttons)

    keyboard.append([InlineKeyboardButton(fav_text, callback_data=f"{fav_action}:series:{series_id}")])
    keyboard.append([
        InlineKeyboardButton("📺 Seriallarga qaytish", callback_data="nav:series"),
        InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")
    ])
    return InlineKeyboardMarkup(keyboard)


def episodes_keyboard(series_id: int, season: int, episodes: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    ep_row = []
    for ep in episodes:
        ep_id = ep.get("id")
        ep_num = ep.get("episode_num")
        ep_row.append(InlineKeyboardButton(f"{ep_num}-qism", callback_data=f"ep_view:{series_id}:{season}:{ep_id}"))
        if len(ep_row) == 3:
            keyboard.append(ep_row)
            ep_row = []
    if ep_row:
        keyboard.append(ep_row)

    keyboard.append([InlineKeyboardButton("⬅️ Serialga qaytish", callback_data=f"view_series:{series_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")])
    return InlineKeyboardMarkup(keyboard)


def episode_detail_keyboard(series_id: int, season: int, watch_url: str) -> InlineKeyboardMarkup:
    keyboard = []
    if watch_url and (watch_url.startswith("http://") or watch_url.startswith("https://") or watch_url.startswith("tg://")):
        keyboard.append([InlineKeyboardButton("▶️ Qismni ko'rish", url=watch_url)])

    keyboard.append([InlineKeyboardButton("⬅️ Qismlar ro'yxatiga qaytish", callback_data=f"series_season:{series_id}:{season}")])
    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")])
    return InlineKeyboardMarkup(keyboard)


def categories_keyboard(item_type: str = 'movies') -> InlineKeyboardMarkup:
    genres = [
        "Jangari", "Komediya", "Drama",
        "Fantastika", "Qo'rqinchli", "Melodrama",
        "Tarixiy", "Multfilm", "Detektiv"
    ]
    keyboard = []
    row = []
    for g in genres:
        row.append(InlineKeyboardButton(g, callback_data=f"genre_flt:{item_type}:{g}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")])
    return InlineKeyboardMarkup(keyboard)


def language_keyboard() -> InlineKeyboardMarkup:
    languages = [
        ("🇺🇿 O'zbekcha", "O'zbek"),
        ("🇷🇺 Ruscha", "Rus"),
        ("🇬🇧 Inglizcha", "Ingliz"),
        ("🇹🇷 Turkcha", "Turk")
    ]
    keyboard = []
    row = []
    for label, val in languages:
        row.append(InlineKeyboardButton(label, callback_data=f"lang_flt:{val}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="nav:home")])
    return InlineKeyboardMarkup(keyboard)


def sub_check_keyboard(channels: list[str]) -> InlineKeyboardMarkup:
    keyboard = []
    for idx, ch in enumerate(channels, start=1):
        clean_channel = ch.replace("@", "")
        url = f"https://t.me/{clean_channel}"
        keyboard.append([InlineKeyboardButton(f"📢 {idx}-kanalga a'zo bo'lish", url=url)])

    keyboard.append([InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistika", callback_data="adm:stats"),
            InlineKeyboardButton("🗃 Zaxira nusxa", callback_data="adm:backup")
        ],
        [
            InlineKeyboardButton("🎬 Kino qo'shish", callback_data="adm:add_movie"),
            InlineKeyboardButton("📺 Serial qo'shish", callback_data="adm:add_series")
        ],
        [
            InlineKeyboardButton("🎞 Qism qo'shish", callback_data="adm:add_episode"),
            InlineKeyboardButton("🗑 Kontent o'chirish", callback_data="adm:del_content")
        ],
        [
            InlineKeyboardButton("📢 Xabar yuborish", callback_data="adm:broadcast"),
            InlineKeyboardButton("📢 Majburiy kanallar", callback_data="adm:channels")
        ],
        [
            InlineKeyboardButton("🚫 Bloklash / Chiqarish", callback_data="adm:block_manage"),
            InlineKeyboardButton("📈 Ko'p qidirilganlar", callback_data="adm:top_searches")
        ],
        [
            InlineKeyboardButton("🔙 Foydalanuvchi menyusi", callback_data="nav:home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Jarayonni bekor qilish", callback_data="adm:cancel")]
    ])