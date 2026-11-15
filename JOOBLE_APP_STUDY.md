# Jooble's app pages and reviews (read 15 Nov 2026)

The owner sent the Google Play and App Store pages of the Jooble app: "study the description and the reviews, maybe something is
wrong on our site; they add 300,000 jobs every day, how, we need the same".

Sources: play.google.com/store/apps/details?id=jooble.org (US, English) and apps.apple.com/us/app/jooble-easy-job-search-app/id1605813568,
both read on 15 Nov 2026 in the built-in browser.

## What the pages say

- Google Play: 3.8 stars from 47.7K reviews, 5M+ downloads, updated 4 Nov 2026. App Store: 4.7 from 566 ratings, version 1.48.0.
- Same description on both. Their own words:
  - "pulls listings from many job sites into one search"; "listings from job boards and classifieds";
  - "Every day, 300,000 new jobs are added to Jooble, more than 3 every second"; "available in 66 countries"; "20 years";
  - "we review postings and work to filter out spam, phishing, and inappropriate listings";
  - features: search by title and place, filters (salary, distance, employment type), recent and popular searches, saved searches with
    push alerts, saved jobs with a reminder "before a good opening is gone", full description in the app, similar jobs under each listing;
  - "Jooble is a job search engine ... apply on the employer's or job site's page where it was posted";
  - audience: first job, teens, students, part-time, weekend shifts, warehouse, delivery, driver, retail, customer service, healthcare,
    office and tech; an in-app event "Peak Season: Warehouse Jobs".
- App Store privacy label: identifiers used to track across other companies' apps; contact info and browsing history linked to the user.

## Where the 300,000 a day come from

From their own description: job boards and classifieds in 66 countries, in each country's language, every kind of work (most of the
volume is shift work: warehouse, delivery, retail, care). A listing that is on five boards can count up to five times, and a job that is
reposted counts again. We count something stricter: unique jobs read from employers' own careers pages. The live site on 15 Nov:
130,719 open, about 1,500 new a day (4,598 posted in the last 3 days on /new/).

The gap is about 200 times. The ways to close it, best first:
1. **More employers' careers pages** (the sources cloud session, under way): 20,000+ companies, and the big hiring systems of large
   employers with shift work (Workday, SuccessFactors, iCIMS, Taleo, SmartRecruiters). One retailer or logistics company has thousands
   of open roles and posts hundreds a day.
2. **Public job APIs of governments**, in English first: USAJOBS (US federal; needs an API key, so an account by the owner), Canada's
   Job Bank (open data). Others are in the local language (Germany's Bundesagentur, Sweden's JobTech, Norway's NAV, France Travail): only
   if the owner allows non-English jobs or with an English-only filter.
3. **XML feeds from partners**: the way Jooble, Adzuna and Talent.com receive jobs from job boards, staffing agencies and ATS vendors.
   Needs letters in the owner's name (his approval first) and a feed reader (easy: dedupe.py already merges sources).
4. Classifieds: not for us. They are where the spam and phishing the reviews complain about come from.

## What the reviews complain about, and what we do

| Complaint (reviews) | Our site |
|---|---|
| The app's language is locked to the country of the search ("looking in Denmark, everything is in Danish") | One English site, any country by filter. Keep it that way. |
| "Redirects to Lensa", "to other sites that gather data and put you on mailing lists" | Every job links to the employer's own page; the job page names the address it opens ("Opens boards.greenhouse.io"). Say it louder on the home and alert pages. |
| "The jobs ... were no longer available" | Every page re-read hourly; closed jobs are marked; the home page explains ghost jobs. |
| "Telemarketing calls and emails", "selling data" | No account needed, nothing sold. Say on the alert sign-up: "we never share or sell your email". |
| "Many not in the area you select", "irrelevant results" | Places are matched to the posting's own location line; still open: "only my country" and "my city" in the search (ROADMAP 116). |
| "A thousand applications, one call" | Not something a board fixes; our resume match and "how long jobs stay open" data help apply where it counts. |

## What they have that we do not (yet)

- A phone app with push alerts. Cheapest path: make the site installable (a PWA) with web push; Google Play accepts a PWA wrapped as
  a Trusted Web Activity. The owner decides; no account is opened without him.
- Saved jobs with a reminder before the job closes: we have My jobs (saved in the browser) and the "chance it is still open next week";
  a reminder needs the alerts service (accounts-alerts cloud session).
- Shift-work audience pages (warehouse, delivery, retail, seasonal "peak season"): only once those jobs are collected (point 1 above).
