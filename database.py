
import sqlite3
import random
import string
import json
import os

if os.path.isdir("/app/data"):
    DATABASE_PATH = "/app/data/zigzag_bingo.db"
else:
    DATABASE_PATH = "zigzag_bingo.db"
print("DATABASE LOCATION:", DATABASE_PATH)


def initialize_database():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id INTEGER PRIMARY KEY,
        player_name TEXT NOT NULL,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_rooms (
        room_id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT UNIQUE NOT NULL,
        host_id INTEGER NOT NULL,
        status TEXT DEFAULT 'waiting',
        winner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("PRAGMA table_info(game_rooms)")
    columns = [row[1] for row in cursor.fetchall()]

    if "winner_id" not in columns:
        cursor.execute(
            "ALTER TABLE game_rooms ADD COLUMN winner_id INTEGER"
        )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS room_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT NOT NULL,
        player_id INTEGER NOT NULL,
        player_name TEXT NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_code, player_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS called_numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT NOT NULL,
        number INTEGER NOT NULL,
        called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_code, number)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bingo_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT NOT NULL,
        player_id INTEGER NOT NULL,
        card_data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(room_code, player_id)
    )
    """)

    connection.commit()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
    """)
    print("DATABASE TABLES:", cursor.fetchall())

    connection.close()
def register_player(player_id, player_name):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO players (player_id, player_name)
        VALUES (?, ?)
        ON CONFLICT(player_id)
        DO UPDATE SET player_name = excluded.player_name
    """, (player_id, player_name))

    connection.commit()

    registered = cursor.rowcount == 1

    connection.close()

    return registered

def get_players():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
    SELECT player_id, player_name, registration_date
    FROM players
    ORDER BY registration_date
    """)

    players = cursor.fetchall()
    connection.close()

    return players

def create_room(host_id, host_name):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    try:
        while True:
            room_code = ''.join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=6
                )
            )

            cursor.execute("""
                SELECT 1 FROM game_rooms
                WHERE room_code = ?
            """, (room_code,))

            if cursor.fetchone() is None:
                break

        cursor.execute("""
            INSERT INTO game_rooms (room_code, host_id)
            VALUES (?, ?)
        """, (room_code, host_id))

        cursor.execute("""
            INSERT INTO room_players
                (room_code, player_id, player_name)
            VALUES (?, ?, ?)
        """, (room_code, host_id, host_name))

        connection.commit()
        return room_code

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def join_room(room_code, player_id, player_name):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    room_code = room_code.upper()

    cursor.execute("""
        SELECT status
        FROM game_rooms
        WHERE room_code = ?
    """, (room_code,))

    room = cursor.fetchone()

    if room is None or room[0] != "waiting":
        connection.close()
        return False

    # Check whether player already joined
    cursor.execute("""
        SELECT 1
        FROM room_players
        WHERE room_code = ? AND player_id = ?
    """, (room_code, player_id))

    existing_player = cursor.fetchone()

    if existing_player:
        connection.close()
        return False

    cursor.execute("""
        INSERT INTO room_players
            (room_code, player_id, player_name)
        VALUES (?, ?, ?)
    """, (room_code, player_id, player_name))

    connection.commit()
    connection.close()

    return True

def get_room_player_ids(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT player_id
        FROM room_players
        WHERE room_code = ?
    """, (room_code.upper(),))

    player_ids = cursor.fetchall()
    connection.close()

    return [player[0] for player in player_ids]


def call_bingo_number(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT status FROM game_rooms WHERE room_code = ?",
        (room_code.upper(),)
    )

    room = cursor.fetchone()

    if room is None:
        connection.close()
        return None

    if room[0] == "finished":
        connection.close()
        return None

    cursor.execute(
        "SELECT number FROM called_numbers WHERE room_code = ?",
        (room_code.upper(),)
    )

    called = {row[0] for row in cursor.fetchall()}

    available = [n for n in range(1, 76) if n not in called]

    if not available:
        connection.close()
        return None

    number = random.choice(available)

    cursor.execute("""
        INSERT INTO called_numbers (room_code, number)
        VALUES (?, ?)
    """, (room_code.upper(), number))

    connection.commit()
    connection.close()

    if number <= 15:
        letter = "B"
    elif number <= 30:
        letter = "I"
    elif number <= 45:
        letter = "N"
    elif number <= 60:
        letter = "G"
    else:
        letter = "O"

    return letter, number

def get_room_player_ids(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT player_id
        FROM room_players
        WHERE room_code = ?
    """, (room_code.upper(),))

    player_ids = cursor.fetchall()
    connection.close()

    return [player[0] for player in player_ids]
def is_room_host(room_code, player_id):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT host_id
        FROM game_rooms
        WHERE room_code = ?
    """, (room_code.upper(),))

    room = cursor.fetchone()
    connection.close()

    if room is None:
        return False

    return int(room[0]) == int(player_id)

def save_bingo_card(room_code, player_id, card_data):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    card_json = json.dumps(card_data)

    cursor.execute("""
    INSERT OR REPLACE INTO bingo_cards
    (room_code, player_id, card_data)
    VALUES (?, ?, ?)
    """, (room_code.upper(), player_id, card_json))

    connection.commit()
    connection.close()

    return True
def get_bingo_card(room_code, player_id):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
    SELECT card_data
    FROM bingo_cards
    WHERE room_code = ? AND player_id = ?
    """, (room_code.upper(), player_id))

    result = cursor.fetchone()
    connection.close()

    if result is None:
        return None

    return json.loads(result[0])
