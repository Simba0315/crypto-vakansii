# Hiring Right Now

An open, daily-updated index of tech jobs: about 36,000 open roles at about 540 companies, collected from the employers' own
careers pages (Greenhouse, Lever and Ashby feeds). Every listing links back to the original posting; closed roles are kept in an archive.

Live site: https://simba0315.github.io/crypto-vakansii/ (temporary address)

## What is here

| For | Where |
|---|---|
| Job seekers | [Search with filters](https://simba0315.github.io/crypto-vakansii/jobs/), [remote jobs](https://simba0315.github.io/crypto-vakansii/remote/), [jobs matched to your skills](https://simba0315.github.io/crypto-vakansii/for-you/), [résumé builder](https://simba0315.github.io/crypto-vakansii/resume/) |
| Data | [Salaries from live postings](https://simba0315.github.io/crypto-vakansii/salaries/), [hiring trends](https://simba0315.github.io/crypto-vakansii/trends/), [skill comparisons](https://simba0315.github.io/crypto-vakansii/compare/), [methodology](https://simba0315.github.io/crypto-vakansii/methodology/) |
| Developers and AI agents | [Free JSON API](https://simba0315.github.io/crypto-vakansii/api/) (no key, CORS), [OpenAPI description](https://simba0315.github.io/crypto-vakansii/api/openapi.json), [llms.txt](https://simba0315.github.io/crypto-vakansii/llms.txt), CSV downloads |
| Site owners | [Jobs widget and live badges](https://simba0315.github.io/crypto-vakansii/widgets/) for any skill, city or company |
| Employers | [Post or promote a job](https://simba0315.github.io/crypto-vakansii/post-a-job/) |

## How it works

`collect.py` reads the public hiring feeds listed in `sources.json` and `sources_tech.json`; `build.py` generates the static site;
`check.py` verifies every page type against a quality checklist; a GitHub Actions workflow runs all three every day and publishes
the result. `server/` holds the accounts and checkout API (Cloudflare Worker + D1). Details: `AGENT_NOTES.md`.

Company names and logos belong to their owners and are shown only to identify the employer.
