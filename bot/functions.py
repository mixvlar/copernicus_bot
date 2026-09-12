import json, sqlite3, time, csv, io
from pathlib import Path
from bot.utils import logger

FILES = Path(__file__).parent.parent / "files"


class Database:
    def __init__(self, name: str):
        self.name = name
        self.connect = sqlite3.connect(self.name, check_same_thread=False)
        self.cursor = self.connect.cursor()

    def execute(self, prompt: str, parameters=None):
        try:
            if parameters is not None:
                self.cursor.execute(prompt, parameters)
            else:
                self.cursor.execute(prompt)
            self.connect.commit()
        except Exception:
            logger.exception(f"DB: {prompt[:70]}")
            raise
        return self.cursor

    def create_tables(self):
        self.execute('''CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, lang TEXT DEFAULT 'en',
            consent_at INTEGER DEFAULT 0, source TEXT DEFAULT 'direct',
            referrer_id INTEGER DEFAULT 0, referrers INTEGER DEFAULT 0,
            subscribed INTEGER DEFAULT 0, step TEXT DEFAULT '',
            notify INTEGER DEFAULT 1, created_at INTEGER)''')
        self.execute('''CREATE TABLE IF NOT EXISTS answers(
            user_id INTEGER, question_key TEXT, answer TEXT, created_at INTEGER,
            PRIMARY KEY(user_id, question_key))''')
        self.execute('''CREATE TABLE IF NOT EXISTS results(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            result TEXT, failed TEXT, created_at INTEGER)''')
        self.execute('''CREATE TABLE IF NOT EXISTS questions(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT,
            answer TEXT DEFAULT '', created_at INTEGER, answered_at INTEGER DEFAULT 0)''')
        self.execute('''CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            event TEXT, meta TEXT, created_at INTEGER)''')
        self.execute('''CREATE TABLE IF NOT EXISTS broadcasts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER, text TEXT,
            segment TEXT, variant TEXT, sent INTEGER DEFAULT 0, created_at INTEGER)''')
        self.execute('''CREATE TABLE IF NOT EXISTS user_programs(
            user_id INTEGER, code TEXT, PRIMARY KEY(user_id, code))''')
        self.execute('''CREATE TABLE IF NOT EXISTS sent_deadlines(
            user_id INTEGER, code TEXT, days INTEGER,
            PRIMARY KEY(user_id, code, days))''')


def load_json(*parts):
    with open(str(FILES.joinpath(*parts)), encoding="UTF-8") as f:
        return json.load(f)


def log_event(database, user_id, event, meta=""):
    database.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)",
                     (user_id, event, meta, int(time.time())))


USER_KEYS = ("user_id", "username", "lang", "consent_at", "source", "referrer_id",
             "referrers", "subscribed", "step", "notify", "created_at")


USER_TABLES = ("answers", "results", "questions", "events", "sent_deadlines", "user_programs")


def delete_user_data(database, user_id):
    for table in USER_TABLES:
        database.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    database.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


def user_lang(database, user_id):
    row = database.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return row[0] if row else "en"


def get_user(database, user_id):
    row = database.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(zip(USER_KEYS, row)) if row else None


def create_user(database, user_id, username, source, referrer_id):
    database.execute("INSERT OR IGNORE INTO users(user_id, username, source, referrer_id, created_at) VALUES(?,?,?,?,?)",
                     (user_id, username, source, referrer_id, int(time.time())))
    if referrer_id:
        database.execute("UPDATE users SET referrers = referrers+1 WHERE user_id = ?", (referrer_id,))


def set_field(database, user_id, field, value):
    database.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))


def t(texts, lang, key, **kwargs):
    s = texts.get(lang, texts["en"]).get(key) or texts["en"].get(key, key)
    return s.format(**kwargs) if kwargs else s


async def check_subscribe(user_id, channels, bot):
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status == "left":
                return False
        except Exception:
            logger.exception(f"check_subscribe {channel}")
            return False
    return True


def save_answer(database, user_id, key, answer):
    database.execute("INSERT OR REPLACE INTO answers(user_id, question_key, answer, created_at) VALUES(?,?,?,?)",
                     (user_id, key, answer, int(time.time())))


def get_answers(database, user_id):
    rows = database.execute("SELECT question_key, answer FROM answers WHERE user_id = ?", (user_id,)).fetchall()
    return dict(rows)


def answer_passes(key, value, eligibility):
    if key == "citizenship":
        return value in eligibility["countries"]
    return value in eligibility["pass"].get(key, [])


