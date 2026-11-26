"""Facts for the comparison pages "Jobs Every Hour vs <job site>" (one page per site in SITES).

The page generator reads this module. Nothing here is written as page copy except the strings themselves; the layout is up to the
generator.

Rules the data follows:
- Every claim about another site comes from a source in that site's "sources" list. A fact that no source gave is left out,
  so some sites have fewer rows than others.
- Facts dated 2026-11-13 were read by the earlier research on that day (PRICING_RESEARCH.md, COMPANIES_RESEARCH.md,
  AGGREGATORS_RESEARCH.md, SOURCES_RESEARCH.md; the comment next to each source names the section). The URL is the site's own page
  that the research opened. Facts dated 2026-11-14 were read from the site's own page on that day.
- Pages that blocked the reader (403, bot check) or did not answer were not worked around. See NOT_SOURCED.
- Facts about our own site come only from US / US_ANSWERS.

Fields of each site:
  slug, name, url (home page), what (one neutral sentence),
  rows: list of (question, them, us), questions in QUESTIONS order, rows without a sourced fact left out,
  them_better / us_better: 2-3 short points each,
  pick: one sentence "Use X if ..., use Jobs Every Hour if ...",
  sources: list of (fact, url, date read).

Each source fact starts with a tag in square brackets that names what it supports, for example
"[Who pays|Price to post one job] ...". Keys are a question from QUESTIONS, "what", "them_better 1".."them_better 3",
"us_better 1".."us_better 3" or "pick". Use source_text() to drop the tag and source_keys() to read it.

Run `python3 compare_sites.py` to check the data.
"""

import re

OUR_NAME = "Jobs Every Hour"

R13 = "2026-11-13"  # read by the research files
R14 = "2026-11-14"  # read from the site's own page for this module
R21 = "2026-11-21"  # read from the site's own page in a real browser (FlexJobs timed out for the reader on 14 Nov)
R24 = "2026-11-24"  # the 16 sites added that day, read on their own pages (some in a real browser) or, for ZipRecruiter, its annual report
R25 = "2026-11-25"  # the 9 sites AI answers name that had no page (Google for Jobs, Ladders, Craigslist, Levels.fyi, GovernmentJobs.com,
                    # HiringCafe, Drivetube, Jobright, Jobscan), read in a real browser on their own pages and help centres

QUESTIONS = [
    "Who pays",
    "Price for job seekers",
    "Price to post one job",
    "Where the jobs come from",
    "Where you apply",
    "Account needed to apply",
    "How fresh the listings are",
    "Kinds of jobs",
    "Payment methods",
]

# Facts about our site, as given by the owner. Use only these.
US = {
    "name": OUR_NAME,
    "open_jobs": 41187,
    "companies": 732,
    "source": "the employers' own careers pages, read from eight hiring systems (Greenhouse, Lever, Ashby, Workday, Workable, Personio, Recruitee and Teamtailor)",
    "refresh": "around the clock",
    "apply": "on the employer's own page",
    "account_needed_to_search": False,
    "account_needed_to_apply": False,
    "price_for_job_seekers": "free",
    "plus_plan": {
        "prices_usd": {"7 days": 9, "30 days": 19, "90 days": 39},
        "one_payment": True,
        "renews": False,
        "on_sale": False,
    },
    "employer_listings": {
        "standard": "free for 30 days",
        "standard_boost": "$99 for 30 days",
        "premium_boost": "$249 for 30 days",
        "self_serve_open": True,                 # a standard listing is posted in the employer account; paid boosts wait for payments
    },
    "payments": "crypto",
    "free_tools": ["resume builder", "resume match checker", "salary data from posted ranges", "jobs map"],
    "launched": "November 2026",
    "languages": ["English"],
}

US_ANSWERS = {
    "Who pays": "Job seekers use it free. Paid options: an optional Plus plan for job seekers (not on sale yet) and boosts for "
                "employers' listings (posting is open and free; paid boosts open when payments are switched on).",
    "Price for job seekers": "Free. Optional Plus plan: $9 for 7 days, $19 for 30 days, $39 for 90 days. One payment, "
                             "nothing renews. Not on sale yet.",
    "Price to post one job": "Standard listing free for 30 days, posted in the employer account. Standard boost $99 and "
                             "Premium boost $249, each for 30 days; boosts open when payments are switched on.",
    "Where the jobs come from": "The employers' own careers pages, read from eight hiring systems (Greenhouse, Lever, Ashby, Workday, Workable, "
                                "Personio, Recruitee and Teamtailor).",
    "Where you apply": "On the employer's own page.",
    "Account needed to apply": "No. You can search and apply without an account.",
    "How fresh the listings are": "Every job is read again from the employer's careers page around the clock.",
    "Kinds of jobs": "The jobs that 732 companies post on their own careers pages (41,187 open jobs). English only.",
    "Payment methods": "Crypto.",
}


def refresh_us(jobs, companies, systems):
    """Our own figures from the build that makes the pages: open jobs, companies, and the hiring systems with open jobs, largest
    first. Without it the pages kept the counts of 13 Nov 2026 (eight systems, 41,187 jobs) beside a button with today's count."""
    names = ", ".join(systems[:4]) + (" and others" if len(systems) > 4 else "")
    US.update(open_jobs=jobs, companies=companies,
              source=f"the employers' own careers pages, read from {len(systems)} hiring systems ({names})")
    US_ANSWERS["Where the jobs come from"] = f"The employers' own careers pages, read from {len(systems)} hiring systems ({names})."
    US_ANSWERS["Kinds of jobs"] = f"The jobs that {companies:,} companies post on their own careers pages ({jobs:,} open jobs). English only."
    for s in SITES:
        s["rows"] = [(q, them, US_ANSWERS[q]) for q, them, _ in s["rows"]]


def _rows(*pairs):
    """Build (question, them, us) rows; the us side always comes from US_ANSWERS."""
    return [(q, them, US_ANSWERS[q]) for q, them in pairs]


