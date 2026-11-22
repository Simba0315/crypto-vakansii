"""Facts for /free-resume-builders/: what a free user of each resume builder can download, read from the builder's own pages.

Rules the data follows:
- Every fact about a builder comes from that builder's own site (pricing page, help centre, terms), read on CHECKED. Reviews and
  "best of" lists by others only helped to find those pages; they are never the source.
- A fact a page did not state is "" and the page shows "Not stated". A builder whose own pages could not be read is left out.
- A cell is "Short answer: detail". pdf is (kind, cell) with kind one of yes, limited, no, trial (PDF only with a paid trial),
  unknown (the builder's pages do not say).
- Prices are the ones the pages showed our reader on CHECKED, in US dollars; several builders say prices differ by country.

Run `python3 builders_check.py` to check the data.
"""

CHECKED = "2026-11-14"
CHECKED_MORE = "2026-11-18"        # the entries with "read": six builders added after the search check (the ones Google and Bing name)
CHECKED_LAST = "2026-11-22"        # OpenResume, the first pick of Perplexity for "free PDF, no sign up", read on this day

BUILDERS = [        # alphabetical; read on 14 Nov 2026
    {"name": 'Adobe Express', "url": 'https://www.adobe.com/express/', "read": "2026-11-18",
     "pdf": ('yes', 'Yes: download as PDF, free to use'), "watermark": '', "docx": '',
     "signup": 'No: free to use with no sign-in or credit card', "limits": 'Free plan has limited AI credits and fewer templates and assets',
     "paid": 'Premium, $9.99 a month, no annual commitment; 30-day free trial, then renews until cancelled',
     "sources": [('https://www.adobe.com/express/create/resume', 'free, no sign-in, PDF download'),
                 ('https://www.adobe.com/express/pricing', 'free plan, Premium price, trial and renewal')]},
    {"name": 'Canva', "url": 'https://www.canva.com/', "read": "2026-11-18",
     "pdf": ('limited', 'Yes: free downloads; premium elements carry a watermark until paid'), "watermark": 'Yes: only on premium elements, until you pay', "docx": '',
     "signup": '', "limits": 'Premium elements watermarked; some download options are Pro only',
     "paid": 'Canva Pro, billed monthly or yearly, renews automatically; prices vary by country',
     "sources": [('https://www.canva.com/create/resumes/', 'resume page: save as PDF, JPG or PNG'),
                 ('https://www.canva.com/help/download-or-purchase/', 'download limits and free-plan rules'),
                 ('https://www.canva.com/help/watermarks-design/', 'watermarks on premium elements'),
                 ('https://www.canva.com/help/subscription-options/', 'billing and automatic renewal')]},
    {"name": "Enhancv", "url": "https://enhancv.com/",
     "pdf": ("unknown", "Not stated: the free plan lasts 7 days, and no page says what a free user can download"),
     "watermark": "Yes: Enhancv branding, removed only on Pro", "docx": "No: resumes download as PDF",
     "signup": "Yes: the 7 free days start when you open an account", "limits": "7 days, basic sections, at most 12 section items",
     "paid": "Pro, billed monthly, every 3 or every 6 months; prices vary by region",
     "sources": [("https://enhancv.com/pricing/", "pricing and the free plan"),
                 ("https://help.enhancv.com/en/articles/1208865-what-is-included-in-the-free-version", "what the free version includes"),
                 ("https://help.enhancv.com/en/articles/2804413-how-can-i-remove-the-enhancv-branding-watermark-from-my-resume", "branding"),
                 ("https://help.enhancv.com/en/articles/1195346-understanding-the-enhancv-pro-plans", "renewal and regional prices")]},
    {"name": "FlowCV", "url": "https://flowcv.com/",
     "pdf": ("limited", "Yes: unlimited downloads, one saved resume"), "watermark": "No", "docx": "No: PDF only, on every plan",
     "signup": "Yes, to save or download; building starts without one", "limits": "1 resume, 1 cover letter, 3 imports; AI writing is Pro only",
     "paid": "$19 a month, $36 every 3 months or $60 a year; renews until cancelled; 14-day refund, no trial",
     "sources": [("https://flowcv.com/pricing", "free plan, prices, renewal, refund"), ("https://flowcv.com/", "no watermark, PDF only, when an account is needed")]},
    {"name": "Indeed", "url": "https://www.indeed.com/",
     "pdf": ("yes", "Yes"), "watermark": "", "docx": "", "signup": "Yes: an Indeed account",
     "limits": "Two resumes per profile: one built on Indeed, one uploaded file", "paid": "None stated: Indeed says its resume tools are free",
     "sources": [("https://www.indeed.com/help/job-seekers/articles/11314976176141-faqs-creating-uploading-and-managing-a-resume-file", "PDF download"),
                 ("https://www.indeed.com/help/job-seekers/articles/28827071763981-resume-options-menu-managing-a-resume", "account needed"),
                 ("https://www.indeed.com/career-advice/resumes-cover-letters/how-to-build-resume-on-indeed", "free, two resumes")]},
    {"name": "Jobscan", "url": "https://www.jobscan.co/resume-builder",
     "pdf": ("yes", "Yes: unlimited resumes and downloads"), "watermark": "", "docx": "",
     "signup": "Yes: a free account", "limits": "AI writing needs a free trial or Premium",
     "paid": "Premium, monthly or every 3 months; a 7-day free trial comes with the 3-month plan; billing continues until cancelled",
     "sources": [("https://www.jobscan.co/resume-builder", "free PDF, no paywall at download"), ("https://www.jobscan.co/ai-resume", "account, AI limits"),
                 ("https://www.jobscan.co/promos", "trial"), ("https://www.jobscan.co/cancellation-policy", "renewal")]},
    {"name": "Kickresume", "url": "https://www.kickresume.com/",
     "pdf": ("limited", "Yes: unlimited, with the free templates and options only"), "watermark": "No", "docx": "",
     "signup": "Yes, to save resumes", "limits": "4 basic templates, 2 fonts; no AI writer or AI checker",
     "paid": "$19 a month, $27 every 3 months or $54 a year; renews until cancelled; 14-day money back",
     "sources": [("https://www.kickresume.com/en/pricing/", "free plan, prices"), ("https://www.kickresume.com/en/templates/resume/free/", "no watermark, account"),
                 ("https://www.kickresume.com/terms/", "auto-renewal")]},
    {"name": 'MyPerfectResume', "url": 'https://www.myperfectresume.com/', "read": "2026-11-18",
     "pdf": ('trial', 'No: TXT only; PDF and Word come with a $2.95 trial of 14 days'), "watermark": '', "docx": 'No: Word needs paid access',
     "signup": '', "limits": 'Builder and content suggestions free; downloads in TXT only',
     "paid": '$2.95 for 14 days, then $23.95 every 4 weeks, or $95.40 a year; renews until cancelled; refund within 14 days',
     "sources": [('https://www.myperfectresume.com/pricing', 'free plan formats, prices, renewal, refund')]},
    {"name": "Novoresume", "url": "https://novoresume.com/",
     "pdf": ("limited", "Yes: one page, free features only; its help centre says free access lasts a limited time"),
     "watermark": "Yes: Novoresume branding on the PDF", "docx": "", "signup": "Yes; no card needed",
     "limits": "One resume, one page, 8 templates, 2 AI credits a month",
     "paid": "One payment, no renewal: $21.99 for a month, $39.99 for 3 months, $69.99 for 6",
     "sources": [("https://novoresume.com/pricing", "free plan, branding, prices"),
                 ("https://intercom.help/novoresume/en/articles/5562888-membership-questions-basic-premium-refund", "free access period (help centre)"),
                 ("https://intercom.help/novoresume/en/articles/13053894-download-my-resume-cv-2-0", "one-page free download (help centre)")]},
    {"name": "OpenResume", "url": "https://www.open-resume.com/", "read": "2026-11-22",
     "pdf": ("yes", "Yes: free forever; the builder makes the resume as a PDF to download"), "watermark": "", "docx": "",
     "signup": "No: no sign up; the data stays in your browser", "limits": "One U.S.-style single-column design",
     "paid": "None: free and open source",
     "sources": [("https://www.open-resume.com/", "free forever, no sign up, data kept in the browser, ATS-friendly design"),
                 ("https://github.com/xitanggg/open-resume", "its own source code repository: the builder downloads a PDF")]},
    {"name": "Reactive Resume", "url": "https://rxresu.me/",
     "pdf": ("yes", "Yes: every feature is free"), "watermark": "", "docx": "Yes: also Markdown and JSON",
     "signup": "Yes: a free account to save", "limits": "None: 18 templates; AI needs your own provider key",
     "paid": "None: open source, funded by donations",
     "sources": [("https://rxresu.me/", "free PDF and Word, no paid tier"), ("https://docs.rxresu.me/guides/creating-an-account", "account"),
                 ("https://docs.rxresu.me/guides/exporting-your-resume", "export formats")]},
    {"name": "Resume Genius", "url": "https://resumegenius.com/",
     "pdf": ("trial", "No: TXT only; the PDF comes with a $2.95 trial"), "watermark": "", "docx": "No, for resumes; yes for cover letters",
     "signup": "Yes: sign in even for the TXT file", "limits": "The resume downloads as plain text only",
     "paid": "$2.95 for 14 days, then $23.95 every 4 weeks unless cancelled; or $95.40 a year",
     "sources": [("https://resumegenius.com/pricing", "free plan, trial and renewal"), ("https://resumegenius.com/support", "sign-in for the TXT"),
                 ("https://resumegenius.com/faq/is-resume-genius-free", "PDF and Word need the paid trial")]},
    {"name": 'Resume Now', "url": 'https://www.resume-now.com/', "read": "2026-11-18",
     "pdf": ('trial', 'No: its pricing page lists paid access only; PDF and DOC come with it'), "watermark": '', "docx": 'No: DOC comes with paid access',
     "signup": '', "limits": 'No free plan on the pricing page',
     "paid": '$1.85 for 14 days, then $23.95 every 4 weeks, or $70.20 a year; renews until cancelled; money-back guarantee',
     "sources": [('https://www.resume-now.com/pricing', 'plans, prices, renewal, formats, money-back')]},
    {"name": "Resume.com", "url": "https://www.resume.com/",
     "pdf": ("yes", "Yes: also plain text"), "watermark": "", "docx": "",
     "signup": "Sign-in is an Indeed account; guest sessions may not keep the resume", "limits": "None stated: several resumes and cover letters",
     "paid": "None: there is no Resume.com subscription",
     "sources": [("https://www.resume.com/help/is-resume-com-really-free/", "free to build and download"),
                 ("https://www.resume.com/help/how-do-i-print-or-download-my-resume/", "formats"),
                 ("https://www.resume.com/help/how-do-i-create-a-new-account/", "Indeed sign-in"),
                 ("https://www.resume.com/help/i-received-a-charge-to-my-credit-card/", "no subscription")]},
    {"name": "Resume.io", "url": "https://resume.io/",
     "pdf": ("trial", "No: TXT only; the PDF comes with a $2.95 trial"), "watermark": "", "docx": "No",
     "signup": "Yes", "limits": "One resume and one cover letter, TXT downloads",
     "paid": "$2.95 for 7 days, then $29.95 every 4 weeks unless cancelled; or $49.95 every 3 months",
     "sources": [("https://resume.io/pricing", "free plan, trial and renewal"), ("https://help.resume.io/en/articles/3784704", "free plan downloads TXT (help centre)"),
                 ("https://help.resume.io/en/articles/3785664", "billing after the trial (help centre)")]},
    {"name": "Rezi", "url": "https://www.rezi.ai/",
     "pdf": ("limited", "Yes: 3 downloads in all"), "watermark": "", "docx": "No: Word needs an upgrade",
     "signup": "Yes; no card needed", "limits": "1 resume, 3 PDF downloads, standard templates only",
     "paid": "$29 a month, or $149 once for life; 30-day refund",
     "sources": [("https://www.rezi.ai/pricing", "free plan, prices, refund"), ("https://www.rezi.ai/rezi-docs/the-finish-up-tab", "3 PDFs, Word needs an upgrade"),
                 ("https://www.rezi.ai/ai-resume-builder", "free account")]},
    {"name": 'Teal', "url": 'https://www.tealhq.com/', "read": "2026-11-18",
     "pdf": ('yes', 'Yes: unlimited PDF downloads, no paywall'), "watermark": '', "docx": '',
     "signup": 'Yes: a free account; no card needed', "limits": '10 templates, basic design settings, top 5 keywords, limited AI credits',
     "paid": 'Teal+, $13 a week, $29 every 30 days or $79 every 90 days; cancel any time',
     "sources": [('https://www.tealhq.com/tools/resume-builder', 'free unlimited PDF downloads, free plan'),
                 ('https://www.tealhq.com/pricing', 'free plan limits, Teal+ prices, cancellation, refunds')]},
    {"name": 'Zety', "url": 'https://zety.com/', "read": "2026-11-18",
     "pdf": ('trial', 'No: TXT only; PDF and Word come with a $1.70 trial of 14 days'), "watermark": '', "docx": 'No: Word needs the paid plan',
     "signup": '', "limits": 'Builder, templates and resume check free; downloads in TXT only',
     "paid": '$1.70 for 14 days, then $23.95 every 4 weeks, or $71.40 a year; renews until cancelled',
     "sources": [('https://zety.com/pricing', 'free plan formats, trial and annual prices, renewal')]},
]
# Builders whose own pages did not open for our reader on CHECKED (403 or a bot check, not worked around): left out, named on the page.
LEFT_OUT = []            # Canva, Teal and Zety were read on 18 Nov 2026 (their pages had not opened on the 14th)

