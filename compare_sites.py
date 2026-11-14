"""Facts for the comparison pages "Hiring Right Now vs <job site>" (one page per site in SITES).

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
  pick: one sentence "Use X if ..., use Hiring Right Now if ...",
  sources: list of (fact, url, date read).

Each source fact starts with a tag in square brackets that names what it supports, for example
"[Who pays|Price to post one job] ...". Keys are a question from QUESTIONS, "what", "them_better 1".."them_better 3",
"us_better 1".."us_better 3" or "pick". Use source_text() to drop the tag and source_keys() to read it.

Run `python3 compare_sites.py` to check the data.
"""

import re

OUR_NAME = "Hiring Right Now"

R13 = "2026-11-13"  # read by the research files
R14 = "2026-11-14"  # read from the site's own page for this module

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
    "source": "the employers' own careers pages (Greenhouse, Lever and Ashby boards)",
    "refresh": "every hour",
    "apply": "on the employer's own page",
    "account_needed_to_search": False,
    "account_needed_to_apply": False,
    "price_for_job_seekers": "free",
    "plus_plan": {
        "prices_usd": {"1 month": 3, "3 months": 7, "12 months": 12},
        "one_payment": True,
        "renews": False,
        "on_sale": False,
    },
    "employer_listings": {
        "standard": "free for 30 days",
        "featured": "$29 for 14 days",
        "pinned": "$59 for 7 days",
        "self_serve_open": False,
    },
    "payments": "crypto",
    "free_tools": ["resume builder", "resume match checker", "salary data from posted ranges", "jobs map"],
    "launched": "November 2026",
    "languages": ["English"],
}

US_ANSWERS = {
    "Who pays": "Job seekers use it free. Paid options: an optional Plus plan for job seekers (not on sale yet) and featured "
                "or pinned listings for employers (self-serve posting is not open yet).",
    "Price for job seekers": "Free. Optional Plus plan: $3 for 1 month, $7 for 3 months, $12 for 12 months. One payment, "
                             "nothing renews. Not on sale yet.",
    "Price to post one job": "Standard listing free for 30 days. Featured $29 for 14 days. Pinned $59 for 7 days. "
                             "Self-serve posting is not open yet.",
    "Where the jobs come from": "The employers' own careers pages (Greenhouse, Lever and Ashby boards).",
    "Where you apply": "On the employer's own page.",
    "Account needed to apply": "No. You can search and apply without an account.",
    "How fresh the listings are": "Every job is read again from the employer's careers page every hour.",
    "Kinds of jobs": "The jobs that 732 companies post on their own careers pages (41,187 open jobs). English only.",
    "Payment methods": "Crypto.",
}


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
            "Employers can post today, and a basic post is free for many jobs. Our self-serve posting is not open yet.",
        ],
        us_better=[
            "We read every job again from the employer's careers page every hour. Indeed reads career-site feeds every 6 hours.",
            "Every job sends you to apply on the employer's own page. On Indeed, some jobs take the application on Indeed.",
            "Our employer prices are public: featured $29 for 14 days, pinned $59 for 7 days. Indeed shows no fixed price for "
            "its paid levels.",
        ],
        pick="Use Indeed if you want the largest general job site and employer tools like Indeed Apply, use Hiring Right Now "
             "if you want jobs checked every hour on employers' own careers pages and to apply there directly.",
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
            "We read every job again from the employer's careers page every hour. LinkedIn reads partner feeds every 6 to 24 "
            "hours.",
            "Our prices are on the page: Plus from $3 (not on sale yet), featured listing $29, pinned $59. LinkedIn shows "
            "Premium prices only after sign-in and publishes no job post prices.",
            "Every job sends you to apply on the employer's own page. Easy Apply keeps the application on LinkedIn.",
        ],
        pick="Use LinkedIn Jobs if you want the biggest professional network and Easy Apply, use Hiring Right Now if you want "
             "jobs checked every hour on employers' careers pages and to apply on the employer's own page.",
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
            "Free job posting is open to employers today. Our self-serve posting is not open yet.",
        ],
        us_better=[
            "No account needed to search or apply. Wellfound asks you to sign in with a profile before you apply.",
            "You apply on the employer's own page. On Wellfound the application is sent inside Wellfound.",
        ],
        pick="Use Wellfound if you want to reach many startups with one profile, use Hiring Right Now if you want to search "
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
            ("Payment methods", "Stripe Checkout, where the buyer picks the method. Its terms name credit card. Invoice by "
                                "email."),
        ),
        them_better=[
            "More ways for employers to stand out: two paid upgrades, and Premium Placement for hiring at scale (from "
            "$1,999).",
            "Bundles for employers who hire often: from $179 a job, up to 40% off, used within 12 months.",
            "Employers can buy and post today. Our self-serve posting is not open yet.",
        ],
        us_better=[
            "A standard listing is free for 30 days (self-serve posting is not open yet). On We Work Remotely the base "
            "listing is $299 for 30 days.",
            "We read every job again from the employer's careers page every hour. A We Work Remotely listing is bought for "
            "a fixed 30 days.",
        ],
        pick="Use We Work Remotely if you want a board of remote listings that employers pay to post, use Hiring Right Now if "
             "you want jobs read every hour from employers' own careers pages.",
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
            # COMPANIES_RESEARCH.md C.12
            ("[Payment methods] Payment \"electronically via credit card or ... other payment method you select.\"",
             "https://weworkremotely.com/terms-and-conditions", R13),
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
            "Much larger: it lists 100,000+ remote jobs from 10,000+ companies and says it reaches 20,100,000+ remote "
            "workers a month.",
            "Wide reach for employers: posts are emailed to 2,692,454 remote job seekers and crossposted to 261 job boards.",
            "It has a public jobs API, and employers can post today. Our self-serve posting is not open yet.",
        ],
        us_better=[
            "No commitment: Plus is one payment that never renews, from $3 for 1 month (not on sale yet). Remote OK Premium "
            "is $14.95 a month with a 12-month commitment.",
            "Salary data from posted ranges is a free tool here. Remote OK lists salary data among its paid Premium "
            "features.",
            "A standard listing is free for 30 days (self-serve posting is not open yet). Remote OK starts at $299 for 30 "
            "days and renews unless turned off.",
        ],
        pick="Use Remote OK if you want a large remote-only board with wide reach for employers, use Hiring Right Now if you "
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
            ("Payment methods", "Credit card and other methods, depending on the buyer's country."),
        ),
        them_better=[
            "A money-back promise: a full refund on request within 14 days of creating the account.",
            "You can buy it and use it today, by card or other local methods. Our Plus plan is not on sale yet.",
        ],
        us_better=[
            "Free for job seekers. FlexJobs charges job seekers, starting at $2.95 for a 14-day trial.",
            "Plus is one payment and never renews: $3 for 1 month, $7 for 3 months, $12 for 12 months (not on sale yet). "
            "FlexJobs plans renew automatically, and the trial renews at $23.95 every 4 weeks.",
        ],
        pick="Use FlexJobs if you are happy to pay for a membership with a 14-day refund window, use Hiring Right Now if you "
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
            "Our self-serve posting is not open yet.",
        ],
        us_better=[
            "A standard listing is free for 30 days (self-serve posting is not open yet). On CryptoJobsList the budget "
            "starts at $150 for 30 days.",
            "Fixed prices for a better place: featured $29 for 14 days, pinned $59 for 7 days. On CryptoJobsList the place "
            "depends on the budget and can change if another employer pays more.",
            "We take payment in crypto. CryptoJobsList offers crypto to selected customers only.",
        ],
        pick="Use CryptoJobsList if you want a long-running board with a large Telegram following, use Hiring Right Now if you "
             "want jobs read every hour from employers' careers pages and fixed, low listing prices.",
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
            "More employers: 42,383 jobs at 7,389 projects, against our 41,187 jobs at 732 companies.",
            "A large crypto audience: its posting page shows 640,903 job post views, 41,000 Twitter followers and 9,000 "
            "Discord members.",
            "Employers get a built-in applicant tracking system (powered by Bondex), and posting is open today. Our "
            "self-serve posting is not open yet.",
        ],
        us_better=[
            "We take payment in crypto. Web3.career's posting form does not offer crypto.",
            "Lower prices to stand out: pinned $59 for 7 days, featured $29 for 14 days (self-serve posting is not open "
            "yet). On Web3.career, 7 days at the top is +$149 and 14 days is +$199.",
        ],
        pick="Use Web3.career if you want the widest list of web3 projects and a large crypto audience, use Hiring Right Now if "
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