def check_eligibility(answers, eligibility):
    failed = [key for key in eligibility["order"]
              if not answer_passes(key, answers.get(key), eligibility)]
    return ("eligible" if not failed else "not_eligible"), failed


def save_result(database, user_id, result, failed):
    database.execute("INSERT INTO results(user_id, result, failed, created_at) VALUES(?,?,?,?)",
                     (user_id, result, ",".join(failed), int(time.time())))


def last_result(database, user_id):
    row = database.execute("SELECT result FROM results WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                           (user_id,)).fetchone()
    return row[0] if row else None


def funnel(database):
    steps = ["start", "consent", "subscribed", "check_intro", "check_started", "check_finished"]
    out = {}
    for step in steps:
        out[step] = database.execute("SELECT COUNT(DISTINCT user_id) FROM events WHERE event = ?",
                                     (step,)).fetchone()[0]
    return out


def stats_by(database, column):
    rows = database.execute(f"SELECT {column}, COUNT(*) FROM users GROUP BY {column} ORDER BY COUNT(*) DESC").fetchall()
    return rows


def stats_results(database):
    rows = database.execute("SELECT result, COUNT(*) FROM results GROUP BY result").fetchall()
    failed = database.execute("SELECT failed FROM results WHERE failed != ''").fetchall()
    reasons = {}
    for (f,) in failed:
        for r in f.split(","):
            reasons[r] = reasons.get(r, 0) + 1
    return rows, reasons


CSV_DELIMITERS = {"en": ",", "ru": ";", "de": ";"}


def csv_delimiter(lang):
    return CSV_DELIMITERS.get(lang, ";")


def to_csv(rows, header, delimiter=";"):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, lineterminator="\r\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def segment_users(database, segment):
    if segment == "all":
        return [r[0] for r in database.execute("SELECT user_id FROM users WHERE notify = 1").fetchall()]
    if segment == "unfinished":
        return [r[0] for r in database.execute(
            "SELECT user_id FROM users WHERE notify = 1 AND step != '' AND step != 'done'").fetchall()]
    if ":" not in segment:
        return []
    key, value = segment.split(":", 1)
    if key == "lang":
        q = "SELECT user_id FROM users WHERE notify = 1 AND lang = ?"
    elif key == "source":
        q = "SELECT user_id FROM users WHERE notify = 1 AND source = ?"
    elif key == "result":
        q = ("SELECT DISTINCT user_id FROM results WHERE result = ? AND user_id IN "
             "(SELECT user_id FROM users WHERE notify = 1)")
    else:
        return []
    return [r[0] for r in database.execute(q, (value,)).fetchall()]


def subscribe_all_programs(database, user_id, codes):
    for code in codes:
        database.execute("INSERT OR IGNORE INTO user_programs(user_id, code) VALUES(?,?)", (user_id, code))


def user_program_codes(database, user_id):
    rows = database.execute("SELECT code FROM user_programs WHERE user_id = ?", (user_id,)).fetchall()
    return {r[0] for r in rows}


def toggle_program(database, user_id, code):
    row = database.execute("SELECT 1 FROM user_programs WHERE user_id = ? AND code = ?", (user_id, code)).fetchone()
    if row:
        database.execute("DELETE FROM user_programs WHERE user_id = ? AND code = ?", (user_id, code))
        return False
    database.execute("INSERT INTO user_programs(user_id, code) VALUES(?,?)", (user_id, code))
    return True


def program_subscribers(database, code):
    rows = database.execute(
        "SELECT u.user_id, u.lang FROM users u JOIN user_programs p ON p.user_id = u.user_id "
        "WHERE p.code = ? AND u.notify = 1", (code,)).fetchall()
    return rows


SEGMENTS = [
    ("all", "admin_seg_all"),
    ("lang:ru", "admin_seg_ru"),
    ("lang:en", "admin_seg_en"),
    ("result:eligible", "admin_seg_eligible"),
    ("result:not_eligible", "admin_seg_not_eligible"),
    ("unfinished", "admin_seg_unfinished"),
    ("source:ig", "admin_seg_ig"),
    ("source:yt", "admin_seg_yt"),
    ("source:tg", "admin_seg_tg")
]


def segment_users_many(database, values):
    if "all" in values:
        return segment_users(database, "all")
    out = []
    seen = set()
    for value in values:
        for uid in segment_users(database, value):
            if uid not in seen:
                seen.add(uid)
                out.append(uid)
    return out


def segment_labels(values):
    names = dict(SEGMENTS)
    return [names[v] for v in values if v in names]