# This site's builder, from its code (assets/resume.js): the PDF comes from the browser's print window, the Word file is a .doc
# that Word opens, the resumes are kept in the browser (localStorage), up to twenty. The number of templates is counted from the same
# file (it said "One resume per browser, 5 templates" on 20 Nov 2026, when the builder kept twenty and had six).
import re as _re
from pathlib import Path as _Path
_RJS = (_Path(__file__).parent / "assets" / "resume.js").read_text()
_TPL = _re.search(r"TPL_NAMES = \{(.*?)\};", _RJS, _re.S)
_MAX = _re.search(r"SET\.items\.length >= (\d+)", _RJS)
OURS = {"pdf": ("yes", "Yes: as many as you like, from the browser’s print window"), "watermark": "No", "docx": "Yes: a Word file (.doc)",
        "signup": "No: the resumes stay in your browser",
        "limits": f"Up to {_MAX.group(1) if _MAX else 'several'} resumes per browser, {len(_re.findall(r'(\w+): \[', _TPL.group(1))) if _TPL else 'several'} templates",
        "paid": "None: the builder is free"}

KINDS = {"yes", "limited", "no", "trial", "unknown"}


def check():
    names = [b["name"] for b in BUILDERS]
    assert names == sorted(names, key=str.lower), "keep the builders in alphabetical order"
    for b in BUILDERS + [OURS]:
        assert b["pdf"][0] in KINDS and b["pdf"][1], b
        for k in ("watermark", "docx", "signup", "limits", "paid"): assert isinstance(b[k], str), (b, k)
    for b in BUILDERS:
        assert b["url"].startswith("https://") and b["sources"], b["name"]
        for u, what in b["sources"]:
            assert u.startswith("https://") and what, (b["name"], u)
            host = lambda x: x.split("/")[2].removeprefix("www.").split(".")[-2]
            # the builder's own source repository counts as its own page (OpenResume links to it from its site)
            assert host(u) == host(b["url"]) or "help" in u or "support" in u or u.startswith("https://github.com/"), f"{b['name']}: a source off the builder's own site: {u}"
    return len(BUILDERS)


if __name__ == "__main__":
    print(f"{check()} builders checked on {CHECKED}")
