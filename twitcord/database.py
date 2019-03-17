import asyncio
import sqlite3
from logging import getLogger

from aiosqlite import connect

from .utils import tweet_factory

log = getLogger(__name__)


class TableManager():
    def __init__(self, table_name, loop=None):
        self.db = "twitcord.db"

        self.table_name = table_name
        self.loop = loop or asyncio.get_event_loop()
        
        self._init_table()

    def _init_table(self):
        db = sqlite3.connect(self.db)
        # why placeholder does not work?
        db.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} (id int primary key,\
                                                                        user_id int,\
                                                                        user_name text,\
                                                                        user_screen_name text,\
                                                                        user_icon text,\
                                                                        tweet text,\
                                                                        timestamp text)")
        db.commit()
        db.close()

    async def update(self, content: list):
        async with connect(self.db) as db:
            await db.executemany(f"INSERT OR IGNORE INTO {self.table_name} values (:id,\
                                                                                    :user_id,\
                                                                                    :user_name,\
                                                                                    :user_screen_name,\
                                                                                    :user_icon,\
                                                                                    :tweet,\
                                                                                    :timestamp)", content)
            await db.commit()

    async def diffs(self, id):
        async with connect(self.db) as db:
            db.row_factory = tweet_factory
            cur = await db.execute(f"SELECT * FROM {self.table_name} WHERE id > {id} ORDER BY id ASC")
            ret = await cur.fetchall()

        return ret or None
