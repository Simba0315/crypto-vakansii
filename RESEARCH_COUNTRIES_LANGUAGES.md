# How large job sites split countries and languages (checked 15 Nov 2026, from the sites themselves)

Read without logging in; 11 sites blocked our reader (403, Cloudflare, captcha) and are marked "could not verify".

| Site | Country split | Interface languages | Job posts / size | Source |
|---|---|---|---|---|
| Indeed | a subdomain per country (62 listed); a second language by `?hl=` | local; Canada en/fr, Switzerland de/fr/it/en, Belgium nl/fr/de/en, Ukraine uk/ru | ru.indeed.com 403 "Blocked"; Indeed "took down its Russian site" (Mar 2022) | indeed.com/worldwide; hreflang on ca.indeed.com; indeed.com/news/releases/indeeds-response-to-the-war-in-ukraine |
| SimplyHired (Indeed) | country domain, 23 countries | local (simplyhired.de German) | – | simplyhired.com, simplyhired.de |
| Glassdoor | country domain; bilingual countries by language subdomain (fr.glassdoor.ca, nl./fr.glassdoor.be) | 23 locales, no Russian | local | hreflang on glassdoor.de |
| LinkedIn | one domain (de.linkedin.com/jobs → www) | 35 incl. Russian | posts as written (German and English posts under a Russian interface); no language filter logged out | linkedin.com/help/linkedin/answer/a521833 |
| XING | one domain | German, English | "1 Mio. Jobs" | xing.com/language |
| ZipRecruiter | country domain (.com → .ie from abroad) | local (.de German) | – | ziprecruiter.de |
| Talent.com | 78 country subdomains + language subfolders (ca.talent.com/fr, ua.talent.com/ru) | local; Kazakhstan defaults to Russian | ru.talent.com closure notice | hreflang on vn.talent.com |
| Jooble | 66 countries, a subdomain each (ua.jooble.org, kz.jooble.org) | one language per country (kz Russian, ua Ukrainian) | ru.jooble.org "ceased operations in Russia" | jooble.org |
| Careerjet | 128 country domains incl. .ru .kz .by | could not verify | – | careerjet.com/sites |
| Jora (SEEK) | country subdomain | English (AU) | au.jora.com 344,368 jobs | au.jora.com |
| hh | country domains: hh.ru, hh.kz, hh.uz, rabota.by, headhunter.ge, headhunter.kg, hh1.az | hh.ru ru/en/kk/uz/ky; hh.kz kk/ru/en; hh.uz uz/ru/en | – | hreflang and language menus |
| Habr Career | one site | Russian | 1,364 vacancies | career.habr.com/vacancies |
| Hirify | one site, interface language switch on the same URL | Russian, English | filter "Язык вакансии" (Ru/En/Ua); **186,667 of 213,179 jobs a month are in English** | hirify.me |
| Reed | UK only | English | 105,839 jobs | reed.co.uk |
| Naukri | India (Gulf: naukrigulf.com) | English | "5 lakh+" | naukri.com |
| InfoJobs | Spain only | Spanish | – | infojobs.net |
| Welcome to the Jungle | one domain, subfolders /en, /en-GB, /fr | English, French | – | hreflang on /en/jobs |
| We Work Remotely, Remote OK, Wellfound, Himalayas | one site each | English only | Wellfound "130K"; Himalayas 121,077 | homepages |
| Could not verify | Monster, StepStone, Totaljobs, SEEK, Pracuj.pl, work.ua, DOU, Djinni, SuperJob, Adzuna, Jobrapido | | | |

**Where Jooble's jobs come from (its own pages):** it indexes "public resources (company sites, job boards, government websites etc.)",
"more than 15 000 public job sources" (ca.jooble.org/how-jooble-works); employers can send "an XML job feed from your site or ATS"; its
crawler respects robots.txt for JoobleBot (help.jooble.org, article 60000037148).

**The pattern.** Global giants (Indeed, Glassdoor, Talent.com, Jooble, ZipRecruiter, SimplyHired) run an edition per country in its
language; bilingual countries get a second language (parameter, subdomain or subfolder); job posts stay in the language they were
written in. Since 2022 none of them has a Russian site; Russian appears only on their Ukraine and Kazakhstan editions. Russian-language
reach is hh's network (7 countries), Habr Career and Hirify. International remote boards are one English-only site. Hirify is the
hybrid: a Russian interface over mostly English jobs (88%), with a filter by the job's language.