SITES = [
    # ------------------------------------------------------------------ Indeed
    dict(
        slug="indeed",
        name="Indeed",
        url="https://www.indeed.com/",
        what="Indeed is a general job site that calls itself the world's #1 job site. Employers post jobs there, many for free, "
             "and can pay to sponsor them.",
        rows=_rows(
            ("Who pays", "Employers, for sponsored posts. A basic post is free for many jobs. Job seekers can buy a plan "
                         "called Indeed Pro through Apple."),
            ("Price to post one job", "A basic post is free for many jobs. The paid levels (Standard, Premium, Premium Plus) "
                                      "show no fixed price. Indeed recommends a budget and bills for clicks or started "
                                      "applications."),
            ("Where the jobs come from", "Employers post on Indeed, or send a feed with all jobs from their career site. "
                                         "Indeed says aggregators are not allowed."),
            ("Where you apply", "Some jobs let you apply on Indeed. Others send you to the employer's website."),
            ("Account needed to apply", "Indeed's help page lists \"Create an account or sign in\" as the first step."),
            ("How fresh the listings are", "Feeds from career sites are read again every 6 hours. Files uploaded to Indeed "
                                           "are read on upload, at most every 2 hours."),
            ("Payment methods", "Employers: a card or bank account on file (US bank debit), invoices by email. Indeed Pro "
                                "is paid through Apple."),
        ),
        them_better=[
            "Far larger. Indeed calls itself the world's #1 job site (Comscore, total visits, March 2026) and reports 685M "
            "job seeker profiles.",
            "Many more employer tools: Indeed Apply, candidate tracking, screener questions, video interviews and a resume "
            "database.",
            "Employers can post today, and a basic post is free for many jobs. Our free posting is open; our paid boosts are not on sale yet.",
        ],
        us_better=[
            "We read every job again from the employer's careers page around the clock. Indeed reads career-site feeds every 6 hours.",
            "Every job sends you to apply on the employer's own page. On Indeed, some jobs take the application on Indeed.",
            "Our employer prices are public: Standard boost $99 and Premium boost $249, each for 30 days. Indeed shows no fixed price for "
            "its paid levels.",
        ],
        pick="Use Indeed if you want the largest general job site and employer tools like Indeed Apply, use Jobs Every Hour "
             "if you want jobs checked around the clock on employers' own careers pages and to apply there directly.",
        sources=[
            ("[what|them_better 1|pick] Calls itself \"the world's #1 job site\" (Comscore, Total Visits, March 2026) and "
             "reports \"685M Job Seeker Profiles\".",
             "https://www.indeed.com/about", R14),
            # PRICING_RESEARCH.md B.1
            ("[what|Who pays|Price to post one job|them_better 3|us_better 3] The employer pays; a basic post is free for "
             "many jobs. Four levels (Free, Standard, Premium, Premium Plus) with no prices: \"Indeed provides a recommended "
             "budget\". Billed for clicks or started applications.",
             "https://www.indeed.com/hire/cs/pricing", R13),
            # COMPANIES_RESEARCH.md C.1
            ("[Who pays|Payment methods] Employers pay by credit card or bank account on file (US bank debit, ACH); invoices "
             "by email. The job-seeker plan Indeed Pro is paid through Apple.",
             "https://www.indeed.com/legal", R13),
            # AGGREGATORS_RESEARCH.md 2.2
            ("[Where the jobs come from|How fresh the listings are|us_better 1] Employers can send an XML feed that must "
             "contain all jobs of the career site. A crawled feed URL or client FTP is refreshed every six hours; "
             "Indeed-hosted FTP on upload, at most every two hours.",
             "https://docs.indeed.com/job-sync-xml/xml-feed", R13),
            # AGGREGATORS_RESEARCH.md 1B
            ("[Where the jobs come from] \"Aggregators are not allowed on Indeed.\"",
             "https://uk.indeed.com/help/employers/articles/360018069792", R13),
            ("[Where you apply|Account needed to apply|us_better 2] \"Some jobs let you apply directly on Indeed. Others "
             "take you to the employer's website.\" The first step under \"Searching for jobs\" is \"Create an account or "
             "sign in\".",
             "https://www.indeed.com/help/job-seekers/articles/204652920-applying-for-a-job-on-indeed", R14),
            # SOURCES_RESEARCH.md section 5
            ("[them_better 2|pick] Indeed for employers offers Indeed Apply, candidate tracking, screener questions, video "
             "interviews and a resume database.",
             "https://www.indeed.com/hire", R13),
        ],
    ),
    # ------------------------------------------------------------------ LinkedIn Jobs
    dict(
        slug="linkedin-jobs",
        name="LinkedIn Jobs",
        url="https://www.linkedin.com/jobs/",
        what="LinkedIn Jobs is the job section of LinkedIn, a professional network with 1.4B+ members. Employers pay to post "
             "or promote jobs there.",
        rows=_rows(
            ("Who pays", "Employers pay for job posts (Hiring Pro, Job Slots). Job seekers can buy Premium Career."),
            ("Price for job seekers", "The public page shows no price for Premium Career. The price appears after sign-in. "
                                      "Eligible members can try Premium for free."),
            ("Price to post one job", "No public price. LinkedIn says prices vary with your hiring needs."),
            ("Where the jobs come from", "Employers post on LinkedIn. Partner feeds may only carry jobs that employers "
                                         "posted directly with the partner. Jobs gathered from other job boards are not "
                                         "allowed."),
            ("Where you apply", "Easy Apply lets you apply without leaving LinkedIn. Jobs from partner feeds link straight "
                                "to the source to apply."),
            ("How fresh the listings are", "Partner feeds are read every 6 hours from hiring systems and every 24 hours "
                                           "from job boards."),
            ("Payment methods", "Cards (Visa, Mastercard, American Express, Discover, JCB, Diners Club, RuPay, prepaid), "
                                "PayPal, Apple Pay and Google Pay for Premium, UPI in India, SEPA debit, iDEAL and Sofort "
                                "in parts of Europe."),
        ),
        them_better=[
            "A huge network: 1.4B+ members and 71M companies, with about 9K job applications sent every minute.",
            "More tools: Hiring Pro and Job Slots for employers, and Premium Career for job seekers.",
            "Many more ways to pay, including cards, PayPal, Apple Pay, Google Pay and local bank methods.",
        ],
        us_better=[
            "We read every job again from the employer's careers page around the clock. LinkedIn reads partner feeds every 6 to 24 "
            "hours.",
            "Our prices are on the page: Plus from $9 (not on sale yet), Standard boost $99, Premium boost $249. LinkedIn shows "
            "Premium prices only after sign-in and publishes no job post prices.",
            "Every job sends you to apply on the employer's own page. Easy Apply keeps the application on LinkedIn.",
        ],
        pick="Use LinkedIn Jobs if you want the biggest professional network and Easy Apply, use Jobs Every Hour if you want "
             "jobs checked around the clock on employers' careers pages and to apply on the employer's own page.",
        sources=[
            ("[what|them_better 1|pick] \"+1.4B Members\", \"71M Companies\"; \"~9K\" job applications are submitted every "
             "minute.",
             "https://news.linkedin.com/about-us", R14),
            # PRICING_RESEARCH.md B.2
            ("[what|Who pays|Price to post one job|Where the jobs come from|them_better 2|us_better 2] Employers pay. "
             "\"Pricing for our job posting tools vary depending on your hiring needs.\" Two products: Hiring Pro and Job "
             "Slots. Button \"Post a job\".",
             "https://business.linkedin.com/hire/post-jobs", R13),
            # PRICING_RESEARCH.md A.2
            ("[Who pays|Price for job seekers|them_better 2|us_better 2] Premium Career is paid by the job seeker. The "
             "public page shows no price; the price appears only after sign-in. \"Eligible LinkedIn members can try "
             "LinkedIn Premium for free.\"",
             "https://premium.linkedin.com/", R13),
            # AGGREGATORS_RESEARCH.md 1B
            ("[Where the jobs come from|Where you apply] Partner feeds must not contain jobs aggregated from other job "
             "boards; only jobs posted directly by employers on the partner's platform. Apply must go straight to the "
             "source without redirects.",
             "https://learn.microsoft.com/en-us/linkedin/talent/job-postings/xml-feeds-job-posting-guidelines", R13),
            ("[Where you apply|us_better 3|pick] Easy Apply \"lets you submit your application without leaving "
             "LinkedIn.com.\"",
             "https://www.linkedin.com/help/linkedin/answer/a512348", R14),
            # AGGREGATORS_RESEARCH.md 2.7
            ("[How fresh the listings are|us_better 1] Feeds are scraped every 6 hours for ATS partners and every 24 hours "
             "for job board partners.",
             "https://learn.microsoft.com/en-us/linkedin/talent/job-postings/xml-feeds-development-guide", R13),
            # COMPANIES_RESEARCH.md C.4
            ("[Payment methods|them_better 3] Cards: American Express, Discover, Mastercard, Visa, RuPay, JCB, Diners Club "
             "(US dollars only), prepaid cards. PayPal for Premium and job posts on desktop. Apple Pay and Google Pay for "
             "Premium. UPI in India. SEPA direct debit, iDEAL, Sofort in parts of Europe.",
             "https://www.linkedin.com/help/billing/answer/74", R13),
        ],
    ),
    # ------------------------------------------------------------------ Wellfound
    dict(
        slug="wellfound",
        name="Wellfound",
        url="https://wellfound.com/",
        what="Wellfound is a job site for startups. Companies post jobs for free, and candidates apply with a Wellfound "
             "profile.",
        rows=_rows(
            ("Who pays", "Employers, for paid extras. Job posts are free. Job seekers never pay."),
            ("Price for job seekers", "Free. Wellfound says job seekers will never pay any fees."),
            ("Price to post one job", "Job posts are free \"forever\". Promoted Job Ads start at $200 per ad."),
            ("Where the jobs come from", "Startups post jobs on Wellfound themselves. It says 27,000+ startups hire there."),
            ("Where you apply", "On Wellfound. You press Apply, add a note and send. The company sees your Wellfound "
                                "profile and resume."),
            ("Account needed to apply", "Yes. The help page says to sign in and keep your profile up to date before you "
                                        "apply."),
            ("Kinds of jobs", "Startup jobs, mostly full-time: software engineering, data science, design, engineering "
                              "management, sales and product."),
            ("Payment methods", "Employers pay by credit card. Invoices can be downloaded."),
        ),
        them_better=[
            "A large startup audience: 27,000+ startups hire there, and 10M+ candidates have opted in to hear from startups.",
            "Employer tools beyond job posts: Reach for sourcing (from $135 per seat a month) and Autopilot, a recruiting "
            "service ($500 a month per role plus a 10% fee on a hire).",
            "Paid hiring tools are on sale today; our paid boosts are not on sale yet. Free posting is open on both.",
        ],
        us_better=[
            "No account needed to search or apply. Wellfound asks you to sign in with a profile before you apply.",
            "You apply on the employer's own page. On Wellfound the application is sent inside Wellfound.",
        ],
        pick="Use Wellfound if you want to reach many startups with one profile, use Jobs Every Hour if you want to search "
             "and apply on employers' own pages without an account.",
        sources=[
            ("[what|Where the jobs come from|them_better 1|pick] \"27,000+ startups hire on Wellfound\"; \"exclusive pool of "
             "10M+ candidates who opted in to hear from startups\"; \"Creating a profile and applying to jobs on Wellfound is "
             "always free for candidates.\"",
             "https://wellfound.com/", R14),
            # PRICING_RESEARCH.md B.8
            ("[what|Who pays|Price to post one job|Where the jobs come from|them_better 2|them_better 3] Employer pays; Job "
             "Posts $0 \"forever\"; Job Ads \"From $200 / ad\"; Reach Starter $135 per seat a month; Autopilot $500 a month "
             "per open role \"+ 10% placement fee on a successful hire\".",
             "https://wellfound.com/recruit/pricing", R13),
            ("[Who pays|Price for job seekers] \"Our platform is complimentary for job-seekers to use. You will never have "
             "any fees as a job seeker using Wellfound.\"",
             "https://help.wellfound.com/article/799-does-angellist-cost-anything-for-job-seekers", R14),
            ("[what|Where you apply|Account needed to apply|us_better 1|us_better 2|pick] Steps before applying: \"Sign in "
             "to your account\" and \"Make sure your profile is up to date\". You press \"Apply\", add a note and press "
             "\"Send Application\"; this lets the company see your job profile and resume.",
             "https://help.wellfound.com/article/769-how-do-i-apply-to-a-job", R14),
            ("[Kinds of jobs] Wellfound \"works with well-funded start-ups\" that hire \"full-time software engineering, "
             "data science, design, engineering management, sales, and product management\" roles.",
             "https://help.wellfound.com/article/802-companies-on-angellist", R14),
            # COMPANIES_RESEARCH.md C.15
            ("[Payment methods] Credit card (help articles on adding and removing a card). Invoices can be downloaded.",
             "https://help.wellfound.com/category/432-billing", R13),
        ],
    ),
    # ------------------------------------------------------------------ We Work Remotely
    dict(
        slug="we-work-remotely",
        name="We Work Remotely",
        url="https://weworkremotely.com/",
        what="We Work Remotely is a remote job board where employers pay to post listings.",
        rows=_rows(
            ("Who pays", "Employers pay for each listing."),
            ("Price to post one job", "$299 for a 30-day listing. Upgrades: +$109 (\"4x visibility\") or +$159 "
                                      "(\"5x visibility\"). Bundles from $179 a job."),
            ("Where the jobs come from", "Employers buy listings on its own posting page."),
            ("How fresh the listings are", "Each listing is bought for 30 days."),
            ("Kinds of jobs", "Remote jobs."),
            ("Payment methods", "Stripe Checkout, where the buyer picks the method. The invoice comes by email."),
        ),
        them_better=[
            "More ways for employers to stand out: two paid upgrades, and Premium Placement for hiring at scale (from "
            "$1,999).",
            "Bundles for employers who hire often: from $179 a job, up to 40% off, used within 12 months.",
            "Employers can buy and post today. Our free posting is open; our paid boosts are not on sale yet.",
        ],
        us_better=[
            "A standard listing is free for 30 days, posted in the employer account. On We Work Remotely the base "
            "listing is $299 for 30 days.",
            "We read every job again from the employer's careers page around the clock. A We Work Remotely listing is bought for "
            "a fixed 30 days.",
        ],
        pick="Use We Work Remotely if you want a board of remote listings that employers pay to post, use Jobs Every Hour if "
             "you want jobs read around the clock from employers' own careers pages.",
        sources=[
            # PRICING_RESEARCH.md B.9
            ("[what|Who pays|Price to post one job|How fresh the listings are|them_better 1|us_better 1|us_better 2|pick] "
             "\"The base price for a job listing on We Work Remotely is $299 per 30-day listing.\" Upgrades: Better +$109 "
             "(\"4x visibility\"), Best +$159 (\"5x visibility\"). Premium Placement \"from $1,999\".",
             "https://weworkremotely.com/remote-jobs/find-your-plan", R13),
            # PRICING_RESEARCH.md B.9
            ("[Price to post one job|them_better 2] Bundles \"from $179/job\", \"save up to 40%\", to be used within 12 "
             "months.",
             "https://weworkremotely.com/bundles", R13),
            # PRICING_RESEARCH.md B.9
            ("[what|Where the jobs come from|Kinds of jobs|Payment methods|them_better 3|pick] The page to post a remote "
             "job ends at \"Continue to Stripe Checkout - You'll choose your payment method and see the final total on "
             "Stripe.\" The invoice comes by email.",
             "https://weworkremotely.com/post-a-remote-job", R13),
        ],
    ),
    # ------------------------------------------------------------------ Remote OK
    dict(
        slug="remote-ok",
        name="Remote OK",
        url="https://remoteok.com/",
        what="Remote OK is a remote job board where employers pay to post jobs and job seekers can buy a Premium plan.",
        rows=_rows(
            ("Who pays", "Employers pay to post. Job seekers can buy Remote OK Premium."),
            ("Price for job seekers", "Remote OK Premium: $14.95 a month with a 12-month commitment, billed monthly. No "
                                      "free trial. A $29.95 a month bundle adds other job sites."),
            ("Price to post one job", "From $299 for 30 days. The button shows $447 when the page loads, with some add-ons "
                                      "ticked."),
            ("Where the jobs come from", "Employers can post through a paid form on the site."),
            ("Where you apply", "The Apply button opens the apply link the employer gives, or an email address if there is "
                                "no link."),
            ("How fresh the listings are", "Posts run 30 days, then renew automatically unless the employer turns renewal "
                                           "off."),
            ("Kinds of jobs", "Remote jobs in programming, design, sales and more."),
            ("Payment methods", "Card through Stripe. A \"Pay later\" option sends a payment link by email."),
        ),
        them_better=[
            "Large: it lists 100,000+ remote jobs from 10,000+ companies and says it reaches 20,100,000+ remote "
            "workers a month.",
            "Wide reach for employers: posts are emailed to 2,692,454 remote job seekers and crossposted to 261 job boards.",
            "It has a public jobs API, and employers can post today. Our free posting is open; our paid boosts are not on sale yet.",
        ],
        us_better=[
            "No commitment: Plus is one payment that never renews, from $9 for 7 days (not on sale yet). Remote OK Premium "
            "is $14.95 a month with a 12-month commitment.",
            "Salary data from posted ranges is a free tool here. Remote OK lists salary data among its paid Premium "
            "features.",
            "A standard listing is free for 30 days, posted in the employer account. Remote OK starts at $299 for 30 "
            "days and renews unless turned off.",
        ],
        pick="Use Remote OK if you want a large remote-only board with wide reach for employers, use Jobs Every Hour if you "
             "want free salary data and no subscription.",
        sources=[
            ("[what|Who pays|Kinds of jobs|them_better 1|pick] \"100,000+ remote jobs\" \"from 10,000+ top companies\"; "
             "\"Remote Jobs in Programming, Design, Sales and more\"; \"Unlock your remote career potential with Remote OK "
             "Premium.\"",
             "https://remoteok.com/", R14),
            ("[what|Price for job seekers|us_better 1|us_better 2|pick] Premium plan \"$14.95\" a month, \"12-month "
             "commitment · billed monthly\"; \"No free trial.\" TopAccess Bundle \"$29.95\" a month with other job sites. "
             "Features include \"See salary data before you apply\".",
             "https://remoteok.com/premium", R14),
            ("[Who pays|Price to post one job|Where the jobs come from|Where you apply|How fresh the listings are|"
             "them_better 1|them_better 2|them_better 3|us_better 3|pick] \"Starting from $299 for 30 days\"; button "
             "\"Post a job — $447\"; posts renew automatically after 30 days unless auto renew is disabled. The Apply "
             "button uses the Apply URL, or the apply email if no URL is given. \"Reach 20,100,000+ remote workers/mo\"; "
             "emailed to 2,692,454 remote job seekers; crossposted to 261 job boards.",
             "https://remoteok.com/hire-remotely", R14),
            # PRICING_RESEARCH.md B.10, COMPANIES_RESEARCH.md C.13
            ("[Price to post one job|Payment methods] The button total on load is above \"Starting from $299\" because "
             "add-ons are ticked. \"Secure payment with Stripe\". A \"Pay later\" box sends a payment link by email.",
             "https://remoteok.com/hire-remotely", R13),
            # AGGREGATORS_RESEARCH.md 1C
            ("[them_better 3] Remote OK publishes an outbound JSON API of its jobs.",
             "https://remoteok.com/api", R13),
        ],
    ),
    # ------------------------------------------------------------------ FlexJobs
    dict(
        slug="flexjobs",
        name="FlexJobs",
        url="https://www.flexjobs.com/",
        what="FlexJobs is a job search service that job seekers pay for through a membership.",
        rows=_rows(
            ("Who pays", "Job seekers, through a membership."),
            ("Price for job seekers", "$2.95 for 14 days, then $23.95 every 4 weeks. Or $29.85 every 3 months, or $71.40 a "
                                      "year. All plans renew automatically. Full refund on request within 14 days."),
            ("Where the jobs come from", "A FlexJobs research team hand-screens each job and company and lists only jobs that "
                                         "offer some kind of work flexibility."),
            ("Where you apply", "Some jobs let you apply through FlexJobs, others send you to a page on the employer's "
                                "website."),
            ("Account needed to apply", "Yes, and a paid one: a subscription is needed to see employers, read full job "
                                        "details or apply."),
            ("Kinds of jobs", "Remote, hybrid, part-time, freelance and flexible-schedule jobs: 244,908 listings from 16,036 "
                              "companies, by its About page."),
            ("Payment methods", "Credit card and other methods, depending on the buyer's country."),
        ),
        them_better=[
            "A money-back promise: a full refund on request within 14 days of creating the account.",
            "You can buy it and use it today, by card or other local methods. Our Plus plan is not on sale yet.",
            "A person checks every job and company before it is listed, and remote or flexible work is its whole focus.",
        ],
        us_better=[
            "Free for job seekers. FlexJobs charges job seekers, starting at $2.95 for a 14-day trial.",
            "Plus is one payment and never renews: $9 for 7 days, $19 for 30 days, $39 for 90 days (not on sale yet). "
            "FlexJobs plans renew automatically, and the trial renews at $23.95 every 4 weeks.",
            "You see the employer and apply without paying or making an account. FlexJobs needs a paid subscription to see "
            "employers, read full job details or apply.",
        ],
        pick="Use FlexJobs if you are happy to pay for a membership with a 14-day refund window, use Jobs Every Hour if you "
             "want to search and apply for free.",
        sources=[
            # PRICING_RESEARCH.md A.3
            ("[what|Who pays|Price for job seekers|them_better 1|them_better 2|us_better 1|us_better 2|pick] Paid by the "
             "job seeker (\"Become a FlexJobs Member\"). \"$2.95 — 14-DAY FULL ACCESS\", \"After 14 days, auto-renews at "
             "$23.95 billed every 4 weeks.\" 3-month: \"Pay $29.85 up front, auto-renews every 3 months.\" Annual: \"Pay "
             "$71.40 up front, auto-renews every year.\" Full refund on request within 14 days of account creation.",
             "https://www.flexjobs.com/pricing", R13),
            # COMPANIES_RESEARCH.md C.11
            ("[Payment methods|them_better 2] Credit card and other methods \"depending on what country you are located\". "
             "Subscription renews by itself. Sold by BOLD LLC, or Auxiliant S.à.r.l as merchant of record.",
             "https://www.flexjobs.com/termsofuse.aspx", R13),
            ("[Where the jobs come from|Where you apply|Account needed to apply|them_better 3|us_better 3] FAQ: \"you need "
             "to have a paid subscription to FlexJobs to see employers, view full job details, or apply for any job.\" "
             "\"Employers may set up the job post to allow you to apply directly through FlexJobs, or they may require you "
             "to apply directly from a page on their website.\" \"Our amazing job research team hand-screens job and "
             "company information\" ... \"offer at least some kind of work flexibility.\"",
             "https://www.flexjobs.com/faq", R21),
            ("[Kinds of jobs|them_better 3] About: \"244,908 Verified Remote and Flexible Jobs\", \"16,036 Companies "
             "currently hiring\"; \"full-time, part-time, freelance, or flexible schedule opportunities\"; home page tabs "
             "Fully Remote, Entry-Level, Part-Time, Hybrid.",
             "https://www.flexjobs.com/about", R21),
        ],
    ),
    # ------------------------------------------------------------------ CryptoJobsList
    dict(
        slug="cryptojobslist",
        name="CryptoJobsList",
        url="https://cryptojobslist.com/",
        what="CryptoJobsList is a job board run by Ksaitor Media in Singapore, where employers choose their own budget to post "
             "a job.",
        rows=_rows(
            ("Who pays", "Employers. It says it never makes recurring charges."),
            ("Price to post one job", "The employer sets a budget from $150 (it recommends more than $200). A higher budget "
                                      "gives a higher place in the list, unless another employer pays more. Hiding the "
                                      "salary costs $25 more."),
            ("Where the jobs come from", "Employers post through a form on the site."),
            ("How fresh the listings are", "A post is \"Live and Promoted for 30 days\"."),
            ("Payment methods", "Card through Stripe. Crypto (BTC, ETH, USDC, Doge) through NowPayments for selected "
                                "customers only. Bank transfer for orders above $10,000."),
        ),
        them_better=[
            "Running since 2017, and it says it has helped 50k+ people find a job. We launched in November 2026.",
            "A Telegram channel with 62.1K subscribers that posts about 3 jobs a day.",
            "More ways for employers to pay (card, bank transfer, crypto for some customers), and posting is open today. "
            "Our free posting is open; our paid boosts are not on sale yet.",
        ],
        us_better=[
            "A standard listing is free for 30 days, posted in the employer account. On CryptoJobsList the budget "
            "starts at $150 for 30 days.",
            "Fixed prices for a better place: Standard boost $99 and Premium boost $249, each for 30 days. On CryptoJobsList the place "
            "depends on the budget and can change if another employer pays more.",
            "We take payment in crypto. CryptoJobsList offers crypto to selected customers only.",
        ],
        pick="Use CryptoJobsList if you want a long-running board with a large Telegram following, use Jobs Every Hour if you "
             "want jobs read around the clock from employers' careers pages and fixed, low listing prices.",
        sources=[
            # PRICING_RESEARCH.md B.15, COMPANIES_RESEARCH.md C.24
            ("[what|Who pays|Price to post one job|Where the jobs come from|How fresh the listings are|Payment methods|"
             "them_better 3|us_better 1|us_better 2|us_better 3] Paid by the employer through a posting form. Budget slider: "
             "minimum $150, \"We recommend setting the budget above $200\"; \"16th position on the list, unless another "
             "employer outbids you\"; \"Live and Promoted for 30 days\"; hiding the salary +$25. \"We never make recurring "
             "charges.\" \"Credit Card payments. Secured by Stripe.\" \"Crypto payments: BTC, ETH, USDC, Doge. Secured by "
             "NowPayments. Select customers only.\" \"Bank transfers for orders above USD $10k.\" Footer: \"Ksaitor Media\" "
             "(Ksaitor Media Pte. Ltd., Singapore).",
             "https://cryptojobslist.com/hire", R13),
            # COMPANIES_RESEARCH.md A.3
            ("[what|them_better 1|pick] \"Since 2017 the site has been helping 50k+ people find a job.\"",
             "https://cryptojobslist.com/hire", R13),
            # SOURCES_RESEARCH.md section 3
            ("[them_better 2|pick] Telegram channel cryptojobslist: 62.1K subscribers, about 3.0 posts a day, links go to "
             "cryptojobslist.com.",
             "https://t.me/s/cryptojobslist", R13),
        ],
    ),
    # ------------------------------------------------------------------ Web3.career
    dict(
        slug="web3-career",
        name="Web3.career",
        url="https://web3.career/",
        what="Web3.career is a job board for blockchain and web3 jobs, part of the Bondex ecosystem.",
        rows=_rows(
            ("Who pays", "Employers pay to post."),
            ("Price to post one job", "No base price is printed. When the page loads, the button reads $695, with four paid "
                                      "add-ons ticked (premium support, 7 days at the top, logo, colour). Renewal every 30 "
                                      "days is also ticked."),
            ("Where the jobs come from", "Employers can post through a paid form on the site."),
            ("Where you apply", "The employer chooses: a link to its own website, or Web3.career's applicant tracking "
                                "system, powered by Bondex."),
            ("Kinds of jobs", "Blockchain and web3 jobs, with sections for remote and non-tech roles."),
            ("Payment methods", "Card. Invoice details can be added. Crypto is not offered on the posting form."),
        ),
        them_better=[
            "Only blockchain and web3 jobs, in one place: 42,383 jobs at 7,389 web3 projects.",
            "A large crypto audience: its posting page shows 640,903 job post views, 41,000 Twitter followers and 9,000 "
            "Discord members.",
            "Employers get a built-in applicant tracking system (powered by Bondex), and posting is open today. Our "
            "free posting is open; our paid boosts are not on sale yet.",
        ],
        us_better=[
            "We take payment in crypto. Web3.career's posting form does not offer crypto.",
            "A lower price to stand out: Standard boost $99 for 30 days (paid boosts are not on sale yet). "
            "On Web3.career, 7 days at the top is +$149 and 14 days is +$199.",
        ],
        pick="Use Web3.career if you want the widest list of web3 projects and a large crypto audience, use Jobs Every Hour if "
             "you want to pay in crypto and apply on employers' own careers pages.",
        sources=[
            ("[what|Kinds of jobs|them_better 1|pick] \"Browse 42,383 blockchain jobs in web3 at 7,389 projects.\" \"Filter "
             "the best remote crypto jobs by salary, location, and skills.\" Sections \"Remote Web3 Jobs\" and \"Remote "
             "Non-Tech Web3 Jobs\".",
             "https://web3.career/", R14),
            # PRICING_RESEARCH.md B.16, COMPANIES_RESEARCH.md C.23
            ("[what|Who pays|Price to post one job|Where the jobs come from|Payment methods|us_better 1|us_better 2|pick] "
             "Paid by the employer. No base price printed; on load the button reads \"Post a Job $695\" with premium "
             "support +99, sticky 7 days +149, logo +49, standard colour +99 ticked. Sticky 14 days +199. \"Auto-renew every "
             "30 days\" ticked on load, charged \"to the same card\". A field for invoice details. Crypto is not offered on "
             "the posting form. Footer: \"Part of the Bondex ecosystem\".",
             "https://web3.career/post-web3-job", R13),
            ("[Where you apply|them_better 2|them_better 3|pick] Apply options for the employer: \"Redirect to a website\" "
             "or \"Our ATS powered by Bondex\". \"Job post views: 640,903\", \"Twitter followers: 41,000\", \"Discord "
             "members: 9,000\".",
             "https://web3.career/post-web3-job", R14),
        ],
    ),
]

