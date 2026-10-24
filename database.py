import os
import shutil
import sqlite3
from datetime import datetime
from config import DB_PATH, BASE_DIR


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                alt_title TEXT,
                description TEXT,
                poster_url TEXT,
                release_year INTEGER,
                genre TEXT,
                country TEXT,
                language TEXT,
                duration TEXT,
                rating REAL DEFAULT 0.0,
                watch_url TEXT,
                views INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                alt_title TEXT,
                description TEXT,
                poster_url TEXT,
                release_year INTEGER,
                genre TEXT,
                country TEXT,
                language TEXT,
                rating REAL DEFAULT 0.0,
                status TEXT DEFAULT 'Davom etmoqda',
                total_seasons INTEGER DEFAULT 1,
                views INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                episode_num INTEGER NOT NULL,
                title TEXT,
                watch_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (series_id) REFERENCES series (id) ON DELETE CASCADE,
                UNIQUE(series_id, season, episode_num)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (tg_id) ON DELETE CASCADE,
                UNIQUE(user_id, item_type, item_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES ('mandatory_sub', '0')
        """)

        conn.commit()


def register_user(tg_id: int, username: str, full_name: str) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (tg_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (tg_id, username or "", full_name or ""))
        conn.commit()


def get_user(tg_id: int) -> dict | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_users() -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def set_user_block(tg_id: int, blocked: int) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_blocked = ? WHERE tg_id = ?", (blocked, tg_id))
        conn.commit()


def add_movie(data: dict) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movies (
                title, alt_title, description, poster_url, release_year,
                genre, country, language, duration, rating, watch_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title"),
            data.get("alt_title", ""),
            data.get("description", ""),
            data.get("poster_url", ""),
            data.get("release_year"),
            data.get("genre", ""),
            data.get("country", ""),
            data.get("language", ""),
            data.get("duration", ""),
            data.get("rating", 0.0),
            data.get("watch_url", "")
        ))
        conn.commit()
        return cursor.lastrowid


def get_movie(movie_id: int) -> dict | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (movie_id,))
        conn.commit()
        cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_movies(
    page: int = 1,
    per_page: int = 5,
    genre: str = None,
    year: int = None,
    lang: str = None,
    order_by: str = "created_at"
) -> tuple[list[dict], int]:
    valid_orders = {
        "created_at": "created_at DESC",
        "rating": "rating DESC",
        "views": "views DESC",
        "title": "title ASC"
    }
    order_clause = valid_orders.get(order_by, "created_at DESC")

    conditions = ["is_active = 1"]
    params = []

    if genre:
        conditions.append("genre LIKE ?")
        params.append(f"%{genre}%")
    if year:
        conditions.append("release_year = ?")
        params.append(year)
    if lang:
        conditions.append("language LIKE ?")
        params.append(f"%{lang}%")

    where_clause = " WHERE " + " AND ".join(conditions)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as cnt FROM movies {where_clause}", params)
        total_count = cursor.fetchone()["cnt"]

        offset = (page - 1) * per_page
        query_sql = f"SELECT * FROM movies {where_clause} ORDER BY {order_clause} LIMIT ? OFFSET ?"
        cursor.execute(query_sql, params + [per_page, offset])
        rows = [dict(row) for row in cursor.fetchall()]

        return rows, total_count


def search_movies_and_series(query: str, page: int = 1, per_page: int = 5) -> tuple[list[dict], int]:
    normalized_query = f"%{query.strip().lower()}%"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        count_sql = """
            SELECT (
                (SELECT COUNT(*) FROM movies WHERE is_active = 1 AND (LOWER(title) LIKE ? OR LOWER(alt_title) LIKE ?)) +
                (SELECT COUNT(*) FROM series WHERE is_active = 1 AND (LOWER(title) LIKE ? OR LOWER(alt_title) LIKE ?))
            ) as total
        """
        cursor.execute(count_sql, (normalized_query, normalized_query, normalized_query, normalized_query))
        total_count = cursor.fetchone()["total"]

        offset = (page - 1) * per_page
        search_sql = """
            SELECT id, title, poster_url, release_year, genre, rating, 'movie' as type, created_at
            FROM movies
            WHERE is_active = 1 AND (LOWER(title) LIKE ? OR LOWER(alt_title) LIKE ?)
            UNION ALL
            SELECT id, title, poster_url, release_year, genre, rating, 'series' as type, created_at
            FROM series
            WHERE is_active = 1 AND (LOWER(title) LIKE ? OR LOWER(alt_title) LIKE ?)
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(search_sql, (
            normalized_query, normalized_query,
            normalized_query, normalized_query,
            per_page, offset
        ))
        rows = [dict(row) for row in cursor.fetchall()]

        return rows, total_count


def delete_movie(movie_id: int) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE item_type = 'movie' AND item_id = ?", (movie_id,))
        cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        conn.commit()


def add_series(data: dict) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO series (
                title, alt_title, description, poster_url, release_year,
                genre, country, language, rating, status, total_seasons
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title"),
            data.get("alt_title", ""),
            data.get("description", ""),
            data.get("poster_url", ""),
            data.get("release_year"),
            data.get("genre", ""),
            data.get("country", ""),
            data.get("language", ""),
            data.get("rating", 0.0),
            data.get("status", "Davom etmoqda"),
            data.get("total_seasons", 1)
        ))
        conn.commit()
        return cursor.lastrowid


