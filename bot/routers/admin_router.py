import asyncio, time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
import bot.keyboards as keyboards
import bot.functions as funcs
from bot.utils import logger
from bot.configuration import database, configuration, programs, texts, ClientStatesGroup, ADMIN_PASSWORD

admin_router = Router()
authorized = set()


def is_admin(user_id):
    return user_id in configuration["admins"] or user_id in authorized


def lang_of(user_id):
    return funcs.user_lang(database, user_id)


@admin_router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.chat.id):
        await open_panel(message.bot, message.chat.id)
        return
    await state.set_state(ClientStatesGroup.admin_password)
    await message.answer("Password:")


@admin_router.message(ClientStatesGroup.admin_password)
async def admin_password(message: Message, state: FSMContext):
    await state.clear()
    if ADMIN_PASSWORD and message.text == ADMIN_PASSWORD:
        authorized.add(message.chat.id)
        logger.info(f"admin login {message.chat.id}")
        await open_panel(message.bot, message.chat.id)
    else:
        await message.answer("Wrong password.")


@admin_router.callback_query(F.data == "adm:stats")
async def stats(call: CallbackQuery):
    if not is_admin(call.message.chat.id):
        return
    lang = lang_of(call.message.chat.id)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, build_stats(lang), parse_mode="HTML",
                                reply_markup=keyboards.keyboard_admin(lang))


@admin_router.callback_query(F.data == "adm:export")
async def export(call: CallbackQuery):
    if not is_admin(call.message.chat.id):
        return
    lang = lang_of(call.message.chat.id)
    rows = database.execute(
        "SELECT u.user_id, u.username, u.lang, u.source, u.referrers, "
        "datetime(u.created_at, 'unixepoch'), u.step, "
        "(SELECT result FROM results r WHERE r.user_id = u.user_id ORDER BY r.id DESC LIMIT 1), "
        "(SELECT answer FROM answers a WHERE a.user_id = u.user_id AND a.question_key = 'citizenship'), "
        "(SELECT COUNT(*) FROM user_programs p WHERE p.user_id = u.user_id) "
        "FROM users u ORDER BY u.created_at DESC").fetchall()
    data = funcs.to_csv(rows, ["user_id", "username", "lang", "source", "referrers",
                               "registered", "step", "result", "citizenship", "programs"],
                        delimiter=funcs.csv_delimiter(lang))
    await call.bot.send_document(call.message.chat.id, BufferedInputFile(data, filename="users.csv"))


@admin_router.callback_query(F.data == "adm:questions")
async def questions(call: CallbackQuery):
    if not is_admin(call.message.chat.id):
        return
    lang = lang_of(call.message.chat.id)
    rows = database.execute(
        "SELECT id, user_id, text FROM questions WHERE answered_at = 0 ORDER BY id LIMIT 10").fetchall()
    await call.message.delete()
    if not rows:
        await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "admin_no_questions"),
                                    reply_markup=keyboards.keyboard_admin(lang))
        return
    body = "\n\n".join(f"❓ #{qid} · {uid}\n{text}" for qid, uid, text in rows)
    await call.bot.send_message(call.message.chat.id, body,
                                reply_markup=keyboards.keyboard_questions(lang, [r[0] for r in rows]))


@admin_router.callback_query(F.data.startswith("qreply:"))
async def question_reply(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.message.chat.id):
        return
    qid = int(call.data.split(":")[1])
    lang = lang_of(call.message.chat.id)
    row = database.execute("SELECT text FROM questions WHERE id = ?", (qid,)).fetchone()
    question = row[0] if row else ""
    await state.set_state(ClientStatesGroup.admin_answer)
    await state.update_data(qid=qid, question=question)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id,
                                funcs.t(texts, lang, "admin_enter_answer", id=qid, question=question))


@admin_router.message(ClientStatesGroup.admin_answer)
async def question_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    qid = data.get("qid")
    question = data.get("question", "")
    await state.clear()
    row = database.execute("SELECT user_id FROM questions WHERE id = ?", (qid,)).fetchone()
    if row is None:
        await message.answer("No such question.")
        return
    database.execute("UPDATE questions SET answer = ?, answered_at = ? WHERE id = ?",
                     (message.text, int(time.time()), qid))
    target_lang = lang_of(row[0])
    try:
        await message.bot.send_message(row[0], funcs.t(texts, target_lang, "answer_received",
                                                       question=question, answer=message.text))
        await message.answer("Sent.", reply_markup=keyboards.keyboard_admin(lang_of(message.chat.id)))
    except Exception:
        logger.exception("answer delivery failed")
        await message.answer("Could not deliver.")


@admin_router.callback_query(F.data == "adm:broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.message.chat.id):
        return
    await state.clear()
    await state.update_data(segments=[])
    lang = lang_of(call.message.chat.id)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "admin_pick_segment"),
                                reply_markup=keyboards.keyboard_segments(lang, []))


@admin_router.callback_query(F.data.startswith("segtoggle:"))
async def broadcast_toggle(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.message.chat.id):
        return
    index = int(call.data.split(":")[1])
    value = funcs.SEGMENTS[index][0]
    data = await state.get_data()
    selected = list(data.get("segments", []))

    if value in selected:
        selected.remove(value)
    elif value == "all":
        selected = ["all"]
    else:
        selected = [v for v in selected if v != "all"] + [value]

    await state.update_data(segments=selected)
    lang = lang_of(call.message.chat.id)
    await call.message.edit_reply_markup(reply_markup=keyboards.keyboard_segments(lang, selected))
    await call.answer()