# 24 Nov 2026: the big US job sites people compare (the owner asked for many more "alternatives" and "X vs Y" pages). Read that day
# on each site's own pages: help centres, pricing, FAQ, terms; ZipRecruiter's main site showed a human check, so its facts come from
# its help centre and its annual report to the SEC (its own words). A site whose pages refused the reader is in SKIPPED, not here.
ZIP_10K = "https://www.sec.gov/Archives/edgar/data/1617553/000161755326000016/zip-20251231.htm"
SITES += [
    # ------------------------------------------------------------------ ZipRecruiter
    dict(
        slug="ziprecruiter",
        name="ZipRecruiter",
        url="https://www.ziprecruiter.com/",
        what="ZipRecruiter is a US job marketplace, listed on the New York Stock Exchange, where employers pay for job posting plans and "
             "job seekers search for free. It reported 71,572 paying employers in the last quarter of 2025.",
        rows=_rows(
            ("Who pays", "Employers, through job posting plans or campaigns paid by clicks or applications. Its annual report says the "
                         "marketplace is free to job seekers."),
            ("Price for job seekers", "Free. You create a free job seeker profile to search and apply."),
            ("Price to post one job", "No public price. The plans are Standard, Premium and Pro, priced by a custom quote over the phone. "
                                      "Plans are billed in advance for one to twelve months; daily plans are billed by the days used."),
            ("Where the jobs come from", "Employers post jobs, and its annual report says job seekers get \"access to millions of jobs from "
                                         "all over the internet\". Employers' jobs are also sent out to partner job boards and search engines."),
            ("Where you apply", "On ZipRecruiter with 1-Click Apply, which sends the resume saved in your account, or on the employer's "
                                "own site when the button reads Apply Now."),
            ("Account needed to apply", "For 1-Click Apply, yes: you apply while logged in to your job seeker account. A new user is "
                                        "asked for a name, email address, phone number and resume."),
            ("How fresh the listings are", "When an employer closes a job, it is removed from all partner job boards within 24 hours."),
            ("Kinds of jobs", "Jobs in all industries and at all levels of seniority, \"millions of jobs\" by its annual report."),
        ),
        them_better=[
            "Far larger: 71,572 employers paid for it in the last quarter of 2025, and it says job seekers can search millions of jobs.",
            "1-Click Apply with a saved resume, a mobile app, and a career advisor called Phil that invites job seekers to apply.",
            "Employers' jobs go out to partner job boards, search engines and social networks at no extra fee for paid subscribers "
            "(the Veteran boards cost extra).",
        ],
        us_better=[
            "No account needed to apply: every Apply button goes to the employer's own page. ZipRecruiter's 1-Click Apply works only "
            "while you are logged in.",
            "A job is gone from this site at the next reading once the employer takes it down. ZipRecruiter removes a closed job "
            "from partner boards within 24 hours.",
            "Our employer prices are public: a standard listing is free for 30 days, boosts are $99 and $249. ZipRecruiter gives its "
            "prices only as a custom quote.",
        ],
        pick="Use ZipRecruiter if you want one profile and 1-Click Apply across millions of jobs, use Jobs Every Hour if you want jobs "
             "read around the clock from employers' own careers pages and to apply there without an account.",
        sources=[
            ("[what|Who pays|Price for job seekers|Where the jobs come from|Kinds of jobs|them_better 1|them_better 2|pick] Annual report "
             "for 2025 (Form 10-K, filed 25 Feb 2026): \"Our marketplace is free to job seekers.\" \"ZipRecruiter provides job seekers "
             "with access to millions of jobs from all over the internet.\" \"For job seekers across all industries and levels of "
             "seniority\". Quarterly Paid Employers: 71,572 in the fourth quarter of 2025. Search \"on our website or in our mobile app\"; "
             "\"Phil\", an AI-powered career advisor, invites candidates to apply. Class A common stock listed on the New York Stock "
             "Exchange (ZIP).", ZIP_10K, R24),
            ("[Who pays|Price to post one job|them_better 3] 10-K: \"Job posting plans are billed in advance of the subscription period, "
             "which typically ranges from one to twelve months, except for daily subscription plans, which are billed in arrears\"; "
             "performance-based customers pay per click or per application; employers' jobs are \"distributed to sites managed by our "
             "Job Distribution Partners\" (job boards, search engines, social networks).", ZIP_10K, R24),
            ("[Price to post one job|us_better 3] \"We offer a range of plans—including Standard, Premium, and Pro\"; \"If you would like "
             "to compare our plans or receive a custom quote\", call (877) 252-1062.",
             "https://support.ziprecruiter.com/s/article/Which-ZipRecruiter-hiring-plan-is-right-for-my-business", R24),
            ("[them_better 3] \"There are no additional fees to post to your job boards when you are a paid subscriber, with the "
             "exception of our Veteran Job Boards.\"",
             "https://support.ziprecruiter.com/s/article/Do-I-have-to-pay-extra-fees-for-each-job-board", R24),
            ("[Where you apply|Account needed to apply|us_better 1|pick] \"If the ad has a “1-Click” apply option, it means you can apply "
             "directly within our site while logged into your Job Seeker account.\" An \"Apply Now\" button means \"the application is "
             "housed externally on another site.\" A new user is prompted for name, email address and phone number, then a resume.",
             "https://support.ziprecruiter.com/candidate/s/article/I-found-a-job-I-like-How-do-I-apply", R24),
            ("[Price for job seekers] \"As a Job Seeker you can create a free Job Seeker profile, upload your resume and search for/apply "
             "to jobs in your field\".",
             "https://support.ziprecruiter.com/candidate/s/article/Can-ZipRecruiter-find-me-a-job", R24),
            ("[How fresh the listings are|us_better 2] \"When you close a job, the job is removed from all partner job boards within 24 "
             "hours.\"",
             "https://support.ziprecruiter.com/s/article/What-happens-when-I-close-a-job", R24),
        ],
    ),
    # ------------------------------------------------------------------ Glassdoor
    dict(
        slug="glassdoor",
        name="Glassdoor",
        url="https://www.glassdoor.com/",
        what="Glassdoor is a site of company reviews, salaries and job listings owned by Indeed, Inc. Since November 18, 2025 every new "
             "Glassdoor account is synced with Indeed.",
        rows=_rows(
            ("Who pays", "Employers, for sponsored jobs, which they buy on Indeed. Job seekers use a free account."),
            ("Price for job seekers", "A free account. Company, salary, interview and benefits insights open after you contribute "
                                      "something yourself (its \"Give-to-Get\" policy)."),
            ("Price to post one job", "Jobs are posted on Indeed. Unsponsored jobs show on Glassdoor at no cost; sponsored jobs use a "
                                      "flexible budget, with no fixed price stated."),
            ("Where the jobs come from", "Jobs posted on Indeed appear on Glassdoor automatically. A Glassdoor post-a-job request is "
                                         "routed to Indeed."),
            ("Where you apply", "With Easy Apply on Glassdoor, through a profile synced with Indeed."),
            ("Account needed to apply", "For Easy Apply, yes: a Glassdoor account synced with Indeed. Every new account since November 18, "
                                        "2025 is synced, and an Indeed account is created for you if you have none."),
        ),
        them_better=[
            "Company reviews, salaries, interview reports and benefits details shared by employees, which this site does not have.",
            "One login with Indeed: a synced profile gives you Easy Apply and makes you easier for hiring employers to find.",
            "Employers can post today: unsponsored jobs show at no cost, and a new US Indeed account gets a $75 credit to sponsor a "
            "first job.",
        ],
        us_better=[
            "No account needed to search or apply. Glassdoor's desktop job search steps start with \"Login to Glassdoor\", and Easy Apply "
            "needs an account synced with Indeed.",
            "Every job here is read from the employer's own careers page and checked around the clock. Glassdoor shows the jobs posted on Indeed.",
        ],
        pick="Use Glassdoor if you want company reviews and salaries next to the jobs, use Jobs Every Hour if you want jobs read every "
             "hour from employers' own careers pages and to apply without an account.",
        sources=[
            ("[what|Price for job seekers|Account needed to apply|them_better 1] \"Create a free Glassdoor account to access job "
             "listings, community discussions, salary insights, company reviews, benefits details, and interview tips.\" \"As of "
             "November 18, 2025, all new Glassdoor accounts must be synced with Indeed. If you don’t have an Indeed account, one will be "
             "created automatically during sign-up.\" \"Unlocking Company, Salary, Interview, and Benefits insights requires a "
             "contribution under our \"Give-to-Get\" policy.\"",
             "https://help.glassdoor.com/s/article/Create-a-Glassdoor-user-account?language=en_US", R24),
            ("[what] Help centre footer: \"Copyright © 2008-2026, Indeed, Inc. “Glassdoor,” “Worklife Pro,” “Bowls,” and logo are "
             "proprietary trademarks of Indeed, Inc.\"",
             "https://help.glassdoor.com/s/?language=en_US", R24),
            ("[Where you apply|Account needed to apply|them_better 2|us_better 1] A synced profile gives \"Faster, more seamless job "
             "applications with access to Easy Apply\" and \"Increased discoverability to hiring employers\"; without an Indeed account "
             "\"One will automatically be created for you during the sign-in process. This will allow you to access features like Easy "
             "Apply\".",
             "https://help.glassdoor.com/s/article/one-login-glassdoor-indeed?language=en_US", R24),
            ("[Where you apply|us_better 1] How to search for a job (Desktop): \"Login to Glassdoor. Select the Jobs tab.\" Applied jobs "
             "list \"any Easy Apply applications submitted\".",
             "https://help.glassdoor.com/s/article/How-to-Find-Save-and-Manage-Jobs-on-Glassdoor-Desktop-App?language=en_US", R24),
            ("[Who pays|Price to post one job|Where the jobs come from|them_better 3|us_better 2|pick] Indeed's page for employers: "
             "\"Jobs posted on Indeed automatically appear on Glassdoor.\" \"If you want to post a job on Glassdoor, you will be routed "
             "to Indeed to complete the posting.\" Unsponsored jobs \"are listed on Glassdoor at no cost\"; sponsor jobs \"using a "
             "flexible budget\"; new US accounts get \"a $75 credit to sponsor your first job\".",
             "https://www.indeed.com/hire/resources/howtohub/how-employers-use-glassdoor-and-indeed", R24),
        ],
    ),
    # ------------------------------------------------------------------ SimplyHired
    dict(
        slug="simplyhired",
        name="SimplyHired",
        url="https://www.simplyhired.com/",
        what="SimplyHired is a job search engine owned by Recruit Holdings, the same parent company as Indeed. It runs job search engines "
             "in 23 countries.",
        rows=_rows(
            ("Who pays", "Employers, to sponsor jobs, paid by the click. Job seekers pay nothing."),
            ("Price for job seekers", "Free: \"There are no subscription fees or charges for candidates.\""),
            ("Price to post one job", "Three free jobs a month, each shown for up to 30 days, posted through a free Indeed employer "
                                      "account. Sponsoring a job is paid by the click."),
            ("Where the jobs come from", "It gathers listings from company career pages, job boards and recruitment agencies, plus jobs "
                                         "posted on it directly. Jobs posted through an Indeed employer account appear on SimplyHired too."),
            ("Account needed to apply", "Yes. You can browse without an account, but you need a free account to apply."),
            ("How fresh the listings are", "Because listings come from outside sources, it says some postings \"may not update in real "
                                           "time once a role is filled or paused\"."),
            ("Kinds of jobs", "A wide range of industries and experience levels, from entry-level and skilled-trade roles up."),
        ),
        them_better=[
            "Part of the same group as Indeed, it runs job search engines in 23 countries and 12 languages.",
            "It also lists jobs from job boards and recruitment agencies, so one search can show openings that are not on an employer's "
            "own careers page.",
            "Employers can post three jobs a month free today and sponsor more, with placement on both SimplyHired and Indeed.",
        ],
        us_better=[
            "No account needed to apply. SimplyHired asks for a free account before you apply.",
            "Every job here is read again from the employer's careers page around the clock and dropped when it closes. SimplyHired says some "
            "postings may not update in real time once a role is filled.",
        ],
        pick="Use SimplyHired if you want one search that also covers job boards and agencies, use Jobs Every Hour if you want jobs read "
             "around the clock from employers' own careers pages and to apply without an account.",
        sources=[
            ("[what|Who pays|Price for job seekers|Price to post one job|Where the jobs come from|Account needed to apply|"
             "How fresh the listings are|Kinds of jobs|them_better 1|them_better 2|them_better 3|us_better 1|us_better 2|pick] "
             "\"SimplyHired is an online job search engine that aggregates listings from company career pages, job boards, and "
             "recruitment agencies across the web.\" \"owned by Recruit Holdings Co., Ltd., the same parent company as Indeed\"; "
             "\"operates job search engines in 23 countries and 12 languages\". \"There are no subscription fees or charges for "
             "candidates\"; \"Job seekers can browse without an account but need to create a free account to apply\". \"Employers can "
             "post three free jobs a month*, each visible for up to 30 days\", through \"a free Indeed employer account\"; \"Sponsorship "
             "works on a pay-per-click basis\"; sponsored jobs \"get enhanced placement on both SimplyHired and Indeed\". \"some "
             "postings may not update in real time once a role is filled or paused\". Roles \"across a wide range of industries and "
             "experience levels, from entry-level and skilled-trade roles\".",
             "https://www.simplyhired.com/brand-facts", R24),
        ],
    ),
    # ------------------------------------------------------------------ Jooble
    dict(
        slug="jooble",
        name="Jooble",
        url="https://jooble.org/",
        what="Jooble is a job search engine founded in 2006 that works in 66 countries; its US page showed 2,583,000+ current vacancies "
             "from 5,840 websites.",
        rows=_rows(
            ("Who pays", "Employers and job publishers, to promote jobs by clicks or by applications. Job seekers do not pay."),
            ("Price for job seekers", "Free: \"All Jooble services for our job seekers are completely free of charge.\""),
            ("Price to post one job", "No free option is listed. Promotion is paid per click or per application, with 50% off the "
                                      "first campaign."),
            ("Where the jobs come from", "Gathered from many public sources; employers can also connect their jobs through a hiring "
                                         "system, an XML feed or their careers site."),
            ("Where you apply", "On the employer's website: you \"choose what jobs to apply for via employers' website\"."),
            ("Kinds of jobs", "Jobs of every kind in 66 countries; the US page showed 2,583,000+ current vacancies from 5,840 websites."),
        ),
        them_better=[
            "Far larger: it says it reads 140,000+ sources and adds 300,000 new jobs a day, in 66 countries.",
            "Running since 2006, in many countries, not only the US.",
            "It also takes jobs from other job sites, so one search can show roles that are not on employers' own careers pages.",
        ],
        us_better=[
            "A standard listing is free for 30 days, posted in the employer account. Jooble charges per click or per application and "
            "lists no free option.",
            "Every job here is read from the employer's own careers page around the clock. Jooble gathers its listings from thousands of other "
            "websites.",
        ],
        pick="Use Jooble if you want the widest search across many countries and websites, use Jobs Every Hour if you want jobs read every "
             "hour from employers' own careers pages.",
        sources=[
            ("[what|Kinds of jobs|them_better 1] \"Jooble — 2.583.000+ current vacancies — Jobs in USA\"; \"More than 2582800 vacancies "
             "across 5840 websites\"; \"66 countries\".", "https://jooble.org/", R24),
            ("[what|them_better 1|them_better 2] Founded in 2006; \"140 000+\" sources; \"300 000\" new jobs every day; 66 countries.",
             "https://jooble.org/info/about", R24),
            ("[Who pays|Price to post one job|us_better 1|pick] \"Pay per received clicks on your job ads\"; \"Promote unlimited jobs and "
             "pay only for the applications you get\"; \"50% off for first campaign\"; \"Connect your jobs via ATS, XML feed, or directly "
             "from your career site\".", "https://jooble.org/partner/advertise", R24),
            ("[Who pays|Price for job seekers|Where the jobs come from|Where you apply|them_better 3|us_better 2] \"As a job aggregator, "
             "Jooble helps people search for jobs from various public sources in one place.\" \"All Jooble services for our job seekers "
             "are completely free of charge.\" \"choose what jobs to apply for via employers' website\".",
             "https://jooble.org/how-jooble-works", R24),
        ],
    ),
    # ------------------------------------------------------------------ Talent.com
    dict(
        slug="talent-com",
        name="Talent.com",
        url="https://www.talent.com/",
        what="Talent.com is a job search engine that says it brings together more than 30 million jobs from over a million companies in "
             "77 countries.",
        rows=_rows(
            ("Who pays", "Employers, for sponsored jobs and campaigns; search results mix sponsored, organic and gathered jobs, and bids "
                         "count. Job seekers pay nothing."),
            ("Price for job seekers", "Free: it says it is \"completely free for job seekers, and always has been\"."),
            ("Price to post one job", "No price is shown. Employers fill in a get-started form, and an account manager runs campaigns to "
                                      "the employer's budget."),
            ("Where the jobs come from", "Gathered from postings across the web, \"much like a search engine for jobs\", always naming "
                                         "the source, plus employers' own campaigns."),
            ("Where you apply", "Quick Apply on Talent.com, or Apply sends you to the site that posted the job, which it says is often a "
                                "third-party platform rather than the employer."),
            ("How fresh the listings are", "No refresh time is stated. The help centre asks you to report a job that shows as expired or "
                                           "out of date."),
            ("Kinds of jobs", "Jobs of every kind: more than 30 million from over a million companies in 77 countries."),
        ),
        them_better=[
            "Far larger: more than 30 million jobs from over a million companies in 77 countries, by its own count.",
            "Quick Apply sends your resume without leaving the site, and it has free salary and after-tax pay tools.",
        ],
        us_better=[
            "Every Apply button here goes to the employer's own careers page. On Talent.com, Apply often leads to a third-party platform "
            "or publisher rather than the employer.",
            "Every job is read again from the employer's careers page around the clock and dropped when it closes. Talent.com states no refresh "
            "time and asks users to report expired jobs.",
        ],
        pick="Use Talent.com if you want the widest search across many countries, use Jobs Every Hour if you want jobs read around the clock from "
             "employers' own careers pages and to apply there.",
        sources=[
            ("[what|Where the jobs come from|Where you apply|Kinds of jobs|them_better 1|them_better 2] \"We bring together more than 30 "
             "million jobs from over a million companies across 77 countries\"; \"much like a search engine for jobs, we gather openings "
             "published across the web and always credit the source\"; \"compare salaries, and estimate your after-tax pay, all free "
             "for job seekers\".", "https://helpcenter.talent.com/hc/en-ca/articles/49967447310996-What-is-Talent-com", R24),
            ("[Price for job seekers|Who pays] \"Yes, Talent.com is completely free for job seekers, and always has been.\"",
             "https://helpcenter.talent.com/hc/en-ca/articles/49966854548372-Is-Talent-com-free", R24),
            ("[Where you apply|us_better 1|pick] When you click Apply, \"we sometimes let you apply directly on Talent.com and other times "
             "send you to the site that posted the job, which is often a third-party platform or publisher rather than the employer "
             "directly.\"", "https://helpcenter.talent.com/hc/en-ca/articles/50233488336916-Why-does-Apply-take-me-to-another-website", R24),
            ("[Where you apply|them_better 2] \"Quick Apply\": \"upload your resume, add your email, and answer any employer questions, "
             "all in one place.\" \"Apply\": \"we send you to the employer's site\".",
             "https://helpcenter.talent.com/hc/en-ca/articles/49968041668116-How-do-I-apply-for-a-job", R24),
            ("[Who pays] \"Search results are a rotating mix of sponsored, organic, and aggregated jobs. Bids matter\".",
             "https://helpcenter.talent.com/hc/en-ca/articles/49968189074196-Why-isn-t-my-job-showing-first-in-search-results", R24),
            ("[Price to post one job|Who pays] \"a dedicated account manager and analyst team optimize your campaigns to your budget\"; "
             "\"fill out the get started form\".",
             "https://helpcenter.talent.com/hc/en-ca/articles/49968619222420-What-solutions-does-Talent-com-offer-employers", R24),
            ("[How fresh the listings are|us_better 2] \"If a job is showing as expired or out of date, let us know with the job link\".",
             "https://helpcenter.talent.com/hc/en-ca/articles/49968605743124-How-do-I-report-an-expired-job", R24),
        ],
    ),
    # ------------------------------------------------------------------ Welcome to the Jungle (Otta)
    dict(
        slug="welcome-to-the-jungle",
        name="Welcome to the Jungle",
        url="https://www.welcometothejungle.com/",
        what="Welcome to the Jungle is a job site with company profiles that bought the UK job site Otta in 2024; its UK site, formerly "
             "Otta, says it has over 3,500 top companies and 70,000+ live jobs.",
        rows=_rows(
            ("Who pays", "Employers, through a subscription plus job packages sized by how many active jobs they want to fill."),
            ("Price to post one job", "No price is published: \"pricing depends on how much you're hiring\", so employers ask for a quote."),
            ("Where you apply", "Most companies take applications through a form on Welcome to the Jungle; others send you to their own "
                                "recruitment site."),
            ("Account needed to apply", "Yes, for its own form: \"you must be logged into your account\". You can browse jobs without "
                                        "logging in."),
            ("Kinds of jobs", "Jobs at the companies that recruit on it: \"over 3,500 top companies and 70,000+ live jobs\" on its UK site."),
        ),
        them_better=[
            "Company profiles that show what each company is like, plus articles about work, which this site does not have.",
            "Employers get employer branding, sourcing and an applicant tracking system in one subscription.",
        ],
        us_better=[
            "No account needed to apply: every Apply button goes to the employer's own page. Welcome to the Jungle's own form needs you "
            "to log in.",
            "Our employer prices are public, and a standard listing is free for 30 days. Welcome to the Jungle publishes no price.",
        ],
        pick="Use Welcome to the Jungle if you want to learn about companies from their profiles before you apply, use Jobs Every Hour if "
             "you want jobs read around the clock from careers pages and to apply without an account.",
        sources=[
            ("[what|Kinds of jobs] Page title \"Welcome To The Jungle UK (formerly Otta)\"; \"over 3,500 top companies and 70,000+ live "
             "jobs\".", "https://uk.welcometothejungle.com/", R24),
            ("[what] Welcome to the Jungle \"has announced the acquisition of London-based Otta, the candidate-first job search "
             "platform\".", "https://press.welcometothejungle.com/news/uk-recruitment-platform-otta-acquired-by-welcome-to-the-jungle", R24),
            ("[Who pays|Price to post one job|them_better 2|us_better 2] Pricing is a base subscription (Employer Brand, Job Matching, "
             "Sourcing, ATS) and job packages by number of active jobs; \"Because pricing depends on how much you're hiring\"; no prices "
             "shown.", "https://solutions.welcometothejungle.com/en/pricing", R24),
            ("[Where you apply|Account needed to apply|us_better 1|pick] \"Most companies on Welcome to the Jungle allow you to send your "
             "application directly from our website.\" \"If you are not logged in, you will be asked to do so, or to create an account\". "
             "\"Some companies on Welcome to the Jungle use an external recruitment platform\".",
             "https://help.welcometothejungle.com/en/send-an-application-via-the-form", R24),
            ("[Account needed to apply|them_better 1|pick] \"You can browse thousands of jobs on Welcome to the Jungle, even when you're "
             "not logged into your account.\" To apply \"you must be logged into your account.\" \"more that 3,000 companies recruiting\"; "
             "\"we've also created a media dedicated to employment\"; company pages.",
             "https://help.welcometothejungle.com/en/why-should-you-create-an-account-on-welcome-to-the-jungle", R24),
        ],
    ),
    # ------------------------------------------------------------------ Dice
    dict(
        slug="dice",
        name="Dice",
        url="https://www.dice.com/",
        what="Dice is a job site where employers buy job slots and plans that include TalentSearch, a search of candidate profiles.",
        rows=_rows(
            ("Who pays", "Employers, for job slots and plans. The pricing page lists no charge for job seekers."),
            ("Price to post one job", "$399 for a single job slot, active for 30 days. Starter: $649 a month month to month (3 active "
                                      "jobs) or $549 a month billed yearly. Standard: $899 or $749 a month (5 active jobs). Prices for "
                                      "new customers."),
            ("Where you apply", "Through Dice Easy Apply, or on the company's own career site."),
            ("Account needed to apply", "Yes. Its help page says to register and set up your profile."),
            ("How fresh the listings are", "A new posting is live and searchable in 30 minutes or less; a single job slot runs 30 days."),
        ),
        them_better=[
            "Employers get TalentSearch, a search of candidate profiles, and a built-in applicant tracking system.",
            "Easy Apply lets you apply without leaving Dice.",
        ],
        us_better=[
            "A standard listing is free for 30 days, posted in the employer account. Dice charges $399 for one job slot for 30 days.",
            "No account needed to search or apply, and every Apply button goes to the employer's own page. Dice asks you to register and "
            "set up a profile.",
        ],
        pick="Use Dice if you want Easy Apply with a Dice profile or an employer needs candidate search, use Jobs Every Hour if you want "
             "to search and apply with no account or post one job free.",
        sources=[
            ("[what|Who pays|Price to post one job|them_better 1|us_better 1|pick] \"Single Job Slot: $399\", \"Job slot active for 30 "
             "days\"; Starter \"$649/month\" \"Billed month-to-month (no annual contract)\" or \"$549/month\" billed annually; Standard "
             "\"$899/month\" or \"$749/month\"; TalentSearch profile views in Starter and Standard; \"Pricing is subject to change and is "
             "valid for new customers only.\"", "https://www.dice.com/hiring/pricing", R24),
            ("[Where you apply|Account needed to apply|them_better 2|us_better 2|pick] \"apply immediately through Dice Easy Apply\" or on "
             "the company's career site; register at dice.com/register and \"ensure your profile is set-up\".",
             "https://www.dice.com/support/candidate-experience/most-frequently-asked-questions.html", R24),
            ("[How fresh the listings are|them_better 1] \"Post will be live and searchable in 30 minutes or less.\" Applications arrive in "
             "Dice's \"built-in applicant tracking system\".",
             "https://www.dice.com/support/employer/jobs/jobs---how-to-post-a-new-job-and-best-practices.html", R24),
        ],
    ),
    # ------------------------------------------------------------------ Built In
    dict(
        slug="built-in",
        name="Built In",
        url="https://builtin.com/",
        what="Built In is a job site and employer branding service that shows 500K+ jobs and 100K+ companies on its home page.",
        rows=_rows(
            ("Who pays", "Employers, for job slots and memberships. Job seekers can make a free account."),
            ("Price for job seekers", "Free: the site offers \"Create Free Account\"."),
            ("Price to post one job", "Not published on its employer pages, which ask you to book a demo."),
            ("Kinds of jobs", "Jobs in many fields, from engineering and product to banking, consulting and sales; the home page states "
                              "500K+ jobs."),
        ),
        them_better=[
            "Large: it states 500K+ jobs and 100K+ companies on its home page.",
            "Company pages and employer branding, plus a job tracker and job alerts for job seekers.",
        ],
        us_better=[
            "Our employer prices are public, and a standard listing is free for 30 days. Built In publishes no price and asks for a demo.",
            "No account needed for anything here. Built In's job alerts and tracker need an account.",
        ],
        pick="Use Built In if you want company profiles next to a large list of jobs, use Jobs Every Hour if you want to search and apply "
             "with no account and post a job free.",
        sources=[
            ("[what|them_better 1] \"500K+ Jobs\"; \"Explore 100K+ Companies\".", "https://builtin.com/", R24),
            ("[what|Who pays|Price to post one job|us_better 1|pick] \"Post Job\" leads to employer membership and job slot pages; "
             "\"Book Demo\"; no prices shown.", "https://employers.builtin.com/membership/", R24),
            ("[Who pays|Price for job seekers|Kinds of jobs|them_better 2|us_better 2|pick] \"Create Free Account\" or \"Log In\"; \"Save "
             "Job Alert\"; the Tracker leads to a login; listings in engineering, product management, consulting, banking, real estate "
             "sales and quantitative research.", "https://builtin.com/jobs", R24),
        ],
    ),
    # ------------------------------------------------------------------ Himalayas
    dict(
        slug="himalayas",
        name="Himalayas",
        url="https://himalayas.app/",
        what="Himalayas is a remote job site run by an Australian company founded in 2020, with 100,000+ remote listings from 70,000+ "
             "companies.",
        rows=_rows(
            ("Who pays", "Employers, only for an optional pinned post. Job seekers can use a free plan or pay for Plus or Max."),
            ("Price for job seekers", "Free plan at $0. Plus is $9 a month and Max $29 a month. ID verification is a one-time $5 on the "
                                      "free plan."),
            ("Price to post one job", "Posting is free and a listing stays up 30 days. A pinned job post costs $299."),
            ("Where the jobs come from", "Companies post roles themselves, or listings are gathered from careers pages and hiring "
                                         "systems; listings are checked for spam and scams."),
            ("Where you apply", "On the company's own application page or a form on Himalayas."),
            ("Account needed to apply", "Yes: you create a free account and build your profile."),
            ("How fresh the listings are", "A listing is active for 30 days from the day it is published, then removed automatically."),
            ("Kinds of jobs", "Remote jobs only. Software development is the largest field, then sales, customer service, operations "
                              "and marketing."),
        ),
        them_better=[
            "A large remote-only list: 100,000+ listings from 70,000+ companies, and 600,000+ public talent profiles for employers.",
            "A job application tracker and resume, cover letter and interview practice tools on its free plan.",
            "Employers can post free for 30 days today and pay for a pinned post.",
        ],
        us_better=[
            "No account needed to search or apply. Himalayas asks you to create an account and build a profile.",
            "Every job is read again from the employer's careers page around the clock. A Himalayas listing stays up 30 days from publication.",
            "A boost to stand out costs $99 for 30 days here (not on sale yet). A pinned post on Himalayas is $299.",
        ],
        pick="Use Himalayas if you want remote jobs only and its profile and application tools, use Jobs Every Hour if you want to search "
             "and apply with no account, on-site and hybrid jobs included.",
        sources=[
            ("[what|Where the jobs come from|Where you apply|Account needed to apply|Kinds of jobs|them_better 1|us_better 1|pick] \"A "
             "remote jobs platform with 100,000+ listings from 70,000+ companies.\" Himalayas Remote Jobs Pty Ltd, \"an Australian company "
             "founded in 2020\"; \"600,000+ talent profiles\"; apply goes to \"the company's own application page (or an in-platform "
             "application form)\"; \"create a free account and build your profile\"; software development the largest field.",
             "https://himalayas.app/docs/what-is-himalayas", R24),
            ("[Who pays|Price for job seekers|Price to post one job|them_better 2|them_better 3|us_better 3] Free plan $0; Plus $9 "
             "monthly; Max $29 monthly; ID verification $5 one time; company profile free with unlimited job posts, each live 30 days; "
             "Pinned Job Post $299 per job.", "https://himalayas.app/pricing", R24),
            ("[Price to post one job|How fresh the listings are|us_better 2] \"Posting a job on Himalayas is free.\" \"Your listing stays "
             "active for 30 days from the publication date.\"", "https://himalayas.app/docs/posting-a-remote-job", R24),
            ("[How fresh the listings are|them_better 2] Listings \"are active for 30 days\"; tools for resumes, cover letters, interview "
             "practice and a Job Application Tracker.", "https://himalayas.app/docs", R24),
        ],
    ),
    # ------------------------------------------------------------------ Remotive
    dict(
        slug="remotive",
        name="Remotive",
        url="https://remotive.com/",
        what="Remotive is a remote job site run by Remotive SARL, a French company; its home page offers 140,000+ fully remote jobs and "
             "shows a small preview to people without a membership.",
        rows=_rows(
            ("Who pays", "Both. Employers pay to post, from $299 for 30 days. Job seekers pay for a membership that opens the full list."),
            ("Price for job seekers", "Membership: €21 a month or €89 a year. It renews automatically unless cancelled; new subscribers "
                                      "can ask for a full refund within 14 days."),
            ("Price to post one job", "$299 to feature a job for 30 days. Higher levels cost $358, $398 and $448; bundles save up to 40%."),
            ("Where the jobs come from", "It lists jobs \"from vetted companies\", and employers can post through its hire page."),
            ("Where you apply", "On the company's side: \"You'll be redirected to the company's careers page or application link.\""),
            ("Kinds of jobs", "Fully remote jobs; without a membership, the home page says \"You're seeing 0.4% of available roles\"."),
            ("Payment methods", "Job seekers are charged through Stripe; the methods are not listed."),
        ),
        them_better=[
            "Only fully remote jobs, 140,000+ by its count, with search filters for location and salary for members.",
            "Members see jobs 24 hours early and get email digests by location or category.",
            "Employers get a 30-day feature with a promise of 200+ Apply clicks or a free repost, and reach through its Slack, daily email "
            "and social posts.",
        ],
        us_better=[
            "Free to search, with no account. Remotive shows 0.4% of its jobs until you pay €21 a month or €89 a year.",
            "A standard listing is free for 30 days, posted in the employer account. Remotive charges from $299 for 30 days.",
            "Plus here is one payment that never renews (not on sale yet). Remotive's membership renews automatically.",
        ],
        pick="Use Remotive if you only want fully remote work and will pay for the full list, use Jobs Every Hour if you want to search "
             "free, read around the clock from employers' careers pages.",
        sources=[
            ("[what|Who pays|Where the jobs come from|Kinds of jobs|them_better 1|them_better 2|us_better 1] \"Browse 140,000+ fully remote "
             "jobs from vetted companies\"; \"You're seeing 0.4% of available roles\"; \"See jobs 24 hours early\"; \"Advanced search "
             "filters (location & salary)\".", "https://remotive.com/", R24),
            ("[what|Price for job seekers|Payment methods|us_better 1|us_better 3|pick] \"Monthly plan: €21/month. Annual plan: "
             "€89/year.\"; renews automatically unless you cancel; full refund within 14 days for new subscribers; \"Charged to your "
             "chosen payment method via Stripe\"; operated by Remotive SARL.",
             "https://support.remotive.com/en/article/terms-of-service-u4kbkf/", R24),
            ("[Who pays|Price to post one job|us_better 2] \"Our base price to post a job is $299 to feature your job for 30 days.\"; "
             "$358, $398, $448; \"save up to 40% with job bundles\".",
             "https://support.remotive.com/en/article/for-recruiters-how-much-does-it-cost-1cdq0y7/", R24),
            ("[Where the jobs come from|them_better 3] \"200+ 'Apply' clicks, or we'll repost it for another month, free of charge\"; "
             "Remotive's Slack, daily email update and social media shares.", "https://remotive.com/hire", R24),
            ("[Where you apply|them_better 2] \"You'll be redirected to the company's careers page or application link.\" \"We're not "
             "involved in the application process.\" Email digests by location or category need premium access.",
             "https://support.remotive.com/en/article/frequently-asked-questions-180nrek/", R24),
        ],
    ),
    # ------------------------------------------------------------------ Remote.co
    dict(
        slug="remote-co",
        name="Remote.co",
        url="https://remote.co/",
        what="Remote.co is a remote job site run by BOLD LLC; its home page says it lists 100k+ jobs in 100+ categories, with 2K+ new "
             "jobs posted every day.",
        rows=_rows(
            ("Where the jobs come from", "Employers submit postings, and its team researches listings to add; every job is reviewed "
                                         "against its quality criteria."),
            ("Where you apply", "On the employer's own page: the job page we opened showed the full description and an Apply link to the "
                                "employer's careers site."),
            ("Account needed to apply", "Not on the job page we opened: its Apply link worked without signing in."),
            ("Kinds of jobs", "Remote and hybrid jobs \"from entry-level to executive positions\", in 100+ categories."),
        ),
        them_better=[
            "Remote and hybrid work only, with every job reviewed against quality criteria before it is listed.",
            "Career articles and question-and-answer pages from 108 remote companies about how they work.",
        ],
        us_better=[
            "Every job here is read from the employer's own careers page around the clock and dropped when it closes. On Remote.co, employers "
            "submit postings and its team adds listings it researches.",
            "Every open job a company posts on its careers page is here, on-site ones too. Remote.co lists remote and hybrid jobs.",
        ],
        pick="Use Remote.co if you want remote and hybrid jobs reviewed by a team, use Jobs Every Hour if you want every job read around the clock "
             "from employers' own careers pages.",
        sources=[
            ("[what|Kinds of jobs|us_better 2] \"Remote.co is a trusted resource for finding remote jobs\"; \"connect job seekers with "
             "companies offering flexible and remote opportunities, from entry-level to executive positions\"; address: Bold LLC.",
             "https://remote.co/about-us", R24),
            ("[what|Kinds of jobs|them_better 2|pick] \"2K+ NEW JOBS POSTED EVERY DAY\"; \"Browse thousands of remote and hybrid jobs\"; "
             "\"Explore more than 100k+ jobs in 100+ Categories\"; \"108 leading remote companies answer your questions\".",
             "https://remote.co/", R24),
            ("[Where the jobs come from|them_better 1|us_better 1|pick] Terms of Use (last updated November 12, 2026), between \"BOLD "
             "LLC\" and users: \"Employers submit job postings to Remote.co for consideration in its job database, and Remote.co’s team "
             "research job listings for consideration to be added to its job database. In either case, every job will be reviewed to "
             "ensure it meets the quality and relevancy criteria.\"", "https://remote.co/tos", R24),
            ("[Where you apply|Account needed to apply] Job page read without signing in: full description, \"Apply\" linking to "
             "miamioh.wd5.myworkdayjobs.com (the employer's own careers site).",
             "https://remote.co/job-details/assistant-director-design-74b0e5d5-9e50-4734-b5b7-ad7e6c793115", R24),
        ],
    ),
    # ------------------------------------------------------------------ Working Nomads
    dict(
        slug="working-nomads",
        name="Working Nomads",
        url="https://www.workingnomads.com/",
        what="Working Nomads is a remote job board that says it \"curates remote digital jobs from around the web\".",
        rows=_rows(
            ("Who pays", "Employers pay to post. Job seekers can pay for Premium."),
            ("Price for job seekers", "Browsing and applying are free. Premium is paid, with monthly, quarterly or yearly plans; the price "
                                      "is not shown on the pages we read."),
            ("Price to post one job", "$199 for one job for 30 days. A bundle of 10 jobs costs $1,690 ($169 a job)."),
            ("Where the jobs come from", "It curates remote jobs from around the web."),
            ("Where you apply", "You follow the employer's application instructions: its own site, a hiring system or email."),
            ("Account needed to apply", "No: \"you don’t need an account to browse or apply for jobs.\""),
            ("Kinds of jobs", "Remote jobs in development, marketing, management, design, healthcare, sales and more."),
            ("Payment methods", "Credit card through PayPal. Bank transfer and purchase orders for larger bundles."),
        ),
        them_better=[
            "Remote jobs only, chosen by hand from around the web.",
            "Employers can buy a 10-job bundle with credits valid for 2 years, and pay by bank transfer or purchase order.",
        ],
        us_better=[
            "A standard listing is free for 30 days, posted in the employer account. Working Nomads charges $199 for one 30-day post.",
            "Every job here is read from the employer's own careers page around the clock. Working Nomads curates jobs from around the web.",
        ],
        pick="Use Working Nomads if you want a hand-picked remote-only board, use Jobs Every Hour if you want jobs read around the clock from "
             "employers' own careers pages and to post a job free.",
        sources=[
            ("[what|Who pays|Price for job seekers|Where the jobs come from|Where you apply|Account needed to apply|Kinds of jobs|"
             "Payment methods|them_better 1|us_better 2|pick] \"curates remote digital jobs from around the web\"; \"No, you don’t need "
             "an account to browse or apply for jobs.\"; Premium \"a paid service\" with \"monthly, quarterly, or annual plans\"; "
             "\"follow the employer’s application instructions\"; industries include development, marketing, management, design, "
             "healthcare, sales; \"Pay using credit card via PayPal payment gate\".", "https://www.workingnomads.com/faq", R24),
            ("[Who pays|Price to post one job|Payment methods|them_better 2|us_better 1|pick] Single Job $199; Job Bundle $169 per job, 10 "
             "jobs for $1,690; each post live 30 days; bundle credits valid 2 years; bank transfer and purchase orders \"for larger "
             "bundles\".", "https://workingnomads.com/post-job-options", R24),
        ],
    ),
    # ------------------------------------------------------------------ Handshake
    dict(
        slug="handshake",
        name="Handshake",
        url="https://joinhandshake.com/",
        what="Handshake is a job network for students and graduates that links job seekers, schools and employers; it states 1,600+ "
             "schools and 1 million employers.",
        rows=_rows(
            ("Who pays", "Employers, for the Pro and Enterprise plans and for promoted jobs. The Basic employer plan is free."),
            ("Price to post one job", "Free on Basic, with 10 messages a month. Pro is $450 a month; Enterprise is priced on request. "
                                      "Promoted jobs start at $34 a day on Basic."),
            ("Account needed to apply", "Yes: its students page asks you to sign up to use it."),
            ("Kinds of jobs", "Jobs and internships for students and graduates, plus career events."),
        ),
        them_better=[
            "Tied to 1,600+ schools and their career centres, with internships and first jobs as its focus.",
            "Mobile apps on the App Store and Google Play.",
        ],
        us_better=[
            "No account needed to search or apply. Handshake asks you to sign up.",
            "A standard listing is free for 30 days with no message limit. Handshake's free employer plan allows 10 messages a month.",
        ],
        pick="Use Handshake if you are a student or new graduate looking for internships through your school, use Jobs Every Hour if you "
             "want to search jobs with no account.",
        sources=[
            ("[what|them_better 1] \"the only three-sided job marketplace\"; \"1,600+ educational institutions\"; \"1 million employers\".",
             "https://joinhandshake.com/about/", R24),
            ("[Who pays|Price to post one job|us_better 2|pick] Basic free (free job posting, 10 messages a month); Pro $450 a month; "
             "Enterprise \"Contact for pricing\"; promoted jobs from $34/day on Basic.", "https://joinhandshake.com/employers/pricing/", R24),
            ("[Account needed to apply|Kinds of jobs|them_better 1|them_better 2|us_better 1|pick] \"Sign up for Handshake and never miss "
             "a connection, opportunity, or event.\"; \"Find jobs and internships\"; apps on the App Store and Google Play.",
             "https://joinhandshake.com/students/", R24),
        ],
    ),
    # ------------------------------------------------------------------ Snagajob
    dict(
        slug="snagajob",
        name="Snagajob",
        url="https://www.snagajob.com/",
        what="Snagajob is a job site for hourly and local jobs, run by Snagajob.com, Inc.",
        rows=_rows(
            ("Who pays", "Employers pay to post jobs. \"Snagajob is free for job seekers.\""),
            ("Price for job seekers", "Free, and so is the profile."),
            ("Where the jobs come from", "Employers list their openings with Snagajob, some of them all year round."),
            ("Where you apply", "On Snagajob with Apply Now; some employers ask you to finish on their own website."),
            ("Account needed to apply", "Yes: \"You must have an account to apply to jobs on Snagajob.\" You must also live in the US."),
            ("How fresh the listings are", "No listing length is stated; new jobs are added daily and some employers list all year."),
            ("Kinds of jobs", "Hourly jobs: full-time, part-time or shifts."),
        ),
        them_better=[
            "Built for hourly and shift work, with filters for part-time and shifts.",
            "Employers search profiles and invite people to interview, and your profile works as your application.",
            "Phone support Monday to Friday, 8:30 AM to 8:30 PM Eastern.",
        ],
        us_better=[
            "No account needed to search or apply. Snagajob says \"You must have an account to apply\".",
            "Every Apply button here goes straight to the employer's own page. On Snagajob, some employers ask you to finish on their "
            "website after applying on Snagajob.",
        ],
        pick="Use Snagajob if you want hourly, part-time or shift work and are happy to keep a profile, use Jobs Every Hour if you want to "
             "search and apply with no account on the employer's own page.",
        sources=[
            ("[what|Kinds of jobs|them_better 1] Page title \"Job Search for Hourly & Local Jobs Hiring Now\"; \"© 2026 Snagajob.com, "
             "Inc.\"; \"Your profile is your application. Apply to jobs instantly.\"", "https://www.snagajob.com/", R24),
            ("[Who pays|Price for job seekers|Where the jobs come from|Where you apply|Account needed to apply|How fresh the listings are|"
             "them_better 3|us_better 1|us_better 2|pick] \"Snagajob is free for job seekers.\" \"You must have an account to apply to "
             "jobs on Snagajob.\" Applicants must be US residents. \"Some employers require you to finish on their own website.\" "
             "Employers \"list their job openings with Snagajob year-round\"; new jobs are added daily. Support Monday through Friday, "
             "8:30 AM to 8:30 PM EST.", "https://www.snagajob.com/faq", R24),
            ("[Price for job seekers|Kinds of jobs|them_better 1|them_better 2] \"Full-time, part-time or Shifts\"; \"Employers search for "
             "candidates and can invite you to interview.\"; \"your free member profile\".", "https://www.snagajob.com/workers", R24),
        ],
    ),
    # ------------------------------------------------------------------ USAJOBS
    dict(
        slug="usajobs",
        name="USAJOBS",
        url="https://www.usajobs.gov/",
        what="USAJOBS is the US federal government's official employment site, run by the Office of Personnel Management; it says over 16 "
             "million job seekers have created accounts.",
        rows=_rows(
            ("Where the jobs come from", "Federal agencies. Job announcements come from each agency's own hiring system."),
            ("Where you apply", "You prepare the application on USAJOBS, then move to the hiring agency's application system."),
            ("Account needed to apply", "Yes: a USAJOBS profile, with sign-in through login.gov."),
            ("Kinds of jobs", "Federal jobs only, in hundreds of agencies and organizations."),
        ),
        them_better=[
            "The official place for US federal jobs, run by the government itself.",
            "A saved profile keeps your resumes and documents, with saved jobs and saved searches.",
            "A five-step guide prepares each federal application.",
        ],
        us_better=[
            "No account or login.gov sign-in needed to search or apply here.",
            "Jobs from thousands of companies' own careers pages. USAJOBS lists federal jobs only.",
        ],
        pick="Use USAJOBS if you want a federal government job, use Jobs Every Hour if you want jobs at companies, searched with no account.",
        sources=[
            ("[what|Account needed to apply|them_better 1|them_better 2|us_better 1] \"USAJOBS is a United States Office of Personnel "
             "Management website.\" \"The Federal Government's official employment site\"; \"over 16 million job seekers to create "
             "accounts to date\"; \"create and complete your profile to apply for any job on USAJOBS\"; save jobs, automated searches, "
             "resumes.", "https://www.usajobs.gov/", R24),
            ("[Where the jobs come from|Kinds of jobs|them_better 1|us_better 2|pick] The \"central location to find jobs in hundreds of "
             "federal agencies and organizations\"; jobs flow \"from the agency's Talent Acquisition System (TAS)\".",
             "https://www.opm.gov/agency-services/talent-systems/usajobs/", R24),
            ("[Where you apply|Account needed to apply|them_better 3|us_better 1] \"We will guide you through a five-step process to "
             "prepare your application\"; then you are transferred to the agency's application system. \"USAJOBS is now using login.gov "
             "for our sign-in process.\"", "https://www.usajobs.gov/getstarted", R24),
        ],
    ),
    # ------------------------------------------------------------------ Idealist
    dict(
        slug="idealist",
        name="Idealist",
        url="https://www.idealist.org/",
        what="Idealist is a New York nonprofit that runs a board of social-impact jobs, internships and volunteer roles; it says more "
             "than 1.2 million jobs have been posted on it.",
        rows=_rows(
            ("Who pays", "Organizations, to post jobs and internships; volunteer listings and events are free. Job seekers pay nothing."),
            ("Price for job seekers", "Free: \"Signing up is free.\""),
            ("Price to post one job", "30 days per listing: $145 a job for nonprofits and government agencies ($25 an internship), $175 "
                                      "for consultants and recruiters, $195 for businesses. Packs cost less a job."),
            ("Where the jobs come from", "Organizations post their own listings."),
            ("Where you apply", "On Idealist, or on the organization's site or by email, as each listing chooses."),
            ("Account needed to apply", "Not required: \"You don't need to, but we definitely suggest signing up\". Applying through "
                                        "Idealist is quickest when logged in."),
            ("How fresh the listings are", "\"Job listings last for 30 days\"; the organization can hide one sooner."),
            ("Kinds of jobs", "Social-impact work: jobs, internships, volunteer roles and events."),
            ("Payment methods", "US nonprofits and government agencies pay by check or credit card; everyone else by credit card."),
        ),
        them_better=[
            "Built for nonprofit and social-impact work, with volunteer roles and internships that a general job site does not carry.",
            "Running since 1995 and a nonprofit itself, with 200,000+ organizations in 180 countries.",
            "You can apply and keep track on the site itself, with a saved resume.",
        ],
        us_better=[
            "A standard listing is free for 30 days, posted in the employer account. Idealist charges $145 to $195 a job for 30 days.",
            "Every Apply button goes to the employer's own page, with no sign-up suggested. Idealist suggests signing up and is quickest "
            "when you are logged in.",
        ],
        pick="Use Idealist if you want nonprofit, volunteer or social-impact work, use Jobs Every Hour if you want jobs read around the clock "
             "from employers' careers pages with no account.",
        sources=[
            ("[what|Kinds of jobs|them_better 1|them_better 2] \"Idealist is a 501(c)(3) organization based in New York.\"; \"more than "
             "1.2 million jobs and 200,000 internships posted so far\"; \"more than 200,000 organizations in 180 countries\"; began in "
             "1995.", "https://www.idealist.org/en/about", R24),
            ("[Who pays|Price to post one job|Payment methods|How fresh the listings are|us_better 1|pick] \"$145 per job and $25 per "
             "internship\"; consultants and recruiters \"$175 per job\"; businesses \"$195 per Job listing per location\"; \"Listings are "
             "priced for a full 30 days\"; US nonprofits \"can pay by check or credit card\", others \"credit card only\"; volunteer "
             "opportunities and events free.", "https://www.idealist.org/help/how-much-does-it-cost-to-post-listings-on-your-site", R24),
            ("[Price to post one job] \"3 job credits for $375 (save $60)\" for US nonprofits.",
             "https://www.idealist.org/en/help/what-are-job-and-internship-packs-and-how-much-do-they-cost", R24),
            ("[Who pays|Price for job seekers|Account needed to apply|us_better 2] \"Signing up is free.\" \"You don't need to, but we "
             "definitely suggest signing up to get the most out of our site!\"",
             "https://www.idealist.org/en/help/do-i-have-to-sign-up-to-use-idealist", R24),
            ("[Where you apply|Account needed to apply|them_better 3|us_better 2] \"The quickest way to apply to these listings is to Log "
             "in\"; upload a resume, answer questions, \"Submit Application\"; or \"Go to Website\", \"Send Email\".",
             "https://www.idealist.org/en/help/how-do-i-apply-for-opportunities-on-idealist", R24),
            ("[Where the jobs come from|How fresh the listings are] Organizations use \"Post a Listing\"; \"Job listings last for 30 "
             "days\".", "https://www.idealist.org/en/help/how-do-i-post-a-job-listing", R24),
        ],
    ),
]

