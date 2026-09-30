from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="Kourosh Games Store API")

DB_NAME = "store.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            cover TEXT,
            download_link TEXT
        )
    """)

    conn.commit()
    conn.close()


class Game(BaseModel):
    name: str
    description: str = ""
    category: str = "Other"
    cover: str = ""
    download_link: str = ""


@app.get("/")
def home():
    return {
        "store": "Kourosh Games Store",
        "status": "online"
    }


@app.get("/games")
def get_games():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games")

    games = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return games


@app.post("/games")
def add_game(game: Game):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO games
        (name, description, category, cover, download_link)
        VALUES (?, ?, ?, ?, ?)
    """, (
        game.name,
        game.description,
        game.category,
        game.cover,
        game.download_link
    ))

    conn.commit()

    game_id = cursor.lastrowid

    conn.close()

    return {
        "success": True,
        "id": game_id,
        "message": "Game added successfully"
    }


@app.delete("/games/{game_id}")
def delete_game(game_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM games WHERE id = ?",
        (game_id,)
    )

    conn.commit()

    deleted = cursor.rowcount > 0

    conn.close()

    return {
        "success": deleted
    }


init_db()