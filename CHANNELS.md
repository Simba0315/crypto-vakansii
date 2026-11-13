# Channels: where the jobs are posted besides the site

Asked by the owner on 2026-11-13 ("LinkedIn, Telegram, X and where else do we post our vacancies; how do we get more traffic").
The plan and its status are in `ROADMAP.md`, section 42. This file is the how-to.

## What runs by itself already

- Google's job box: every job page carries JobPosting data.
- Bing and Yandex: IndexNow pings after each update.
- Other people's sites: the widget, the live badges, the API and the open data files.
- Other people's channels: `/feeds/` lists an RSS address for every field, kind of work and skill. A channel owner gives the
  address to an RSS bot and each new job is posted with a link back to us.

## The owner's own channels: `post.py`

`post.py` posts the jobs the collector saw for the first time today. It is written and tested (`python3 post.py --test`,
`python3 post.py --dry`) and stays silent until two things exist: a channel in `channels.json` and a secret in the repository
settings. The owner creates accounts and enters secrets himself; nobody else handles his tokens.

Telegram, about ten minutes:
1. In Telegram open @BotFather, send `/newbot`, choose a name. BotFather answers with a token.
2. Create a public channel (for example one for all jobs and one for remote jobs). Add the bot to the channel as an administrator
   with the right to post.
3. On GitHub: repository → Settings → Secrets and variables → Actions → New repository secret. Name `TELEGRAM_BOT_TOKEN`, value: the token.
4. Put the channel into `channels.json`, for example:
   `{"telegram": [{"chat": "@your_channel", "filter": {}, "max_per_run": 10}, {"chat": "@your_remote_channel", "filter": {"remote": true}, "max_per_run": 10}]}`
   Filters: `remote`, `crypto`, `entry` (true), `cat` (a category slug or a list), `title` (a pattern), `min_usd` (a number).
5. The workflow step that runs `post.py` after the deploy and keeps `data/posted.json` on the data branch is added together with
   the hourly schedule.

X: an account at developer.x.com with an app that has read and write access gives four values; they go into the secrets
`X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`, and `"x": {"enabled": true}` in `channels.json`. The free tier
allows about 500 posts a month, so the default is two well-paid jobs per run.

LinkedIn: posting through the API needs an app approved by LinkedIn for a company page, which a new site does not get. The
practical route is a company page and one post a week ("the best paid new jobs this week"); the text and the picture can be
produced by the site for the owner to paste.

Job aggregators (Jooble, Adzuna, Talent.com, Careerjet, Jobrapido, WhatJobs): they take a feed of jobs in XML from job sites and
send visitors back without charge. Each one has a form for publishers; the owner submits it (the texts can be prepared for him).
An XML feed in their format is not built yet.

## What not to do

Posting the same links from many accounts on Reddit or forums, buying links, paying for followers: it gets the domain banned.
