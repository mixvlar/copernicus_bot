import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import bot.keyboards as keyboards
import bot.functions as funcs
from bot.utils import logger
from bot.configuration import database, configuration, programs, texts, LANGS

user_router = Router()


@user_router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    if message.chat.type != "private":
        return

    args = message.text.split(maxsplit=1)
    payload = args[1].strip() if len(args) == 2 else ""
    source, referrer_id = "direct", 0
    if payload.isdigit():
        referrer_id = int(payload)
    elif payload in configuration["sources"]:
        source = payload

    user = funcs.get_user(database, message.chat.id)
    if user is None:
        funcs.create_user(database, message.chat.id, message.from_user.username, source, referrer_id)
        funcs.log_event(database, message.chat.id, "start", source)
        logger.log(level=logger.cstm_lvl["start_"],
                   msg=f"@{message.from_user.username} {message.chat.id} start source={source} ref={referrer_id}")
        await message.answer(funcs.t(texts, "en", "choose_language"), reply_markup=keyboards.keyboard_languages())
        return

    funcs.log_event(database, message.chat.id, "start", user["source"])
    await show_menu(message.bot, message.chat.id, user["lang"])


@user_router.callback_query(F.data.startswith("lang:"))
async def choose_language(call: CallbackQuery):
    lang = call.data.split(":")[1]
    if lang not in LANGS:
        return
    funcs.set_field(database, call.message.chat.id, "lang", lang)
    await call.message.delete()
    await call.bot.send_message(
        call.message.chat.id,
        funcs.t(texts, lang, "consent", privacy_url=configuration["privacy_url"]),
        reply_markup=keyboards.keyboard_consent(lang),
        disable_web_page_preview=True)


@user_router.callback_query(F.data == "change_lang")
async def change_language(call: CallbackQuery):
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, "en", "choose_language"),
                                reply_markup=keyboards.keyboard_languages())


@user_router.callback_query(F.data == "consent")
async def consent(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    funcs.set_field(database, call.message.chat.id, "consent_at", int(time.time()))
    funcs.subscribe_all_programs(database, call.message.chat.id, list(programs.keys()))
    funcs.log_event(database, call.message.chat.id, "consent")
    logger.log(level=logger.cstm_lvl["consent_"], msg=f"{call.message.chat.id} consent")
    await call.message.delete()
    await require_subscription(call.bot, call.message.chat.id, lang)


@user_router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    if await funcs.check_subscribe(call.message.chat.id, configuration["channels_to_subscribe"], call.bot):
        funcs.set_field(database, call.message.chat.id, "subscribed", 1)
        funcs.log_event(database, call.message.chat.id, "subscribed")
        await call.message.delete()
        await show_menu(call.bot, call.message.chat.id, lang)
    else:
        await call.answer(funcs.t(texts, lang, "not_subscribed"), show_alert=True)


@user_router.callback_query(F.data == "menu")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user = funcs.get_user(database, call.message.chat.id)
    await call.message.delete()
    await show_menu(call.bot, call.message.chat.id, user["lang"])


@user_router.message(Command("delete_me"))
async def delete_me(message: Message):
    lang = funcs.user_lang(database, message.chat.id)
    funcs.delete_user_data(database, message.chat.id)
    await message.answer(funcs.t(texts, lang, "deleted"))


async def require_subscription(bot, chat_id, lang):
    if await funcs.check_subscribe(chat_id, configuration["channels_to_subscribe"], bot):
        funcs.set_field(database, chat_id, "subscribed", 1)
        funcs.log_event(database, chat_id, "subscribed")
        await show_menu(bot, chat_id, lang)
    else:
        await bot.send_message(chat_id, funcs.t(texts, lang, "need_subscribe"),
                               reply_markup=keyboards.keyboard_subscribe(lang))


async def show_menu(bot, chat_id, lang):
    user = funcs.get_user(database, chat_id)
    if user and user["step"] and user["step"] != "done":
        await bot.send_message(chat_id, funcs.t(texts, lang, "resume_check"),
                               reply_markup=keyboards.keyboard_resume(lang))
        return
    await bot.send_message(chat_id, funcs.t(texts, lang, "menu"), reply_markup=keyboards.keyboard_menu(lang))