# 25 Nov 2026: the sites Google's AI answer, ChatGPT and Perplexity name for "best job search sites", "ziprecruiter alternatives" and
# "a job search engine that reads company career pages" that had no page here (SERP_AI_CHECK.md, "/vs/"). Each read that day on its own
# pages in a real browser. theladders.com answers "available only in the United States and Canada" outside them, so Ladders' facts come
# from its own help centre (support.theladders.com). LinkUp showed a human check and is in SKIPPED.
SITES += [
    # ------------------------------------------------------------------ Google for Jobs
    dict(
        slug="google-for-jobs",
        name="Google for Jobs",
        url="https://www.google.com/search?q=jobs+near+me",
        what="Google for Jobs is the job search inside Google Search: a jobs box that shows listings from the pages of employers and job sites "
             "that carry Google's job posting markup. Job listing providers do not pay Google to appear.",
        rows=_rows(
            ("Who pays", "No one pays Google for a place: listing providers \"don't pay Google to appear in job search results and can't pay to "
                         "influence their ranking\"."),
            ("Price to post one job", "Nothing paid to Google. A job can appear when the employer's or job site's own page carries job posting "
                                      "markup, on the same page as the job description."),
            ("Where the jobs come from", "\"Jobs come directly from employers and career sites across the web\", from pages that carry job posting "
                                         "markup."),
            ("Where you apply", "On the site you pick under \"Apply\": the employer's own site or a job site that carries the job. Google does not "
                                "allow job postings with no way to apply."),
            ("Account needed to apply", "Not to search. Signing in to a Google Account only personalizes the results; you apply on the site you "
                                        "pick."),
            ("How fresh the listings are", "A closed job leaves when its site marks it expired or asks Google to remove it. Google says it may take "
                                           "several days to find and crawl a newly published page."),
            ("Kinds of jobs", "Jobs of every kind, found by your search words; the jobs box is not available in all languages or countries."),
        ),
        them_better=[
            "Built into Google Search: one search shows jobs from employers and career sites across the web, with filters and saved jobs.",
            "Listing providers cannot pay to rank higher: results are sorted by relevance.",
            "Job alerts and results shaped by your earlier searches when you are signed in to a Google Account.",
        ],
        us_better=[
            "Every job here is read from the employer's own careers page around the clock and dropped at the next reading once it closes. Google "
            "relies on each site to mark a closed job expired, and says crawling a new page can take several days.",
            "Every Apply button here goes to the employer's own page. On Google, Apply lists the sites that carry the job, job boards included.",
        ],
        pick="Use Google for Jobs if you want one search across employers and job sites everywhere, use Jobs Every Hour if you want jobs read "
             "around the clock from employers' own careers pages and to apply there.",
        sources=[
            ("[what|Who pays|Price to post one job|Where the jobs come from|Where you apply|Account needed to apply|Kinds of jobs|them_better 1|"
             "them_better 2|them_better 3|us_better 2|pick] \"Jobs come directly from employers and career sites across the web.\" \"Job "
             "listing providers don't pay Google to appear in job search results and can't pay to influence their ranking.\" \"By default, job "
             "results are sorted by relevance.\" To see jobs from one site: \"Under \"Apply,\" tap or click a job site.\" Saved jobs; "
             "\"sign up for alerts\"; \"If you're signed in to your Google Account, personalization may also be based on your previous job "
             "searches.\" \"This feature is not available in all languages or countries.\"",
             "https://support.google.com/websearch/answer/7498276?hl=en", R25),
            ("[what|Price to post one job|Where the jobs come from|Where you apply|How fresh the listings are|us_better 1|us_better 2] Job "
             "posting structured data makes postings \"eligible to appear in a special user experience in Google Search results\", for "
             "\"employers and job content site owners\"; \"The structured data must appear on the same page as the job description\". \"We "
             "don't allow job postings that don't have a way to apply.\" Jobs no longer open \"must be expired\": validThrough in the past, or "
             "removal through the Indexing API; \"it may take several days after publishing a page for Google to find and crawl it.\"",
             "https://developers.google.com/search/docs/appearance/structured-data/job-posting", R25),
        ],
    ),
    # ------------------------------------------------------------------ Ladders
    dict(
        slug="ladders",
        name="Ladders",
        url="https://www.theladders.com/",
        what="Ladders is a job site for $100K+ careers in the US and Canada; it says it has over 10 million members and works with 22,000+ "
             "verified recruiters and hiring managers.",
        rows=_rows(
            ("Who pays", "Job seekers, for Premium; a Basic account is free. The help pages we read give no employer prices."),
            ("Price for job seekers", "Basic is free: search, previews of listings and your resume in its database. Premium is paid and renews "
                                      "until auto-renew is turned off; a full refund only within 3 business days if Apply4Me was not used. The "
                                      "help pages we read give no price."),
            ("Where the jobs come from", "Employers post directly on Ladders, and its Job Analysts add jobs with a link to the hiring company's "
                                         "website."),
            ("Where you apply", "Three ways: Apply4Me (Premium: its team fills in the company's application for you), Easy Apply (your resume "
                                "goes to the recruiter on Ladders) or Apply Manually on the employer's original posting."),
            ("Account needed to apply", "Yes: Basic members see previews, and \"Full job details and application access are available with "
                                        "Premium.\""),
            ("Kinds of jobs", "Full-time professional jobs with a base salary of at least $80K, all in the US or Canada."),
        ),
        them_better=[
            "Apply4Me on Premium: its team fills in job applications for you, 50 to 75 a month by plan, with a browser extension for other "
            "job sites.",
            "Every job pays a base salary of at least $80K, and 22,000+ verified recruiters can search the resumes in its database.",
            "Free tools for all members: resume review, an ATS resume scan, company search and salary search.",
        ],
        us_better=[
            "Full job details and applying are free here, with no account. Ladders shows Basic members previews; full details and applying need "
            "Premium.",
            "Plus here is one payment that never renews (not on sale yet). Ladders Premium renews until auto-renew is turned off, with a refund "
            "only within 3 business days.",
            "Every job here names its employer and is read from its own careers page around the clock. Ladders lists some jobs with the company name "
            "hidden.",
        ],
        pick="Use Ladders if you want $80K-plus roles only and will pay for Premium and Apply4Me, use Jobs Every Hour if you want full job "
             "details and to apply on the employer's own page for free.",
        sources=[
            ("[what|them_better 2|them_better 3] \"Ladders is the leader in $100K+ careers, helping over 10 million members connect with "
             "high-paying opportunities.\" \"We work with 22,000+ verified recruiters and hiring managers who are focused on sourcing "
             "high-level talent across the U.S. and Canada.\" Members can use a \"free resume review\" and an \"ATS resume scan\"; company "
             "search, job compensation search and salary insights.",
             "https://support.theladders.com/en_us/how-is-ladders-different-than-other-career-sites-rky5IyFgxl", R25),
            ("[Who pays|Price for job seekers|Account needed to apply|them_better 3|us_better 1|pick] \"A Basic membership with Ladders is "
             "completely free.\" \"View previews of job listings during your search. Full job details and application access are available "
             "with Premium.\" Your resume goes to a database \"searchable by 22,000+ verified recruiters\". Free for all members: Resume "
             "Review, ATS Resume Scan, Company Search, Job Salary Search.",
             "https://support.theladders.com/en_us/what-is-basic-membership-rygUkFxex", R25),
            ("[Who pays|Price for job seekers|them_better 1|pick] Premium gives \"unlimited access to our curated 100k+ jobs database\". "
             "Apply4Me: \"our expert team completes your application for you\", 50 credits on a 1-month plan, 60 on 3 months, 65 on 6 months, "
             "75 on 12 months, and \"a browser extension that allows you to use this tool on other job sites\". The article names no price.",
             "https://support.theladders.com/en_us/what-is-premium-membership-H1mlLyYgll", R25),
            ("[Price for job seekers|us_better 2] Turning off auto-renew \"ensures you will not be charged again\"; fees are \"non-refundable\" "
             "except a \"3-Day Refund Period\" (full refund within 3 business days if Apply4Me was not used) and a 7-day switch for longer "
             "plans.", "https://support.theladders.com/en_us/what-is-your-cancellation-policy-HknJLytxel", R25),
            ("[what|Where the jobs come from|Kinds of jobs|them_better 2|pick] \"Ladders posts full-time, professional positions on our site "
             "with a base salary of at least $80K\", \"all located within the United States or Canada\". \"We have employers who post new "
             "opportunities with Ladders directly on our site. We also have a team of Job Analysts who bring jobs to you with a link to the "
             "hiring company's website.\"",
             "https://support.theladders.com/en_us/what-kinds-of-jobs-are-posted-on-ladders-BydQI1Yxgl", R25),
            ("[Where you apply|them_better 1] Three options: Apply4Me (\"our team will submit the application on your behalf\"), Easy Apply "
             "(\"send your resume directly to the recruiter or job poster on Ladders\") and Apply Manually (\"redirect you to the employer's "
             "original job posting\").", "https://support.theladders.com/en_us/how-do-i-apply-to-a-job-on-ladders-rkFapgLMll", R25),
            ("[us_better 3] \"You may come across job listings on Ladders where the company name is not displayed.\"",
             "https://support.theladders.com/en_us/why-are-some-companies-listed-as-confidential-on-ladders-BJ_tkLMxe", R25),
        ],
    ),
    # ------------------------------------------------------------------ Craigslist
    dict(
        slug="craigslist",
        name="Craigslist",
        url="https://www.craigslist.org/",
        what="Craigslist is a site of local classifieds; jobs is one of its posting types, beside community, services, housing, for sale, gigs "
             "and resumes. A job posting costs $10 to $75 in the US, by area.",
        rows=_rows(
            ("Who pays", "Employers, a one-time fee for each job posting. Craigslist says it has no subscription fees."),
            ("Price to post one job", "$10 to $75 in the US, by area ($0 to $75 in Canada), one time. A paid posting is live 30 days; a repost is a "
                                      "new paid posting."),
            ("Where the jobs come from", "Posters create them on the craigslist site of their area (\"create a posting\"); a posting appears about "
                                         "15 minutes after it is confirmed."),
            ("Where you apply", "You reply to the posting by the contact the poster chose: email through a craigslist relay address, phone or "
                                "text, or chat."),
            ("How fresh the listings are", "Paid postings are live for 30 days; all postings move down the list as new ones are published."),
            ("Kinds of jobs", "Local jobs and gigs, searched by place."),
            ("Payment methods", "Visa, Mastercard and American Express, paid when the posting is created."),
        ),
        them_better=[
            "Local jobs and short gigs ($3 to $10 to post) in one place, searched by place.",
            "Replies go through a relay address craigslist creates for each posting, so the poster's email stays hidden.",
            "Employers can pay and post today, with a one-time fee and no subscription.",
        ],
        us_better=[
            "A standard listing is free for 30 days here, posted in the employer account. A craigslist job posting costs $10 to $75 in the US, "
            "by area.",
            "Every job here is read from the employer's own careers page around the clock, and you apply on the employer's own page. On craigslist you "
            "reply to a posting by email, phone or chat.",
        ],
        pick="Use Craigslist if you want local jobs and gigs near you, use Jobs Every Hour if you want jobs read around the clock from employers' own "
             "careers pages and to apply there.",
        sources=[
            ("[what|Kinds of jobs] \"craigslist currently offers the following types of postings: community, services, housing, for sale, jobs, "
             "gigs, and resumes.\"", "https://www.craigslist.org/about/help/posting/features/type", R25),
            ("[what|Who pays|Price to post one job|Payment methods|them_better 1|them_better 3|us_better 1|pick] US: \"Job postings $10-75\", "
             "\"Gigs $3-10\"; Canada: \"Job postings $0-75\". \"Fees vary depending on geographic location.\" \"Publishing your posting is a one "
             "time charge. craigslist does not have any subscription fees, or additional charges.\" \"You can only pay for a posting via our "
             "website or mobile app at the time that the posting is created.\"", "https://www.craigslist.org/about/help/faqs/fees", R25),
            ("[Price to post one job|Payment methods] \"Job categories in US and parts of CA —$10-75 (fee varies by area)\"; \"Visa, MasterCard, "
             "and American Express are accepted.\"", "https://www.craigslist.org/about/help/posting_fees", R25),
            ("[Price to post one job|How fresh the listings are|us_better 1] \"Paid postings are live on the site for 30 days.\" \"All postings "
             "move down the listings as new postings are published.\"", "https://www.craigslist.org/about/help/faqs/lifespan", R25),
            ("[Price to post one job] \"There are no free reposts for paid postings. A repost is a new posting and must be paid for.\"",
             "https://www.craigslist.org/about/help/posting/modify/repost", R25),
            ("[Where the jobs come from] Choose the geographic location, click \"create a posting\", pick a type and category, publish; \"Paid "
             "postings will show their price and require payment.\" \"Your posting should appear on craigslist about 15 minutes after "
             "confirmation.\"", "https://www.craigslist.org/about/help/posting/create", R25),
            ("[Where you apply|us_better 2|pick] The \"contact info\" box lets the poster choose \"how you would like to interact with other "
             "craigslist users\": email and CL mail relay, phone/text, or chat.",
             "https://www.craigslist.org/about/help/posting/features/contact-info", R25),
            ("[Where you apply|them_better 2] \"craigslist creates a randomized custom email address for each posting.\"",
             "https://www.craigslist.org/about/help/posting/features/contact-info/email/mail-relay", R25),
            ("[Kinds of jobs|them_better 1|pick] \"You can search on craigslist using both text and categories. Results are based up location.\"",
             "https://www.craigslist.org/about/help/searching/how-to-search", R25),
        ],
    ),
    # ------------------------------------------------------------------ Levels.fyi
    dict(
        slug="levels-fyi",
        name="Levels.fyi",
        url="https://www.levels.fyi/",
        what="Levels.fyi is a pay data site, started in 2017, that shows what work pays by company, level and location; its job board lists open "
             "jobs beside its pay estimates. It says more than 3 million professionals use it each month.",
        rows=_rows(
            ("Who pays", "Employers, for pay data (plans from $800 a month), branding and its Talent Pool; job seekers only for optional coaching. "
                         "The job board and salary data are free."),
            ("Price for job seekers", "Free to search jobs and salaries. Paid help: negotiation coaching from $1,500, with a guaranteed raise or "
                                      "a full refund, and resume review."),
            ("Price to post one job", "Free: its jobs page offers \"Create a free Job Post\". Promoted listings are part of its paid employer "
                                      "branding."),
            ("Where you apply", "Off the site: on the two jobs we opened, \"Apply Now\" led to the job's posting on LinkedIn."),
            ("Account needed to apply", "Not on Levels.fyi: its job pages and Apply Now links opened without signing in."),
            ("How fresh the listings are", "Each listing shows its age; the pages we read showed jobs posted from 2 days to 7 months earlier."),
            ("Kinds of jobs", "245,483 jobs at 10,000 hiring companies on its jobs page, with pay estimates; it began with tech and now covers "
                              "100+ roles."),
        ),
        them_better=[
            "Pay data by company and level: more than 1 million salaries shared, and a pay estimate beside each job.",
            "Paid negotiation coaching with a guaranteed raise in year-one pay or a full refund (from $1,500).",
            "Its Talent Pool lets companies come to you with the role and the pay upfront.",
        ],
        us_better=[
            "Every job here is read from the employer's own careers page around the clock and dropped when it closes. The Levels.fyi pages we read "
            "showed listings up to 7 months old.",
            "Every Apply button here goes to the employer's own page. On the Levels.fyi jobs we opened, Apply Now led to a LinkedIn posting.",
        ],
        pick="Use Levels.fyi if you want pay data by level beside each job, use Jobs Every Hour if you want jobs read around the clock from employers' "
             "careers pages and to apply on the employer's own page.",
        sources=[
            ("[what|Who pays|Price for job seekers|Kinds of jobs|them_better 1|them_better 2|them_better 3|pick] \"Levels.fyi is a compensation "
             "data platform that shows what work pays at every company, level, and location\"; started in 2017; \"more than 3 million "
             "professionals use Levels.fyi each month\"; \"we now cover more than 100 roles\". Under \"FREE FOR EVERYONE\": salary data "
             "(\"more than 1 million salaries\") and the job board (\"open jobs alongside our total compensation estimates by level\"; \"join "
             "the Talent Pool and let companies come to you with the role and pay upfront\"). Coaching: \"Packages start at $1,500, with a "
             "guaranteed increase in year-one total compensation.\" Pay data for employers: \"Plans start at $800 a month.\"",
             "https://www.levels.fyi/about", R25),
            ("[Price for job seekers|them_better 2] Negotiation packages $1,500 (Standard, Startup), $2,450 (Premium), $5,000 (Leadership); \"If "
             "we don't raise your offer by the guaranteed amount, we refund your entire coaching fee\".", "https://www.levels.fyi/services/", R25),
            ("[Price to post one job|How fresh the listings are|Kinds of jobs|us_better 1] \"10,000 companies hiring\", \"245,483 total jobs\"; "
             "\"Create a free Job Post\"; listings marked \"Promoted\" link to its employer branding page; ages from \"2 days ago\" to \"5 "
             "months ago\" on the first page, and \"7 months ago\" in a search for software engineer.", "https://www.levels.fyi/jobs", R25),
            ("[Who pays|Price to post one job] For employers: Talent Branding (\"Put your company in front of the 1 in 10 US tech professionals "
             "who visit each month\"), Talent Pool and pay data; no prices on the page.", "https://www.levels.fyi/offerings/", R25),
            ("[Where you apply|Account needed to apply|us_better 1|us_better 2|pick] Job pages opened without signing in: \"Software Engineer, "
             "Growth\" at Slash (\"7 months ago\") and \"Software Engineer\" at Apple; on both, \"Apply Now\" links to the job on "
             "linkedin.com.", "https://www.levels.fyi/jobs?jobId=03cds6p5s2sbf", R25),
        ],
    ),
    # ------------------------------------------------------------------ GovernmentJobs.com
    dict(
        slug="governmentjobs",
        name="GovernmentJobs.com",
        url="https://www.governmentjobs.com/",
        what="GovernmentJobs.com is a job site for public-sector jobs run by NEOGOV (Governmentjobs.com, Inc.); it says millions of job seekers "
             "apply there to jobs from 2,000+ agencies nationwide.",
        rows=_rows(
            ("Who pays", "Government agencies, which buy NEOGOV's services on an annual basis to post their jobs. Its Access Membership for "
                         "job seekers is free."),
            ("Price for job seekers", "Free: one free profile to apply, and an Access Membership that \"will be free forever\"."),
            ("Price to post one job", "No price is published: agencies buy its services on an annual basis."),
            ("Where the jobs come from", "Federal, state, local, tribal and other government agencies post their own openings through NEOGOV's "
                                         "services."),
            ("Where you apply", "On GovernmentJobs.com: press Apply, fill in the steps each employer sets, then certify and submit."),
            ("Account needed to apply", "Yes: its application guide starts with creating an account (email and password, or Google)."),
            ("Kinds of jobs", "Government and public-sector jobs from 2,000+ agencies across the US."),
        ),
        them_better=[
            "Public-sector jobs from 2,000+ agencies, with one profile to apply to many of them.",
            "A free Access Membership: agencies can find your resume and contact you, and SalaryChecker compares public-sector pay across "
            "agencies.",
            "You follow the status of each application and schedule appointments in your account.",
        ],
        us_better=[
            "No account needed to search or apply here. GovernmentJobs.com's application guide starts with creating an account.",
            "Jobs from thousands of companies' own careers pages, read around the clock. GovernmentJobs.com lists public-sector jobs.",
        ],
        pick="Use GovernmentJobs.com if you want a public-sector job, use Jobs Every Hour if you want jobs at companies, searched and applied for "
             "with no account.",
        sources=[
            ("[what|Price for job seekers|Kinds of jobs|them_better 1] \"Join millions of job seekers applying to jobs from 2,000+ agencies "
             "nationwide.\" \"Create one free profile and get matched to government jobs faster.\" \"Create your government resume once and "
             "apply to thousands of public sector jobs nationwide in just a few clicks.\" Footer: \"Powered by NEOGOV\".",
             "https://www.governmentjobs.com/", R25),
            ("[what|Who pays|Price to post one job|Where the jobs come from|us_better 2|pick] \"This website is owned and operated by "
             "Governmentjobs.com, Inc. (DBA \"NEOGOV\").\" \"Our Customers are organizations such as federal, state, local, tribal, or other "
             "municipal government agencies\"; \"Our Customers use our Services to post job opportunities\"; \"the Services you purchase are "
             "offered on an annual basis\".", "https://www.governmentjobs.com/home/companyinfo", R25),
            ("[Who pays|Price for job seekers|them_better 2] \"Membership is FREE\"; \"Your Access Membership will be free forever.\" Make your "
             "resume searchable by employers, get contacted by employers, and \"SalaryChecker, a tool that compares wages for public sector "
             "positions at different agencies\".", "https://www.governmentjobs.com/AccessMembership", R25),
            ("[Where you apply|Account needed to apply|them_better 3|us_better 1|pick] \"This guide describes how to apply for jobs using the "
             "Government Jobs website.\" First step \"Create a New Account\": \"Select SIGN UP. Enter an email and password\", or \"Continue "
             "with Google\". To apply: \"Select APPLY\"; \"The specific steps that you must complete are determined by the employer\"; "
             "\"Proceed to Certify and Submit\". Also Check Application Status and Schedule an Appointment.",
             "https://www.governmentjobs.com/home/applicationguide", R25),
        ],
    ),
    # ------------------------------------------------------------------ HiringCafe
    dict(
        slug="hiringcafe",
        name="HiringCafe",
        url="https://hiringcafe.com/",
        what="HiringCafe is a free job search engine run by SPICYHR INC. that says it collects jobs directly from company websites in real time; "
             "its home page states over 5 million open jobs.",
        rows=_rows(
            ("Who pays", "No one, by its pages: \"Our product is free.\" It says that once people love it, \"we can deliver value for "
                         "employers, too\"."),
            ("Price for job seekers", "Free: job seekers \"search jobs, use filters, save searches, build boards, and explore opportunities "
                                      "without paying\"."),
            ("Price to post one job", "No price is shown: an \"Add jobs\" form and an \"Employers\" contact form."),
            ("Where the jobs come from", "\"We collect jobs directly from company websites in real time and filter out external recruiting "
                                         "agencies and fake consulting firms.\""),
            ("Where you apply", "On the employer's site: the job page's Apply button reads \"Apply directly on employer's site\"."),
            ("Account needed to apply", "Not to open a job and its Apply button: the job page we opened showed both without signing in."),
            ("How fresh the listings are", "\"In real time\", it says, with systems that detect stale postings and duplicate roles; no reading "
                                           "interval is stated."),
            ("Kinds of jobs", "Jobs of every kind, \"over 5 million open jobs\", with filters for pay, benefits, licenses, security clearance, "
                              "shifts, company stage and size."),
        ),
        them_better=[
            "Far larger: it states over 5 million open jobs.",
            "Many more filters (pay, benefits, clearance, shifts, company stage and size) and a Talent Agent that looks for jobs for you every "
            "day.",
            "A job tracker with saved searches and boards, and a 100K+ member Reddit community.",
        ],
        us_better=[
            "A standard listing is free for 30 days in an employer account here. HiringCafe has only an \"Add jobs\" form and an employer "
            "contact form, with no price.",
            "Each job here is read again from the employer's careers page around the clock, and a closed job keeps its page, marked closed. "
            "HiringCafe says \"in real time\" and states no reading interval.",
        ],
        pick="Use HiringCafe if you want the largest search of jobs from company websites with many filters, use Jobs Every Hour if you want each "
             "job read around the clock from employers' careers pages and closed jobs marked as closed.",
        sources=[
            ("[what|Who pays|Price for job seekers|Where the jobs come from|How fresh the listings are|them_better 2|them_better 3|us_better 2|"
             "pick] \"We collect jobs directly from company websites in real time and filter out external recruiting agencies and fake "
             "consulting firms.\" FAQ: \"Job seekers can search jobs, use filters, save searches, build boards, and explore opportunities "
             "without paying to access the core search experience.\" \"We keep improving systems that detect stale postings, duplicate "
             "roles\". \"Our product is free.\" \"we believe that once people fall in love with our product, we can deliver value for "
             "employers, too.\" The Talent Agent \"finds the most relevant jobs for you every day\"; \"100K+ member Reddit community\"; "
             "\"HiringCafe, operated by SPICYHR INC.\"", "https://hiringcafe.com/about", R25),
            ("[what|Price to post one job|Kinds of jobs|them_better 1|them_better 2|them_better 3|us_better 1] \"HiringCafe has over 5 million "
             "open jobs\"; filters for salary, benefits and perks, licenses and certifications, security clearance, shifts and schedules, stage "
             "and funding, size; links \"Add jobs\" (a form) and \"Employers\" (a contact form); \"Tracker\".", "https://hiringcafe.com/", R25),
            ("[Where you apply|Account needed to apply] A job page opened without signing in shows \"Apply\", labelled \"Apply directly on "
             "employer's site\".", "https://hiringcafe.com/job/account-manager-hanoi-booking-com-hanoi-hanoi-ub93wlrsabpkd46d", R25),
        ],
    ),
    # ------------------------------------------------------------------ SecretJobs (Google's first result for "job search engine that pulls
    # jobs directly from company career pages", 25 Nov 2026; read on its home page and its questions that day)
    dict(
        slug="secretjobs",
        name="SecretJobs",
        url="https://www.secretjobs.ai/",
        what="SecretJobs is a job search site that says it pulls jobs straight from the career pages of 400,000+ companies every hour, 8M+ "
             "open jobs, and sells an AI plan that tailors resumes and applies for you.",
        rows=_rows(
            ("Who pays", "Job seekers, for the AI plan. \"Searching every job, saving and tracking are free.\""),
            ("Price for job seekers", "Free to search, save and track. The AI plan is paid and renews until cancelled; its price is not on the home "
                                      "page."),
            ("Where the jobs come from", "\"directly from companies' own career pages and applicant-tracking systems\": 400,000+ companies."),
            ("Where you apply", "On the company's application page; on the AI plan, \"Apply for me\" fills in the form and sends it."),
            ("How fresh the listings are", "\"We re-scan 400,000+ company career pages every hour\"; when a company takes a job down, \"it disappears "
                                           "from SecretJobs too\"."),
            ("Kinds of jobs", "8M+ open jobs worldwide, deepest in the US, UK, Canada, Australia and Israel, plus remote roles."),
        ),
        them_better=[
            "Far larger: 8M+ open jobs from 400,000+ employers, read every hour.",
            "A paid AI plan tailors your resume to each job, applies for you when you press Apply for me, and preps you for each company's "
            "interviews.",
            "Private by design: employers never see who views or saves their jobs, and recruiters contact you only if you say yes.",
        ],
        us_better=[
            "A closed job keeps its page here, marked closed, so a saved link still says what happened. On SecretJobs a job taken down "
            "disappears.",
            "Plus here is one payment that never renews (not on sale yet). SecretJobs' AI plan renews until it is cancelled.",
        ],
        pick="Use SecretJobs if you want the largest search of career-page jobs and will pay for AI that applies for you, use Jobs Every Hour if "
             "you want closed jobs kept and marked, and nothing that renews.",
        sources=[
            ("[what|Who pays|Price for job seekers|Where the jobs come from|Where you apply|How fresh the listings are|Kinds of jobs|"
             "them_better 1|them_better 2|them_better 3|us_better 1|us_better 2|pick] \"8M+ open jobs · 400,000+ employers\", \"Updated every "
             "hour\". Questions: \"We pull openings directly from companies' own career pages and applicant-tracking systems\"; \"Searching "
             "every job, saving and tracking are free. The AI plan, which tailors your résumé, applies for you and preps you for interviews, is "
             "paid.\" \"We re-scan 400,000+ company career pages every hour\"; \"deepest coverage in the US, UK, Canada, Australia and "
             "Israel, plus remote roles\"; \"It applies to a job when you press Apply for me on it\"; \"When a company takes a job down, it "
             "disappears from SecretJobs too\"; \"Cancel in a click and you won't be charged again, and we remind you before every renewal.\" "
             "\"Employers never see who's looking at their jobs\"; \"Recruiters can contact you only if you say yes.\"",
             "https://www.secretjobs.ai/", R25),
        ],
    ),
    # ------------------------------------------------------------------ Drivetube
    dict(
        slug="drivetube",
        name="Drivetube",
        url="https://drivetube.ai/",
        what="Drivetube is a job search site run by Drivetube AI (India and the US) with a free job board read from 160,000+ company career "
             "pages, beside paid resume writing and application services.",
        rows=_rows(
            ("Who pays", "No one, for the job board: it is free. Job seekers pay only for optional services (community membership, resume "
                         "writing, a managed application program)."),
            ("Price for job seekers", "The job board is free with no account. Community membership from $39.99 for 3 months; resume writing "
                                      "from $25.99, up to $179.99."),
            ("Price to post one job", "No job posts: employers use Drivetube Hire, which matches a job description with candidates' resumes, "
                                      "\"no job postings, no applications\"."),
            ("Where the jobs come from", "\"aggregated ATS-by-ATS directly from 160,000+ real company career pages across 50+ ATS platforms\"."),
            ("Where you apply", "\"Every listing links to the company's real application page.\""),
            ("Account needed to apply", "No: \"Free, no account required\"."),
            ("How fresh the listings are", "\"Only roles posted in the last 3 days.\""),
            ("Kinds of jobs", "Jobs in the US, UK, Canada, Australia, India and Europe, with visa-sponsorship filters for members."),
        ),
        them_better=[
            "It reads more career pages: 160,000+ across 50+ hiring systems, in the US, UK, Canada, Australia, India and Europe.",
            "Paid help beside the free board: human resume writing from $25.99 and a managed program that tailors and fills in applications.",
            "A free online resume profile that verified employers can find and send interview requests to.",
        ],
        us_better=[
            "A job stays here for as long as the employer keeps it open, read around the clock. Drivetube shows only roles posted in the last 3 days, "
            "so an opening that is older and still open is not there.",
            "Employers can post a standard listing free for 30 days here. Drivetube takes no job posts.",
        ],
        pick="Use Drivetube if you only want jobs posted in the last 3 days, from several countries, use Jobs Every Hour if you want every open "
             "job on employers' careers pages, however long it has been open, read around the clock.",
        sources=[
            ("[what|Who pays|Price for job seekers|Price to post one job|Where the jobs come from|Where you apply|Account needed to apply|How "
             "fresh the listings are|Kinds of jobs|them_better 1|them_better 2|them_better 3|us_better 1|us_better 2|pick] \"a free verified "
             "job board built from 160,000+ real company career pages\"; \"Verified job openings aggregated ATS-by-ATS directly from 160,000+ "
             "real company career pages across 50+ ATS platforms\"; \"Only roles posted in the last 3 days.\" \"Every listing links to the "
             "company's real application page\"; \"Covers the US, UK, Canada, Australia, India and Europe\"; \"Free, no account required\". "
             "Drivetube Profile: \"Verified employers can discover the profile and send interview requests\". Community membership with "
             "visa-sponsorship filters \"From $39.99 for 3 months\"; resume writing \"From ₹499.99 in India / $25.99 elsewhere, up to ₹15,999 "
             "/ $179.99\"; Job Hunt Program with tailored resumes and autofill. Employers: Drivetube Hire, \"no job postings, no "
             "applications\". Operated by Drivetube AI Private Limited (India) and Drivetube AI, LLC (US/Delaware).",
             "https://drivetube.ai/docs/overview", R25),
        ],
    ),
    # ------------------------------------------------------------------ Jobright
    dict(
        slug="jobright",
        name="Jobright",
        url="https://jobright.ai/",
        what="Jobright is an AI job search tool from Santa Clara, California, launched in 2023, that matches US jobs to your resume, tailors "
             "resumes and fills in applications; its home page states 8,000,000+ jobs.",
        rows=_rows(
            ("Who pays", "Job seekers, for Premium (the basic service is free); employers, $499 a month per active role for its AI recruiter."),
            ("Price for job seekers", "A free basic service; Premium was \"$30/month\" by its own blog in June 2025. jobright.ai/pricing was "
                                      "not found."),
            ("Price to post one job", "No job posts: employers pay $499 a month per active role for an AI recruiter that finds and contacts "
                                      "candidates; one role can be tried free."),
            ("Where the jobs come from", "\"aggregated from LinkedIn, Indeed, company career pages, and more\"; its remote jobs page says "
                                         "\"major job boards and 200K+ company career sites\"."),
            ("Where you apply", "On the employer's site (\"Apply on Employer Site\"), or with its autofill (\"Apply With Autofill\")."),
            ("Account needed to apply", "Yes: pressing Apply Now on a job page showed \"Sign Up to Apply\"."),
            ("How fresh the listings are", "Its remote jobs page says \"Updated hourly\"; it says about 400,000 new listings are added every day."),
            ("Kinds of jobs", "US jobs of every kind, \"Over 8 million live job postings\", with an H-1B filter."),
        ),
        them_better=[
            "Far larger: its home page states 8,000,000+ jobs and 400,000+ new ones a day.",
            "AI tools: a resume tailored to each job, autofill of applications on hiring systems, insider connections and a career coach chat.",
            "An H-1B filter for jobs likely to sponsor a visa.",
        ],
        us_better=[
            "No account needed to apply: every Apply button goes to the employer's own page. On Jobright, Apply Now asks you to sign up.",
            "Every job here comes from the employer's own careers page. Jobright also takes listings from LinkedIn, Indeed and other job boards.",
            "Free for job seekers, with nothing to renew. Jobright's Premium was $30 a month in June 2025, by its own blog.",
        ],
        pick="Use Jobright if you want AI to match, tailor and fill in applications across millions of US jobs, use Jobs Every Hour if you want "
             "jobs from employers' own careers pages, free and with no account.",
        sources=[
            ("[what|Kinds of jobs|them_better 1|them_better 2] \"Total Jobs 8,000,000+\", \"Today's New Jobs 400,000+\", \"3,000,000 trusted "
             "users\"; \"Get matched jobs, autofill applications, tailored resume, and recommended insider connections\"; \"Sign up for "
             "free\".", "https://jobright.ai/", R25),
            ("[what|Who pays|Price for job seekers|Where the jobs come from|How fresh the listings are|Kinds of jobs|them_better 2|them_better 3|"
             "us_better 2|us_better 3|pick] Its own post \"Is Jobright Legit?\" (18 June 2025): launched in 2023, based in Santa Clara, "
             "California; \"Over 8 million live job postings currently and ~400,000 fresh listings added every day, aggregated from LinkedIn, "
             "Indeed, company career pages, and more.\" \"Our basic service is free, and many members upgrade to our Premium plans "
             "($30/month)\". \"Jobright focuses on the U.S. market—complete with an H‑1B visa job filter\". Autofill on \"thousands of ATS "
             "platforms\"; Orion, a 24/7 chat coach; insider connections.", "https://jobright.ai/blog/is-jobright-legit/", R25),
            ("[Where the jobs come from|How fresh the listings are] \"Top U.S. 100% Remote Jobs (Updated Hourly)\"; \"Updated hourly from major "
             "job boards and 200K+ company career sites.\"", "https://jobright.ai/remote-jobs", R25),
            ("[Where you apply|Account needed to apply|us_better 1|pick] A job page shows \"Apply on Employer Site\", \"APPLY NOW\" and \"Apply "
             "With Autofill\"; pressing APPLY NOW showed \"Sign Up to Apply\".", "https://jobright.ai/jobs/info/6b06f4902662686ad8e05974", R25),
            ("[Who pays|Price to post one job] \"One flat monthly price per active role\": \"Jobright $499\"; \"Try your AI recruiter free\", "
             "\"One role per trial\".", "https://jobright.ai/employers/pricing", R25),
            ("[Price for job seekers] jobright.ai/pricing answered \"Page Not Found\".", "https://jobright.ai/pricing", R25),
        ],
    ),
    # ------------------------------------------------------------------ Jobscan
    dict(
        slug="jobscan",
        name="Jobscan",
        url="https://www.jobscan.co/",
        what="Jobscan is a resume scanner that compares your resume with a job posting and shows the missing keywords; it also matches jobs to "
             "your resume from Greenhouse, Lever, Workable and 20+ other hiring systems.",
        rows=_rows(
            ("Who pays", "Job seekers, for Premium. The free plan includes 5 resume scans a month."),
            ("Price for job seekers", "Free plan with 5 resume scans a month. Premium: $49.95 a month, or $89.95 every 3 months after a 7-day free "
                                      "trial. Auto Apply credits cost extra, from $1.40 each."),
            ("Where the jobs come from", "Its job matches come \"from Greenhouse, Lever, Workable, and 20+ ATS platforms\"."),
            ("Where you apply", "On the company's site, or with Auto Apply, which fills in the application and sends it after you approve it."),
            ("Account needed to apply", "Yes, for its job matches: \"Sign up free to find jobs based on your resume\"; Premium unlocks every Top "
                                        "Match job."),
            ("Payment methods", "\"any major credit card\", plus state and local sales tax."),
        ),
        them_better=[
            "A full resume scanner: a match rate for each job, ATS and recruiter findings, AI rewriting and a LinkedIn optimizer (most on "
            "Premium).",
            "Auto Apply drafts each application from your resume and sends it only after you approve it (credits from $1.40).",
            "A job tracker and a Chrome extension that saves jobs from other job boards.",
        ],
        us_better=[
            "The resume match check here is free, with no limit and no account. Jobscan's free plan has 5 scans a month; unlimited scans cost "
            "$49.95 a month.",
            "You see and open every job here with no account. Jobscan's job matches need a sign-up, and Premium unlocks every Top Match job.",
            "Plus here is one payment that never renews (not on sale yet). Jobscan Premium bills every month or every 3 months until cancelled.",
        ],
        pick="Use Jobscan if you want AI rewriting and a match rate for each job you apply to, use Jobs Every Hour if you want a free, unlimited "
             "resume check and jobs from careers pages with no account.",
        sources=[
            ("[what|Who pays|Price for job seekers|Payment methods|them_better 1|us_better 1|us_better 3|pick] Free \"$0 forever\": \"5 Free "
             "Resume Scans monthly\", Job Tracker, Resume Builder, Chrome Extension. Quarterly \"$29.98 per month\", \"Billed as $89.95 every 3 "
             "months\", \"Try 7 Days Free\"; Monthly \"$49.95 per month\". Premium: \"Unlimited Resume Scans\", \"Unlimited AI "
             "Optimizations\", \"Linkedin Optimizer\", \"AI Job Match\", \"2 free Auto Apply Credits a month\". \"You can purchase Jobscan with "
             "any major credit card.\" Sales tax by billing address. \"You may cancel at any time\".", "https://app.jobscan.co/plan", R25),
            ("[what|Where you apply|Account needed to apply|them_better 3|us_better 2|pick] AI Job Match: \"Upload your resume to find jobs "
             "that fit your skills\"; \"apply on the company's site\"; \"AI Job Match is free to start. Sign up free to find jobs based on your "
             "resume, and use the Job Tracker and the Chrome extension. Premium unlocks every Top Match job\"; \"Save from your matches or from "
             "job boards with the Chrome extension.\" \"Trusted by 10M+ job seekers since 2013\".", "https://www.jobscan.co/job-search", R25),
            ("[what|Price for job seekers|Where the jobs come from|Where you apply|them_better 2] \"Auto Apply currently matches you with jobs "
             "from Greenhouse, Lever, Workable, and 20+ ATS platforms\"; \"Nothing is sent until you approve it\"; credits: 5 for $8.50, 10 for "
             "$15.00, 25 for $35.00 ($1.40 a credit); Premium users get 2 a month.", "https://www.jobscan.co/auto-apply", R25),
            ("[what|them_better 1] \"Jobscan checks your resume against the specific system screening it, shows you the keywords and skills you "
             "are missing\"; \"We recommend a match rate score of 75%. However, many career counselors and Jobscan users see success even with "
             "just a 65% match rate.\"", "https://www.jobscan.co/", R25),
        ],
    ),
]

