# Job aggregators that accept a jobs feed: research

Date of research: 13 Nov 2026. Method: official pages opened today. No form was submitted, no email sent, no account created.

## How to read this file

Status labels used in every table:

| Label | Meaning |
|---|---|
| OPENED | The official page was opened today and the fact comes from it. |
| INDEX | The official page blocked us. The fact comes from a search engine's summary of that same official page. Check it before you code against it. |
| 3RD | The fact comes from a third-party page (an ATS vendor, a job board software vendor). Treat as a hint. |
| BLOCKED | The page could not be opened. Nothing is claimed. See the last section. |

Two limits you should know about:

- Many aggregator sites showed a bot check or a 403 from this network. That includes the feed specification pages of Adzuna and Talent.com, and the whole sites of Jobsora, Jobted, Recruit.net, JobisJob, Joblift, Jobtome, Monster, ZipRecruiter. They are listed in "Not opened or not verified".
- Rules are paraphrased closely, not quoted. One short verbatim quote is given (Indeed). Open the linked page for the exact wording.

## Main findings in short

1. The three biggest names refuse a board like ours. Indeed bans aggregators. LinkedIn bans feeds with aggregated jobs. Jora (SEEK) wants only jobs posted directly on your platform that do not redirect to a third-party site.
2. Google for Jobs needs no application. It reads `JobPosting` structured data on each job page. It is free. It has a policy line against posting for a company without authorization, which is a risk for any aggregator.
3. The classic "meta" aggregators are the realistic targets: Careerjet, Jooble, Adzuna, Talent.com, Trovit and Mitula, Jobrapido. Careerjet and Adzuna say inclusion is free on pages opened today. Jooble's partner page lists only paid packages. Talent.com and Jobrapido do not publish their terms.
4. There is no single feed format. Four shapes cover almost everything: the Jooble shape (`jobs/job`), the Indeed shape (`source/job`, also used by Talent.com, LinkedIn, PostJobFree), the Trovit shape (`trovit/ad`), and the Adzuna field set.
5. Remote job boards (Himalayas, Remote OK, Remotive) publish outbound APIs only. Their API terms forbid passing their jobs on to other aggregators.

---

## 1. Who accepts a feed

### 1A. Multi-country aggregators

| Name | Official page | Countries | Free or paid | Accepts a board that gathers jobs from employer ATS and links out? | How to apply | Feed format and spec | Status |
|---|---|---|---|---|---|---|---|
| Jooble | Partner form: https://jooble.org/partner/ppc . Also https://jooble.org/partner/advertise . Help: https://help.jooble.org/en/support/solutions/articles/60000037108-why-is-partnership-with-jooble-useful-and-what-are-the-cooperation-options | 66 (partner page), 67 (help article) | Mixed. Jooble's crawler indexes public job pages and job boards on its own, free. The partner page for feed senders lists only paid packages: Premium Basic from $200, Premium Advanced from $500. A multi-country site, or more than one site, needs Premium Advanced. Billing is per click or per application. | Yes in principle. The contact form lists job sites and job aggregators among partner roles. No rule against aggregated jobs was found. The feed link must open a page with the full job description, and the feed description must match that page. | Form on the partner page: name, email, plan, number of jobs, site, link to feed. Technical questions: xml_support@jooble.com | XML. Spec PDF: https://jooble.org/files/xml_feed_specifications.pdf | OPENED |
| Careerjet (Opcionempleo, Optioncarriere) | Overview: https://www.careerjet.co.uk/recruiter/indexing . FAQ: https://www.careerjet.co.uk/faqs . Form: https://www.careerjet.com/recruiter/indexing/submit-your-website | Over 90 countries, 28 languages (about page). Over 58,000 sites scanned daily. | Free indexing. Paid boosts are optional: PPC from GBP 3.00 per click, PPL from GBP 5.00 per application (UK prices). | Not stated. The pages speak to recruiters. No rule against job boards was found on the pages opened. The form page itself was behind a bot check. | Web form "Submit your website". Send the feed URL with it. Careerjet reviews and confirms. | Any feed type is accepted. A feed is helpful but not needed. No public spec. | OPENED, except the form page (BLOCKED) |
| Adzuna | Product page: https://www.adzuna.co.uk/hire/products/job-listings/ . Spec: https://www.adzuna.co.uk/jobs/xml-specification.html | 19: AU, AT, BE, BR, CA, CH, FR, DE, ES, IN, IT, MX, NL, NZ, PL, SG, ZA, UK, US (INDEX) | Free for an XML feed of all organic jobs on your platform (OPENED). Sponsored options exist. | Unclear. The opened page gives no eligibility rule. A third party (JBoard) says Adzuna takes only directly posted jobs and asks a $600 monthly PPC minimum. The two sources conflict. Ask Adzuna. | Contact form "Speak to our team": https://www.adzuna.co.uk/hire/contact/ | XML. Spec page above. | Product pages OPENED. Spec INDEX. |
| Talent.com (ex-Neuvoo) | Integration guide: https://www.talent.com/integrations . Publisher page: https://employers.talent.com/publishers | 79 (publisher page) | Not verified on an official page. An ATS vendor (ExactHire) describes an organic XML feed with free posting. Sponsored CPC also exists. | Not verified. | Contact page: https://www.talent.com/contact . ATS vendors send the feed URL to a Talent.com account manager with company details; validation takes at least 2 business days (3RD). | XML, root `source`. | Publisher page OPENED. Integration guide BLOCKED (INDEX used). |
| Jobrapido | Partnership article: https://support.jobrapido.com/hc/en-us/articles/29103217516444-Affiliate-Program-and-Partnership-Proposals . Partner page: https://corporate.jobrapido.com/partner-program/ | 58 | Not public. Company services are tailor-made offers and sponsored "Featured Ads". Partnership terms come after a request. | Jobrapido says it partners with publishers, job boards and business networks, with interest in traffic acquisition and exchange. | Link "Submit a request": https://support.jobrapido.com/hc/en-us/requests/new . Include company name, site URL, short proposal, target countries. | XML feed is mentioned on the partner page. The old spec article now returns 404. | OPENED |
| Trovit and Mitula (also Nestoria, Nuroa). Owner: Lifull Connect. Partner tool: Thribee. | How to upload: https://help.thribee.com/hc/en-us/articles/360005969594-Uploading-your-content-to-our-sites . Spec: https://help.thribee.com/hc/en-us/articles/7742955286300-Technical-specifications-for-Jobs | 57 countries in the feed-spec table, including USA, UK, Canada, Germany, France, Spain, Brazil, India, Japan, UAE, South Africa, Nigeria, Kenya | Free inclusion. Paid CPC campaigns in Thribee are optional (auction, pay per click only). | For owners of a classified ads portal with public ads. Job offers only: no services, training or business opportunities. No rule on aggregated jobs was found. | Email the feed URL to thribee.salesinfo@lifullconnect.com | XML, root `trovit`, items `ad`. Per-country pages, for example https://help.thribee.com/hc/en-us/articles/7742664218524-Canada-Jobs-feed | OPENED |
| Jora (SEEK group) | https://support.jora.com/hc/en-us/articles/13919677306383-Get-your-jobs-published-on-Jora-with-an-XML-feed . Content rules: https://support.jora.com/hc/en-us/articles/13919751300239-XML-Feed-content-requirements | 12 (stated in the article) | Free | No. Feed jobs must be unique, posted directly on your platform, not copied from another source, and must not redirect to a third-party site. | Contact through the support site. Commercial questions: support@jora.com | XML or JSON. Spec is in the article. | OPENED |
| WhatJobs | https://www.whatjobs.com/xml-feed-specification | 77 (list at https://www.whatjobs.com/international) | Paid. A `CPC` tag is listed as required in the feed. No rates published. | Not stated. | Form: https://www.whatjobs.com/contact/business | XML. Spec page above. | OPENED |
| Jobijoba | https://www.jobijoba.com/fr/contact | France plus 12: AT, AU, BE, BR, CH, DE, ES, IE, IT, MX, PT, UK | Not stated | Not stated. The page has a "publish your offers on Jobijoba" heading with no detail. | Contact form on that page | Not published | OPENED |
| PostJobFree | https://www.postjobfree.com/include-job-feed | Global | Redirect to your site usually costs $0.10 to $0.50 per click. Free redirect is possible when jobs are attractive and hard to find elsewhere. Email-apply is usually free. | No eligibility rule stated. | Form on the page: email, company, contact, feed link, notes. | XML, Indeed-like: `title`, `date`, `referencenumber`, `url`, `company`, `location`, `description`, `salary`, `email`, `cpc`. Jobs up to 30 days old. | OPENED |
| Trabajo.org (beBee) | https://www.trabajo.org/ | Country portals in the Americas, Europe, Asia, Africa | Not stated | The home page says it gathers listings from employers and partner sites. No partner page was found. | Not found | Not published | OPENED (home page only) |
| JobAdX | https://www.jobadx.com/docs/developer/advertisers-xml-feed-specifications/ | Global | Paid (bid per job, target cost per apply) | Not stated | Signup on site | XML: `job`, `title`, `date`, `identifier`, `organization`, `url`, `region`, `description` | OPENED |
| Talroo | https://www.talroo.com/publisher/job-boards/ | US focus | The publisher programme pays job boards to show Talroo ads. Sending jobs to Talroo is paid advertising. No free inclusion. | n/a | Create a publisher account | XML, API, widget | OPENED |
| Jobsora | https://uk.jobsora.com/jobsora-xml.pdf | 34 (3RD) | Paid PPC (3RD) | Not verified | Not verified | PDF spec | BLOCKED |
| Jobted, Recruit.net, JobisJob, Joblift, Jobtome | - | - | - | - | - | - | BLOCKED |

