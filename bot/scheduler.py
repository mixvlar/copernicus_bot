import asyncio, time
from datetime import datetime
import bot.functions as funcs
from bot.utils import logger
from bot.configuration import database, programs, texts

REMIND_DAYS = (14, 7, 1)
UNFINISHED_AFTER = 24 * 3600


async def deadlines(bot):
    now = int(time.time())
    for code, program in programs.items():
        if not program["deadline"]:
            continue
        deadline = int(datetime.strptime(program["deadline"], "%Y-%m-%d").timestamp())
        days_left = (deadline - now) // 86400
        if days_left not in REMIND_DAYS:
            continue
        rows = funcs.program_subscribers(database, code)
        for uid, lang in rows:
            already = database.execute("SELECT 1 FROM sent_deadlines WHERE user_id = ? AND code = ? AND days = ?",
                                       (uid, code, days_left)).fetchone()
            if already:
                continue
            try:
                title = program["title"].get(lang, program["title"]["en"])
                await bot.send_message(uid, funcs.t(texts, lang, "deadline_soon",
                                                    title=title, days=days_left, url=program["url"]))
                database.execute("INSERT INTO sent_deadlines(user_id, code, days) VALUES(?,?,?)",
                                 (uid, code, days_left))
            except Exception:
                pass
            await asyncio.sleep(0.05)


async def unfinished(bot):
    now = int(time.time())
    rows = database.execute(
        "SELECT user_id, lang FROM users WHERE notify = 1 AND step != '' AND step != 'done' AND created_at < ?",
        (now - UNFINISHED_AFTER,)).fetchall()
    for uid, lang in rows:
        already = database.execute("SELECT 1 FROM events WHERE user_id = ? AND event = 'nudged'", (uid,)).fetchone()
        if already:
            continue
        try:
            await bot.send_message(uid, funcs.t(texts, lang, "resume_check"))
            funcs.log_event(database, uid, "nudged")
        except Exception:
            pass
        await asyncio.sleep(0.05)


async def loop(bot):
    while True:
        try:
            await deadlines(bot)
            await unfinished(bot)
        except Exception:
            logger.exception("scheduler")
        await asyncio.sleep(3600)