# What could not be sourced, per site (pages blocked or not answering on 13-14 Nov 2026; nothing was worked around).
NOT_SOURCED = {
    "indeed": ["Price for job seekers (Indeed Pro price not seen)", "Kinds of jobs"],
    "linkedin-jobs": ["Account needed to apply (not stated on the pages read)", "Kinds of jobs",
                      "about.linkedin.com returned 403"],
    "wellfound": ["How fresh the listings are"],
    "we-work-remotely": ["Price for job seekers", "Where you apply", "Account needed to apply",
                         "weworkremotely.com home, about-us and terms returned 403 or a bot check"],
    "remote-ok": ["Account needed to apply"],
    "flexjobs": ["Price to post one job", "Where the jobs come from", "Where you apply", "Account needed to apply",
                 "How fresh the listings are", "Kinds of jobs",
                 "flexjobs.com pages timed out on every try on 14 Nov 2026"],
    "cryptojobslist": ["Price for job seekers", "Where you apply", "Account needed to apply", "Kinds of jobs",
                       "cryptojobslist.com home, /about and /hire returned 403 on 14 Nov 2026"],
    "web3-career": ["Price for job seekers", "Account needed to apply", "How fresh the listings are"],
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
    if len(SITES) != 8 or len(set(slugs)) != len(slugs):
        problems.append(f"expected 8 unique sites, got {slugs}")
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
            if date not in (R13, R14):
                problems.append(f"{p}: bad date {date!r}")
        rows = s["rows"]
        if len(rows) < 4:
            problems.append(f"{p}: only {len(rows)} rows (need 4)")
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
        if not (s["pick"].startswith(f"Use {s['name']} if") and f"use {OUR_NAME} if" in s["pick"]):
            problems.append(f"{p}: pick does not follow 'Use X if..., use {OUR_NAME} if...'")
    for line in problems:
        print("FAIL", line)
    assert not problems, f"{len(problems)} problem(s)"
    rows = sum(len(s["rows"]) for s in SITES)
    srcs = sum(len(s["sources"]) for s in SITES)
    print(f"OK: {len(SITES)} sites, {rows} rows, {srcs} sources; "
          + ", ".join(f"{s['slug']} {len(s['rows'])}" for s in SITES))


if __name__ == "__main__":
    test()
