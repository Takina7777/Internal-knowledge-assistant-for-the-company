"""用户存储：SQLite（stdlib sqlite3）。

表：users（账号）、refresh_tokens（刷新令牌，哈希存储，支持轮换）。
首次使用时按配置自动创建管理员账号（ADMIN_USERNAME / ADMIN_PASSWORD）。
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings
from app.core.security import hash_password, verify_password

_DEFAULT_DB = BACKEND_DIR / get_settings().DB_PATH


class UserStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_admin()

    # ---- 基础设施 ----

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    department TEXT NOT NULL DEFAULT '',
                    clearance INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token_hash TEXT UNIQUE NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL)"""
            )
            # 存量库迁移：老库 users 表没有 department / clearance 列，补上
            self._ensure_column(conn, "users", "department", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "users", "clearance", "INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    def _seed_admin(self) -> None:
        s = get_settings()
        if self.get_by_username(s.ADMIN_USERNAME) is None:
            self.create_user(
                s.ADMIN_USERNAME,
                s.ADMIN_PASSWORD,
                display_name="管理员",
                role="admin",
                department=s.ADMIN_DEPARTMENT,
                clearance=s.ADMIN_CLEARANCE,
            )

    # ---- 用户 ----

    def create_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        role: str = "user",
        department: str = "",
        clearance: int = 0,
    ) -> dict:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, display_name, role, is_active, department, clearance, created_at)"
                " VALUES (?,?,?,?,1,?,?,?)",
                (
                    username,
                    hash_password(password),
                    display_name,
                    role,
                    department,
                    clearance,
                    datetime.now().isoformat(),
                ),
            )
        user = self.get_by_username(username)
        assert user is not None
        return user

    def get_by_username(self, username: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, display_name, role, is_active, department, clearance"
                " FROM users WHERE username=?",
                (username,),
            ).fetchone()
        return self._row_to_user(row)

    def get_by_id(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, display_name, role, is_active, department, clearance"
                " FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
        return self._row_to_user(row)

    def authenticate(self, username: str, password: str) -> dict | None:
        """校验账号密码；成功返回用户信息，失败返回 None。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, display_name, role, is_active, department, clearance"
                " FROM users WHERE username=?",
                (username,),
            ).fetchone()
        if not row or row[5] != 1 or not verify_password(password, row[2]):
            return None
        return {
            "id": row[0],
            "username": row[1],
            "display_name": row[3],
            "role": row[4],
            "department": row[6],
            "clearance": row[7],
        }

    # ---- 刷新令牌（哈希存储 + 轮换）----

    def issue_refresh_token(self, user_id: int) -> str:
        token = secrets.token_urlsafe(48)
        expires_at = datetime.now() + timedelta(days=get_settings().JWT_REFRESH_EXPIRE_DAYS)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO refresh_tokens (user_id, token_hash, expires_at, created_at) VALUES (?,?,?,?)",
                (user_id, self._hash(token), expires_at.isoformat(), datetime.now().isoformat()),
            )
        return token

    def consume_refresh_token(self, token: str) -> dict | None:
        """校验刷新令牌并吊销（轮换）；有效则返回对应用户。"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, user_id, expires_at, revoked FROM refresh_tokens WHERE token_hash=?",
                (self._hash(token),),
            ).fetchone()
            if not row or row[3] or datetime.fromisoformat(row[2]) < datetime.now():
                return None
            conn.execute("UPDATE refresh_tokens SET revoked=1 WHERE id=?", (row[0],))
        return self.get_by_id(row[1])

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _row_to_user(row) -> dict | None:  # noqa: ANN001
        """users 表 7 列查询：id, username, display_name, role, is_active, department, clearance。"""
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "display_name": row[2],
            "role": row[3],
            "is_active": row[4],
            "department": row[5],
            "clearance": row[6],
        }
