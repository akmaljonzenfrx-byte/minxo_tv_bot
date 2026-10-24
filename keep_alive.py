import logging
from threading import Thread
from flask import Flask, jsonify

app = Flask(__name__)
logger = logging.getLogger("MINXO_TV")

# Flask o'z loglarini konsolga haddan tashqari ko'p chiqarmasligi uchun
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.ERROR)


@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "service": "MINXO TV Telegram Bot",
        "message": "Bot muvaffaqiyatli ishlamoqda!"
    }), 200


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


def run_flask(port: int):
    try:
        app.run(host="0.0.0.0", port=port, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask keep-alive serverida xatolik yuz berdi: {e}")


def start_keep_alive(port: int):
    thread = Thread(target=run_flask, args=(port,), daemon=True)
    thread.start()
    logger.info(f"Flask keep-alive web-serveri 0.0.0.0:{port} portida ishga tushirildi.")