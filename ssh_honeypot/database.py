import asyncio
import logging
import aiosqlite
import time

class UserDatabase:
    def __init__(self, filename):
        self._set_up = False
        self._filename = filename
        self._logger = logging.getLogger(self.__class__.__name__)

    async def prepare(self):
        queries = [
        "PRAGMA journal_mode=WAL;",
        "create table if not exists user (username text, password text, created_at integer)",
        "create unique index if not exists idx_user_main on user (username, password)",
        "create index if not exists idx_user_time on user (created_at)",

        "create table if not exists cred_usage (username text, password text, count integer)",
        "create unique index if not exists idx_cred_usage_main on cred_usage (username, password)",

        "create table if not exists command (username text, session blob, ts real, command text, single boolean)",
        "create index if not exists idx_command_session_ts on command (session, ts)",
        ]
        async with aiosqlite.connect(self._filename) as db:
            for q in queries:
                await db.execute(q)
            await db.commit()

    async def add_user(self, login, password):
        ts = int(time.time())
        async with aiosqlite.connect(self._filename) as db:
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute('insert into user (username, password, created_at)'
                             'values (?, ?, ?) on conflict(username, password) '
                             'do update set created_at = ?',
                             (login, password, ts, ts))
            await db.commit()

    async def check_user(self, login, password):
        async with aiosqlite.connect(self._filename) as db:
            async with db.execute('select created_at from user where '
                                  'username=? and password=?',
                                  (login, password)) as cur:
                res = await cur.fetchone()
        return res

    async def count_credentials(self, login, password):
        async with aiosqlite.connect(self._filename) as db:
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute('insert into cred_usage (username, password, count) '
                             'values (?, ?, ?) on conflict(username, password) '
                             'do update set count = count + 1',
                             (login, password, 1))
            await db.commit()

    async def log_command(self, login, session, ts, command, single):
        async with aiosqlite.connect(self._filename) as db:
            await db.execute("PRAGMA synchronous=NORMAL;")
            await db.execute('insert into command (username, session, ts, '
                             'command, single) values (?, ?, ?, ?, ?)',
                             (login, session.bytes, ts, command, single))
            await db.commit()
