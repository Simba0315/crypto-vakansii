# Changelog

One line per improvement run, newest first: date and time, what changed, why, which pages.

- 2026-11-13 04:40 — Companies directory: every employer row now shows a green "+N" mark (roles it posted in the last 7 days, by the employer's own posting date) next to its open-role count; three sort buttons (Most open roles, Most new this week, A–Z) that work together with the name filter; the lead became a direct answer computed from the data (who has the most open roles, how many employers posted this week and which led). Why: the page was a bare list of 544 names with one number, and "who is actually hiring this week" is the question a job seeker brings to it; the answer sentence is quotable by search and AI answers. Pages: /companies/ (build.py, site.js, style.css: `.up`, `.csort`). Sort buttons are hidden without JavaScript.
- 2026-11-13 01:30 — Salary by level pay ladder (intern, junior, senior, lead and above, no level in title: median, middle half, role count) with a one-sentence direct answer computed from the data (for example, how much more senior roles advertise than junior ones). Why: "what does a senior X make" is the most common salary question and we already hold the data; the sentence is quotable by other sites and AI answers. Pages: new section on /salaries/; on the /salaries/<skill, role or category>/ pages it replaces the plain two-column level table that landed in parallel (levels now in career order, with the middle half). New `.t4` table class keeps four-column tables inside a phone screen.

## Ideas for the owner

- (none yet)