### 1B. Big platforms

| Name | Official page | Free or paid | Accepts a board like ours? | How to apply | Feed format | Status |
|---|---|---|---|---|---|---|
| Indeed | Policy: https://uk.indeed.com/help/employers/articles/360018069792 . Feed policy 2026: https://uk.indeed.com/help/employers/articles/single-source-feed-policy-effective-march-31-2026 . XML guide: https://docs.indeed.com/job-sync-xml/xml-feed | Organic visibility is no longer guaranteed. From 31 Mar 2026 single-source XML feeds lose free visibility when the jobs could come through an ATS that integrates with Indeed Apply. | No. Quote: "Aggregators are not allowed on Indeed." (Indeed Employer Help, article 360018069792). Partner feeds must not include job board content. Indeed's search quality page also asks for original listings that were not reposted or aggregated. The Japan rules say not to include job board jobs. | No route for aggregators. | XML, root `source`. See section 2. | OPENED |
| LinkedIn (Basic Jobs, also called Limited Listings; job wrapping) | Overview: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/xml-feeds . Guidelines: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/xml-feeds-job-posting-guidelines . Spec: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/xml-feeds-development-guide | Ingestion of Basic Jobs is free. Job wrapping needs paid Job Slots. | No. The feed must not contain jobs aggregated from other job boards. LinkedIn takes only jobs posted directly by employers on your platform. Apply must go straight to the source without redirects. Each job needs a poster email on a corporate domain. Since August 2024 some third-party jobs are hidden. | Approval needed. Email LL-BD@linkedin.com with daily job count, markets, search page URL and sample job URLs. | XML, root `source`. See section 2. | OPENED |
| Google for Jobs | Structured data: https://developers.google.com/search/docs/appearance/structured-data/job-posting . Indexing API: https://developers.google.com/search/apis/indexing-api/v3/quickstart . Quota: https://developers.google.com/search/apis/indexing-api/v3/quota-pricing | Free | Yes, with conditions. Google says third-party job sites can integrate. Policies: markup only on single-job pages, no login wall, no expired jobs, a way to apply, do not change the employer's job title. One policy line forbids job postings on behalf of a company without authorization. `baseSalary` may come only from the employer. | No application. Add `JobPosting` JSON-LD to each job page. Verify the site in Search Console. Optionally use the Indexing API. | Not XML. JSON-LD on the page. See section 2. | OPENED |
| ZipRecruiter | https://www.ziprecruiter.com/partner/documentation/feed-import/ | Not verified | Not verified | Not verified | Feed import spec exists | BLOCKED |
| SimplyHired | https://www.simplyhired.com/ | Not verified | Not verified | Not verified | - | BLOCKED |
| Glassdoor | - | Not verified | Not verified. One older vendor guide says Glassdoor jobs are pushed from Indeed (3RD). | - | - | Not opened |
| Monster | https://partner.monster.com/job-ads-non-duration | Not verified | Not verified | Not verified | XML partner feed exists; a 50 MB file limit is mentioned in a search summary (INDEX) | BLOCKED |
| CareerBuilder | https://www.careerbuilder.com/ | Not verified | Not verified | - | - | BLOCKED |

