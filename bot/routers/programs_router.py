from datetime import datetime
from pathlib import Path
from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
import bot.keyboards as keyboards
import bot.functions as funcs
from bot.utils import logger
from bot.configuration import database, programs, texts

programs_router = Router()

CODES = list(programs.keys())
IMAGES = Path(__file__).parent.parent.parent / "files" / "images"
photo_cache = {}


@programs_router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@programs_router.callback_query(F.data.startswith("programs:"))
async def show_program(call: CallbackQuery):
    index = int(call.data.split(":")[1]) % len(CODES)
    user = funcs.get_user(database, call.message.chat.id)
    funcs.log_event(database, call.message.chat.id, "program_view", CODES[index])
    await render(call, user["lang"], index)


@programs_router.callback_query(F.data.startswith("progtoggle:"))
async def toggle(call: CallbackQuery):
    _, code, index = call.data.split(":")
    user = funcs.get_user(database, call.message.chat.id)
    now_on = funcs.toggle_program(database, call.message.chat.id, code)
    funcs.log_event(database, call.message.chat.id, "program_toggle", f"{code}:{int(now_on)}")
    await call.answer(funcs.t(texts, user["lang"], "remind_on" if now_on else "remind_off"))
    await render(call, user["lang"], int(index))


@programs_router.callback_query(F.data.startswith("progopen:"))
async def open_link(call: CallbackQuery):
    index = int(call.data.split(":")[1]) % len(CODES)
    code = CODES[index]
    program = programs[code]
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    funcs.log_event(database, call.message.chat.id, "program_open", code)
    logger.log(level=logger.cstm_lvl["apply_"], msg=f"{call.message.chat.id} opened {code}")

    title = program["title"].get(lang, program["title"]["en"])
    await call.answer()
    await call.bot.send_message(
        call.message.chat.id,
        funcs.t(texts, lang, "open_link", title=title),
        reply_markup=keyboards.ikb([[keyboards.url_btn(program["url"], program["url"])]]),
        disable_web_page_preview=True)


@programs_router.callback_query(F.data.startswith("progfull:"))
async def show_full(call: CallbackQuery):
    index = int(call.data.split(":")[1]) % len(CODES)
    code = CODES[index]
    program = programs[code]
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    funcs.log_event(database, call.message.chat.id, "program_full", code)

    title = program["title"].get(lang, program["title"]["en"])
    text = f"{title}\n\n{program['full']}"
    markup = keyboards.ikb([
        [keyboards.btn(funcs.t(texts, lang, "details"), f"progopen:{index}")],
        [keyboards.btn(funcs.t(texts, lang, "back"), f"programs:{index}")]
    ])
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, text[:4000], reply_markup=markup,
                                disable_web_page_preview=True)


async def render(call, lang, index):
    code = CODES[index]
    program = programs[code]
    caption = build_caption(lang, program)
    subscribed = code in funcs.user_program_codes(database, call.message.chat.id)
    markup = keyboards.keyboard_program(lang, index, len(CODES), code,
                                        bool(program["deadline"]), subscribed)
    media = photo_cache.get(code) or FSInputFile(str(IMAGES / program["image"]))

    try:
        if call.message.photo:
            result = await call.message.edit_media(
                media=InputMediaPhoto(media=media, caption=caption), reply_markup=markup)
        else:
            await call.message.delete()
            result = await call.bot.send_photo(call.message.chat.id, media,
                                               caption=caption, reply_markup=markup)
        if code not in photo_cache and getattr(result, "photo", None):
            photo_cache[code] = result.photo[-1].file_id
    except Exception:
        logger.exception(f"render program {code}")
        await call.bot.send_message(call.message.chat.id, caption, reply_markup=markup)


def build_caption(lang, program):
    def field(key):
        value = program[key]
        return value.get(lang, value["en"]) if isinstance(value, dict) else value

    caption = funcs.t(texts, lang, "programs_caption",
                      title=field("title"), type=field("type"),
                      location=field("location"), date=field("date"),
                      description=field("short"))
    if program["deadline"]:
        pretty = datetime.strptime(program["deadline"], "%Y-%m-%d").strftime("%d.%m.%Y")
        caption += funcs.t(texts, lang, "deadline_line", date=pretty)
    return caption
