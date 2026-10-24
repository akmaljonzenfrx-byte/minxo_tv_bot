import html
import json
import os
import sys
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, ADMIN_IDS, setup_logger
from database import init_db
from keep_alive import start_keep_alive
from user_handlers import (
    start_handler,
    check_subscription_handler,
    menu_navigation_handler,
    movie_view_handler,
    series_view_handler,
    favorite_toggle_handler,
    my_favorites_handler,
    search_text_handler,
    profile_handler,
    help_handler,
)
from admin_handlers import (
    admin_panel_handler,
    admin_stats_handler,
    admin_backup_handler,
    get_movie_add_conversation,
    get_series_add_conversation,
    get_episode_add_conversation,
    admin_block_user,
    cancel_admin_action,
)

logger = setup_logger()
PORT = int(os.getenv("PORT", 8080))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Botda xatolik yuz berdi:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    message = (
        f"⚠️ <b>Tizim xatoligi yuz berdi!</b>\n\n"
        f"<b>Update:</b>\n<code>{html.escape(json.dumps(update_str, indent=2, ensure_ascii=False)[:400])}</code>\n\n"
        f"<b>Xatolik:</b>\n<code>{html.escape(str(context.error))}</code>\n\n"
        f"<b>Traceback:</b>\n<code>{html.escape(tb_string[-1000:])}</code>"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
        except Exception as send_err:
            logger.error(f"Adminga xatolik yuborishda muammo: {send_err}")

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Kechirasiz, so'rovingizni bajarishda kutilmagan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
            )
        except Exception:
            pass


def main():
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN aniqlanmadi! Iltimos, .env faylini tekshiring.")
        sys.exit(1)

    logger.info("Ma'lumotlar bazasi initsializatsiya qilinmoqda...")
    init_db()

    logger.info("Render uchun keep-alive Flask serveri ishga tushirilmoqda...")
    try:
        start_keep_alive(port=PORT)
    except TypeError:
        start_keep_alive()

    logger.info("Telegram bot ilovasi qurilmoqda...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Admin ConversationHandler lari
    application.add_handler(get_movie_add_conversation())
    application.add_handler(get_series_add_conversation())
    application.add_handler(get_episode_add_conversation())

    # Buyruqlar
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("admin", admin_panel_handler))
    application.add_handler(CommandHandler("stats", admin_stats_handler))
    application.add_handler(CommandHandler("profile", profile_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("favorites", my_favorites_handler))
    application.add_handler(CommandHandler("cancel", cancel_admin_action))

    # Obunani tekshirish Callback
    application.add_handler(CallbackQueryHandler(check_subscription_handler, pattern="^check_subscription$"))

    # Bo'sh callbacklar
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern="^noop$"))

    # Admin Callback handlerlari
    application.add_handler(CallbackQueryHandler(admin_panel_handler, pattern="^admin:main$"))
    application.add_handler(CallbackQueryHandler(admin_stats_handler, pattern="^adm:stats$"))
    application.add_handler(CallbackQueryHandler(admin_backup_handler, pattern="^adm:backup$"))
    application.add_handler(CallbackQueryHandler(admin_block_user, pattern="^adm:block_manage$"))
    application.add_handler(CallbackQueryHandler(cancel_admin_action, pattern="^adm:cancel$"))

    # Sevimlilar Callback handlerlari
    application.add_handler(CallbackQueryHandler(favorite_toggle_handler, pattern="^(fav_add|fav_rem):"))

    # Foydalanuvchi Navigatsiya Callback handlerlari
    application.add_handler(CallbackQueryHandler(menu_navigation_handler, pattern="^(nav:|mov_pg:|genre_flt:|lang_flt:)"))

    # Kino va Serial ko'rish Callback handlerlari
    application.add_handler(CallbackQueryHandler(movie_view_handler, pattern="^view_movie:"))
    application.add_handler(CallbackQueryHandler(series_view_handler, pattern="^(view_series|series_season|ep_view):"))

    # Qidiruv va boshqa matnli xabarlar
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_text_handler))

    # Global xatoliklar ushlovchisi
    application.add_error_handler(error_handler)

    logger.info("MINXO TV boti muvaffaqiyatli ishga tushirildi!")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()