# The kind of each site, for the "alternatives" pages (similar sites first) and the chips of the comparison tool. Our own label, not a
# fact about the site: each one is backed by the site's "Kinds of jobs" or "what" above, or its own name (Remote OK, We Work Remotely).
KINDS = {"general": "General job sites", "engine": "Job search engines", "ai": "AI job search and resume tools", "tech": "Tech and startup jobs", "remote": "Remote jobs",
         "students": "Students and new graduates", "hourly": "Hourly and shift jobs", "government": "Government jobs",
         "nonprofit": "Nonprofit jobs", "crypto": "Crypto and web3 jobs"}
KIND = {"indeed": "general", "linkedin-jobs": "general", "ziprecruiter": "general", "glassdoor": "general", "welcome-to-the-jungle": "general",
        "simplyhired": "engine", "jooble": "engine", "talent-com": "engine",
        "dice": "tech", "built-in": "tech", "wellfound": "tech",
        "we-work-remotely": "remote", "remote-ok": "remote", "flexjobs": "remote", "remotive": "remote", "himalayas": "remote",
        "remote-co": "remote", "working-nomads": "remote",
        "handshake": "students", "snagajob": "hourly", "usajobs": "government", "idealist": "nonprofit",
        "cryptojobslist": "crypto", "web3-career": "crypto",
        # 25 Nov 2026
        "google-for-jobs": "engine", "hiringcafe": "engine", "drivetube": "engine", "ladders": "general", "craigslist": "hourly",
        "levels-fyi": "tech", "governmentjobs": "government", "jobright": "ai", "jobscan": "ai", "secretjobs": "engine"}
