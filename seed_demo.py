import random, time, sqlite3, sys
from pathlib import Path

DB = str(Path(__file__).parent / "copernicus.db")
COUNTRIES = ["Russia", "Ukraine", "Kazakhstan", "Turkey", "Serbia", "Georgia", "Armenia",
             "Uzbekistan", "Belarus", "Moldova", "Germany", "Poland", "India"]
SOURCES = ["ig", "yt", "tg", "vk", "tiktok", "direct"]
LANGS = ["en", "ru", "de"]
WEIGHTS = [35, 25, 15, 10, 8, 7]

connect = sqlite3.connect(DB)
cursor = connect.cursor()
now = int(time.time())
n = int(sys.argv[1]) if len(sys.argv) > 1 else 60

for i in range(n):
    uid = 900000000 + i
    source = random.choices(SOURCES, weights=WEIGHTS)[0]
    lang = random.choices(LANGS, weights=[50, 40, 10])[0]
    created = now - random.randint(0, 21) * 86400

    cursor.execute("INSERT OR REPLACE INTO users(user_id, username, lang, consent_at, source, referrer_id, referrers, subscribed, step, notify, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (uid, f"demo{i}", lang, created, source, 0, random.choice([0, 0, 0, 1, 2]), 1, "done", 1, created))
    cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)", (uid, "start", source, created))

    if random.random() < 0.88:
        cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)", (uid, "consent", "", created))
    else:
        continue
    if random.random() < 0.74:
        cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)", (uid, "subscribed", "", created))
    else:
        continue
    if random.random() < 0.72:
        cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)", (uid, "check_intro", "", created))
    else:
        continue
    if random.random() < 0.8:
        cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)", (uid, "check_started", "", created))
    else:
        continue

    citizenship = random.choices(COUNTRIES, weights=[25, 12, 10, 8, 6, 6, 6, 6, 5, 4, 5, 4, 3])[0]
    age = random.choices(["under_28", "28_or_older"], weights=[80, 20])[0]
    enrolled = random.choices(["bachelor", "master", "phd", "not_enrolled"], weights=[50, 25, 10, 15])[0]
    language = random.choices(["en_b1", "de_b1", "both", "neither"], weights=[55, 10, 20, 15])[0]

    for key, value in (("citizenship", citizenship), ("age", age), ("enrolled", enrolled), ("language", language)):
        cursor.execute("INSERT OR REPLACE INTO answers(user_id, question_key, answer, created_at) VALUES(?,?,?,?)",
                       (uid, key, value, created))

    failed = []
    if citizenship not in ["Russia", "Ukraine", "Kazakhstan", "Turkey", "Serbia", "Georgia",
                           "Armenia", "Uzbekistan", "Belarus", "Moldova"]:
        failed.append("citizenship")
    if age != "under_28":
        failed.append("age")
    if enrolled == "not_enrolled":
        failed.append("enrolled")
    if language == "neither":
        failed.append("language")

    result = "eligible" if not failed else "not_eligible"
    cursor.execute("INSERT INTO results(user_id, result, failed, created_at) VALUES(?,?,?,?)",
                   (uid, result, ",".join(failed), created))
    cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)",
                   (uid, "check_finished", result, created))

    if random.random() < 0.5:
        code = random.choice(["ies", "bootcamp", "pir", "leaders", "edu_tourism"])
        cursor.execute("INSERT INTO events(user_id, event, meta, created_at) VALUES(?,?,?,?)",
                       (uid, "program_open", code, created))

questions = [
    "Can I apply if I graduate next year?",
    "Is German required or is English enough?",
    "Можно ли подать заявку с академическим отпуском?",
    "Does the scholarship cover flights?",
    "How many people usually apply?"
]
for i, q in enumerate(questions):
    cursor.execute("INSERT INTO questions(user_id, text, answer, created_at, answered_at) VALUES(?,?,?,?,?)",
                   (900000000 + i, q, "" if i > 1 else "Yes.", now - i * 3600, 0 if i > 1 else now))

connect.commit()
print(f"seeded {n} demo users")