def get_called_numbers(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
    SELECT number
    FROM called_numbers
    WHERE room_code = ?
    """, (room_code.upper(),))

    results = cursor.fetchall()
    connection.close()

    return [row[0] for row in results]
def finish_game(room_code, winner_id):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE game_rooms
        SET status = 'finished',
            winner_id = ?
        WHERE room_code = ?
    """, (winner_id, room_code.upper()))

    success = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return success

def reset_game(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT room_id FROM game_rooms WHERE room_code = ?",
        (room_code,)
    )

    room = cursor.fetchone()

    if room is None:
        connection.close()
        return False

    cursor.execute(
        "DELETE FROM called_numbers WHERE room_code = ?",
        (room_code,)
    )

    cursor.execute(
        "DELETE FROM bingo_cards WHERE room_code = ?",
        (room_code,)
    )

    cursor.execute(
        "UPDATE game_rooms SET status = 'waiting' WHERE room_code = ?",
        (room_code,)
    )

    connection.commit()
    connection.close()

    return True

    cursor.execute(
        "DELETE FROM bingo_cards WHERE room_code = ?",
        (room_code.upper(),)
    )

    cursor.execute(
        "UPDATE game_rooms SET status = 'waiting' WHERE room_code = ?",
        (room_code.upper(),)
    )

    connection.commit()
    connection.close()

    return True
def reset_game(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT room_id FROM game_rooms WHERE room_code = ?",
        (room_code.upper(),)
    )

    room = cursor.fetchone()

    if room is None:
        connection.close()
        return False

    cursor.execute(
        "DELETE FROM called_numbers WHERE room_code = ?",
        (room_code.upper(),)
    )

    cursor.execute(
        "DELETE FROM bingo_cards WHERE room_code = ?",
        (room_code.upper(),)
    )

    cursor.execute(
        "UPDATE game_rooms SET status = 'waiting' WHERE room_code = ?",
        (room_code.upper(),)
    )

    connection.commit()
    connection.close()

    return True
def get_game_history(limit=10):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT room_code, status, winner_id, created_at
        FROM game_rooms
        ORDER BY room_id DESC
        LIMIT ?
    """, (limit,))

    games = cursor.fetchall()
    connection.close()

    return games
def get_dashboard_stats():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM players")
    total_players = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM game_rooms")
    total_rooms = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM game_rooms WHERE status = 'waiting'"
    )
    active_games = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM game_rooms WHERE status = 'finished'"
    )
    finished_games = cursor.fetchone()[0]

    cursor.execute("""
        SELECT room_code, winner_id, created_at
        FROM game_rooms
        WHERE winner_id IS NOT NULL
        ORDER BY room_id DESC
        LIMIT 5
    """)
    recent_winners = cursor.fetchall()

    connection.close()

    return (
        total_players,
        total_rooms,
        active_games,
        finished_games,
        recent_winners
    )
def get_leaderboard(limit=10):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT players.player_name, COUNT(game_rooms.winner_id)
        FROM players
        INNER JOIN game_rooms
            ON players.player_id = game_rooms.winner_id
        WHERE game_rooms.status = 'finished'
        GROUP BY players.player_id, players.player_name
        ORDER BY COUNT(game_rooms.winner_id) DESC,
                 players.player_name ASC
        LIMIT ?
    """, (limit,))

    leaderboard = cursor.fetchall()
    connection.close()

    return leaderboard
def get_game_statistics():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # Count all games
    cursor.execute("""
        SELECT COUNT(*)
        FROM game_rooms
    """)
    total_games = cursor.fetchone()[0]

    # Count finished games
    cursor.execute("""
        SELECT COUNT(*)
        FROM game_rooms
        WHERE status = 'finished'
    """)
    finished_games = cursor.fetchone()[0]

    # Find the player with the most wins
    cursor.execute("""
        SELECT players.player_name,
               COUNT(game_rooms.winner_id) AS total_wins
        FROM players
        INNER JOIN game_rooms
            ON players.player_id = game_rooms.winner_id
        WHERE game_rooms.status = 'finished'
        GROUP BY players.player_id, players.player_name
        ORDER BY total_wins DESC
        LIMIT 1
    """)
    top_player = cursor.fetchone()

    connection.close()

    return total_games, finished_games, top_player
def get_player_statistics():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            players.player_id,
            players.player_name,
            COUNT(DISTINCT room_players.room_code) AS games_joined,
            COUNT(DISTINCT CASE
                WHEN game_rooms.status = 'finished'
                AND game_rooms.winner_id = players.player_id
                THEN game_rooms.room_code
            END) AS games_won
        FROM players
        LEFT JOIN room_players
            ON players.player_id = room_players.player_id
        LEFT JOIN game_rooms
            ON room_players.room_code = game_rooms.room_code
        GROUP BY players.player_id, players.player_name
        ORDER BY games_joined DESC, games_won DESC
    """)

    results = cursor.fetchall()
    connection.close()

    return results
def get_room_players(room_code):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT player_id, player_name
        FROM room_players
        WHERE room_code = ?
        ORDER BY joined_at
    """, (room_code.upper(),))

    players = cursor.fetchall()
    connection.close()

    return players