Google details that matter for the generator:

- Required properties: `datePosted`, `description`, `hiringOrganization`, `jobLocation` (with `addressCountry`), `title`.
- Recommended: `applicantLocationRequirements`, `baseSalary`, `directApply`, `employmentType`, `identifier`, `jobLocationType`, `validThrough`.
- Remote: `jobLocationType` = `TELECOMMUTE` only for fully remote jobs, plus at least one country in `applicantLocationRequirements`.
- `employmentType` values: `FULL_TIME`, `PART_TIME`, `CONTRACTOR`, `TEMPORARY`, `INTERN`, `VOLUNTEER`, `PER_DIEM`, `OTHER`.
- `baseSalary` units: `HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR`.
- Indexing API: only for pages with `JobPosting` (or livestream video). Default quota 200 publish requests per day per project. Up to 100 calls per batch. Free. Google recommends it over sitemaps for job URLs. With 37,000 jobs the default quota covers only a small part, so keep a sitemap with accurate `lastmod`.
- Available regions include North America, Latin America, Sub-Saharan Africa, most of Western Europe, India, Japan, much of South-East Asia and MENA.

### 1C. Remote job boards

| Name | Official page | What it offers | Accepts a feed from us? | Status |
|---|---|---|---|---|
| Himalayas | https://himalayas.app/api | Outbound JSON API, RSS, widget, MCP server | No inbound feed programme found. API terms forbid passing Himalayas jobs to other job boards, aggregators, Google Jobs or LinkedIn. | OPENED (API page). Employer pages returned 404. |
| Remote OK | https://remoteok.com/api | Outbound JSON API. Terms: link back with a followed link and name Remote OK as source. | No inbound feed documented. | OPENED (API). Posting page not opened. |
| Remotive | https://github.com/remotive-io/remote-jobs-api | Outbound API. Terms: link back, credit Remotive, do not submit its jobs to third-party sites such as Jooble, Google Jobs or LinkedIn. Jobs delayed 24 hours. | No inbound feed documented. | OPENED |
| Jobgether | https://jobgether.com/ | Job search with paid plans for job seekers. Says it lists only openings from verified employers. | No employer, partner or feed page found. | OPENED (home page only) |

Note: if our board ever takes jobs from the Himalayas or Remotive APIs, those jobs must stay out of every outgoing feed and out of `JobPosting` markup.

### 1D. Country-specific

| Country | Name | Official page | Free or paid | Accepts a board like ours? | How to apply | Status |
|---|---|---|---|---|---|---|
| Germany | Jobbörse of the Bundesagentur für Arbeit (HR-BA-XML) | https://www.arbeitsagentur.de/unternehmen/arbeitskraefte/hr-ba-xml-schnittstelle | Free | Possibly. The page names employers, job boards (Stellenbörsen), public bodies and municipal providers, each with its own cooperation model. Needs a central job database, a supervised employer account, a signed cooperation agreement, and a client certificate (X.509, .p12). | Email service-haus.vam-accountmgmt@arbeitsagentur.de to ask for the cooperation agreement. Spec, catalogues and sample files are ZIP downloads on the page. Format: HR-BA-XML. | OPENED |
| Germany | Kimeta | https://feedvalidation.kimeta.de/ | Not verified | Not verified | Not verified | BLOCKED (HTTP 503) |
| Germany | StepStone | https://www.stepstone.de/ | Not verified | Not verified | - | Not opened (timeout) |
| France | France Travail | https://www.francetravail.fr/candidat/vos-services-en-ligne/des-partenaires-pour-vous-propos.html | Free | Partner job sites are shown on francetravail.fr under an agreement that covers free access, quality, legality and freshness of offers. The page does not say how to become a partner. | Not found on the page | OPENED |
| France | HelloWork | https://recruteur.hellowork.com/fr/ | Paid for most: very small companies get up to 2 free offers, SMEs from EUR 99 per month. | No programme for job boards described. Works through ATS connections. | Recruiter contact page | OPENED |
| France and others | Jobijoba | see 1A | | | | |
| Spain, LatAm | Computrabajo | - | Not verified | A search found only employer posting, no feed programme. | - | Not opened |
| Spain, LatAm | Jobomas | https://www.jobomas.com/ | Not verified | Not verified | - | BLOCKED (403) |
| Spain, LatAm | Trabajo.org | see 1A | | | | |
| Brazil | Local boards (Catho, Vagas, InfoJobs, Trabalha Brasil) | - | Not verified | Not verified | - | Not opened |
| Brazil | Covered by | Jooble, Careerjet, Trovit, Mitula, Adzuna (BR), Jobijoba (BR), WhatJobs, Talent.com | | | | |
| Japan | Kyujinbox (求人ボックス) | https://xn--pckua2a7gp15o89zb.com/無料求人掲載 | Free crawler-based listing | For sites with many openings: employer career sites, staffing sites, and a link for operators of job sites. Listings must pass screening. Cannot be combined with its manual posting tool. | Contact page on the site | OPENED |
| Japan | Stanby | https://stanby.co.jp/ . Request form: https://cs-support.stanby.co.jp/contactus/s/faq-requestpublication | Not stated | Not stated on the page opened | Listing request form (certificate error from here, not opened) | Home page OPENED |
| India | Local boards (Naukri, Shine, foundit) | - | Not verified | Not verified | - | Not opened |
| India | Covered by | Adzuna (IN), Jooble, Careerjet, WhatJobs, Trovit, Talent.com | | | | |
| MENA | Bayt | https://www.bayt.com/en/employers/ | Not verified | Not verified | - | BLOCKED (403) |
| MENA | Covered by | Trovit and Mitula (UAE, Saudi Arabia, Qatar, Kuwait, Egypt, Morocco), Jooble, Careerjet, WhatJobs | | | | |
| Australia | Jora | see 1A (does not accept aggregated jobs) | | | | |
| Australia, South-East Asia | SEEK, JobStreet, Jobsdb | https://developer.seek.com/ | Job posting is a paid product | The SEEK API is for software providers and needs SEEK's approval. Nothing for aggregated jobs. | Integration request form: https://employer.seek.com/partners/integration-request/ | OPENED |
| South-East Asia | GrabJobs | https://grabjobs.co/ | Not verified | Not verified | - | BLOCKED (403) |
| Eastern Europe | Covered by | Jooble, Trovit (PL, RO, HU, CZ, UA), Careerjet, Adzuna (PL) | | | | |
| Eastern Europe | Profesia.sk | https://podpora.profesia.sk/367485-XML-Feed-Requirements | Not verified | Not verified | - | Not opened (redirect to another host) |
| Africa | Covered by | Careerjet, Jooble, Trovit and Mitula (South Africa, Nigeria, Kenya, Egypt, Morocco), Adzuna (ZA), WhatJobs, Google for Jobs (Sub-Saharan Africa) | | | | |
| Africa | Local boards (Jobberman, Careers24, Pnet, BrighterMonday) | - | Not verified | Not verified | - | Not opened |

