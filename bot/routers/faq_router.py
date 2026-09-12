import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import bot.keyboards as keyboards
import bot.functions as funcs
from bot.utils import logger
from bot.configuration import database, configuration, faq, texts, ClientStatesGroup

faq_router = Router()


@faq_router.callback_query(F.data == "faq")
async def show_faq(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    funcs.log_event(database, call.message.chat.id, "faq_open")
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, user["lang"], "faq_title"),
                                reply_markup=keyboards.keyboard_faq(user["lang"]))


@faq_router.callback_query(F.data.startswith("faq:"))
async def faq_item(call: CallbackQuery):
    key = call.data.split(":")[1]
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    item = faq[key].get(lang, faq[key]["en"])
    funcs.log_event(database, call.message.chat.id, "faq_read", key)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, f"{item[0]}\n\n{item[1]}",
                                reply_markup=keyboards.keyboard_back(lang, "faq"))


@faq_router.callback_query(F.data == "socials")
async def socials(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    lang = user["lang"]
    funcs.log_event(database, call.message.chat.id, "socials_open")
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, lang, "socials_text"),
                                reply_markup=keyboards.keyboard_socials(lang))


@faq_router.callback_query(F.data == "ask")
async def ask_start(call: CallbackQuery, state: FSMContext):
    user = funcs.get_user(database, call.message.chat.id)
    await state.set_state(ClientStatesGroup.asking_question)
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, funcs.t(texts, user["lang"], "ask_prompt"),
                                reply_markup=keyboards.keyboard_back(user["lang"]))


@faq_router.message(ClientStatesGroup.asking_question)
async def ask_save(message: Message, state: FSMContext):
    user = funcs.get_user(database, message.chat.id)
    lang = user["lang"]
    database.execute("INSERT INTO questions(user_id, text, created_at) VALUES(?,?,?)",
                     (message.chat.id, message.text, int(time.time())))
    qid = database.cursor.lastrowid
    funcs.log_event(database, message.chat.id, "question_asked")
    logger.log(level=logger.cstm_lvl["ask_"], msg=f"{message.chat.id} asked #{qid}")
    await state.clear()
    await message.answer(funcs.t(texts, lang, "ask_sent"), reply_markup=keyboards.keyboard_menu(lang))

    for admin in configuration["admins"]:
        try:
            await message.bot.send_message(admin, f"💬 New question #{qid} from @{message.from_user.username}:\n\n{message.text}")
        except Exception:
            logger.exception("notify admin failed")