OUR_KIND = "engine"          # we read employers' careers pages and drop closed jobs: a job search engine, shown with the others of that kind
# The sites people compare most; a pair with one of them is built for every other site (see pairs()).
BIG = ("indeed", "linkedin-jobs", "ziprecruiter", "glassdoor")
# The first eight sites, compared pairwise since 14 Nov 2026: their pair pages stay, whatever pairs() decides for the rest.
FIRST8 = ("indeed", "linkedin-jobs", "wellfound", "we-work-remotely", "remote-ok", "flexjobs", "cryptojobslist", "web3-career")
_ORDER = list(KIND)          # keeps the first eight in their old order, so the addresses of their pair pages do not change
SITES.sort(key=lambda s: _ORDER.index(s["slug"]))
for _s in SITES:
    _s["kind"] = KIND[_s["slug"]]


def pairs(sites):
    """Pairs of sites worth a page of their own: the ones people search ("indeed vs ziprecruiter", "glassdoor vs indeed",
    "remotive vs we work remotely"). Two sites of the same kind, any site with one of the four big ones, and the first eight with each
    other (their pages are live since 14 Nov). Crypto boards are paired only with each other and with the first eight. Order follows
    SITES, so a pair's address is stable."""
    out = []
    for i, a in enumerate(sites):
        for b in sites[i + 1:]:
            same = a["kind"] == b["kind"]
            big = (a["slug"] in BIG or b["slug"] in BIG) and not {"crypto", "ai"} & {a["kind"], b["kind"]}     # "Indeed vs Jobscan" is no search
            first = a["slug"] in FIRST8 and b["slug"] in FIRST8
            if same or big or first:
                out.append((a, b))
    return out