def get_series(series_id: int) -> dict | None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE series SET views = views + 1 WHERE id = ?", (series_id,))
        conn.commit()
        cursor.execute("SELECT * FROM series WHERE id = ?", (series_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_series(page: int = 1, per_page: int = 5) -> tuple[list[dict], int]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM series WHERE is_active = 1")
        total_count = cursor.fetchone()["cnt"]

        offset = (page - 1) * per_page
        cursor.execute("""
            SELECT * FROM series
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        rows = [dict(row) for row in cursor.fetchall()]

        return rows, total_count


def delete_series(series_id: int) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE item_type = 'series' AND item_id = ?", (series_id,))
        cursor.execute("DELETE FROM episodes WHERE series_id = ?", (series_id,))
        cursor.execute("DELETE FROM series WHERE id = ?", (series_id,))
        conn.commit()


def add_episode(series_id: int, season: int, episode_num: int, title: str, watch_url: str) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO episodes (series_id, season, episode_num, title, watch_url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(series_id, season, episode_num) DO UPDATE SET
                title = excluded.title,
                watch_url = excluded.watch_url
        """, (series_id, season, episode_num, title, watch_url))

        cursor.execute("""
            UPDATE series
            SET total_seasons = MAX(total_seasons, ?)
            WHERE id = ?
        """, (season, series_id))

        conn.commit()
        return cursor.lastrowid


def get_episodes(series_id: int, season: int) -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM episodes
            WHERE series_id = ? AND season = ?
            ORDER BY episode_num ASC
        """, (series_id, season))
        return [dict(row) for row in cursor.fetchall()]


def get_seasons(series_id: int) -> list[int]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT season FROM episodes
            WHERE series_id = ?
            ORDER BY season ASC
        """, (series_id,))
        rows = cursor.fetchall()
        seasons = [row["season"] for row in rows]
        if not seasons:
            cursor.execute("SELECT total_seasons FROM series WHERE id = ?", (series_id,))
            s_row = cursor.fetchone()
            if s_row and s_row["total_seasons"] > 0:
                seasons = list(range(1, s_row["total_seasons"] + 1))
        return seasons


def toggle_favorite(user_id: int, item_type: str, item_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM favorites
            WHERE user_id = ? AND item_type = ? AND item_id = ?
        """, (user_id, item_type, item_id))
        row = cursor.fetchone()

        if row:
            cursor.execute("DELETE FROM favorites WHERE id = ?", (row["id"],))
            conn.commit()
            return False
        else:
            cursor.execute("""
                INSERT INTO favorites (user_id, item_type, item_id)
                VALUES (?, ?, ?)
            """, (user_id, item_type, item_id))
            conn.commit()
            return True


def is_favorite(user_id: int, item_type: str, item_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM favorites
            WHERE user_id = ? AND item_type = ? AND item_id = ?
        """, (user_id, item_type, item_id))
        return cursor.fetchone() is not None


def get_favorites(user_id: int) -> list[dict]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.item_type, f.item_id,
                   CASE WHEN f.item_type = 'movie' THEN m.title ELSE s.title END as title,
                   CASE WHEN f.item_type = 'movie' THEN m.rating ELSE s.rating END as rating,
                   CASE WHEN f.item_type = 'movie' THEN m.release_year ELSE s.release_year END as release_year
            FROM favorites f
            LEFT JOIN movies m ON f.item_type = 'movie' AND f.item_id = m.id
            LEFT JOIN series s ON f.item_type = 'series' AND f.item_id = s.id
            WHERE f.user_id = ?
            ORDER BY f.created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def log_search(user_id: int, query: str) -> None:
    if not query or not query.strip():
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO search_logs (user_id, query)
            VALUES (?, ?)
        """, (user_id, query.strip().lower()))
        conn.commit()


def get_top_searches(limit: int = 5) -> list[tuple[str, int]]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT query, COUNT(*) as cnt
            FROM search_logs
            GROUP BY query
            ORDER BY cnt DESC
            LIMIT ?
        """, (limit,))
        return [(row["query"], row["cnt"]) for row in cursor.fetchall()]