@admin_router.callback_query(F.data == "seg:done")
async def broadcast_segments_done(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.message.chat.id):
        return
    data = await state.get_data()
    selected = data.get("segments", [])
    lang = lang_of(call.message.chat.id)
    if not selected:
        await call.answer(funcs.t(texts, lang, "admin_pick_none"), show_alert=True)
        return
    await state.set_state(ClientStatesGroup.admin_broadcast)
    await state.update_data(segments=selected)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "admin_enter_text"))


@admin_router.message(ClientStatesGroup.admin_broadcast)
async def broadcast_text(message: Message, state: FSMContext):
    data = await state.get_data()
    segments = data.get("segments", ["all"])
    lang = lang_of(message.chat.id)
    users = funcs.segment_users_many(database, segments)
    await state.update_data(text=message.text)
    variants = [v.strip() for v in message.text.split("||")]
    groups = ", ".join(funcs.t(texts, lang, key) for key in funcs.segment_labels(segments))
    preview = "\n\n---\n\n".join(variants)
    await message.answer(funcs.t(texts, lang, "admin_confirm", count=len(users), preview=preview) + f"\n\n[{groups}]",
                         reply_markup=keyboards.keyboard_confirm(lang))


@admin_router.callback_query(F.data == "adm:send")
async def broadcast_send(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.message.chat.id):
        return
    data = await state.get_data()
    await state.clear()
    segments, text = data.get("segments", ["all"]), data.get("text", "")
    if not text:
        await call.answer("Nothing to send", show_alert=True)
        return

    variants = [v.strip() for v in text.split("||")]
    users = funcs.segment_users_many(database, segments)
    segment = "+".join(segments)
    await call.message.delete()

    sent = 0
    for i, uid in enumerate(users):
        index = i % len(variants)
        try:
            await call.bot.send_message(uid, variants[index])
            sent += 1
            database.execute(
                "INSERT INTO broadcasts(admin_id, text, segment, variant, sent, created_at) VALUES(?,?,?,?,?,?)",
                (call.message.chat.id, variants[index], segment, chr(65 + index), 1, int(time.time())))
        except Exception:
            pass
        if i and i % 20 == 0:
            await asyncio.sleep(1)

    logger.log(level=logger.cstm_lvl["broadcast_"], msg=f"broadcast {segment} {sent}/{len(users)}")
    await call.bot.send_message(call.message.chat.id, f"Sent {sent} of {len(users)}.",
                                reply_markup=keyboards.keyboard_admin(lang_of(call.message.chat.id)))


@admin_router.callback_query(F.data == "adm:cancel")
async def admin_cancel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.message.chat.id):
        return
    await state.clear()
    lang = lang_of(call.message.chat.id)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "admin_cancelled"),
                                reply_markup=keyboards.keyboard_admin(lang))


async def open_panel(bot, chat_id):
    lang = lang_of(chat_id)
    await bot.send_message(chat_id, funcs.t(texts, lang, "admin_menu"),
                           reply_markup=keyboards.keyboard_admin(lang))


SOURCE_ICONS = {"ig": "📸", "yt": "▶️", "tg": "✈️", "vk": "🔵", "tiktok": "🎵",
                "li": "💼", "fb": "📘", "direct": "🔗"}
LANG_ICONS = {"en": "🇬🇧", "ru": "🇷🇺", "de": "🇩🇪"}


def build_stats(lang):
    def tt(key, **kw):
        return funcs.t(texts, lang, key, **kw)

    total = database.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    lines = [tt("stats_title"), "", tt("stats_users", count=total), "", tt("stats_funnel")]

    previous = None
    for step, count in funcs.funnel(database).items():
        share = "" if previous in (None, 0) else f"  <i>({round(count / previous * 100)}%)</i>"
        lines.append(f"▫️ {tt('step_' + step)} — <b>{count}</b>{share}")
        previous = count

    lines += ["", tt("stats_sources")]
    for source, count in funcs.stats_by(database, "source"):
        lines.append(f"{SOURCE_ICONS.get(source, '•')} {source} — <b>{count}</b>")

    lines += ["", tt("stats_langs")]
    for code, count in funcs.stats_by(database, "lang"):
        lines.append(f"{LANG_ICONS.get(code, '•')} {code} — <b>{count}</b>")

    results, reasons = funcs.stats_results(database)
    lines += ["", tt("stats_elig")]
    for result, count in results:
        icon = "✅" if result == "eligible" else "🚫"
        lines.append(f"{icon} {result} — <b>{count}</b>")

    if reasons:
        lines += ["", tt("stats_reasons")]
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            lines.append(f"▫️ {funcs.t(texts, lang, 'reason_' + reason)} — <b>{count}</b>")

    for event, header in (("program_open", "stats_opened"), ("program_full", "stats_reads")):
        top = database.execute(
            "SELECT meta, COUNT(DISTINCT user_id) FROM events WHERE event = ? GROUP BY meta "
            "ORDER BY COUNT(DISTINCT user_id) DESC LIMIT 5", (event,)).fetchall()
        if not top:
            continue
        lines += ["", tt(header)]
        for code, count in top:
            title = programs[code]["title"]["en"] if code in programs else code
            lines.append(f"▫️ {title} — <b>{count}</b>")

    unanswered = database.execute("SELECT COUNT(*) FROM questions WHERE answered_at = 0").fetchone()[0]
    lines += ["", tt("stats_questions", count=unanswered)]
    return "\n".join(lines)
