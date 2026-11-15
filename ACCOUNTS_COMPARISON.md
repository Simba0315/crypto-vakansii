# Personal accounts: ours against Indeed, LinkedIn, Glassdoor, ZipRecruiter, hh.ru, Teal (15 Nov 2026)

The owner: "are the personal accounts fully worked out? did you check how all the other sites do it? log in with a work email or
LinkedIn to post; job seekers need an account too". Status of ours: **live** = on jobseveryhour.com now; **server** = the API is
installed on our server (15 Nov) and the code is tested (948 tests), the pages come with the accounts session's merge; **keys** =
built, switched on when the owner sets his own key; **to build** = not written yet (passed to the accounts session).

The features below are the ones those sites show to every user on their public pages and help centers; nothing here is a guess
about their internals.

## Job seeker

| Feature | Indeed | LinkedIn | Glassdoor | ZipRecruiter | hh.ru | Teal | Ours |
|---|---|---|---|---|---|---|---|
| Search, save jobs, track applications without an account | — | — | — | — | — | — | **live** (in the browser) |
| Account with email + password, email confirmation, password reset | yes | yes | yes | yes | yes | yes | **server** |
| Sign in with Google | yes | yes | yes | yes | — | yes | **to build** (owner's Google OAuth client) |
| Sign in with LinkedIn | — | (is LinkedIn) | — | — | — | yes | **keys** |
| Saved and applied jobs synced across devices | yes | yes | yes | yes | yes | yes | **server** (/api/sync) |
| Job alerts by email, frequency choice, one-click unsubscribe | yes | yes | yes | yes | yes | — | **server** (double opt-in, one letter a day) |
| Resume stored in the account, several versions | yes | yes | yes | yes | yes | yes | in the browser now; **to build** in the account |
| "Let employers find my resume" (searchable profile, hidden contacts) | yes | yes | — | yes | yes | — | **to build** (opt-in, contacts only on acceptance) |
| Application status from the employer ("viewed", "rejected") | yes | partly | — | yes | yes | — | not possible: people apply on the employer's own page |
| Recommended jobs from the profile | yes | yes | yes | yes | yes | yes | **live** (/for-you/, in the browser) |
| Salary and company insights inside the account | yes | Premium | yes | — | — | — | live as public pages |
| AI resume / cover letter / tailoring | yes | Premium | — | — | — | Teal+ | **keys** (Plus, AI key) |
| Export my data, delete account for good | yes | yes | yes | yes | yes | yes | **to build** (delete exists in the API plan; export to add) |

## Employer / recruiter

| Feature | Indeed | LinkedIn | Glassdoor | ZipRecruiter | hh.ru | Ours |
|---|---|---|---|---|---|---|
| Post a job free | yes | 1 free | via Indeed | trial | paid | **server** (reviewed first, fraud checks) |
| Prove who is posting: work email / company domain | email | company page | via Indeed | email | company check | **server** (work email; DNS record or file on the site) |
| Recruiter posting for a client, marked as such | yes | yes | — | yes | yes | **server** (with LinkedIn sign-in, always reviewed, marked) |
| Sign in with LinkedIn / Google | — / yes | yes | — | — / yes | — | **keys** / **to build** |
| Job dashboard: views, clicks on Apply | yes | yes | yes | yes | yes | **server** |
| Paid promotion (sponsored / featured / urgent badge) | yes (per click) | yes (budget) | via Indeed | yes | yes | featured and pinned built; **to build**: "Urgently hiring" badge, top-3 rotation, boost per job (research) |
| Claim and edit the company page | yes | yes | yes | — | yes | **server** (claim) ; editing **to build** |
| Team members posting for one company | yes | yes | yes | yes | yes | **to build** |
| Invoices and receipts | yes | yes | yes | yes | yes | **to build** (crypto receipts) |
| Resume search, contact requests | paid | paid (Recruiter) | — | paid | paid | **to build** (after seekers opt in) |
| Applicants inside the site (ATS) | yes | yes | — | yes | yes | not planned: apply on the employer's own page is our promise |

## What only the owner can do (one-time)

1. The mailbox password of support@: typed into the terminal tab, never seen by anyone else. Without it no confirmation letters.
2. Sign In with LinkedIn: an app in the LinkedIn Developer Portal (developer.linkedin.com → Create app, product "Sign In with LinkedIn
   using OpenID Connect", redirect URL `https://jobseveryhour.com/account/`), then the Client ID and Secret typed in the same way.
3. Sign in with Google (when built): an OAuth client in Google Cloud Console, redirect URL the same account page.
4. Payments: the Cryptomus merchant keys, last.
