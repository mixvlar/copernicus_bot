from aiogram import Router, F
from aiogram.types import CallbackQuery
import bot.keyboards as keyboards
import bot.functions as funcs
from bot.utils import logger
from bot.configuration import database, eligibility, texts, configuration

eligibility_router = Router()

ORDER = eligibility["order"]


@eligibility_router.callback_query(F.data == "check_intro")
async def check_intro(call: CallbackQuery):
    lang = funcs.user_lang(database, call.message.chat.id)
    funcs.log_event(database, call.message.chat.id, "check_intro")
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "check_intro"),
                                parse_mode="HTML",
                                reply_markup=keyboards.keyboard_check_intro(lang))


@eligibility_router.callback_query(F.data == "check")
async def start_check(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    database.execute("DELETE FROM answers WHERE user_id = ?", (call.message.chat.id,))
    funcs.set_field(database, call.message.chat.id, "step", ORDER[0])
    funcs.log_event(database, call.message.chat.id, "check_started")
    logger.log(level=logger.cstm_lvl["check_"], msg=f"{call.message.chat.id} check started")
    await call.message.delete()
    await ask(call.bot, call.message.chat.id, user["lang"], ORDER[0])


@eligibility_router.callback_query(F.data == "resume_yes")
async def resume(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    await call.message.delete()
    await ask(call.bot, call.message.chat.id, user["lang"], user["step"])


@eligibility_router.callback_query(F.data == "cancel_check")
async def cancel_check(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    funcs.set_field(database, call.message.chat.id, "step", "")
    database.execute("DELETE FROM answers WHERE user_id = ?", (call.message.chat.id,))
    funcs.log_event(database, call.message.chat.id, "check_cancelled", user["step"])
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "check_cancelled"))
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "menu"),
                                reply_markup=keyboards.keyboard_menu(lang))


@eligibility_router.callback_query(F.data.startswith("ans:"))
async def answer(call: CallbackQuery):
    _, key, value = call.data.split(":", 2)
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]

    funcs.save_answer(database, call.message.chat.id, key, value)
    index = ORDER.index(key)
    await call.message.delete()

    if not funcs.answer_passes(key, value, eligibility):
        await finish(call, lang, "not_eligible", [key])
        return

    if index + 1 < len(ORDER):
        next_key = ORDER[index + 1]
        funcs.set_field(database, call.message.chat.id, "step", next_key)
        await ask(call.bot, call.message.chat.id, lang, next_key)
        return

    await finish(call, lang, "eligible", [])


async def finish(call, lang, result, failed):
    funcs.set_field(database, call.message.chat.id, "step", "done")
    funcs.save_result(database, call.message.chat.id, result, failed)
    funcs.log_event(database, call.message.chat.id, "check_finished", result)
    logger.log(level=logger.cstm_lvl["check_"], msg=f"{call.message.chat.id} check {result} {failed}")

    if result == "eligible":
        text = funcs.t(texts, lang, "result_eligible")
    else:
        reasons = "\n".join("• " + funcs.t(texts, lang, f"reason_{x}") for x in failed)
        text = funcs.t(texts, lang, "result_not_eligible", reasons=reasons)
        text += "\n\n" + funcs.t(texts, lang, "other_programs")

    await call.bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                                reply_markup=keyboards.keyboard_result(lang, result == "eligible"))


@eligibility_router.callback_query(F.data.startswith("back:"))
async def back(call: CallbackQuery):
    key = call.data.split(":")[1]
    user = funcs.get_user(database, call.message.chat.id)
    index = ORDER.index(key)
    await call.message.delete()

    if index == 0:
        funcs.set_field(database, call.message.chat.id, "step", "")
        await call.bot.send_message(call.message.chat.id, funcs.t(texts, user["lang"], "menu"),
                                    reply_markup=keyboards.keyboard_menu(user["lang"]))
        return

    prev_key = ORDER[index - 1]
    funcs.set_field(database, call.message.chat.id, "step", prev_key)
    await ask(call.bot, call.message.chat.id, user["lang"], prev_key)


async def ask(bot, chat_id, lang, key):
    if key == "citizenship":
        await bot.send_message(chat_id, funcs.t(texts, lang, "q_citizenship"),
                               reply_markup=keyboards.keyboard_countries(lang))
    else:
        await bot.send_message(chat_id, funcs.t(texts, lang, f"q_{key}"),
                               reply_markup=keyboards.keyboard_options(lang, key))