---

## 2. Feed specifications

### 2.1 Jooble (OPENED, full)

Source: https://jooble.org/files/xml_feed_specifications.pdf (5 pages).

General rules:

- Declare the encoding in the XML header, for example utf-8.
- All job content must be inside CDATA sections.
- One common root tag. The example uses `jobs`.
- Each job sits in its own tag (`job` in the example). That tag must carry exactly one attribute, `id`, with the unique job ID.
- The feed must hold all current jobs published on the site.
- Crawler name: JoobleBot. It fetches the feed at least once every 24 hours. Time and frequency can be changed on request.
- Age rule: Jooble indexes only jobs published less than 45 days before it first indexed the feed. The rule reads `pubdate` and `updated`. With neither tag, a job is valid for 45 days from first indexing.
- No size limit is stated.
- Contact: xml_support@jooble.com

Elements inside the job tag:

| Element | Status in the PDF | Content |
|---|---|---|
| `link` | Required | Full URL of the job. Must open a page with the complete job description. |
| `name` | Required | Job title. |
| `region` | Required | List of regions or cities as text. Any punctuation may separate them. |
| `description` | Required | Complete job description with HTML formatting. Must include every section shown on the page (requirements, duties, conditions). Content and order must match the page behind `link`. |
| `pubdate` | Required | Original publication date. Format DD.MM.YYYY. |
| `updated` | Listed in the required box with one asterisk | Last modification date. Format DD.MM.YYYY. The PDF does not explain the single asterisk here. In the optional box the same mark is used for optional tags. Treat as recommended. |
| `salary` | Required if shown on your site (two asterisks) | Amount plus currency as text. The PDF's examples are of the form 300$, 1500€, 167£. Its sample feed uses £161/day. |
| `company` | Required if shown on your site | Employer name. |
| `expire` | Required if shown on your site | Expiry date. Format DD.MM.YYYY. |
| `jobtype` | Required if shown on your site | Free text such as full-time, part-time, contract, internship, temporary. |
| `company_logo` | Optional | URL of the logo. Height 15px, width over 40px. JPG, PNG or GIF. |
| `email` | Optional | Address for applications. Several addresses may be comma-separated; the first is used by default. |
| `paid` | Paid campaigns only | Marks a job for promotion, value True. Any tag name can be used for segmentation. |
| `cpc` | Paid campaigns only | CPC bid per job, for example 0.3. |
| `budget` | Paid campaigns only | Whole number, same value for all jobs of one campaign. |

What is missing in the Jooble format:

- No country element. Location is only the `region` text. Jooble runs one index per country, so plan one feed per country, or put the country name into `region` and ask Jooble how they want it.
- No remote element. Put "Remote" into `region` or `jobtype` text and ask Jooble.

Example written for this file (not copied from the PDF):

```xml
<?xml version="1.0" encoding="utf-8"?>
<jobs>
  <job id="gh-4512345">
    <link><![CDATA[https://example.com/jobs/gh-4512345-backend-engineer]]></link>
    <name><![CDATA[Backend Engineer]]></name>
    <region><![CDATA[Berlin, Germany]]></region>
    <description><![CDATA[<p>Full text, same as on the page.</p><ul><li>Duty one</li></ul>]]></description>
    <pubdate>02.11.2026</pubdate>
    <updated>10.11.2026</updated>
    <salary><![CDATA[70000-90000 EUR per year]]></salary>
    <company><![CDATA[Example GmbH]]></company>
    <expire>02.12.2026</expire>
    <jobtype><![CDATA[full-time]]></jobtype>
    <company_logo><![CDATA[https://example.com/logos/example.png]]></company_logo>
  </job>
</jobs>
```

### 2.2 Indeed (OPENED, full) - for reference only, Indeed does not accept aggregators

Sources: https://docs.indeed.com/job-sync-xml/xml-feed (last updated 2 Oct 2026) and https://docs.indeed.com/sponsored-jobs-api/shared-resources/xml-job-feed-format

General rules:

- XML declaration with encoding, for example utf-8. Root node `source`. One `job` node per job.
- Wrap values in CDATA. HTML in `description` goes inside CDATA.
- HTML entities are not supported. Use the literal characters.
- Every element used in the feed must appear in every job, even when empty.
- The feed must contain all jobs of the career site. Partial feeds are not accepted.
- Each job needs a unique `referencenumber`, a unique location and unique content. One entry per location or language.
- Allowed description HTML: `b`, `strong`, `em`, `h1` to `h6`, `br`, `p`, `ul`, `li`, simple tables.
- Fetch: a crawled URL or client-hosted FTP/SFTP is refreshed every six hours, four times a day. Indeed-hosted FTP is refreshed on upload, at most every two hours.
- No file size limit is stated. Compressed files are recommended for FTP upload.

Feed-level elements:

| Element | Status |
|---|---|
| `publisher` | ATS developers only |
| `publisherurl` | ATS developers only |
| `job` | Required, one per job |

Job elements:

