from aiogram import Router, F
from aiogram.types import CallbackQuery
import bot.keyboards as keyboards
import bot.functions as funcs
from bot.configuration import database, configuration, programs, texts, LANGS

profile_router = Router()


@profile_router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery):
    await call.message.delete()
    await send_profile(call.bot, call.message.chat.id)


@profile_router.callback_query(F.data == "toggle_notify")
async def toggle_notify(call: CallbackQuery):
    user = funcs.get_user(database, call.message.chat.id)
    funcs.set_field(database, call.message.chat.id, "notify", 0 if user["notify"] else 1)
    await call.message.delete()
    await send_profile(call.bot, call.message.chat.id)


@profile_router.callback_query(F.data == "delete_me")
async def delete_me(call: CallbackQuery):
    uid = call.message.chat.id
    lang = funcs.user_lang(database, uid)
    funcs.delete_user_data(database, uid)
    await call.message.delete()
    await call.bot.send_message(uid, funcs.t(texts, lang, "deleted"))


async def send_profile(bot, chat_id):
    user = funcs.get_user(database, chat_id)
    lang = user["lang"]
    result = funcs.last_result(database, chat_id) or funcs.t(texts, lang, "profile_not_checked")
    ref_link = f"https://t.me/{configuration['bot_username']}?start={chat_id}"
    codes = funcs.user_program_codes(database, chat_id)
    text = funcs.t(texts, lang, "profile",
                   language=LANGS.get(lang, lang),
                   result=result,
                   notify=funcs.t(texts, lang, "notify_on" if user["notify"] else "notify_off"),
                   referrers=user["referrers"],
                   ref_link=ref_link)
    text += "\n" + funcs.t(texts, lang, "my_programs", count=len(codes), total=len(programs))
    await bot.send_message(chat_id, text, parse_mode="HTML",
                           reply_markup=keyboards.keyboard_profile(lang, ref_link, funcs.t(texts, lang, "share_text")),
                           disable_web_page_preview=True)