def get_stats() -> dict:
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total_users FROM users")
        total_users = cursor.fetchone()["total_users"]

        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) as new_today FROM users WHERE DATE(created_at) = ?", (today_str,))
        new_today = cursor.fetchone()["new_today"]

        cursor.execute("SELECT COUNT(*) as blocked_users FROM users WHERE is_blocked = 1")
        blocked_users = cursor.fetchone()["blocked_users"]

        cursor.execute("SELECT COUNT(*) as total_movies FROM movies WHERE is_active = 1")
        total_movies = cursor.fetchone()["total_movies"]

        cursor.execute("SELECT COUNT(*) as total_series FROM series WHERE is_active = 1")
        total_series = cursor.fetchone()["total_series"]

        cursor.execute("SELECT COUNT(*) as total_episodes FROM episodes")
        total_episodes = cursor.fetchone()["total_episodes"]

        cursor.execute("SELECT COUNT(*) as total_searches FROM search_logs")
        total_searches = cursor.fetchone()["total_searches"]

        cursor.execute("SELECT COUNT(*) as total_favorites FROM favorites")
        total_favorites = cursor.fetchone()["total_favorites"]

        return {
            "total_users": total_users,
            "new_today": new_today,
            "blocked_users": blocked_users,
            "total_movies": total_movies,
            "total_series": total_series,
            "total_episodes": total_episodes,
            "total_searches": total_searches,
            "total_favorites": total_favorites
        }


def get_required_channels() -> list[str]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_username FROM required_channels ORDER BY id ASC")
        return [row["channel_username"] for row in cursor.fetchall()]


def add_channel(channel: str) -> None:
    cleaned = channel.strip()
    if not cleaned.startswith("@") and not cleaned.startswith("-100"):
        cleaned = f"@{cleaned}"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO required_channels (channel_username)
            VALUES (?)
        """, (cleaned,))
        conn.commit()


def remove_channel(channel: str) -> None:
    cleaned = channel.strip()
    if not cleaned.startswith("@") and not cleaned.startswith("-100"):
        cleaned = f"@{cleaned}"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM required_channels WHERE channel_username = ?", (cleaned,))
        conn.commit()


def create_db_backup() -> str:
    backups_dir = os.path.join(BASE_DIR, "backups")
    os.makedirs(backups_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file_path = os.path.join(backups_dir, f"minxo_backup_{timestamp}.sqlite")
    shutil.copyfile(DB_PATH, backup_file_path)
    return backup_file_path