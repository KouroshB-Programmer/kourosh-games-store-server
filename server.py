from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import uuid

app = FastAPI(title="Kourosh Games Store API")

DB_NAME = "store.db"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            game_filename TEXT NOT NULL,
            cover_filename TEXT
        )
    """)
    conn.commit()
    conn.close()

def row_to_game(row):
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2] or "",
        "category": row[3] or "Other",
        "file_url": f"/files/games/{row[4]}",
        "cover_url": f"/files/covers/{row[5]}" if row[5] else ""
    }

@app.get("/")
def home():
    return {"store": "Kourosh Games Store", "status": "online"}

@app.get("/games")
def get_games(request: Request):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, category, game_filename, cover_filename FROM games ORDER BY id DESC")
    games = [row_to_game(row) for row in cursor.fetchall()]
    conn.close()

    # Make URLs absolute so the desktop client can download them.
    base = str(request.base_url).rstrip("/")
    if base:
        for game in games:
            game["file_url"] = base + game["file_url"]
            if game["cover_url"]:
                game["cover_url"] = base + game["cover_url"]
    return games

@app.post("/games/upload")
async def upload_game(
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("Other"),
    game_file: UploadFile = File(...),
    cover_file: UploadFile | None = File(None)
):
    original = os.path.basename(game_file.filename or "game.zip")
    ext = os.path.splitext(original)[1].lower()
    if ext not in (".zip", ".exe"):
        raise HTTPException(status_code=400, detail="Game file must be ZIP or EXE")

    game_filename = f"{uuid.uuid4().hex}{ext}"
    game_path = os.path.join(UPLOAD_DIR, game_filename)

    with open(game_path, "wb") as out:
        while True:
            chunk = await game_file.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)

    cover_filename = None
    if cover_file and cover_file.filename:
        cover_ext = os.path.splitext(os.path.basename(cover_file.filename))[1].lower()
        if cover_ext not in (".jpg", ".jpeg", ".png", ".webp"):
            os.remove(game_path)
            raise HTTPException(status_code=400, detail="Invalid cover image")
        cover_filename = f"{uuid.uuid4().hex}{cover_ext}"
        cover_path = os.path.join(UPLOAD_DIR, cover_filename)
        with open(cover_path, "wb") as out:
            while True:
                chunk = await cover_file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO games (name, description, category, game_filename, cover_filename) VALUES (?, ?, ?, ?, ?)",
        (name.strip(), description.strip(), category.strip() or "Other", game_filename, cover_filename)
    )
    conn.commit()
    game_id = cursor.lastrowid
    conn.close()

    return {"success": True, "id": game_id, "message": "Game uploaded successfully"}

@app.delete("/games/{game_id}")
def delete_game(game_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT game_filename, cover_filename FROM games WHERE id = ?", (game_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False}

    cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
    conn.commit()
    conn.close()

    for filename in row:
        if filename:
            path = os.path.join(UPLOAD_DIR, filename)
            try:
                os.remove(path)
            except OSError:
                pass

    return {"success": True}

@app.get("/files/games/{filename}")
def get_game_file(filename: str):
    safe = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=safe, media_type="application/octet-stream")

@app.get("/files/covers/{filename}")
def get_cover_file(filename: str):
    safe = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(path)

init_db()