| Element | Status | Format and notes |
|---|---|---|
| `title` | Required (not in Japan) | Title only. No salary, type, location. |
| `date` | Required | First publish date, ISO 8601, for example 2026-11-02T09:00:00Z. |
| `referencenumber` | Required | Unique ID per job entry. Never change it. |
| `requisitionid` | Required | Requisition ID. Shared across locations of the same role. |
| `apijobid` | Optional | Only if different from `requisitionid`. |
| `url` | Required | Job description page, not the application form. Add `source=Indeed`. |
| `company` | Required | Employer or brand name. |
| `sourcename` | Required for ATS developers | Parent organisation. |
| `city` | Required | |
| `state` | Required | US postal abbreviation such as CA; province or region elsewhere. |
| `country` | Required | Country code such as US. |
| `postalcode` | Required if on the career site | |
| `streetaddress` | Required if on the career site | |
| `email` | Required | Contact email tied to the client's Indeed account. |
| `description` | Required | Full HTML description, same content and order as the page. |
| `salary` | Required if on the career site | Free text, for example `$50000 per year` or `$4000 - $5000 per month`. Empty if none. |
| `education` | Required if on the career site | Free text. |
| `jobtype` | Required if on the career site | Comma-separated, for example `fulltime, parttime`. |
| `experience` | Required if on the career site | Free text, for example `5+ years`. |
| `expirationdate` | Required if on the career site | YYYY-MM-DD. Read as US Central time by default. |
| `category` | Optional, recommended | Comma-separated list. |
| `tracking_url` | Optional (not in Japan) | Called with GET on each click. |
| `remotetype` | Optional | `Fully remote`, `Hybrid remote`, or `COVID-19`. Does not set the location. |
| `lastactivitydate` | Optional | ISO 8601 timestamp. |
| `billingId` | Optional | Client's business unit ID. |
| `hide_from_indeed_search` | Optional (not in Japan) | `CONFIDENTIAL_JOB`, `TALENT_POOL`, `OPT_OUT`. |
| `indeed-apply-data` | Separate section | Indeed Apply configuration. |

Japan-only optional elements: `timeshift`, `subwayaccess`, `rawlocation`, `expdate`, `benefits`, `rawsalary`, `hires`, `keywords`, `imageUrls`.

Location rules: give at least `city`, `state`, `country`. For a statewide or countrywide job leave `city` and `postalcode` empty. For a fully remote job write "remote" in `city` or `state`.

Example written for this file:

```xml
<?xml version="1.0" encoding="utf-8"?>
<source>
  <job>
    <title><![CDATA[Backend Engineer]]></title>
    <date><![CDATA[2026-11-02T09:00:00Z]]></date>
    <referencenumber><![CDATA[gh-4512345]]></referencenumber>
    <requisitionid><![CDATA[4512345]]></requisitionid>
    <url><![CDATA[https://example.com/jobs/gh-4512345-backend-engineer?source=Indeed]]></url>
    <company><![CDATA[Example GmbH]]></company>
    <city><![CDATA[Berlin]]></city>
    <state><![CDATA[Berlin]]></state>
    <country><![CDATA[DE]]></country>
    <postalcode><![CDATA[]]></postalcode>
    <description><![CDATA[<p>Full text, same as on the page.</p>]]></description>
    <salary><![CDATA[70000 - 90000 EUR per year]]></salary>
    <jobtype><![CDATA[fulltime]]></jobtype>
    <category><![CDATA[Engineering]]></category>
    <expirationdate><![CDATA[2026-12-02]]></expirationdate>
    <remotetype><![CDATA[Hybrid remote]]></remotetype>
  </job>
</source>
```

The Indeed shape is worth generating anyway. Talent.com, LinkedIn and PostJobFree use the same root and very similar names.

### 2.3 Adzuna (INDEX only - the spec page showed a human-verification screen)

Spec URL: https://www.adzuna.co.uk/jobs/xml-specification.html . Everything below comes from a search engine's summary of that page. Open the page in a normal browser before coding.

- The feed is a well-formed XML document. Each ad sits in its own tag under one root element. Tag names for root and item were not visible in the summary.
- Unicode with a declared encoding is preferred.
- CDATA is optional. Without it, angle brackets and ampersands must be escaped.
- Compression with gz or zip is strongly preferred.
- Delivery: a URL (can be password-protected) or upload to Adzuna's FTP.
- Adzuna downloads the file at least once per day. Refresh it at least daily.
- No size limit seen.

| Element | Status | Notes |
|---|---|---|
| `title` | Mandatory | |
| `id` | Mandatory | Unique ad ID. |
| `description` | Mandatory | HTML formatted, at least 100 characters. |
| `url` | Mandatory | Unique job page where the user can apply online. |
| `location` | Mandatory | For a remote job use the country name, for example United Kingdom. |
| `country` | Mandatory | Two-letter code from the supported list. |
| `geo_lat`, `geo_lng` | Optional | Both must be present to be used. |
| `postcode` | Optional | Separate tag. |
| `salary_min`, `salary_max` | Optional | Numbers. |
| `salary_frequency` | Optional | `hour`, `day`, `month`, `year`. |
| `salary_currency` | Optional | Currency code. |
| `company` | Optional | |
| `category` | Optional | One per ad, as label or ID. 29 categories, from 1 (Accounting and Finance) to 29 (Other/General). |
| `contract_type` | Optional | Single value such as `permanent` or `contract`. |
| `contract_time` | Optional | `full_time` or `part_time`. |
| `date` | Optional | Initial publication date. Format not confirmed. |
| `remote` | Optional | `1`, `Yes`, `Remote` or `0`, `No`, `Non-Remote`. |
| `cpc` | Optional | Bid for programmatic campaigns. |

### 2.4 Talent.com (INDEX only - every talent.com page returned 403 from this network)

Spec URL: https://www.talent.com/integrations (page title "XML feed attributes"). Everything below comes from search engine summaries of that page. The summaries note copy-paste errors in the page itself. Open it in a normal browser before coding.

- Root node `source`. Each posting in a `job` element.
- All job content must be wrapped in CDATA.
- Talent.com reads a feed by crawling an XML URL or an FTP site.
- A tracking token such as `source=talent` may be added to the job URL.
- Crawl frequency: every 4 hours according to an ATS vendor (3RD).
- No size limit seen.

| Element | Level | Status | Notes |
|---|---|---|---|
| `publisher` | Feed | Optional | |
| `publisherurl` | Feed | Optional | |
| `lastbuilddate` | Feed | Optional | |
| `referencenumber` | Job | Required | Job ID from the ATS. |
| `title` | Job | Required | Title only, no location or job type. |
| `company` | Job | Required | No location or category in the name. |
| `city` | Job | Required | |
| `state` | Job | Required | |
| `country` | Job | Required | |
| `dateposted` | Job | Required | Suggested format yyyy-MM-ddTHH:mm:ssZ. |
| `url` | Job | Required | URL of the original listing. |
| `description` | Job | Required | Same text as the job source, HTML suggested, at least 50 characters. |
| `expirationdate` | Job | Recommended | |
| `streetaddress` | Job | Recommended | |
| `postalcode` | Job | Recommended | |
| `jobtype` | Job | Recommended | |
| `isremote` | Job | Recommended | yes or no. |
| `category` | Job | Recommended | |
| `logo` | Job | Recommended | PNG, suggested 128 x 128 pixels. |
| `experience` | Job | Recommended | Structured: minimum, maximum, period. |
| `salary` | Job | Recommended | Structured: max, min, currency, period, type. |
| `cpc` | Job | Recommended | For sponsored jobs. |

