# Copernicus IES Applicant Bot

Telegram bot for the International Excellence Scholarship applicant funnel.

## Local run

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m bot

## Configuration

.env                  BOT_TOKEN, ADMIN_PASSWORD (secrets, not in git)
files/config.json     channels, admins, links, bot username
files/eligibility.json  20 eligible countries, questions, pass rules
files/programs.json   programmes and deadlines
files/faq.json        FAQ entries
files/texts/*.json    interface texts per language

## Demo data

python3 seed_demo.py 60

## Admin panel

Send /admin. Admins from config.json enter without a password, everyone else
is asked for ADMIN_PASSWORD from .env. Everything after that is buttons:

Statistics   funnel, sources, languages, eligibility breakdown, most viewed programmes
Questions    open questions, each with a Reply button
Broadcast    pick a segment, send the text, confirm
Export CSV   users with their source and check result

A/B test: when writing the broadcast text, separate two variants with ||

## Programmes

files/programs.json  8 programmes, each with title, type, location, date,
                     deadline, description (en/ru) and an image
files/images/        card images used in the carousel

Users browse them with arrows; the bell button subscribes to deadline reminders
for that programme.

## Source tracking

https://t.me/<bot>?start=ig
https://t.me/<bot>?start=yt
https://t.me/<bot>?start=tg
https://t.me/<bot>?start=vk
https://t.me/<bot>?start=tiktok

Referral links use the numeric user id: https://t.me/<bot>?start=<user_id>

## Deploy (Ubuntu)

sudo cp copernicus-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now copernicus-bot
sudo journalctl -u copernicus-bot -f
