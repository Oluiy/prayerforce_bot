<h1 style="text-align: center; background-color: white;"> Tehillah </h1>

Tehillah is prayer force bot interactive bot, that helps to make lots of prayer force operations more effective and efficient, through making manual or stressful operation more automated.

Operations we want it to do:
- Disseminate information to members DMs - Must only be done by Admins
- Educate members on the history of prayer force, not in one go but in sections.
- Make payments, via bachs for conferences or any where, it will be integrated via the telegramm bot.
- Used to administer quizzes to be done, and rank the winners via two members which includes highest grades and fastest time to finish the tool.
- Also it should help to filter out the most recent information for members
- Give them pre-services time, post-service time, what was discussed - even as voiec note
- Use it to send birthday messages also.
- Also very important, varieties of LOVE LETTERS.


## Project structure

Run the bot from the `bot/` folder with `python main.py`.

```
bot/
├── main.py            Starts the bot
├── messages.py        All text the bot sends to users
├── config/            Settings (read .env values) and fixed values (times, links, quiz rules)
├── handlers/          What happens when a user sends a command
├── jobs/              Tasks that run on a schedule (quizzes, birthdays)
├── services/          The actual logic (quizzes, broadcasts, Gemini AI, PDFs, Google Sheets)
├── repositories/      Every database query
├── database/          Database schema and connection
├── utils/             Small helpers
└── scripts/           One-off tasks, e.g. python -m scripts.sync_users
```

How a request flows: a **handler** or **job** receives it, asks a **service** to do the work,
the service uses **repositories** to read or write the database, and the reply text comes from **messages.py**.

Only `config/settings.py` reads the `.env` file.
