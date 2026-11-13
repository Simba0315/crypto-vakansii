# Job widgets: who is out there and what we do about it (2026-11-13)

Asked by the owner: "study jobswidget.com and every other job widget, make ours better, rank first".
Source: 30 products opened one by one, first pages of Google and Bing for "job widget for website" and "job board widget".

## What the market looks like

Two kinds of product share the name "job widget":

- **(a) A job board gives publishers a list of its own jobs.** Himalayas (search box inside the widget, FAQ, docs per platform),
  Jobicy (script widget, WordPress plugin with 68 settings, referral parameter, API playground), Careerjet, WhatJobs, Talroo,
  Jooble and Adzuna (publisher programmes that pay per click, behind sign-up). RemoteOK, Remotive, We Work Remotely, Arbeitnow
  and web3.career offer only an API or RSS, no widget.
- **(b) A company shows its own jobs.** Widget builders where jobs are typed in by hand: Elfsight, Common Ninja, Jotform, POWR,
  Poper, SociableKIT, Shareables, Fouita, Webynize, Flowxtra, Jobspage, jobswidget.com (free plan = 1 job, 19–38 EUR once for
  unlimited). And the embeds of hiring systems: Greenhouse, Lever, Ashby, Workable, Recruitee, Teamtailor.

Every result on the first page of Google for the two main phrases is kind (b). The only board that ranks is Himalayas, first for
"remote jobs widget".

## What the ranking pages have that ours did not

1. A keyword in the H1 and 1,000–3,000 words of real copy (ours had about 160 words).
2. FAQ with FAQPage markup; WebApplication markup with a zero-price offer.
3. Numbered install steps and a guide per platform (Elfsight has a separate page per platform, and those rank for
   "webflow job board embed", "job feed widget wordpress").
4. A reference of every option with defaults.
5. A comparison section and an honest "limits" section; a "will Google index embedded jobs?" section.
6. In the widget: a search box, "show more", filters, a job popup.
7. For publishers: click statistics, a referral parameter, revenue share, an email-alert sign-up form.
8. A WordPress plugin (Jobicy's listing on wordpress.org ranks by itself).

## What we built the same day

- `/widgets/` rewritten: H1 "Free job widget for your website", install steps, where to paste on nine platforms, option
  reference, comparison of the three kinds of widget, the Google question answered honestly, limits, eight questions with
  FAQPage and WebApplication markup. Title bug fixed (the word "Site" was cut off).
- **Own-board mode, which nobody on the first page has:** `data-hrn-jobs="greenhouse:acme"` (also `lever:`, `ashby:`) reads the
  company's public board in the visitor's browser. No account, no typing jobs in, always current. Checked 2026-11-13: all three
  feeds answer with `Access-Control-Allow-Origin: *` (Greenhouse 43 KB gzipped for Stripe; Lever 815 KB for Spotify; Ashby
  1.5 MB compressed for OpenAI, so very large boards load slowly).
- `data-search="1"`: search box, team filter and "show more" in any layout.
- The widget was restyled to the site's new look.

## Still open (in order of value)

1. A page per platform: `/widgets/wordpress/`, `/widgets/webflow/`, `/widgets/wix/`, `/widgets/squarespace/`,
   `/widgets/shopify/`, `/widgets/framer/`, `/widgets/notion/`, each with its own steps and screenshots of the result.
2. Pages for the neighbouring searches: "remote jobs widget", "careers page widget", "embed job listings on website",
   "greenhouse job board embed", "lever jobs embed", "hiring badge".
3. A WordPress plugin (shortcode and block) published on wordpress.org: needs the owner's wordpress.org account.
4. More hiring systems in own-board mode where the public feed allows cross-origin reads (Workable, Recruitee, SmartRecruiters,
   Teamtailor: check each first).
5. Job popup inside the widget; carousel layout; custom CSS hook.
6. Click statistics and an email-alert form: need the server.
7. Revenue share for publishers: needs payments and real traffic first.

## Search phrases collected

job widget · jobs widget · job widget for website (free) · job board widget (free) · job search widget · embeddable job widget ·
embed job listings on website · embed jobs · careers page widget free · indeed job widget · linkedin jobs widget · google jobs
widget · workable widget · teamtailor jobs widget · greenhouse embed job board · ashbyhq job board · remote jobs widget ·
job feed widget wordpress free · job listing plugin wordpress · webflow job board · wix job board plugin · squarespace job board
plugin · framer job board · notion job board template · job api free · job board api free · jobs rss feed · hiring badge