### 2.5 Careerjet (OPENED - there is no public spec)

- FAQ at https://www.careerjet.co.uk/faqs says: submit your website for free; a feed helps but is not needed; all feed types are supported; send your existing feed with the submission.
- No element list, date format, size limit or fetch frequency is published.
- Practical choice: send the Indeed-shape feed or the Jooble-shape feed.

### 2.6 Jobrapido (OPENED - the spec article is gone)

- The article that used to hold the spec (https://support.jobrapido.com/hc/en-us/articles/360019196973-FEED-XML-how-can-I-send-my-feed-to-Jobrapido) now returns 404. A search of the Jobrapido help centre finds no feed article.
- The partner page says only that integration is done through an XML feed.
- Expect to receive the format after the partnership request is accepted.

### 2.7 Other specs opened today (useful for the generator)

**Trovit and Mitula** (Thribee). Sources: https://help.thribee.com/hc/en-us/articles/7742955286300-Technical-specifications-for-Jobs and the per-country pages.

- UTF-8. Root `trovit`. One `ad` element per job. Values in CDATA in the official template.
- Required: `id`, `url`, `title`, `content` (at least 30 characters).
- Optional: `mobile_url`, `company`, `experience`, `requirements`, `studies`, `category`, `contract` (permanent, temporary, contract, internship), `working_hours` (full time, part time), `telecommute` (boolean), `salary` (free text, ranges allowed), `neighborhood`, `city_area`, `city`, `region`, `postcode`, `date`, `expiration_date`. The sample also shows a `time` element.
- Dates: DD/MM/YYYY or YYYY/MM/DD, with optional HH:MM:SS. The technical page also allows dashes.
- Boolean true: `true`, `yes`, `si`, `1`. False: `false`, `no`, `0`.
- No country element. One feed per country site.

**Jora**. Source: the support article in 1A.

- Root must be a single element (`jobs` or `source`), items `job`. No RSS. Zip and gzip accepted. CDATA optional. HTML or decimal entities only, no hex.
- Mandatory: `title`, `id`, `description` (with HTML tags), `url`, `location`.
- Optional: `city`, `state`, `postcode`, `country` (ISO 3166-1 preferred).
- Highly preferable: job type (the table says `job_type`, the sample uses `jobtype`), `listed_date` (ISO 8601), `closing_date` (ISO 8601), `salary` with children `type` (hourly, daily, weekly, monthly, yearly), `min`, `max`, `currency`, `additionalText`, and `organisation`.
- Hosting: HTTP or Amazon S3. No FTP.
- Fetch: every 2 to 24 hours. Jobs without expiry date expire after 60 days.
- Content rules: at most two invisible redirects, land on the job description page, apply within four clicks, no paywall.

**WhatJobs**. Source: https://www.whatjobs.com/xml-feed-specification

- Encoding in the header. All content in CDATA. One root tag. Each job in its own tag with a unique `id` attribute.
- Required list on the page: `id`, `link`, `title`, `city`, `region`, `state`, `country`, `language`, `description`, `CPC`, `pubdate`, `updated`, `salary`, `company`, `expire`, `jobtype`, `company_logo`. `location` appears in both the required and the optional list; either `location` or the city/region/state tags may be used.
- Optional: `joblocationtype` (remote; the value telecommute is also accepted), `category`, `location`, `zipcode`, `street`.
- Dates DD.MM.YYYY. Salary is amount plus currency as text.
- Description HTML: `p`, `ul`, `b`, `li`. Incomplete descriptions are rejected.
- Logo: SVG preferred, PNG up to 50 KB.
- Only jobs published less than 28 days ago are indexed.
- Crawler TheWhatBot fetches at least once every 24 hours.

**LinkedIn Basic Jobs**. Source: the development guide in 1B.

- Root `source`. Feed-level: `lastBuildDate`, `publisherUrl`, `publisher`, `expectedJobCount`.
- Mandatory per job: `partnerJobId` (max 40 characters), `title`, `description` (min 100 characters), `applyUrl`, `location` (or `city`, `state`, `country`), `posterEmail`; `company` when posting to several company pages; `companyId` for ATS partners.
- Optional: `alternateLocations/alternateLocation` (max 7), `postalCode`, `workplaceTypes` (`On-site`, `Hybrid`, `Remote`), `industryCodes/industryCode`, `experienceLevel`, `jobFunctions/jobFunction`, `jobtype` (`FULL_TIME`, `PART_TIME`, `CONTRACT`, `INTERNSHIP`, `VOLUNTEER`), `skills/skill`, `salaries/salary` with `highEnd` and `lowEnd` (`amount`, `currencyCode`), `period`, `type`, then `listDate` and `expirationDate` (MM/DD/YYYY), `jobPostingAvailability`.
- CDATA for HTML. No escaped entities. Allowed tags: `b`, `strong`, `u`, `i`, `br`, `p`, `ul`, `li`, `em`.
- Max 500,000 jobs per feed. Full list every time. Scraped every 6 hours for ATS partners and every 24 hours for job board partners.

### 2.8 Fields the main specs have in common

| Concept | Jooble | Indeed shape | Adzuna (INDEX) | Talent.com (INDEX) | Trovit, Mitula | Jora | WhatJobs |
|---|---|---|---|---|---|---|---|
| Root / item | `jobs` / `job id=""` | `source` / `job` | not confirmed | `source` / `job` | `trovit` / `ad` | `jobs` or `source` / `job` | one root / job tag with `id=""` |
| Unique ID | `id` attribute | `referencenumber` | `id` | `referencenumber` | `id` | `id` | `id` |
| Title | `name` | `title` | `title` | `title` | `title` | `title` | `title` |
| Job page URL | `link` | `url` | `url` | `url` | `url` | `url` | `link` |
| Description (HTML) | `description` | `description` | `description` | `description` | `content` | `description` | `description` |
| Employer | `company` | `company` | `company` | `company` | `company` | `organisation` | `company` |
| Location | `region` (text) | `city`, `state`, `postalcode`, `streetaddress` | `location`, `postcode`, `geo_lat`, `geo_lng` | `city`, `state`, `postalcode`, `streetaddress` | `city`, `city_area`, `region`, `postcode` | `location`, `city`, `state`, `postcode` | `city`, `region`, `state`, `location`, `zipcode`, `street` |
| Country | none | `country` (code) | `country` (code) | `country` | none (feed per country) | `country` (ISO) | `country` |
| Date posted | `pubdate` DD.MM.YYYY | `date` ISO 8601 | `date` | `dateposted` ISO-like | `date` DD/MM/YYYY | `listed_date` ISO 8601 | `pubdate` DD.MM.YYYY |
| Date updated | `updated` | `lastactivitydate` | - | - | - | - | `updated` |
| Expiry | `expire` DD.MM.YYYY | `expirationdate` YYYY-MM-DD | - | `expirationdate` | `expiration_date` | `closing_date` | `expire` |
| Salary | `salary` text | `salary` text | `salary_min`, `salary_max`, `salary_frequency`, `salary_currency` | `salary` structured | `salary` text | `salary` structured | `salary` text |
| Job type | `jobtype` text | `jobtype` list | `contract_type`, `contract_time` | `jobtype` | `contract`, `working_hours` | `jobtype` / `job_type` | `jobtype` |
| Remote | none | `remotetype` | `remote` | `isremote` | `telecommute` | none | `joblocationtype` |
| Category | none | `category` | `category` | `category` | `category` | - | `category` |
| Logo | `company_logo` | - | - | `logo` | - | - | `company_logo` |
| CDATA | Required | Required | Optional | Required | Used in template | Optional | Required |
| Fetch frequency | At least every 24 h | Every 6 h | At least daily | Every 4 h (3RD) | Not stated | Every 2 to 24 h | At least every 24 h |
| Max job age | 45 days | - | - | - | - | 60 days if no expiry | 28 days |
| Min description | Complete text | Complete text | 100 chars | 50 chars | 30 chars | - | Complete text |

### 2.9 Advice for the generator

- Keep one internal job record with: stable ID, title, employer, full HTML description, own job page URL, city, region, postcode, country code, country name, remote flag (remote, hybrid, on-site), posted date, updated date, expiry date, salary min, salary max, currency, period, job type, category, logo URL.
- Write one small renderer per target: Jooble shape, Indeed shape (covers Talent.com, PostJobFree and "any feed" Careerjet), Trovit shape, Adzuna field set.
- Always: UTF-8 with declaration, CDATA around every text value, split any `]]>` inside text, literal characters instead of HTML entities, simple HTML only (`p`, `br`, `ul`, `li`, `b`, `strong`, `em`).
- The description in the feed must be the same text as on the job page. Several aggregators check this.
- The URL must open our job page that shows the full description without login.
- Remove closed jobs from the feed. Do not mark them as filled.
- Never reuse an ID. Keep the same ID for the same job on every run.
- Drop or flag jobs older than 28 days for WhatJobs and 45 days for Jooble.
- Skip jobs with a description under 100 characters.
- Jooble and Trovit have no country element: produce one feed file per country for them. One global file is fine for the Indeed shape and for Adzuna (19 countries only).
- Offer gzip copies. Adzuna prefers them (INDEX). Jora accepts them.
- Regenerate at least every 6 hours. The fastest readers documented are Jora (as often as every 2 h), Talent.com (4 h, 3RD) and Indeed (6 h).
- Add a tracking parameter per target to the job URL, for example `utm_source=jooble`. Jora and Talent.com mention this.

---

## 3. Where to apply first

Ranking rule: free first, then open to job boards, then traffic and country reach. Items whose terms could not be read today are marked.

| # | Name | Apply here | Free or paid | Why |
|---|---|---|---|---|
| 1 | Google for Jobs | No application. Spec: https://developers.google.com/search/docs/appearance/structured-data/job-posting | Free | Largest reach, works worldwide, needs only `JobPosting` markup and a sitemap. Watch the authorization policy line. |
| 2 | Careerjet | https://www.careerjet.com/recruiter/indexing/submit-your-website | Free | Over 90 countries. The FAQ says site submission is free and any feed type is fine. |
| 3 | Jooble | https://jooble.org/partner/ppc | Crawler indexing free; feed-partner packages from $200 (from $500 for multi-country) | 66 to 67 countries. Public spec. The form lists job sites and aggregators as partner types. Ask for organic inclusion first. |
| 4 | Adzuna | https://www.adzuna.co.uk/hire/contact/ | Free for an organic feed (opened page) | 19 markets including US, UK, DE, FR, IN, BR (INDEX). Confirm that aggregated jobs are allowed. |
| 5 | Talent.com | https://www.talent.com/contact (spec: https://www.talent.com/integrations) | Organic feed reported free (3RD); not verified | 79 countries. Indeed-shape feed. Terms not readable from this network. |
| 6 | Trovit and Mitula (Lifull Connect) | Email thribee.salesinfo@lifullconnect.com | Free; CPC optional | 57 countries in its feed-spec table, including Spain, Italy, LatAm, India, Gulf states and several African countries. Simple public spec. |
| 7 | Jobrapido | https://support.jobrapido.com/hc/en-us/requests/new | Terms on request | 58 countries. States that it partners with job boards for traffic. |
| 8 | Jobijoba | https://www.jobijoba.com/fr/contact | Not stated | France plus 12 countries. Contact form only. |
| 9 | PostJobFree | https://www.postjobfree.com/include-job-feed | Free only for hard-to-find jobs; else $0.10 to $0.50 per click | Simple form, Indeed-shape feed, US traffic. |
| 10 | Bundesagentur für Arbeit Jobbörse | Email service-haus.vam-accountmgmt@arbeitsagentur.de | Free | Germany's public job portal has a cooperation model for job boards. Heavy paperwork. Only worth it for German jobs. |

Next in line if a budget appears: WhatJobs (77 countries, CPC required).

Candidates that could not be judged today because their sites were blocked: Jobsora, Jobted, Recruit.net, Joblift, Jobtome, JobisJob, Kimeta. Check them from a normal browser.

Do not spend time on: Indeed, LinkedIn, Jora (rules exclude aggregated jobs), SEEK/JobStreet (software partner API only), Himalayas, Remote OK, Remotive (outbound only).

---

## 4. Not opened or not verified

| Item | What happened | What is therefore unknown |
|---|---|---|
| Adzuna spec page https://www.adzuna.co.uk/jobs/xml-specification.html | Human-verification screen (HTTP 405) in the browser, 403 in the fetch tool. The mirror host static.dev.adzuna.co.uk did not resolve. | Exact root and item tag names, date format, example, contact address. Section 2.3 is from a search summary. |
| Adzuna rule on aggregated jobs | Not on any opened page. Third-party claim only. | Whether a board like ours is accepted, and whether a $600 minimum applies. |
| Talent.com: www.talent.com/integrations, /publishers, ca.talent.com, feeds.talent.com | HTTP 403 (CloudFront block) in both tools. Only employers.talent.com/publishers opened. | Full spec, eligibility rules, pricing, how to submit. Section 2.4 is from search summaries. |
| Careerjet form page /recruiter/indexing/submit-your-website (.com and .co.uk) | Bot verification page. | Form fields and any rules shown on the form. |
| Jobrapido spec article 360019196973 | HTTP 404. | The whole Jobrapido feed format. |
| Jobsora https://uk.jobsora.com/jobsora-xml.pdf and https://jobsora.com/ | Cloudflare check / 403. | Everything. |
| Jobted (jobted.com, uk.jobted.com) | Connection dropped; browser navigation failed. | Everything. |
| Recruit.net | Cloudflare check (403). | Everything. |
| JobisJob | HTTP 403. | Everything, including whether the site still runs a partner programme. |
| Joblift | Human-verification screen. | Everything. |
| Jobtome | Redirect to a captcha page. | Everything. |
| Kimeta (kimeta.de, feedvalidation.kimeta.de) | HTTP 503 on three tries. | Everything. |
| ZipRecruiter partner docs | Cloudflare check. | Feed import spec and eligibility. |
| Monster partner site | Blocked by its firewall. | Feed spec, eligibility, the 50 MB limit seen in a search summary. |
| SimplyHired, CareerBuilder, Bayt, GrabJobs, Jobomas | HTTP 403. | Everything. |
| Glassdoor | Not opened. | Whether it still takes any feed; a vendor guide says jobs are pushed from Indeed. |
| StepStone | Timeout. | Pricing and any feed programme. |
| Stanby request form (cs-support.stanby.co.jp) | Certificate error. | Conditions for job sites, feed format. |
| Kyujinbox | Page opened, but it gives no feed format. | Whether an XML feed is accepted and its fields. |
| France Travail | Page opened, but no route to become a partner is given. | Application process and feed format. |
| Himalayas and Remote OK employer pages | 404 / redirect not followed. | Posting price and any import from ATS. |
| Computrabajo, local boards in Brazil, India, Africa, Eastern Europe (Catho, Vagas, InfoJobs, Naukri, Shine, foundit, Jobberman, Careers24, Pnet, Pracuj, Jobs.cz, Profesia) | Not opened. | Everything. Whether any of them takes a feed from a job board was not checked today. |
| Jooble: free organic inclusion of a submitted feed | The partner page lists only paid packages. The help centre says the crawler indexes public job boards. | Whether Jooble will take our feed without a paid package. |
| Jooble: meaning of the single asterisk on `updated` | Not explained in the PDF. | Whether `updated` is strictly required. |
| Indeed organic rules for job boards outside the help article | Only the help article and docs were read. | Any private partner terms. |
| Size limits | Not stated by Jooble, Indeed, Jora, WhatJobs, Trovit. Only LinkedIn states 500,000 jobs per feed. | Real limits for Adzuna, Talent.com, Careerjet, Jobrapido. |

---

## 5. Pages opened today

- Jooble: https://jooble.org/files/xml_feed_specifications.pdf , https://jooble.org/partner/ppc , https://jooble.org/partner/advertise , https://jooble.org/jooble-bot , https://help.jooble.org/en/support/home and two partner articles
- Careerjet: https://www.careerjet.co.uk/partners/ , /recruiter/indexing , /recruiter/indexing/ppc-campaign , /recruiter/ats , /faqs , /about-us , /partners/publishers
- Adzuna: https://www.adzuna.co.uk/hire/products/job-listings/ , https://www.adzuna.com/hire/products/ , https://www.adzuna.co.uk/hire/partners/ , https://developer.adzuna.com/
- Talent.com: https://employers.talent.com/publishers
- Jobrapido: https://support.jobrapido.com/hc/en-us (section "Are you a company?" and its four articles), https://corporate.jobrapido.com/ , https://corporate.jobrapido.com/partner-program/
- Jora: the two support articles listed in 1A
- WhatJobs: https://www.whatjobs.com/xml-feed-specification , https://www.whatjobs.com/international , https://www.whatjobs.com/contact/business (read only)
- Thribee: help centre home, feed-spec section, jobs technical spec, Canada jobs feed, upload article, pricing, partner plans
- Indeed: https://docs.indeed.com/job-sync-xml/xml-feed , https://docs.indeed.com/indeed-apply/xml-feed , https://docs.indeed.com/sponsored-jobs-api/shared-resources/xml-job-feed-format , https://docs.indeed.com/job-sync-api/ , https://uk.indeed.com/help/employers/articles/360018069792 , https://uk.indeed.com/help/employers/articles/single-source-feed-policy-effective-march-31-2026 , https://ca.indeed.com/leadershiphub/how-search-quality-works-at-indeed
- LinkedIn: the three Microsoft Learn pages in 1B plus https://learn.microsoft.com/en-us/linkedin/talent/job-postings/xml-feeds-faq
- Google: the three developer pages in 1B plus https://developers.google.com/search/apis/indexing-api/v3/using-api
- Others: https://www.postjobfree.com/include-job-feed , https://www.jobadx.com/docs/developer/advertisers-xml-feed-specifications/ , https://www.talroo.com/publisher/job-boards/ , https://himalayas.app/api , https://remoteok.com/api , https://github.com/remotive-io/remote-jobs-api , https://jobgether.com/ , https://www.arbeitsagentur.de/unternehmen/arbeitskraefte/hr-ba-xml-schnittstelle , https://www.francetravail.fr/candidat/vos-services-en-ligne/des-partenaires-pour-vous-propos.html , https://recruteur.hellowork.com/fr/ , https://www.jobijoba.com/fr/ , https://www.jobijoba.com/fr/contact , https://www.jobijoba.com/fr/affiliation-offres-emploi , https://stanby.co.jp/ , https://biz-help.stanby.com/ , https://xn--pckua2a7gp15o89zb.com/無料求人掲載 , https://developer.seek.com/ , https://www.trabajo.org/
- Third-party pages used as hints only: https://jboard.io/blog/job-feeds , https://cavuno.com/docs/xml-feeds , https://support.exacthire.com/talent.com-job-board-integration-qa , https://support.teamdash.com/en/articles/9691394-talent-com
