<h1 style="text-align: center; background-color: white;"> Tehillah </h1>

Tehillah is prayer force bot interactive bot, that helps to make lots of prayer force operations more effective and efficient, through making manual or stressful operation more automated.

Operations we want it to do:
- Disseminate information to members DMs - Must only be done by Admins delegated to Iyanu 
- Educate members on the history of prayer force, not in one go but in sections. Delegated  to Solution
- Make payments, via bachs for conferences or any where, it will be integrated via the telegramm bot. Delegated to Boluwatife
- Used to administer quizzes to be done, and rank the winners via two members which includes highest grades and fastest time to finish the tool. delegated to by Iyanu
- Also it should help to filter out the most recent information for members
- Give them pre-services time, post-service time, what was discussed Delgated to Olaoluwa
- Use it to send birthday messages also. Delegated to Honeybell
- Also very important, varieties of LOVE LETTERS. Delegated 


## Project structure

Run the bot from the `bot/` folder with `python main.py`.

```
bot/
├── main.py            Starts the bot
├── messages.py        All text the bot sends to users
├── keyboards.py       The buttons shown under messages
├── notifications.py   Announcing quiz openings and results to everyone
├── config/            Settings (read .env values) and defaults (times, links, quiz rules)
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

## Changing things without touching the code

Two kinds of timing, handled differently on purpose.

**Each quiz carries its own times.** When an admin runs `/generate_quiz`, the bot asks what
kind of quiz it is and when it should open and close. Those times are saved on the quiz itself,
so two quizzes can run completely different windows and nothing is fixed in the code.
A job checks every minute for quizzes due to open or close, which means a restart or a short
outage just gets picked up on the next check.

**Everything else lives in `/settings`.** Admins change meeting times, prices, quiz rules and
the remaining job times from inside Telegram, and the change applies immediately. The message
text is built from the same stored value as the schedule, so what members are told can't drift
away from what the bot actually does.

### Admin commands

| Command | What it does |
| --- | --- |
| `/generate_quiz` | Send meeting notes (text or PDF), the AI writes questions, then you pick the type and the open/close times |
| `/quizzes` | What's open, what's scheduled, and what recently closed |
| `/end_quiz` | Close an open quiz straight away and send out the results |
| `/broadcastmessage` | Send any message to every member |
| `/settings` | Change meeting times, prices, quiz rules and job times |
| `/admins` | See who has admin access and how long temporary access has left |
| `/make_admin` | Give a member admin access for a set time |
| `/revoke_admin` | End someone's temporary access now |

Admins see these in their Telegram command menu; members don't. Hiding a command isn't
protection though — every admin command also checks who sent it, in `utils/auth.py`.

## Admins

There are two kinds.

**Permanent admins** are Telegram user IDs in `ADMIN_IDS` in `.env`, comma separated.
They never expire, and only they can give or take away access. The **first** ID in the
list is the primary admin, and is the only one who can run `/generate_quiz`.

**Temporary admins** are members given access for a set time with `/make_admin` — pick
them by name or Telegram ID, then choose 30 minutes, 2 hours, 6 hours, 24 hours, or type
your own length like `90m` or `3d`. Useful when you're away and someone needs to broadcast
or close a quiz.

Temporary access:

- stops by itself when the time is up, with nothing to remember
- survives a restart, because the grants are stored in the database
- can be ended early with `/revoke_admin`
- **cannot** be used to give anyone else access, or to extend their own time
- adds the admin commands to their menu while it lasts, and removes them afterwards

The member is told when their access starts and when it ends. Every grant records who
gave it and who ended it.