# Job sites asked for on 24 Nov 2026 that have no page, and why. Shown on /vs/ so a visitor knows they were not left out by choice.
SKIPPED = [
    ("Monster", "its pages refused our reader (\"waf blocked\") on 24 Nov 2026, so no fact could be checked. Its job board business and "
                "CareerBuilder's were bought by BOLD in 2025 after a Chapter 11 sale.",
     "https://www.prweb.com/releases/bold-completes-acquisition-of-careerbuilder--monster-job-boards-302519807.html"),
    ("CareerBuilder", "the same block as Monster on 24 Nov 2026; its hiring site now sends visitors to Monster's.",
     "https://www.prweb.com/releases/bold-completes-acquisition-of-careerbuilder--monster-job-boards-302519807.html"),
    ("Adzuna", "every page asked us to prove we are human on 24 Nov 2026, so no fact could be checked.", "https://www.adzuna.com/"),
    ("LinkUp", "its site asked our browser to prove it is human on 18 and 25 Nov 2026, so no fact could be checked; we do not go past "
               "such checks.", "https://www.linkup.com/"),
    ("Hired", "no longer a job site of its own: it was folded into LHH Recruitment Solutions in June 2024, and hired.com now sends "
              "visitors to lhh.com.", "https://www.staffingindustry.com/news/global-daily-news/adecco-incorporating-hired-lhh-business"),
]

