# Jobs Every Hour

**[jobseveryhour.com](https://jobseveryhour.com)** is a free job search engine that reads jobs directly from company career pages
and removes the ones that have closed.

- **Where the jobs come from:** the public hiring feeds companies themselves publish on Greenhouse, Lever, Ashby, Workday, Workable,
  Personio, Recruitee and Teamtailor. Nothing is copied from another job board, and nothing is typed in by hand.
- **How fresh:** the feeds are read again every hour (the largest boards in turn, every four hours). A job that is gone from the
  company's list is marked closed and leaves the lists of open jobs; its page stays at the same address, marked as closed.
- **How many:** 259,035 open jobs at 6,325 companies on 18 November 2026. The live count is on the home page.
- **What it costs:** nothing. No account is needed to search, save jobs or apply. Every "Apply" button opens the employer's own page.

How the hourly check works, step by step: [How we check job postings every hour](https://jobseveryhour.com/guides/how-we-check-jobs-every-hour/)
and the [methodology](https://jobseveryhour.com/methodology/).

## What is on the site

| For | Where |
|---|---|
| Job seekers | [Search all jobs with filters](https://jobseveryhour.com/jobs/), [new jobs](https://jobseveryhour.com/new/), [remote jobs](https://jobseveryhour.com/remote/), [jobs matched to your answers](https://jobseveryhour.com/for-you/), [company pages](https://jobseveryhour.com/companies/) |
| Data | [Salaries counted from live postings](https://jobseveryhour.com/salaries/), guides and insights recounted from today's postings |
| Tools | [Resume builder](https://jobseveryhour.com/resume/) (Word and PDF, free) and [free tools](https://jobseveryhour.com/tools/): pay calculators, resume check, letters, an application tracker |
| Developers and AI agents | [Free JSON API](https://jobseveryhour.com/api/) (no key, CORS), [OpenAPI description](https://jobseveryhour.com/api/openapi.json), [llms.txt](https://jobseveryhour.com/llms.txt), an MCP endpoint at `https://jobseveryhour.com/mcp` |
| Site owners | [Jobs widget and live badges](https://jobseveryhour.com/widgets/) for any skill, city or company |
| Employers | [Post a job for free](https://jobseveryhour.com/post-a-job/); a company can take over its page, add a logo and see views and clicks |

## How it works

`collect.py` reads the public hiring feeds listed in the `sources*.json` files and compares each list with the last reading: a job
that is new gets its first-seen time, a job that is missing is closed. `build.py` generates the site; `check.py` verifies every kind
of page against a quality checklist; `records.py` and `serve.py` serve job pages from records on the server; `live.py` re-reads the
boards between builds. A GitHub Actions workflow runs the collection and the build every hour and uploads the result.
`server/` holds the accounts API (job alerts, saved jobs, employer accounts). Details: `AGENT_NOTES.md`.

Company names and logos belong to their owners and are shown only to identify the employer.
