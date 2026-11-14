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

BUILDERS = [        # alphabetical; read on 14 Nov 2026
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
    {"name": "Novoresume", "url": "https://novoresume.com/",
     "pdf": ("limited", "Yes: one page, free features only; its help centre says free access lasts a limited time"),
     "watermark": "Yes: Novoresume branding on the PDF", "docx": "", "signup": "Yes; no card needed",
     "limits": "One resume, one page, 8 templates, 2 AI credits a month",
     "paid": "One payment, no renewal: $21.99 for a month, $39.99 for 3 months, $69.99 for 6",
     "sources": [("https://novoresume.com/pricing", "free plan, branding, prices"),
                 ("https://intercom.help/novoresume/en/articles/5562888-membership-questions-basic-premium-refund", "free access period (help centre)"),
                 ("https://intercom.help/novoresume/en/articles/13053894-download-my-resume-cv-2-0", "one-page free download (help centre)")]},
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
]
# Builders whose own pages did not open for our reader on CHECKED (403 or a bot check, not worked around): left out, named on the page.
LEFT_OUT = ["Canva", "Teal", "Zety"]

# This site's builder, from its code (assets/resume.js): the PDF comes from the browser's print window, the Word file is a .doc
# that Word opens, the resume is kept in the browser (localStorage), one at a time.
OURS = {"pdf": ("yes", "Yes: as many as you like, from the browser’s print window"), "watermark": "No", "docx": "Yes: a Word file (.doc)",
        "signup": "No: the resume stays in your browser", "limits": "One resume per browser, 5 templates", "paid": "None: the builder is free"}

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
            assert host(u) == host(b["url"]) or "help" in u or "support" in u, f"{b['name']}: a source off the builder's own site: {u}"
    return len(BUILDERS)


if __name__ == "__main__":
    print(f"{check()} builders checked on {CHECKED}")
