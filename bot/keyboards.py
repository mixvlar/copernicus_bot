from urllib.parse import quote
from aiogram import types
from bot.functions import t
from bot.configuration import configuration, eligibility, programs, faq, texts, LANGS


def ikb(rows):
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def btn(text, data):
    return types.InlineKeyboardButton(text=text, callback_data=data)


def url_btn(text, url):
    return types.InlineKeyboardButton(text=text, url=url)


def keyboard_languages():
    return ikb([[btn(name, f"lang:{code}")] for code, name in LANGS.items()])


def keyboard_consent(lang):
    return ikb([[btn(t(texts, lang, "consent_button"), "consent")]])


def keyboard_subscribe(lang):
    return ikb([
        [url_btn(t(texts, lang, "subscribe_button"), configuration["channel_url"])],
        [btn(t(texts, lang, "check_button"), "check_sub")]
    ])


def keyboard_menu(lang):
    return ikb([
        [btn(t(texts, lang, "menu_check"), "check_intro")],
        [btn(t(texts, lang, "menu_programs"), "programs:0")],
        [btn(t(texts, lang, "menu_faq"), "faq")],
        [btn(t(texts, lang, "menu_ask"), "ask")],
        [btn(t(texts, lang, "menu_socials"), "socials")],
        [btn(t(texts, lang, "menu_profile"), "profile")],
        [url_btn(t(texts, lang, "menu_apply"), configuration["apply_url"])]
    ])


def keyboard_countries(lang):
    rows = []
    countries = eligibility["countries"]
    for i in range(0, len(countries), 2):
        rows.append([btn(c, f"ans:citizenship:{c}") for c in countries[i:i + 2]])
    rows.append([btn(t(texts, lang, "q_citizenship_other"), "ans:citizenship:OTHER")])
    rows.append([btn(t(texts, lang, "cancel_check"), "cancel_check")])
    return ikb(rows)


def keyboard_options(lang, key):
    rows = [[btn(t(texts, lang, f"a_{o}"), f"ans:{key}:{o}")] for o in eligibility["options"][key]]
    rows.append([
        btn(t(texts, lang, "back"), f"back:{key}"),
        btn(t(texts, lang, "cancel_check"), "cancel_check")
    ])
    return ikb(rows)


def keyboard_result(lang, eligible):
    rows = []
    if eligible:
        rows.append([url_btn(t(texts, lang, "menu_apply"), configuration["apply_url"])])
    rows.append([btn(t(texts, lang, "menu_programs"), "programs:0")])
    rows.append([btn(t(texts, lang, "retake"), "check")])
    rows.append([btn(t(texts, lang, "back"), "menu")])
    return ikb(rows)


def keyboard_faq(lang):
    rows = [[btn(v.get(lang, v["en"])[0], f"faq:{key}")] for key, v in faq.items()]
    rows.append([btn(t(texts, lang, "back"), "menu")])
    return ikb(rows)


def keyboard_back(lang, data="menu"):
    return ikb([[btn(t(texts, lang, "back"), data)]])


def keyboard_profile(lang, ref_link, share_text):
    share = f"https://t.me/share/url?url={quote(ref_link, safe='')}&text={quote(share_text, safe='')}"
    return ikb([
        [url_btn(t(texts, lang, "share_button"), share)],
        [btn(t(texts, lang, "menu_programs"), "programs:0")],
        [btn(t(texts, lang, "toggle_notify"), "toggle_notify")],
        [btn(t(texts, lang, "change_lang"), "change_lang")],
        [btn(t(texts, lang, "delete_data"), "delete_me")],
        [btn(t(texts, lang, "back"), "menu")]
    ])


def keyboard_resume(lang):
    return ikb([
        [btn(t(texts, lang, "resume_yes"), "resume_yes")],
        [btn(t(texts, lang, "resume_no"), "check")]
    ])


def keyboard_program(lang, index, total, code, has_deadline, subscribed):
    prev_index = (index - 1) % total
    next_index = (index + 1) % total
    rows = [[
        btn("◀", f"programs:{prev_index}"),
        btn(f"{index + 1}/{total}", "noop"),
        btn("▶", f"programs:{next_index}")
    ], [btn(t(texts, lang, "read_more"), f"progfull:{index}")],
        [btn(t(texts, lang, "details"), f"progopen:{index}")]]
    if has_deadline:
        label = ("🔔 " + t(texts, lang, "remind_on")) if subscribed else ("🔕 " + t(texts, lang, "remind_off"))
        rows.append([btn(label, f"progtoggle:{code}:{index}")])
    rows.append([btn(t(texts, lang, "back"), "menu")])
    return ikb(rows)


def keyboard_admin(lang):
    return ikb([
        [btn(t(texts, lang, "admin_stats"), "adm:stats")],
        [btn(t(texts, lang, "admin_questions"), "adm:questions")],
        [btn(t(texts, lang, "admin_broadcast"), "adm:broadcast")],
        [btn(t(texts, lang, "admin_export"), "adm:export")]
    ])


def keyboard_segments(lang, selected):
    from bot.functions import SEGMENTS
    rows = []
    for index, (value, key) in enumerate(SEGMENTS):
        mark = "☑" if value in selected else "☐"
        rows.append([btn(f"{mark} {t(texts, lang, key)}", f"segtoggle:{index}")])
    if selected:
        rows.append([btn(t(texts, lang, "admin_next"), "seg:done")])
    rows.append([btn(t(texts, lang, "admin_cancel"), "adm:cancel")])
    return ikb(rows)


def keyboard_confirm(lang):
    return ikb([
        [btn(t(texts, lang, "admin_send"), "adm:send")],
        [btn(t(texts, lang, "admin_cancel"), "adm:cancel")]
    ])


def keyboard_questions(lang, rows_data):
    rows = [[btn(t(texts, lang, "admin_reply_to", id=qid), f"qreply:{qid}")] for qid in rows_data]
    rows.append([btn(t(texts, lang, "admin_cancel"), "adm:cancel")])
    return ikb(rows)


def keyboard_socials(lang):
    rows = [[url_btn(label, url)] for label, url in configuration["socials"].items()]
    rows.append([btn(t(texts, lang, "back"), "menu")])
    return ikb(rows)


def keyboard_check_intro(lang):
    return ikb([
        [btn(t(texts, lang, "check_start_button"), "check")],
        [btn(t(texts, lang, "menu_programs"), "programs:0")],
        [btn(t(texts, lang, "back"), "menu")]
    ])