# What could not be sourced, per site (pages blocked or not answering on 13-14 Nov 2026; nothing was worked around).
NOT_SOURCED = {
    "indeed": ["Price for job seekers (Indeed Pro price not seen)", "Kinds of jobs"],
    "linkedin-jobs": ["Account needed to apply (not stated on the pages read)", "Kinds of jobs",
                      "about.linkedin.com returned 403"],
    "wellfound": ["How fresh the listings are"],
    "we-work-remotely": ["Price for job seekers", "Where you apply", "Account needed to apply",
                         "weworkremotely.com home, about-us and terms returned 403 or a bot check"],
    "remote-ok": ["Account needed to apply"],
    "flexjobs": ["Price to post one job", "How fresh the listings are",
                 "flexjobs.com pages timed out on every try on 14 Nov 2026; FAQ and About read in a browser on 21 Nov 2026"],
    "cryptojobslist": ["Price for job seekers", "Where you apply", "Account needed to apply", "Kinds of jobs",
                       "cryptojobslist.com home, /about and /hire returned 403 on 14 Nov 2026"],
    "web3-career": ["Price for job seekers", "Account needed to apply", "How fresh the listings are"],
    # read on 24 Nov 2026
    "ziprecruiter": ["Payment methods", "www.ziprecruiter.com showed a human check; read its help centre and its 10-K instead"],
    "glassdoor": ["How fresh the listings are", "Kinds of jobs", "Payment methods"],
    "simplyhired": ["Where you apply", "Payment methods"],
    "jooble": ["Account needed to apply", "How fresh the listings are", "Payment methods"],
    "talent-com": ["Account needed to apply", "Payment methods"],
    "welcome-to-the-jungle": ["Price for job seekers", "Where the jobs come from", "How fresh the listings are", "Payment methods"],
    "dice": ["Price for job seekers", "Where the jobs come from", "Kinds of jobs", "Payment methods"],
    "built-in": ["Where the jobs come from", "Where you apply", "Account needed to apply", "How fresh the listings are", "Payment methods"],
    "himalayas": ["Payment methods"],
    "remotive": ["Account needed to apply", "How fresh the listings are"],
    "remote-co": ["Who pays", "Price for job seekers", "Price to post one job", "How fresh the listings are", "Payment methods",
                  "remote.co/pricing was a 404"],
    "working-nomads": ["How fresh the listings are"],
    "handshake": ["Price for job seekers", "Where the jobs come from", "Where you apply", "How fresh the listings are", "Payment methods"],
    "snagajob": ["Price to post one job", "Payment methods"],
    "usajobs": ["Who pays", "Price for job seekers", "Price to post one job", "How fresh the listings are", "Payment methods"],
    "idealist": [],
    # read on 25 Nov 2026
    "google-for-jobs": ["Price for job seekers", "Payment methods"],
    "ladders": ["Price to post one job", "How fresh the listings are", "Payment methods",
                "theladders.com answered \"Ladders is currently available only in the United States and Canada\"; read its help centre instead"],
    "craigslist": ["Price for job seekers", "Account needed to apply", "the about and FAQ index pages state no figures"],
    "levels-fyi": ["Where the jobs come from", "Payment methods"],
    "governmentjobs": ["How fresh the listings are", "Payment methods"],
    "hiringcafe": ["Payment methods"],
    "drivetube": ["Payment methods"],
    "secretjobs": ["Price to post one job", "Account needed to apply", "Payment methods", "the AI plan's price is behind its sign-up"],
    "jobright": ["Payment methods", "jobright.ai/pricing was a 404; the Premium price is from its own blog post of June 2025"],
    "jobscan": ["Price to post one job", "How fresh the listings are", "Kinds of jobs"],
}

_TAG = re.compile(r"^\[([^\]]+)\]\s*")


def source_keys(fact):
    """Keys a source supports, read from its leading [tag]."""
    m = _TAG.match(fact)
    return [k.strip() for k in m.group(1).split("|")] if m else []


def source_text(fact):
    """The fact without its leading [tag], ready for a page."""
    return _TAG.sub("", fact, count=1)


def site(slug):
    return next(s for s in SITES if s["slug"] == slug)


def test():
    problems = []
    slugs = [s["slug"] for s in SITES]
    if len(SITES) < 34 or len(set(slugs)) != len(slugs) or set(slugs) != set(KIND):      # 8 (14 Nov), +16 (24 Nov), +10 (25 Nov)
        problems.append(f"expected 34+ unique sites, each with a kind, got {slugs}")
    for s in SITES:
        p = s["slug"]
        for field in ("slug", "name", "url", "what", "rows", "them_better", "us_better", "pick", "sources"):
            if not s.get(field):
                problems.append(f"{p}: missing {field}")
        keys = set()
        for src in s["sources"]:
            if len(src) != 3:
                problems.append(f"{p}: source is not (fact, url, date): {src!r}")
                continue
            fact, url, date = src
            if not source_keys(fact):
                problems.append(f"{p}: source without a [tag]: {fact[:60]!r}")
            keys.update(source_keys(fact))
            if not url.startswith("https://"):
                problems.append(f"{p}: bad url {url!r}")
            if date not in (R13, R14, R21, R24, R25):
                problems.append(f"{p}: bad date {date!r}")
        rows = s["rows"]
        if len(rows) < 4:      # build.py gives such a site no page until a fourth fact is sourced
            print(f"NOTE {p}: only {len(rows)} sourced rows, so no page")
        order = [QUESTIONS.index(q) for q, _, _ in rows if q in QUESTIONS]
        if len(order) != len(rows) or order != sorted(order) or len(set(order)) != len(order):
            problems.append(f"{p}: rows not in QUESTIONS order or unknown question")
        for q, them, us in rows:
            if not them or us != US_ANSWERS.get(q):
                problems.append(f"{p}: row {q!r} has empty 'them' or a changed 'us'")
            if q not in keys:
                problems.append(f"{p}: no source for row {q!r}")
        for field, lo in (("them_better", 2), ("us_better", 2)):
            n = len(s[field])
            if not lo <= n <= 3:
                problems.append(f"{p}: {field} has {n} points (need 2-3)")
            for i in range(1, n + 1):
                if f"{field} {i}" not in keys:
                    problems.append(f"{p}: no source for {field} {i}")
        if "what" not in keys:
            problems.append(f"{p}: no source for 'what'")
        if s["kind"] not in KINDS:
            problems.append(f"{p}: unknown kind {s['kind']!r}")
        if not (s["pick"].startswith(f"Use {s['name']} if") and f"use {OUR_NAME} if" in s["pick"]):
            problems.append(f"{p}: pick does not follow 'Use X if..., use {OUR_NAME} if...'")
    for line in problems:
        print("FAIL", line)
    assert not problems, f"{len(problems)} problem(s)"
    refresh_us(500000, 25000, ["Workday", "Greenhouse", "Ashby", "JazzHR", "Lever"])
    assert all(u == US_ANSWERS[q] for s in SITES for q, _, u in s["rows"]) and "5 hiring systems" in US_ANSWERS["Where the jobs come from"]
    assert "25,000 companies" in US_ANSWERS["Kinds of jobs"], US_ANSWERS["Kinds of jobs"]
    pp = pairs([s for s in SITES if len(s["rows"]) >= 4])
    assert any({a["slug"], b["slug"]} == {"indeed", "ziprecruiter"} for a, b in pp) and all(a["slug"] != b["slug"] for a, b in pp)
    assert not any({a["slug"], b["slug"]} == {"indeed", "jobscan"} for a, b in pp)          # a resume tool is paired only with its own kind
    assert {"jobscan", "jobright"} <= {s["slug"] for s in SITES if s["kind"] == "ai"}
    rows = sum(len(s["rows"]) for s in SITES)
    srcs = sum(len(s["sources"]) for s in SITES)
    print(f"OK: {len(SITES)} sites, {len(pp)} pairs, {rows} rows, {srcs} sources; "
          + ", ".join(f"{s['slug']} {len(s['rows'])}" for s in SITES))


if __name__ == "__main__":
    test()
