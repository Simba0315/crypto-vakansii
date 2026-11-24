"""Example resumes, one per kind of work.

Resume builders get most of their search traffic from pages like "data analyst resume example". Ours differ in one thing: next to
the example stands what employers ask for in today's open postings for that work, counted on every build.

The example itself is invented and says so: a made-up person ("Alex Example"), made-up employers and made-up numbers. Every kind
of work has its own entry in ROLE: the title the person carries, the skills in plain words, four achievements. An achievement is
written the way a good resume line is: a verb first, one result, one number.

A tool may stand in a line only through a typed place such as {lang:Python}: the first skill of that kind that today's postings
for the role really name goes there, and the word after the colon is used when they name none. Never put a skill into a line any
other way: "designed a housing in Python" is what a place without a kind produces.

Search results for such pages show the same work at several levels, so every kind of work in ROLE also has three lines for a
beginner and three for someone senior, written by the same rules (a verb first, a number in each, tools only through typed places,
at most 160 characters):
- ENTRY: what a beginner can honestly have, in this order: a course, bootcamp or personal project; an internship, placement or
  first job; volunteer or part-time work. The scale stays small: a student project does not serve 1,200 requests a second.
- SENIOR: what someone years further on has, in this order: leading a team; owning a strategy or a large program; hiring and
  mentoring, or a result reached together with other teams.
- ENTRY_TITLE: the beginner's title, only where it is not simply "Junior" before the title in ROLE (a Staff Accountant, not a
  Junior Senior Accountant; a Line Cook, not a Junior Sous Chef). For the rest the build puts "Junior" in front.

The skill tags of the collector are all technical. For work in TECH they say what the employer wants and lead the skills line and
the chart. For other work a tag mostly describes the employer (a recruiter's posting at a machine learning company), so only the
office tools in OFFICE are counted there.

Kinds of work written later (MORE, resume_examples_more.json). Why (20 Nov 2026): 248 of the 390 example pages had no entry of their
own and showed the lines of their field, so the actuary example "ran the yearly budget for 14 departments". Their entries were
drafted by Claude in one batch (ai_fill.py) under the rules above, each line checked by line_problem() before it was kept, then read
through. They are added to ROLE, ENTRY, SENIOR, ENTRY_TITLE and TECH below and pass the same test(); an entry written here by hand
always wins over one in the file.
"""
import json, re
from pathlib import Path

KIND = {
    "lang": ["Python", "Go", "Java", "C++", "TypeScript", "JavaScript", "Rust", "Ruby", "Kotlin", "C#", "Scala", "Swift", "PHP", "Elixir"],
    "front": ["React", "Vue", "Angular", "Next.js"],
    "mobile": ["Kotlin", "Swift", "React Native", "Flutter"],
    "cloud": ["AWS", "GCP", "Azure"],
    "orch": ["Kubernetes"],
    "iac": ["Terraform"],
    "rel": ["PostgreSQL", "MySQL"],
    "wh": ["Snowflake"],
    "queue": ["Kafka"],
    "airflow": ["Airflow"],
    "dbt": ["dbt"],
    "bi": ["Tableau", "Looker"],
    "ml": ["PyTorch", "TensorFlow"],
    "crm": ["Salesforce", "HubSpot"],
    "sheet": ["SQL", "Excel"],
    "design": ["Figma"],
    "os": ["Linux"],
}
OFFICE = {"SQL", "Excel", "Tableau", "Looker", "Jira", "HubSpot", "Salesforce", "Figma", "SEO", "Agile", "AML/KYC", "Trading", "Snowflake", "dbt"}

# kind of work -> (title on the resume, skills in plain words, four achievements)
ROLE = {
    # software
    "software-engineer": ("Software Engineer", "code review, system design, automated testing", [
        "Rebuilt the order service in {lang:Python}, cutting median response time from 480 ms to 190 ms at the same traffic",
        "Raised automated test coverage of the payment code from 41% to 86%; releases rolled back fell from 5 a quarter to 1",
        "Split a 300,000-line application into 6 services, so 4 teams now release independently",
        "Reviewed about 20 code changes a week and mentored 3 junior engineers"]),
    "backend-engineer": ("Backend Engineer", "API design, database tuning, on-call", [
        "Designed and built a payments API in {lang:Go} that serves 1,200 requests a second with 99.98% availability",
        "Rewrote the 12 slowest {rel:PostgreSQL} queries; the slowest page went from 3.1 s to 400 ms",
        "Moved 14 scheduled jobs to a queue on {queue:Kafka}, ending a nightly failure that cost about 6 hours a week",
        "Cut the cloud bill of the service by 31% by caching the 5 most requested responses"]),
    "frontend-engineer": ("Frontend Engineer", "accessibility, web performance, component libraries", [
        "Rebuilt the checkout pages in {front:React}; page load on a mid-range phone fell from 4.2 s to 1.6 s",
        "Built a library of 40 components now used by 5 teams",
        "Fixed 120 accessibility problems; the site passed an outside WCAG 2.2 AA audit",
        "Added end-to-end tests for the 15 main user paths; visual bugs reaching production fell by 70%"]),
    "full-stack-engineer": ("Full-Stack Engineer", "API design, relational databases, automated testing", [
        "Built team billing end to end, from the {rel:PostgreSQL} schema to the {front:React} screens, in 9 weeks; it now brings 18% of new revenue",
        "Replaced page reloads with live updates on the dashboard; time spent in the product rose 22%",
        "Cut the build from 14 minutes to 4 by splitting the bundle and caching dependencies",
        "Shipped 30 customer-requested fixes in a quarter as the engineer on the support rotation"]),
    "mobile-engineer": ("Mobile Engineer", "app releases, offline storage, crash monitoring", [
        "Rebuilt the home screen in {mobile:Kotlin}; cold start fell from 3.4 s to 1.2 s",
        "Raised the crash-free rate from 98.1% to 99.8% across 600,000 monthly users",
        "Added offline mode, used in 31% of sessions within two months",
        "Moved releases from monthly to weekly with staged rollouts and automated screenshot tests"]),
    "qa-engineer": ("QA Engineer", "test planning, test automation, bug triage", [
        "Automated 420 regression tests in {lang:Python}; a full run takes 18 minutes instead of 2 days by hand",
        "Cut bugs found by customers from 34 a quarter to 9",
        "Made a failed test block the release; rollbacks fell from 6 a quarter to 1",
        "Wrote the test plan for a payments launch in 4 countries; it shipped with no critical defect"]),
    "embedded-engineer": ("Embedded Software Engineer", "firmware, real-time systems, hardware debugging", [
        "Wrote firmware in {lang:C++} for a sensor board; power draw fell 28% and battery life rose from 9 months to 12",
        "Cut boot time from 4.5 s to 1.1 s by reordering driver start-up",
        "Built over-the-air updates used on 40,000 devices with no device lost",
        "Found a memory fault that appeared once in 3 weeks of running; field returns fell by a third"]),
    "engineering-manager": ("Engineering Manager", "hiring, planning, one-to-ones, incident reviews", [
        "Led a team of 9 engineers that delivered 11 of 12 quarterly commitments, up from 7 the year before",
        "Hired 6 engineers in a year with a median time to hire of 38 days; none left in the first year",
        "Cut the time from finished code to production from 9 days to 2 by removing two manual approvals",
        "Moved two engineers to senior level through written growth plans reviewed each month"]),
    "web-developer": ("Web Developer", "HTML and CSS, page speed, content management systems", [
        "Rebuilt the marketing site as 60 static pages; load time fell from 3.8 s to 1.1 s and sign-ups from search rose 24%",
        "Built 25 landing page templates that marketers now publish without a developer",
        "Raised the share of pages passing Core Web Vitals from 48% to 96%",
        "Moved 400 pages to a new content system with every old address redirected and no loss of search traffic"]),
    "product-engineer": ("Product Engineer", "talking to customers, prototyping, A/B tests", [
        "Shipped saved searches from first sketch to release in 5 weeks; 34% of weekly users now use it",
        "Spoke to 20 customers before building import; setup time fell from 2 hours to 10 minutes",
        "Ran 8 A/B tests on onboarding; 3 shipped and raised activation from 38% to 47%",
        "Removed a settings page used by under 1% of customers and the 2,000 lines behind it"]),
    "systems-software": ("Systems Software Engineer", "operating systems, concurrency, performance profiling", [
        "Rewrote the storage engine’s write path in {lang:C++}; throughput rose from 40,000 to 110,000 writes a second on the same hardware",
        "Fixed a lock contention problem that cut 99th-percentile latency from 85 ms to 12 ms",
        "Reduced the memory used by the query planner by 35%",
        "Wrote a fault-injection test suite that found 14 crash bugs before release"]),
    "graphics-engineer": ("Graphics Engineer", "rendering, shaders, GPU profiling", [
        "Rewrote the shadow pass; frame time on a mid-range GPU fell from 21 ms to 13 ms",
        "Added a level-of-detail system that cut the memory used by large scenes by 40%",
        "Built a shader debugging tool that artists use daily; shader bugs passed to engineers fell by half",
        "Ported the renderer to a second graphics API in 4 months with the same image output"]),
    "game-developer": ("Gameplay Programmer", "gameplay systems, game engines, performance profiling", [
        "Built the combat system in {lang:C++} for a game played by 2 million people in its first month",
        "Raised the frame rate on the oldest supported console from 24 to a steady 30 by reworking how enemies are updated",
        "Wrote tools that let designers tune 300 values without a programmer; tuning a level went from days to hours",
        "Cut loading time between levels from 28 s to 9 s"]),
    "tech-lead": ("Tech Lead", "technical direction, code review, mentoring, planning", [
        "Led a team of 6 engineers that rebuilt the checkout in {lang:Java}; conversion rose from 2.1% to 2.6% in the first quarter",
        "Introduced design reviews for every change over a week of work; production incidents fell from 9 to 3 a quarter",
        "Planned each quarter with product and design; the team delivered 11 of 12 committed goals in 2025",
        "Mentored 2 engineers to senior level and hired 3 more, each through a structured interview loop"]),
    "software-architect": ("Software Architect", "system design, technical strategy, design reviews", [
        "Designed the move from one database to per-service storage; the platform now handles 5 times the load at the same cost",
        "Wrote the reference design used by 12 teams; a new service reaches production in 2 days instead of 3 weeks",
        "Led 40 design reviews a year; 6 projects changed course before any code was written",
        "Planned and ran the move of 80 services to {cloud:AWS} with 20 minutes of total downtime"]),
    "developer-advocate": ("Developer Advocate", "technical writing, public speaking, sample code", [
        "Wrote 30 tutorials read 400,000 times in a year; sign-ups that start from documentation rose 45%",
        "Built 12 sample applications; the time for a new developer to make a first API call fell from 40 minutes to 6",
        "Spoke at 14 conferences and ran 9 workshops for 1,100 developers",
        "Collected 200 pieces of developer feedback; 35 became product changes"]),
    "automation-engineer": ("Integration Engineer", "APIs, data mapping, monitoring", [
        "Built 18 integrations between the product and customers’ systems in {lang:Python}; a typical one takes 4 days instead of 3 weeks",
        "Automated a manual data transfer that took 2 people 10 hours a week",
        "Added retries and alerts to every integration; failed transfers fell from 3% to 0.2%",
        "Wrote a test harness that replays 5,000 real messages before each release"]),
    "business-systems": ("Business Systems Analyst", "requirements, process mapping, system administration, user training", [
        "Rebuilt quote-to-cash in {crm:Salesforce}; a quote takes 10 minutes instead of 2 days",
        "Connected the billing and accounting systems, removing 1,200 manual entries a month",
        "Collected requirements from 6 departments and delivered 40 changes a quarter with a backlog under 3 weeks",
        "Trained 150 users on the new system; support requests about it fell by half within 2 months"]),
    # AI and machine learning
    "machine-learning-engineer": ("Machine Learning Engineer", "model training, evaluation, model serving", [
        "Trained a ranking model in {ml:PyTorch} that raised click-through on search results from 21% to 27% in an A/B test",
        "Cut training cost by 38% with mixed precision and smaller batches",
        "Built an evaluation set of 4,000 labelled examples; regressions are now caught before release",
        "Put the model behind an API that answers 900 requests a second in 60 ms"]),
    "ai-engineer": ("AI Engineer", "prompt design, retrieval, evaluation, cost control", [
        "Built a support assistant on a large language model that resolves 41% of questions without a person",
        "Raised answer accuracy from 72% to 91% on 1,500 real questions by adding retrieval from the help center",
        "Cut the cost of a conversation by 60% by routing simple questions to a smaller model",
        "Wrote automatic checks that score every release on 600 cases before it reaches customers"]),
    "forward-deployed-engineer": ("Forward Deployed Engineer", "customer discovery, data integration, rapid prototyping", [
        "Worked on site with 5 enterprise customers; each went from signed contract to daily use in under 8 weeks",
        "Built a data pipeline in {lang:Python} joining 9 of a customer’s systems; a weekly report that took 3 days is ready each morning",
        "Turned 4 one-off customer solutions into product features now used by 60 accounts",
        "Grew one account from a $200K pilot to a $1.8M contract"]),
    "applied-ai": ("Applied AI Engineer", "workflow analysis, prompt design, evaluation, training colleagues", [
        "Put AI assistants into 6 internal workflows; the sales team saves about 5 hours a person each week",
        "Built an agent that drafts replies to 70% of support tickets; agents send 58% of drafts unchanged",
        "Measured each workflow before and after; 2 that showed no gain were switched off",
        "Trained 180 colleagues to write prompts; weekly active use rose from 22% to 74%"]),
    "computer-vision": ("Computer Vision Engineer", "image models, data labelling, model optimization", [
        "Trained a detection model that finds defects on a production line with 98.4% recall, up from 91%",
        "Cut inference time from 80 ms to 22 ms so the model runs on the camera itself",
        "Set up labelling that produced 120,000 images in 3 months at 97% agreement between labellers",
        "Reduced false alarms by 63% by adding hard examples from night shifts"]),
    "mlops": ("ML Platform Engineer", "model serving, training pipelines, GPU scheduling", [
        "Built the platform 40 researchers use to train models; starting a job takes 2 minutes instead of half a day",
        "Raised GPU use from 45% to 82% with a shared queue, saving about $1.2M a year",
        "Cut model release time from 2 weeks to 1 day with automated evaluation and staged rollout",
        "Set up monitoring that caught 5 cases of model drift before customers noticed"]),
    "research-scientist": ("Research Scientist", "experiment design, deep learning, scientific writing", [
        "Proposed and tested a training method that improved accuracy on the team’s main benchmark by 3.2 points",
        "Published 4 papers at peer-reviewed conferences, 2 as first author",
        "Ran 200 controlled experiments; the results set the direction of the next model",
        "Released an evaluation suite now used by 6 teams"]),
    "ai-trainer": ("AI Training Specialist", "writing guidelines, quality review, data labelling, fact checking", [
        "Wrote and reviewed 3,000 training examples in a quarter with a 97% acceptance rate at audit",
        "Wrote the guidelines used by 60 annotators; agreement between annotators rose from 71% to 89%",
        "Found 14 recurring model errors and wrote test cases for each",
        "Checked 500 model answers a week against their sources"]),
    # data
    "data-engineer": ("Data Engineer", "data modeling, pipelines, data quality", [
        "Built pipelines in {airflow:Airflow} that load 2 billion rows a day; data is ready by 6 am instead of noon",
        "Moved the warehouse to {wh:Snowflake}; query cost fell 34% and the slowest dashboard loads in 4 s instead of 50",
        "Added 180 data quality checks; wrong numbers reaching reports fell from 9 a month to 1",
        "Documented 60 tables so a new analyst answers a first question in a day instead of a week"]),
    "data-scientist": ("Data Scientist", "statistics, experiment design, machine learning", [
        "Built a churn model in {lang:Python} that finds 62% of leaving customers a month ahead; the retention team kept $900K of revenue with it",
        "Designed and read 25 A/B tests; 9 shipped and raised revenue per visitor by 6%",
        "Showed that a planned discount would lose money; it was dropped",
        "Built a demand forecast that stayed within 5% of actual sales for 8 quarters"]),
    "data-analyst": ("Data Analyst", "dashboards, statistics, presenting findings", [
        "Built a revenue dashboard in {bi:Tableau} used by 40 people each week; monthly reporting went from 3 days to 4 hours",
        "Found a pricing error with a check in {sheet:SQL} that had cost about $18K a month; it was fixed within the week",
        "Read 12 A/B tests; 5 shipped and lifted trial-to-paid conversion from 6.1% to 7.4%",
        "Answered about 15 questions a week from sales and product, most within a day"]),
    "analytics-engineer": ("Analytics Engineer", "data modeling, testing, documentation", [
        "Rebuilt 140 reporting models in {dbt:dbt} with tests on every one; conflicting numbers between dashboards fell to zero",
        "Defined 25 company metrics in one place; finance and product now report the same revenue figure",
        "Cut the daily build from 3 hours to 35 minutes",
        "Taught 12 analysts to add their own models through code review"]),
    "business-analyst": ("Business Analyst", "requirements, process mapping, stakeholder interviews", [
        "Mapped the order process across 4 departments and removed 6 of 15 steps; an order is confirmed in 1 day instead of 4",
        "Wrote requirements for a billing change delivered on time with 2 change requests instead of the usual 10",
        "Built a report in {sheet:SQL} that showed 8% of invoices went out late; cash now arrives 5 days sooner",
        "Ran 30 interviews with users before a system change; adoption reached 90% in the first month"]),
    "quant": ("Quantitative Researcher", "statistics, time series, backtesting", [
        "Researched and launched 3 trading signals that added 4 points of yearly return to the strategy",
        "Built a backtesting tool in {lang:Python} that tests an idea on 10 years of data in 6 minutes instead of 2 hours",
        "Cut trading costs by 18% with a better model of market impact",
        "Rejected 40 ideas that failed out-of-sample tests before any capital was put behind them"]),
    "pricing": ("Pricing Analyst", "price testing, elasticity analysis, financial modeling, competitor research", [
        "Ran 6 price tests; a new plan structure raised revenue per customer by 11% with no rise in cancellations",
        "Built a model of price sensitivity for 40 products from 2 years of sales",
        "Cut the average discount given by sales from 22% to 14% with a clear approval table",
        "Tracked 15 competitors’ prices each month; 3 findings changed our own"]),
    "research-analyst": ("Research Analyst", "desk research, interviews, data analysis, report writing", [
        "Wrote 24 research reports a year read by 300 clients",
        "Sized a new market at $400M from public filings and 30 interviews; the company entered it the next year",
        "Built a database of 500 competitors, updated each quarter",
        "Briefed the leadership team each month in 5 pages"]),
    "data-governance": ("Data Governance Analyst", "data catalogs, data quality rules, access policies", [
        "Cataloged 1,200 tables with an owner and a description for each; finding the right table takes minutes instead of hours",
        "Wrote quality rules for the 50 most used tables; failed checks fell from 14% to 2%",
        "Removed access to personal data from 300 accounts that did not need it",
        "Took the data platform through a privacy audit with no findings"]),
    # cloud, DevOps and IT
    "devops-engineer": ("DevOps Engineer", "release pipelines, infrastructure as code, monitoring", [
        "Moved 35 services to {orch:Kubernetes}; a deploy takes 6 minutes instead of 40",
        "Described the whole infrastructure in {iac:Terraform}; a new environment takes 20 minutes, not 2 days",
        "Set up alerts that cut the time to notice an outage from 25 minutes to 3",
        "Lowered the monthly {cloud:AWS} bill by 23% by right-sizing 120 instances"]),
    "site-reliability-engineer": ("Site Reliability Engineer", "incident response, capacity planning, service level objectives", [
        "Raised availability of the main API from 99.9% to 99.99% over a year",
        "Led 30 incident reviews; repeat incidents fell from 9 a quarter to 2",
        "Cut pages to the on-call engineer from 60 a week to 8 by removing alerts that needed no action",
        "Ran quarterly failure drills on {orch:Kubernetes}; recovery from losing a region takes 4 minutes instead of 45"]),
    "it-support": ("IT Support Specialist", "device management, account administration, network troubleshooting, ticketing", [
        "Resolved about 45 requests a week for 400 employees; 85% were closed the same day",
        "Set up laptops and accounts for 120 new hires, each ready on the first morning",
        "Wrote 40 self-help articles; password and VPN tickets fell by a third",
        "Rolled out two-step sign-in to every employee in 6 weeks"]),
    "systems-engineer": ("Systems Engineer", "identity management, scripting, device management", [
        "Automated account creation across 30 applications; onboarding takes 15 minutes instead of 3 hours",
        "Moved 500 employees to single sign-on with no lost working day",
        "Wrote {lang:Python} scripts that patch 800 laptops; devices behind on updates fell from 26% to 3%",
        "Cut software license costs by $210K by removing unused seats"]),
    "cloud-engineer": ("Cloud Engineer", "networking, infrastructure as code, cost control", [
        "Built the {cloud:AWS} foundation for 60 services: networks, accounts and access rules, all in {iac:Terraform}",
        "Cut the cloud bill by 27% with reserved capacity and by switching off idle resources",
        "Moved 25 services out of a data center with under 10 minutes of downtime each",
        "Set up a second region; the platform now survives the loss of one"]),
    "network-engineer": ("Network Engineer", "routing and switching, firewalls, wireless networks, network monitoring", [
        "Redesigned the network for 12 offices; outages fell from 14 a year to 2",
        "Replaced the VPN for 2,000 users; reported connection problems fell by 70%",
        "Automated the configuration of 300 switches with {lang:Python}; a change takes 10 minutes instead of a day",
        "Raised wireless coverage in the head office from 81% to 99% of desks"]),
    "database-administrator": ("Database Administrator", "backups and recovery, query tuning, replication", [
        "Ran 60 {rel:PostgreSQL} databases holding 14 TB with 99.99% availability",
        "Tuned the 20 slowest queries; average response time fell by 65%",
        "Tested restore from backup every month; recovery takes 20 minutes instead of 4 hours",
        "Upgraded every database by two major versions with under 5 minutes of downtime each"]),
    "data-center": ("Data Center Technician", "server hardware, cabling, hardware diagnostics, safety procedures", [
        "Installed and cabled 1,400 servers in 6 months with no rework at inspection",
        "Replaced about 30 failed parts a week, each within the 4-hour target",
        "Found the cause of repeated overheating in one row; failures there fell by 80%",
        "Trained 5 new technicians on safety and handling procedures"]),
    "support-engineer": ("Technical Support Engineer", "troubleshooting, reading logs, APIs, writing to customers", [
        "Solved about 35 technical cases a week with a satisfaction score of 96%",
        "Found the cause of 60 bugs a year and passed each to engineering with steps to reproduce; 48 were fixed",
        "Wrote 50 troubleshooting guides; cases passed to engineers fell from 22% to 11%",
        "Cut the median time to a solution from 19 hours to 6"]),
    "system-administrator": ("System Administrator", "server administration, scripting, backups, access management", [
        "Ran 250 {os:Linux} servers with 99.95% availability",
        "Automated patching; servers missing security updates fell from 30% to 2%",
        "Moved email and files for 600 employees to a cloud service over one weekend",
        "Reviewed access every quarter and removed 400 unused accounts"]),
    # security
    "cybersecurity": ("Security Engineer", "threat modeling, vulnerability management, incident response", [
        "Found and fixed 130 vulnerabilities in a year; the median time to fix a critical one fell from 21 days to 4",
        "Added security checks to the release pipeline; 90% of problems are now caught before release",
        "Led the response to 6 incidents with no customer data lost",
        "Ran phishing drills for 800 employees; the click rate fell from 18% to 3%"]),
    "security-engineer": ("Security Engineer", "application security, code review, cloud security", [
        "Reviewed the design of 45 features before build; 12 changed to close a risk",
        "Built automatic scanning of every code change; high-risk findings reaching production fell by 85%",
        "Cut accounts with administrator rights in {cloud:AWS} from 140 to 22",
        "Ran a bug bounty that paid for 38 valid reports, 5 of them critical, all fixed within 30 days"]),
    "security-analyst": ("Security Analyst", "log analysis, detection rules, incident response", [
        "Handled about 50 alerts a day; the median time to contain a real threat fell from 4 hours to 35 minutes",
        "Wrote 60 detection rules that cut false alerts by 60% and caught 2 real intrusions",
        "Wrote response playbooks for the 10 most common kinds of incident",
        "Led 4 incident investigations from first alert to written report"]),
    "penetration-tester": ("Penetration Tester", "web and network testing, exploit development, report writing", [
        "Ran 28 penetration tests in a year and reported 190 findings, 22 of them critical",
        "Reached domain administrator in 9 of 12 internal tests and showed each client the path",
        "Wrote reports developers could act on; 94% of critical findings were fixed within 30 days",
        "Built a tool that automates the first day of a test"]),
    "security-compliance": ("GRC Analyst", "SOC 2 and ISO 27001, risk assessment, policy writing, audit evidence", [
        "Led the SOC 2 audit: 84 controls, passed with no exceptions",
        "Automated evidence collection for 60 controls; audit preparation takes 2 weeks instead of 8",
        "Answered 150 customer security questionnaires a year with a median turnaround of 2 days",
        "Assessed 90 suppliers; 7 were replaced or asked to close gaps"]),
    "fraud-risk": ("Fraud Analyst", "transaction monitoring, rule writing, case investigation, chargebacks", [
        "Wrote 40 fraud rules that cut losses from 0.42% of volume to 0.15% while declining fewer good customers",
        "Reviewed about 80 cases a day with 98% accuracy at audit",
        "Found a ring of 300 linked accounts and stopped $1.1M in payouts",
        "Cut the share of good payments wrongly declined from 2.3% to 0.9%"]),
    "trust-safety": ("Trust and Safety Specialist", "content policy, case review, escalation, quality audits", [
        "Reviewed about 400 reports a day against policy with 97% accuracy at audit",
        "Rewrote the policy on impersonation; appeals that overturned a decision fell from 12% to 4%",
        "Cut the median time to act on a serious report from 9 hours to 50 minutes",
        "Trained 25 reviewers and wrote the examples used in training"]),
    "physical-security": ("Security Operations Specialist", "access control, CCTV, incident reports, emergency procedures", [
        "Ran security for 3 sites and 1,500 people with no serious incident in 2 years",
        "Replaced the badge system at all sites; lost-badge incidents fell by 60%",
        "Wrote emergency procedures and ran 8 drills a year; evacuation time fell from 11 minutes to 6",
        "Managed a guard contract of $1.4M and cut overtime by 20%"]),
    "privacy": ("Privacy Analyst", "GDPR and CCPA, data mapping, impact assessments, data subject requests", [
        "Mapped personal data across 70 systems for the record of processing",
        "Handled 900 access and deletion requests a year, every one inside the legal deadline",
        "Ran 35 impact assessments; 8 products changed before launch",
        "Trained 600 employees; every reported incident was handled within 72 hours"]),
    # product and project
    "product-manager": ("Product Manager", "roadmaps, customer interviews, prioritization, A/B tests, writing specifications", [
        "Led the launch of saved searches; weekly active users rose 18% in two months",
        "Ran 25 customer interviews and cut the sign-up form from 11 fields to 4; completion went from 52% to 71%",
        "Retired 3 features used by under 1% of customers, which freed a third of the support queue",
        "Set the yearly plan for a team of 8 and delivered 5 of its 6 goals"]),
    "program-manager": ("Program Manager", "planning, risk tracking, stakeholder updates, budgeting", [
        "Ran a program of 7 teams and 60 people that launched in 4 countries on the planned date",
        "Kept a risk list reviewed weekly; 9 of 11 serious risks were closed before they caused delay",
        "Cut status meetings from 6 hours a week to 2 with one written update",
        "Managed a budget of $4M and finished 3% under it"]),
    "technical-program-manager": ("Technical Program Manager", "dependency mapping, release planning, risk tracking, incident follow-up", [
        "Led the move of 120 services to a new platform across 14 teams, finished a month early",
        "Mapped 200 dependencies between teams before the work began; only 3 caused a delay",
        "Cut the release cycle from 6 weeks to 2",
        "Ran the launch review for 20 features a year; none was rolled back"]),
    "project-manager": ("Project Manager", "scheduling, budgeting, risk management, supplier coordination", [
        "Delivered 14 projects in 2 years, 12 on time and all within 5% of budget",
        "Kept a 9-person team on a 12-week plan and shipped on the date, with 2 items moved out by agreement in week 3",
        "Managed 6 suppliers on one project with a combined contract value of $2.2M",
        "Closed each project with a written review; 15 lessons became standard practice"]),
    "product-operations": ("Product Operations Manager", "launch planning, feedback analysis, process design, support training", [
        "Ran the launch process for 40 releases a year; support was briefed before every one",
        "Sorted 6,000 pieces of customer feedback a quarter into 20 themes used in planning",
        "Cut the time from a customer report to a product decision from 5 weeks to 9 days",
        "Built the beta program: 300 customers, 12 betas a year"]),
    "scrum-master": ("Scrum Master", "sprint planning, retrospectives, backlog refinement, removing blockers", [
        "Coached 3 teams; the share of sprint commitments delivered rose from 61% to 88%",
        "Cut the average time a task waits on another team from 6 days to 2",
        "Ran 70 retrospectives; 45 agreed actions were completed",
        "Shortened the release cycle from monthly to fortnightly"]),
    "business-operations": ("Business Operations Manager", "financial modeling, process design, planning cycles, reporting", [
        "Built the operating review the leadership team reads weekly: 30 metrics on one page",
        "Led a pricing and packaging project that raised average contract value by 14%",
        "Found $1.3M of yearly savings in supplier and software spending",
        "Ran the yearly planning cycle for 12 departments, finished 3 weeks earlier than the year before"]),
    "chief-of-staff": ("Chief of Staff", "planning, executive communication, project leadership, meeting design", [
        "Ran the leadership team’s weekly and quarterly rhythm for a company of 600",
        "Led 5 cross-company projects, including opening an office in a new country in 4 months",
        "Cut the CEO’s standing meetings from 22 hours a week to 13",
        "Wrote the board papers each quarter, sent a week ahead every time"]),
    # design
    "product-designer": ("Product Designer", "interaction design, prototyping, usability testing, design systems", [
        "Redesigned checkout in {design:Figma}; drop-off at the payment step fell from 34% to 22%",
        "Built a design system of 48 components that 5 teams now use",
        "Ran 16 usability tests and fixed the 7 problems most people hit",
        "Designed onboarding that raised first-week activation from 38% to 51%"]),
    "ux-researcher": ("UX Researcher", "interviews, usability testing, surveys, synthesis, presenting findings", [
        "Ran 90 interviews and 24 usability tests in a year across 5 product teams",
        "Showed that 40% of new users failed at the import step; after the redesign 9% did",
        "Ran a survey of 2,300 customers that set the next year’s priorities",
        "Built a library of 300 findings that designers search before starting work"]),
    "graphic-designer": ("Brand Designer", "visual identity, layout, illustration, typography", [
        "Redesigned the brand identity and applied it to 200 assets in 3 months",
        "Produced 30 campaign visuals a month with a two-day turnaround",
        "Drew a set of 120 illustrations now used across the product and the website",
        "Built templates that let marketing make their own social posts; design requests fell by 40%"]),
    "content-designer": ("Content Designer", "UX writing, style guides, information architecture, usability testing", [
        "Rewrote the 60 error messages users see most; support contacts about errors fell 25%",
        "Wrote the product’s style guide, now used by 30 designers and writers",
        "Cut the words in onboarding by half; completion rose from 58% to 69%",
        "Tested 5 names for a new feature with 400 users before launch"]),
    "video-motion": ("Motion Designer", "animation, video editing, storyboarding, sound", [
        "Made 45 product videos in a year; the launch film was watched 1.2 million times",
        "Animated 80 interface moments for the mobile app",
        "Cut the time to produce a 30-second advert from 3 weeks to 6 days with reusable templates",
        "Storyboarded and directed 4 customer stories filmed on location"]),
    "audio": ("Audio Engineer", "recording, mixing, sound design, audio software", [
        "Recorded, mixed and delivered the sound for 3 released games, about 4,000 sound effects in all",
        "Cut the memory used by audio by 35% with no audible loss",
        "Mixed 60 podcast episodes a year, each delivered within 2 days of recording",
        "Built a library of 9,000 tagged sounds the whole team searches"]),
    # marketing and communications
    "marketing-manager": ("Marketing Manager", "campaign planning, budgeting, email, content, analytics", [
        "Ran campaigns with a yearly budget of $1.2M that produced 38% of new sales pipeline",
        "Rewrote the welcome emails; activation in the first week rose from 31% to 44%",
        "Launched 6 products with one plan for web, email, events and press",
        "Cut the cost of a qualified lead from $310 to $190"]),
    "product-marketing": ("Product Marketing Manager", "positioning, messaging, launches, sales enablement, competitor research", [
        "Led 9 product launches; the largest brought 4,000 sign-ups in its first week",
        "Rewrote the positioning after 30 customer interviews; the win rate against the main competitor rose from 31% to 42%",
        "Built the sales deck and 12 competitor briefs used by 80 sellers",
        "Rewrote the pricing page; trial starts from it rose 19%"]),
    "growth-marketing": ("Growth Marketing Manager", "paid acquisition, lifecycle email, A/B tests, analytics", [
        "Managed paid campaigns of $150K a month and cut the cost of a new customer from $84 to $57",
        "Ran 60 landing page tests; conversion rose from 2.8% to 4.1%",
        "Built a series of 14 lifecycle emails that brought back 9% of lapsed users",
        "Grew the referral program to 22% of new sign-ups"]),
    "content-writer": ("Content Writer", "long-form articles, editing, search optimization, interviews", [
        "Wrote 90 articles in a year that bring 120,000 visits a month from search",
        "Edited about 40,000 words a month to one style guide",
        "Wrote 12 customer stories used by the sales team",
        "Rewrote the 20 most-read help pages; the time to an answer fell from 4 minutes to 90 seconds"]),
    "seo": ("SEO Manager", "keyword research, technical SEO, content planning, link earning, analytics", [
        "Grew visits from search from 40,000 to 95,000 a month in a year with 60 new pages",
        "Fixed crawling and duplicate-page problems across 12,000 pages; indexed pages rose from 61% to 94%",
        "Took 35 priority search terms into the top three results",
        "Cut paid search spending by $20K a month by winning the same visits from unpaid results"]),
    "advertising": ("Paid Media Manager", "campaign set-up, bidding, creative testing, measurement, budgeting", [
        "Managed $3M a year across search, social and video with a return of $4.20 for every $1 spent",
        "Tested 200 adverts a quarter; the best cut the cost of a sign-up by 31%",
        "Set up conversion tracking that matched finance’s numbers within 3%",
        "Moved 20% of the budget to two new channels that now bring a quarter of sign-ups"]),
    "social-media": ("Social Media Manager", "content calendars, short video, community replies, analytics", [
        "Grew followers from 40,000 to 165,000 in a year across 4 networks",
        "Published 25 posts a week; the average post reached 3 times as many people as the year before",
        "Made a video series that was watched 2 million times",
        "Answered about 60 customer messages a day within an hour"]),
    "community-manager": ("Community Manager", "moderation, events, member programs, feedback reports", [
        "Grew the community from 5,000 to 28,000 members with 35% active each month",
        "Ran 40 online events a year with an average of 300 people",
        "Built an ambassador program of 60 members who answer 45% of questions",
        "Sent a monthly feedback report to the product team; 18 requests were built"]),
    "communications": ("Communications Manager", "press relations, writing, internal communications, crisis response", [
        "Earned 60 pieces of press coverage in a year, 9 of them in national outlets",
        "Wrote the weekly company email and the monthly all-hands for 1,200 employees; 84% read the email each week",
        "Prepared 5 executives for 30 interviews",
        "Led communications during a service outage: first statement in 40 minutes, an update every hour"]),
    "events": ("Events Manager", "venue sourcing, budgeting, supplier management, on-site logistics", [
        "Ran 30 events a year, from dinners for 20 to a conference for 1,800",
        "Delivered the yearly conference 6% under a budget of $900K with a rating of 4.7 out of 5",
        "Brought $3.4M of sales pipeline from 12 field events",
        "Negotiated venue and catering contracts that saved $110K"]),
    "ecommerce": ("E-commerce Manager", "merchandising, pricing, conversion, marketplace listings, analytics", [
        "Ran an online store with $8M in yearly sales and grew it 26%",
        "Rewrote 600 product pages; the share of visitors who buy rose from 1.9% to 2.6%",
        "Cut abandoned baskets from 74% to 66% with a shorter checkout",
        "Planned 12 seasonal campaigns, including a sale day that took $420K"]),
    # sales
    "solutions-engineer": ("Solutions Engineer", "product demonstrations, proofs of concept, APIs, discovery calls", [
        "Supported $6M of closed sales in a year as the technical lead on 45 deals",
        "Ran 120 product demonstrations; 38% moved to a trial",
        "Built 20 proofs of concept, 15 of which became contracts",
        "Answered 60 security and technical questionnaires with a median turnaround of 3 days"]),
    "account-executive": ("Account Executive", "prospecting, discovery, negotiation, forecasting", [
        "Closed $1.4M in new business in a year, 118% of target",
        "Built a pipeline of 60 qualified deals, half of it from my own outreach",
        "Shortened the average sales cycle from 74 days to 51 by adding a technical call in the first week",
        "Kept every deal up to date in {crm:the CRM}; forecasts were within 6% of the result four quarters in a row"]),
    "sales-development": ("Sales Development Representative", "cold calling, email outreach, lead qualification, CRM", [
        "Booked 22 qualified meetings a month against a target of 15",
        "Sourced $2.1M of pipeline in a year, of which $480K closed",
        "Made about 60 calls and sent 80 emails a day; the reply rate rose from 3% to 8% after I rewrote the first email",
        "Promoted to team lead after 10 months"]),
    "account-manager": ("Account Manager", "relationship management, renewals, upselling, negotiation", [
        "Managed 45 accounts worth $5.2M a year, of which 96% renewed",
        "Grew revenue from existing accounts by 24% through upgrades",
        "Recovered 3 accounts that had given notice, worth $600K",
        "Held a quarterly review with every account"]),
    "sales-manager": ("Sales Manager", "coaching, forecasting, hiring, territory planning", [
        "Led a team of 8 that closed $11M, 112% of target",
        "Hired 5 sellers; all reached full target within 6 months",
        "Raised the win rate from 19% to 27% with weekly deal reviews",
        "Forecast each quarter within 5% of the result"]),
    "sales-representative": ("Sales Representative", "prospecting, product knowledge, negotiation, closing", [
        "Sold $900K in a year, 124% of target, second of 30 in the team",
        "Opened 70 new accounts in a territory that had 12",
        "Visited about 25 customers a week",
        "Won back 15 customers lost to a competitor"]),
    "sales-operations": ("Revenue Operations Manager", "forecasting, territory design, commission plans, reporting", [
        "Rebuilt the sales process in {crm:the CRM}; forecast accuracy rose from 71% to 93%",
        "Designed territories for 60 sellers; the gap between the best and the worst territory halved",
        "Cut quote approval from 3 days to 4 hours",
        "Built the weekly report the leadership team uses to run the business"]),
    "business-development": ("Business Development Manager", "partnerships, negotiation, market research, contract terms", [
        "Signed 12 partnerships that brought $3.5M in their first year",
        "Opened 2 new countries through local partners",
        "Negotiated a distribution agreement that reaches 4,000 resellers",
        "Built a list of 200 target partners and met 60 of them"]),
    "solutions-architect": ("Solutions Architect", "architecture design, technical workshops, proofs of concept", [
        "Designed the architecture for 30 enterprise customers moving to the platform, with a combined contract value of $14M",
        "Ran 40 technical workshops with customers’ engineers",
        "Wrote 8 reference designs now used by the whole team",
        "Cut the average time from contract to first production workload from 5 months to 7 weeks"]),
    "sales-engineer": ("Sales Engineer", "product demonstrations, technical discovery, proofs of concept", [
        "Was the technical lead on deals worth $8M closed in a year, with a 41% win rate",
        "Ran 150 demonstrations, each on the buyer’s own data",
        "Built a demonstration environment the whole team uses; preparing a demo fell from 4 hours to 30 minutes",
        "Wrote answers to the 100 most common technical questions"]),
    "retail": ("Sales Associate", "customer service, POS and cash handling, stock control, visual merchandising", [
        "Served about 120 customers a shift and kept the store’s satisfaction score above 90%",
        "Sold 15% above the store average over a year and signed up about 40 shoppers a month for the loyalty card",
        "Took cash and card payments at the POS with no cash discrepancy in 14 months",
        "Trained 5 new team members on the POS and on returns"]),
    # customer service
    "customer-success-manager": ("Customer Success Manager", "onboarding, business reviews, renewals, product adoption", [
        "Managed 60 accounts worth $4.8M a year, with 97% of revenue renewed",
        "Onboarded 25 new customers; the median time to first value fell from 45 days to 18",
        "Grew accounts by 21% through upgrades",
        "Spotted 9 at-risk accounts from usage data and kept 8"]),
    "technical-account-manager": ("Technical Account Manager", "technical reviews, escalation management, architecture advice", [
        "Was the technical contact for 12 enterprise accounts worth $9M a year; all renewed",
        "Led quarterly technical reviews; 30 recommendations were adopted",
        "Cut priority-one incidents across my accounts by 40% with reviews before each launch",
        "Managed 15 escalations to a fix with daily written updates"]),
    "customer-support": ("Customer Support Specialist", "written replies, phone support, ticketing systems, product knowledge", [
        "Answered about 60 customers a day by chat and email with a satisfaction score of 96%",
        "Solved 82% of questions in the first reply",
        "Wrote 45 help articles; tickets on those topics fell by a third",
        "Trained 6 new agents; all reached the team’s quality bar within a month"]),
    "implementation": ("Implementation Consultant", "project planning, configuration, data migration, customer training", [
        "Led 35 customer implementations in a year, 31 live on the planned date",
        "Cut the average implementation from 14 weeks to 8 with a standard plan",
        "Moved 2 million records for one customer with a difference of under 0.01% at reconciliation",
        "Trained 900 end users with an average rating of 4.8 out of 5"]),
    # accounting and finance
    "accounting": ("Senior Accountant", "month-end close, reconciliations, accounts payable and receivable, US GAAP", [
        "Closed the books in 5 working days instead of 9 by automating 30 reconciliations",
        "Found $210K of duplicate supplier payments in a review of accounts payable; all of it was recovered",
        "Prepared the company for its first audit, which required no adjustments",
        "Processed about 600 invoices a month with an error rate under 0.5%"]),
    "financial-analyst": ("Financial Analyst", "forecasting, budgeting, financial modeling, variance analysis", [
        "Built a forecast that stayed within 3% of actual revenue for six quarters",
        "Ran the yearly budget for 14 departments, finished 2 weeks earlier than the year before",
        "Modeled 3 pricing options for the board; the one chosen added $2M in yearly revenue",
        "Cut the monthly reporting pack from 60 pages to 12"]),
    "tax": ("Tax Manager", "corporate income tax, indirect tax, transfer pricing, tax provision", [
        "Filed returns in 14 countries on time for 3 years with no penalty",
        "Claimed $1.8M in research tax credits",
        "Cut the effective tax rate by 2 points through a review of intercompany pricing",
        "Took the company through 2 tax audits with no adjustment"]),
    "treasury": ("Treasury Analyst", "cash forecasting, bank relationships, foreign exchange, liquidity", [
        "Forecast cash weekly across 30 bank accounts within 4% of actual",
        "Earned $1.1M more interest a year by moving idle cash into short-term funds",
        "Cut bank fees by 28% by closing 12 accounts and renegotiating 2 contracts",
        "Hedged currency exposure of $40M; losses from exchange rates fell by 70%"]),
    "payroll": ("Payroll Specialist", "multi-country payroll, tax filings, benefits deductions, payroll software", [
        "Ran payroll for 1,400 employees in 6 countries with 99.9% accuracy",
        "Cut payroll corrections from 40 a month to 5",
        "Moved payroll to a new provider with no missed or late payment",
        "Answered about 100 employee questions a month within one working day"]),
    "audit": ("Internal Auditor", "risk assessment, control testing, audit reports, SOX", [
        "Led 12 audits a year: 85 findings, of which 80 were closed on time",
        "Tested 140 financial controls for SOX with no material weakness",
        "Found a gap in payment approvals that exposed $3M a year; it was closed within a month",
        "Tested every transaction instead of a sample in 5 audits by using data analysis"]),
    "investment": ("Corporate Development Associate", "valuation, financial modeling, due diligence, deal execution", [
        "Worked on 6 acquisitions worth $240M in total, from first model to close",
        "Screened 300 companies and took 25 to management meetings",
        "Built the valuation model for the largest deal; first-year results came within 8% of it",
        "Led due diligence across 40 workstreams on one deal"]),
    "trader": ("Trader", "risk management, market making, execution, derivatives", [
        "Traded a book with a daily volume of $30M and stayed inside risk limits every day for 2 years",
        "Made $4.2M in a year; the worst single month lost $310K",
        "Cut execution costs by 15% by changing how large orders are split",
        "Quoted prices to 40 counterparties, 90% of them within 30 seconds"]),
    "insurance": ("Underwriting Analyst", "risk assessment, pricing, claims review, policy wording", [
        "Underwrote about 60 commercial policies a month with a loss ratio 6 points better than the portfolio",
        "Reviewed 400 claims a year; payment time fell from 21 days to 9",
        "Built the pricing model for a new product that reached $5M in premiums in its first year",
        "Found 35 fraudulent claims worth $700K"]),
    "lending": ("Credit Analyst", "credit assessment, loan structuring, portfolio monitoring, regulation", [
        "Assessed about 50 loan applications a month; defaults on loans I approved were 1.1% against 2.4% for the portfolio",
        "Cut the decision time on a small business loan from 6 days to 1",
        "Monitored a portfolio of $120M and flagged 14 accounts early; 11 were restructured without loss",
        "Rewrote the credit policy for one product, approved by the risk committee at first reading"]),
    "procurement": ("Procurement Manager", "sourcing, negotiation, supplier management, contract terms", [
        "Managed $30M of yearly spending and saved 9% through 20 tenders",
        "Cut the number of suppliers from 400 to 180",
        "Shortened the time from request to purchase order from 12 days to 3",
        "Found a second source for 8 critical parts"]),
    # legal and compliance
    "legal-counsel": ("Commercial Counsel", "contract drafting, negotiation, commercial law, advising the business", [
        "Reviewed and negotiated about 30 commercial contracts a month; median turnaround fell from 8 days to 3",
        "Wrote the template agreements now used for 80% of sales without legal review",
        "Advised on 5 product launches in regulated markets",
        "Settled 4 disputes for under a third of the amounts claimed"]),
    "paralegal": ("Paralegal", "contract management, legal research, filings, document review", [
        "Tracked the renewal dates of 2,500 contracts; no renewal was missed in 2 years",
        "Prepared filings for 40 company entities in 12 countries, all on time",
        "Drafted about 50 confidentiality agreements a month from templates, each within a day",
        "Reviewed 20,000 documents for one case"]),
    "compliance": ("Compliance Analyst", "anti-money-laundering, customer due diligence, policy writing, regulatory reporting", [
        "Took the anti-money-laundering program through a regulator’s inspection with no findings",
        "Reviewed about 70 customer files a week with 99% accuracy at audit",
        "Filed 120 suspicious activity reports a year, every one inside the deadline",
        "Rewrote 15 policies and trained 400 employees on them"]),
    "policy": ("Public Policy Manager", "policy analysis, government relations, written submissions, coalition building", [
        "Wrote 18 submissions to regulators; 6 of our proposals appeared in the final rules",
        "Briefed 40 officials and legislators in a year",
        "Tracked 200 bills across 12 jurisdictions and flagged the 15 that mattered",
        "Built a coalition of 9 companies on one issue"]),
    # HR and recruiting
    "recruiter": ("Recruiter", "sourcing, interviewing, offer negotiation, applicant tracking systems", [
        "Hired 42 people in a year with a median time to hire of 34 days",
        "Raised the offer acceptance rate from 68% to 85% by naming the pay range in the first call",
        "Found 60% of hires by direct search, cutting agency spending by $180K",
        "Wrote to every candidate each week; the candidate survey rose from 3.9 to 4.6 out of 5"]),
    "technical-recruiter": ("Technical Recruiter", "sourcing engineers, technical screening, offer negotiation, working with hiring managers", [
        "Hired 31 engineers in a year, 9 of them senior or above",
        "Wrote first messages that 32% of engineers answered, against a team average of 14%",
        "Cut the interview process from 6 stages to 4; time to offer fell from 41 days to 26",
        "Trained 20 engineers to interview"]),
    "human-resources": ("HR Business Partner", "employee relations, performance management, organization design, employment law", [
        "Was the HR partner for 300 employees in 3 departments",
        "Cut yearly turnover in one department from 24% to 13% through exit interviews and manager coaching",
        "Handled 40 employee relations cases a year; none went to a tribunal",
        "Ran the yearly performance review for 300 people, finished on time for the first time in 3 years"]),
    "compensation-benefits": ("Compensation Analyst", "salary benchmarking, job levelling, benefits design, equity plans", [
        "Built salary bands for 120 job levels from 3 market surveys",
        "Ran the yearly pay review for 1,500 employees inside a budget of $6M",
        "Found and closed pay gaps for 85 employees",
        "Changed the health plan provider, saving $400K a year with the same cover"]),
    "training": ("Learning and Development Manager", "instructional design, workshop facilitation, learning platforms, measuring results", [
        "Rebuilt sales onboarding; new hires reached a first deal in 6 weeks instead of 10",
        "Designed 25 courses taken by 2,000 employees with a completion rate of 88%",
        "Ran 40 live workshops with an average rating of 4.7 out of 5",
        "Built a program for new managers; 120 finished it in a year"]),
    # operations and administration
    "operations-manager": ("Operations Manager", "process improvement, team leadership, supplier management, reporting", [
        "Led a team of 22 handling 9,000 orders a month",
        "Simplified order handling from 9 steps to 5; errors fell by 40%",
        "Renegotiated 12 supplier contracts and saved $140K a year",
        "Raised on-time delivery from 87% to 97%"]),
    "executive-assistant": ("Executive Assistant", "calendar management, travel planning, expense reports, meeting preparation", [
        "Managed calendars, travel and expenses for 3 executives across 4 time zones",
        "Planned 45 trips a year with no missed connection or meeting",
        "Prepared the papers for the weekly leadership meeting, sent a day ahead every week",
        "Organized 2 company off-sites for 150 people within budget"]),
    "workplace": ("Workplace Manager", "facilities, supplier management, health and safety, office moves", [
        "Ran 3 offices for 500 people with a satisfaction score of 4.5 out of 5",
        "Planned an office move for 120 people, finished on time and 8% under budget",
        "Cut facilities costs by 15% by rebidding cleaning and catering",
        "Answered about 30 workplace requests a week, 90% within a day"]),
    "supply-chain": ("Supply Chain Analyst", "demand planning, inventory control, logistics, supplier scorecards", [
        "Cut stock held from 62 days of sales to 41 with no rise in stock-outs",
        "Raised on-time delivery from suppliers from 82% to 95% with a monthly scorecard",
        "Saved $600K a year in freight by combining shipments",
        "Built a demand forecast accurate to within 8% for each product"]),
    "ehs": ("EHS Specialist", "risk assessments, incident investigation, safety training, regulatory compliance", [
        "Cut recordable injuries from 14 a year to 4 at a site of 800 people",
        "Ran 120 risk assessments and closed 95% of actions on time",
        "Trained 600 employees a year",
        "Passed 3 regulatory inspections with no citation"]),
    # hardware and engineering
    "hardware-engineer": ("Hardware Design Engineer", "schematic capture, circuit board layout, design verification, lab testing", [
        "Took a circuit board from schematic to production in 7 months, passing certification at the first attempt",
        "Cut the cost of parts for the board by 18% with no loss of performance",
        "Wrote verification tests that found 30 design bugs before the chip was manufactured",
        "Found the cause of a field failure in 3 weeks and released the fix to 5,000 units"]),
    "mechanical-engineer": ("Mechanical Engineer", "3D CAD, tolerance analysis, design for manufacture, prototyping", [
        "Designed a housing that cut assembly time from 14 minutes to 9",
        "Reduced the weight of a bracket by 22% while passing the same load tests",
        "Took 6 parts from concept to production tooling in 5 months",
        "Analyzed returned units and fixed the 3 commonest causes of failure; returns fell by 40%"]),
    "electrical-engineer": ("Electrical Engineer", "circuit design, power electronics, circuit board layout, lab testing", [
        "Designed a power supply board that is 94% efficient, up from 88%",
        "Passed electromagnetic compatibility testing at the first attempt on 3 products",
        "Cut the board’s part count from 210 to 160",
        "Wrote the test procedure used on the production line; test time per unit fell from 6 minutes to 2"]),
    "optics": ("Optical Engineer", "optical design, alignment, laser systems, optical testing", [
        "Designed a lens assembly that raised coupling efficiency from 61% to 78%",
        "Built an alignment process that cut assembly time for each unit from 3 hours to 40 minutes",
        "Characterized 12 laser designs and chose the one now in production",
        "Raised production yield from 70% to 91%"]),
    "materials-engineer": ("Materials Engineer", "metallurgy, failure analysis, process development, materials testing", [
        "Developed a heat treatment that raised the fatigue life of a part by 30%",
        "Qualified 2 new alloys for production in 8 months",
        "Found the cause of cracking in a welded joint; scrap fell from 9% to 2%",
        "Ran 400 mechanical tests a year and wrote the reports used for design approval"]),
    "robotics": ("Robotics Engineer", "motion planning, control systems, sensors, simulation", [
        "Wrote the motion planner in {lang:C++} for a warehouse robot; picks an hour rose from 280 to 410",
        "Cut collisions in testing from 1 in 2,000 moves to 1 in 60,000",
        "Built a simulator that runs 10,000 test scenarios overnight",
        "Brought 120 robots into service at 3 customer sites"]),
    "manufacturing": ("Manufacturing Engineer", "process design, lean methods, statistical process control, root cause analysis", [
        "Raised line output from 320 to 450 units a shift by rebalancing 5 stations",
        "Cut scrap from 6.2% to 2.1%",
        "Brought 3 new products into production, each at target yield within 6 weeks",
        "Cut changeover time from 50 minutes to 15"]),
    "test-engineer": ("Test Engineer", "test planning, test automation, data acquisition, failure analysis", [
        "Built a test rig that checks 200 units a shift; defects reaching customers fell from 2.1% to 0.4%",
        "Automated 80 tests in {lang:Python}; a full run takes 3 hours instead of 2 days",
        "Wrote the validation plan for 2 products, both released on schedule",
        "Found 45 design problems before production"]),
    "aerospace": ("Aerospace Engineer", "flight software, guidance and control, simulation, systems testing", [
        "Wrote flight software that has flown on 14 missions without a software fault",
        "Built a simulation that tests each release on 5,000 flight scenarios",
        "Tuned the control system; landing accuracy improved from 12 m to 3 m",
        "Led the software readiness review for 6 launches"]),
    "technician": ("Technician", "fault finding, preventive maintenance, reading schematics, safety procedures", [
        "Kept 60 machines running with 98% uptime",
        "Completed about 25 repairs a week, 90% of them at the first visit",
        "Cut repeat faults by 35% by adding 2 checks to routine maintenance",
        "Trained 4 apprentices"]),
    "field-service": ("Field Service Engineer", "installation, fault finding, customer training, service reports", [
        "Installed and commissioned 45 systems at customer sites in a year",
        "Fixed 88% of faults at the first visit, against a team average of 71%",
        "Covered a territory of 60 customers and answered every call within 24 hours",
        "Trained 200 operators"]),
    "construction": ("Construction Project Manager", "scheduling, cost control, contractor management, site safety, permits", [
        "Delivered a $28M building 3 weeks early and 2% under budget",
        "Managed 18 subcontractors on site with no lost-time injury in 400,000 hours worked",
        "Resolved 600 design queries with no delay to the critical path",
        "Obtained every permit for 3 sites inside the planned dates"]),
    # writing
    "technical-writer": ("Technical Writer", "API documentation, style guides, editing, working with engineers", [
        "Wrote and maintained 180 pages of documentation; support questions about setup fell by 28%",
        "Documented an API of 120 endpoints, each with a working example",
        "Rewrote the quick-start guide; the time to a first working call fell from 40 minutes to 8",
        "Moved the documentation into the code repository, so engineers update it with each change"]),
    # science and healthcare
    "life-sciences": ("Research Associate", "laboratory techniques, experiment design, data analysis, lab records", [
        "Ran about 30 experiments a month and kept records that passed 2 audits with no finding",
        "Cut the time from sample to result from 6 days to 2 by reordering the lab workflow",
        "Developed an assay now used by 3 teams",
        "Co-authored 3 peer-reviewed papers"]),
    "healthcare": ("Clinical Operations Manager", "clinical workflows, scheduling, quality measures, healthcare regulation", [
        "Ran clinical operations for a telehealth service of 60 clinicians and 9,000 visits a month",
        "Cut the wait for a first appointment from 9 days to 2",
        "Raised patient satisfaction from 4.3 to 4.8 out of 5",
        "Passed 2 accreditation reviews with no finding"]),
    "nursing": ("Registered Nurse", "patient assessment, care planning, patient education, electronic health records", [
        "Cared for about 18 patients a day by video and phone, with a satisfaction score of 4.8 out of 5",
        "Managed 150 patients with long-term conditions; hospital readmissions fell by 22%",
        "Trained 9 new nurses on documentation; audit findings fell to zero",
        "Triaged about 40 calls a shift"]),
    "mental-health": ("Licensed Therapist", "assessment, treatment planning, cognitive behavioral therapy, clinical documentation", [
        "Saw about 25 clients a week by video; 78% completed their treatment plan",
        "Measured outcomes with standard questionnaires; 64% of clients showed reliable improvement",
        "Completed clinical notes within 24 hours of every session",
        "Supervised 3 trainee therapists"]),
    "clinical-research": ("Clinical Research Associate", "study protocols, site monitoring, good clinical practice, regulatory submissions", [
        "Monitored 12 study sites across 3 trials; all met their enrollment targets",
        "Ran 3 studies from protocol to report",
        "Prepared 2 regulatory submissions, both accepted without a major question",
        "Closed 95% of data queries within 5 days"]),
    # education, hospitality, first jobs, crypto
    "education": ("Instructor", "curriculum design, teaching, assessment, learning platforms", [
        "Designed and taught a 6-week course taken by 340 people; 92% finished it",
        "Wrote 25 lessons with exercises and answer keys",
        "Raised the pass rate from 71% to 86% by adding weekly practice tests",
        "Taught 12 live classes a week with an average rating of 4.7 out of 5"]),
    "hospitality": ("Sous Chef", "menu planning, food safety, stock control, team leadership", [
        "Ran a kitchen serving 300 covers a day with a team of 8",
        "Cut food waste by 30% with daily stock counts and smaller batches",
        "Passed every hygiene inspection with the top rating for 3 years",
        "Wrote 4 seasonal menus a year at a food cost of 28%"]),
    "intern": ("Computer Science Student", "teamwork, writing, learning fast", [
        "Finished a 12-week internship; my change to the search page shipped to all users",
        "Built a course project in {lang:Python} that 60 classmates used to book study rooms",
        "Organized a student event for 200 people on a budget of $1,500",
        "Worked 15 hours a week during studies, handling about 30 customer requests a shift"]),
    "blockchain-engineer": ("Blockchain Engineer", "consensus, cryptography, node operation, security review", [
        "Built a wallet service in {lang:Go} that signs 2 million transactions a month with no loss of funds",
        "Cut the time for a node to sync from 9 hours to 50 minutes",
        "Added support for 6 chains, each in under 3 weeks",
        "Fixed 11 findings from two outside audits before launch"]),
    "smart-contract-engineer": ("Smart Contract Engineer", "testing, gas optimization, security audits", [
        "Wrote and shipped 6 smart contracts that hold $40M, with no incident",
        "Cut the gas used by the main contract by 27%",
        "Wrote 400 tests, fuzz tests among them, that cover every line",
        "Fixed 11 findings from two outside audits before launch"]),
}

# kind of work -> the beginner's title, where it is not simply "Junior " and the title in ROLE
ENTRY_TITLE = {
    "engineering-manager": "Team Lead", "tech-lead": "Associate Tech Lead", "software-architect": "Associate Software Architect",
    "research-scientist": "Research Scientist Intern", "ai-trainer": "AI Data Annotator", "it-support": "IT Help Desk Technician",
    "trust-safety": "Content Moderator", "physical-security": "Security Officer", "product-manager": "Associate Product Manager",
    "program-manager": "Program Coordinator", "technical-program-manager": "Associate Technical Program Manager",
    "project-manager": "Project Coordinator", "product-operations": "Product Operations Associate",
    "business-operations": "Business Operations Associate", "chief-of-staff": "Special Projects Associate",
    "graphic-designer": "Junior Graphic Designer", "audio": "Assistant Audio Engineer", "marketing-manager": "Marketing Coordinator",
    "product-marketing": "Associate Product Marketing Manager", "growth-marketing": "Growth Marketing Associate",
    "seo": "Junior SEO Specialist", "advertising": "Paid Media Coordinator", "social-media": "Social Media Coordinator",
    "communications": "Communications Coordinator", "events": "Events Coordinator", "ecommerce": "E-commerce Coordinator",
    "account-executive": "Associate Account Executive", "sales-development": "Sales Development Representative",
    "sales-manager": "Assistant Sales Manager", "sales-operations": "Revenue Operations Analyst",
    "business-development": "Business Development Associate", "solutions-architect": "Associate Solutions Architect",
    "retail": "Part-Time Sales Associate", "customer-success-manager": "Customer Success Associate",
    "technical-account-manager": "Associate Technical Account Manager", "customer-support": "Customer Support Representative",
    "accounting": "Staff Accountant", "tax": "Tax Associate", "payroll": "Payroll Assistant", "investment": "Corporate Development Analyst",
    "insurance": "Underwriting Assistant", "procurement": "Procurement Assistant", "legal-counsel": "Law Clerk", "policy": "Policy Associate",
    "recruiter": "Recruiting Coordinator", "human-resources": "HR Coordinator", "training": "Learning and Development Coordinator",
    "operations-manager": "Operations Coordinator", "executive-assistant": "Administrative Assistant", "workplace": "Office Coordinator",
    "ehs": "EHS Coordinator", "technician": "Apprentice Technician", "construction": "Assistant Project Manager",
    "life-sciences": "Research Assistant", "healthcare": "Clinical Operations Coordinator", "nursing": "New Graduate Registered Nurse",
    "mental-health": "Pre-Licensed Therapist", "clinical-research": "Clinical Research Coordinator", "education": "Teaching Assistant",
    "hospitality": "Line Cook", "intern": "Computer Science Student",
}

# kind of work -> what a beginner can honestly have: [a course, bootcamp or personal project; an internship, placement or first job;
# volunteer or part-time work]
ENTRY = {
    # software
    "software-engineer": [
        "Built a habit-tracking web app in {lang:Python} as a personal project; 40 people used it in its first month",
        "Fixed 25 bugs during a summer internship, each merged after code review",
        "Rebuilt the sign-up form of a local food bank as a volunteer; volunteer sign-ups rose 30%"],
    "backend-engineer": [
        "Built a REST API in {lang:Go} for a course project with 30 endpoints, each covered by an automated test",
        "Rewrote a slow {rel:PostgreSQL} query during a summer internship; an internal report went from 8 s to 2 s",
        "Built a booking system for a volunteer-run sports club that takes about 200 bookings a month"],
    "frontend-engineer": [
        "Built a recipe site in {front:React} as a bootcamp final project that scored 95 in an automated accessibility audit",
        "Built 8 interface components during a summer internship, now used on the company’s settings pages",
        "Redesigned the website of a local animal shelter as a volunteer; adoption inquiries rose 20%"],
    "full-stack-engineer": [
        "Built a class project tracker with a {front:React} front end and a {rel:PostgreSQL} database, used by 25 students",
        "Shipped 4 small features end to end during a summer internship, all released to customers",
        "Built an online order form for a family bakery as part-time work; it takes about 80 orders a week"],
    "mobile-engineer": [
        "Published a study timer app built in {mobile:Kotlin} as a personal project; it reached 1,200 downloads",
        "Fixed 15 crash reports in a shopping app during a summer internship",
        "Built an event app for a student festival as a volunteer, used by 900 attendees"],
    "qa-engineer": [
        "Wrote 60 automated tests in {lang:Python} for a bootcamp project that run on every change",
        "Found and reported 45 bugs during a summer internship, each with steps to reproduce",
        "Tested a nonprofit’s donation site as a volunteer and found 12 bugs before launch"],
    "embedded-engineer": [
        "Built a battery-powered weather station in {lang:C++} for a course project that runs 6 months on one charge",
        "Wrote a driver for a temperature sensor during a summer internship, tested on 20 boards",
        "Repaired about 15 electronic devices a month at a volunteer-run community repair shop"],
    "engineering-manager": [
        "Completed a 10-week course for new engineering managers on feedback, hiring and planning",
        "Led a team of 4 engineers as acting lead while the manager was on leave",
        "Organized a volunteer coding workshop for 40 high school students"],
    "web-developer": [
        "Built a portfolio site of 12 pages as a personal project that loads in under a second on a phone",
        "Built 6 landing pages during a summer internship, each live within a week",
        "Rebuilt the website of a local theater as a volunteer; online ticket sales rose 35%"],
    "product-engineer": [
        "Launched a side project that gained 300 sign-ups in its first month",
        "Interviewed 10 users during a summer internship and shipped the fix most of them asked for",
        "Built a sign-up flow for a student society, moving 150 members off a paper form"],
    "systems-software": [
        "Wrote a memory allocator in {lang:C++} for a course project, 3 times faster than the default on the course benchmark",
        "Found and removed a lock during a summer internship that cut the run time of a test suite by 20%",
        "Fixed 6 bugs in an open-source file system tool, all merged by its maintainers"],
    "graphics-engineer": [
        "Wrote a ray tracer in {lang:C++} as a personal project that renders a test scene in 4 s",
        "Cut frame time in a game by 2 ms during a summer internship by removing wasted draw calls",
        "Taught a shader workshop to 30 members of a student game club"],
    "game-developer": [
        "Made a platform game in {lang:C++} as a personal project, downloaded 3,000 times",
        "Built 5 gameplay features during a summer internship at a game studio, all in the released game",
        "Built a puzzle game in a weekend game jam that placed third out of 120 entries"],
    "tech-lead": [
        "Led a 4-person capstone project in {lang:Java} from design to demo in one term",
        "Led a project of 3 engineers for the first time, shipping a reporting feature a week early",
        "Mentored 6 bootcamp students through their final projects as a volunteer"],
    "software-architect": [
        "Completed a 10-week course in distributed systems design and wrote a design document for each module",
        "Designed a notification service in a first engineering job; it now sends 50,000 messages a day",
        "Reviewed the hosting setup of a nonprofit as a volunteer and cut its hosting bill by 40%"],
    "developer-advocate": [
        "Wrote tutorials on a personal blog that were read 20,000 times in a year",
        "Built 4 sample apps during a developer relations internship, each linked from the documentation",
        "Organized a local developer meetup that grew to 150 members"],
    "automation-engineer": [
        "Built a course project in {lang:Python} that joins 3 public APIs into one daily report",
        "Built 4 data integrations during a summer internship, each with an alert on failure",
        "Automated the member list of a volunteer group, saving its organizers 3 hours a week"],
    "business-systems": [
        "Built 5 practice workflows in {crm:Salesforce} during an administrator course",
        "Automated an approval process during a summer internship, saving the finance team 4 hours a week",
        "Set up a donor database for a local charity as a volunteer, moving 1,500 records out of spreadsheets"],
    # AI and machine learning
    "machine-learning-engineer": [
        "Trained an image classifier in {ml:PyTorch} for a course project that reached 92% accuracy",
        "Built an evaluation script during a summer internship that runs 500 test cases on each model",
        "Built a model for a volunteer library that sorted 2,000 donated books by topic"],
    "ai-engineer": [
        "Built a study assistant on a large language model as a personal project, used by 50 classmates",
        "Wrote 200 test questions during a summer internship to score a chatbot before each release",
        "Built a question bot for a nonprofit’s help page as a volunteer; it answers 60% of common questions"],
    "forward-deployed-engineer": [
        "Built an inventory report in {lang:Python} for a local shop as a capstone project, replacing 3 hours of counting a week",
        "Joined customer calls during a summer internship and built 2 small tools from what customers asked for",
        "Set up shared forms and reports for a food bank as a volunteer; weekly reporting went from 3 hours to 30 minutes"],
    "applied-ai": [
        "Built a set of prompts for a course project that cut the time to draft a lab report by 40%",
        "Tested AI assistants on 3 workflows during a summer internship and wrote up which ones saved time",
        "Taught a prompt-writing workshop to 40 members of a local small-business group"],
    "computer-vision": [
        "Trained a model to count birds in feeder photos as a personal project, correct on 90% of test photos",
        "Labeled and cleaned 5,000 images during a summer internship for a defect detection model",
        "Built a plant disease detector for a community garden as a volunteer, 85% accurate on members’ photos"],
    "mlops": [
        "Built a pipeline for a course project that retrains a model each night and keeps the last 10 versions",
        "Packaged 3 models in containers during a summer internship, each deployable with one command",
        "Set up a shared GPU server for a student AI club of 40 members"],
    "research-scientist": [
        "Reproduced the results of 3 published papers for a graduate course and released the code",
        "Ran 40 experiments during a summer research internship that became a workshop paper",
        "Reviewed 6 papers as a volunteer reviewer for a conference workshop"],
    "ai-trainer": [
        "Labeled 2,000 practice samples in an online annotation course",
        "Wrote training examples during a freelance trial with a 94% acceptance rate at audit",
        "Checked facts for a student newspaper as a volunteer, about 20 articles a month"],
    # data
    "data-engineer": [
        "Built a pipeline in {lang:Python} for a personal project that loads 2 million rows of public transit data each night",
        "Wrote 20 data quality checks during a summer internship that caught broken loads before reports did",
        "Cleaned and merged 5 years of donor records for a local charity as a volunteer"],
    "data-scientist": [
        "Built a model in {lang:Python} for a course project that predicts bike-share demand within 12%",
        "Analyzed 3 A/B tests during a summer internship and presented the results to product leaders",
        "Analyzed survey answers from 800 residents for a volunteer city group"],
    "data-analyst": [
        "Built a dashboard in {bi:Tableau} for a course project that tracks 10 years of city rent prices",
        "Wrote weekly reports in {sheet:SQL} during a summer internship, used by a sales team of 12",
        "Analyzed donation data for a local nonprofit as a volunteer and found its 3 best months for appeals"],
    "analytics-engineer": [
        "Built 12 tested data models in {dbt:dbt} for a personal project on public sports data",
        "Documented 30 tables during a summer internship so analysts could find them",
        "Set up a reporting database for a volunteer group, replacing 6 separate spreadsheets"],
    "business-analyst": [
        "Mapped the course registration process for a university project and proposed 3 changes",
        "Wrote requirements for 2 small features during a summer internship, both delivered",
        "Ran 12 interviews for a nonprofit as a volunteer and wrote the report that chose its donor system"],
    "quant": [
        "Backtested a momentum strategy in {lang:Python} for a course project on 15 years of daily prices",
        "Cleaned 10 years of options data during a summer internship for the research team",
        "Placed second of 80 teams in a university trading competition"],
    "pricing": [
        "Compared the prices of 30 grocery products across local chains for a course project",
        "Tracked competitor prices for 50 products each week during a summer internship",
        "Set ticket prices for a student theater as a volunteer; sales rose 18%"],
    "research-analyst": [
        "Wrote a 20-page report on electric scooter sharing for a university course",
        "Collected data on 150 companies during a summer internship for a market sizing report",
        "Ran a survey of 300 local residents as a volunteer for a community group"],
    "data-governance": [
        "Wrote a data dictionary for 15 tables in a data management course",
        "Added descriptions and owners to 200 tables during a summer internship",
        "Wrote a privacy checklist as a volunteer for a group that keeps records of 400 members"],
    # cloud, DevOps and IT
    "devops-engineer": [
        "Set up an automated release pipeline on {cloud:AWS} for a personal project that deploys in 4 minutes",
        "Wrote {iac:Terraform} for 3 test environments during a summer internship",
        "Set up hosting and nightly backups for a nonprofit’s website as a volunteer, with no outage in 12 months"],
    "site-reliability-engineer": [
        "Built monitoring for a home server project that alerts within 1 minute of a failure",
        "Wrote 10 runbooks during a summer internship for the most common alerts",
        "Kept the servers of a student club running as a volunteer for its 300 members"],
    "it-support": [
        "Completed a 12-week IT support certificate course covering networks, hardware and accounts",
        "Answered about 20 help desk tickets a day during a summer internship at a school district",
        "Set up 30 donated laptops for a community center as a volunteer"],
    "systems-engineer": [
        "Built a home lab of 4 virtual servers with shared sign-in as a personal project",
        "Wrote {lang:Python} scripts during a summer internship that created 200 user accounts",
        "Managed accounts and devices as a volunteer for a nonprofit of 25 staff"],
    "cloud-engineer": [
        "Hosted a personal website on {cloud:AWS}, built with {iac:Terraform}, for under $2 a month",
        "Tagged 400 cloud resources during a summer internship so costs could be traced to teams",
        "Moved a nonprofit’s file server to the cloud as a volunteer for its 20 staff"],
    "network-engineer": [
        "Built a home lab of 5 routers and switches for a networking certificate course",
        "Mapped 120 network devices during a summer internship",
        "Set up Wi-Fi across 3 floors of a community center as a volunteer"],
    "database-administrator": [
        "Set up a {rel:PostgreSQL} database for a course project and tested 5 restores from backup",
        "Tuned 4 slow queries during a summer internship",
        "Moved the membership records of 2,000 people for a volunteer group into a database"],
    "data-center": [
        "Completed a 10-week course in server hardware and cabling",
        "Installed about 40 servers a week during a summer placement under a senior technician",
        "Rebuilt 25 donated computers for a local school as a volunteer"],
    "support-engineer": [
        "Wrote a troubleshooting guide for the 5 most common errors of a course project API",
        "Answered about 15 technical tickets a day during a summer internship",
        "Answered about 30 questions a month on an open-source project’s forum as a volunteer"],
    "system-administrator": [
        "Ran 3 {os:Linux} servers at home as a personal project with automatic backups",
        "Patched 150 servers during a summer internship under a senior administrator",
        "Managed email and accounts for a local charity of 30 volunteers"],
    # security
    "cybersecurity": [
        "Solved 60 challenges on a public capture-the-flag practice site as a personal project",
        "Triaged about 30 vulnerability scan findings a week during a summer internship",
        "Gave a phishing awareness talk to 50 staff of a local charity as a volunteer"],
    "security-engineer": [
        "Built a scanner for a course project that checks web apps for 10 common vulnerabilities",
        "Reviewed 20 code changes for security issues during a summer internship",
        "Reported 3 vulnerabilities through public bug bounty programs, all confirmed and fixed"],
    "security-analyst": [
        "Built a home lab that collects logs from 5 machines and alerts on failed logins",
        "Reviewed about 40 alerts a day during a summer internship in a security operations center",
        "Checked the website of a local charity as a volunteer and fixed 4 weak security settings"],
    "penetration-tester": [
        "Completed 50 practice machines on a training platform and wrote a report for each",
        "Assisted on 6 penetration tests during a summer internship, writing up the findings",
        "Found 2 vulnerabilities in open-source projects and reported them to the maintainers"],
    "security-compliance": [
        "Mapped 40 controls for a practice company in a security frameworks course",
        "Collected audit evidence for 30 controls during a summer internship",
        "Wrote 5 basic security policies for a small nonprofit as a volunteer"],
    "fraud-risk": [
        "Found 4 fraud patterns in public card transaction data with {sheet:SQL} for a course project",
        "Reviewed about 40 flagged orders a day during a summer internship",
        "Checked 200 grant applications for duplicates as a volunteer for a community fund"],
    "trust-safety": [
        "Completed a 4-week online course in content policy and online safety",
        "Reviewed about 200 posts a day against policy during a short contract",
        "Moderated an online forum of 5,000 members as a volunteer"],
    "physical-security": [
        "Completed a 40-hour security officer course with first aid certification",
        "Patrolled a 3-building site on night shifts and wrote a report for every incident",
        "Managed crowd entry for 2,000 people at a community festival as a volunteer"],
    "privacy": [
        "Wrote a sample privacy notice for a fictional app in a 6-week privacy law course",
        "Logged 80 data subject requests during a summer internship, all answered on time",
        "Wrote a privacy policy for a local charity as a volunteer covering 1,000 donors"],
    # product and project
    "product-manager": [
        "Interviewed 15 students for a course project and wrote a product proposal from what they said",
        "Wrote specifications for 3 features during a summer internship, all shipped before it ended",
        "Launched a campus app with friends that reached 800 students in a term"],
    "program-manager": [
        "Planned a student conference for 250 people as a course project",
        "Tracked actions and risks for a program of 4 teams during a summer internship",
        "Coordinated 30 volunteers for a weekly food distribution"],
    "technical-program-manager": [
        "Coordinated a 6-person capstone project, delivered in one term",
        "Tracked 50 dependencies for a platform launch during a summer internship",
        "Coordinated the release of an open-source tool across 8 volunteer contributors"],
    "project-manager": [
        "Planned a sample project of 80 tasks in a project management course",
        "Kept the schedule for 3 projects during a summer internship",
        "Organized a charity run for 400 runners as a volunteer, on budget"],
    "product-operations": [
        "Sorted 1,000 app store reviews into themes for a course project",
        "Wrote release notes for 12 launches during a summer internship",
        "Ran the beta test of a student app with 60 volunteer testers"],
    "scrum-master": [
        "Earned a scrum master certificate after a 2-day course",
        "Ran daily stand-ups and 5 retrospectives during a summer internship",
        "Ran 2-week work cycles for a volunteer team building a charity website"],
    "business-operations": [
        "Built a financial model for a course case study of a 50-person company",
        "Built a weekly report of 15 metrics during a summer internship",
        "Kept the books for a student society with a yearly budget of $8,000"],
    "chief-of-staff": [
        "Won a business school strategy case competition against 40 teams",
        "Prepared the slides for 8 leadership meetings during a summer internship",
        "Ran the weekly meeting of a 12-person volunteer board"],
    # design
    "product-designer": [
        "Designed a mobile app in {design:Figma} for a course project and tested it with 8 people",
        "Designed 5 screens during a summer internship that shipped to customers",
        "Redesigned the donation page of a local charity as a volunteer; online gifts rose 25%"],
    "ux-researcher": [
        "Ran 10 usability tests on a library website for a course project",
        "Ran 12 user interviews during a summer internship and presented the findings to the product team",
        "Surveyed 300 members of a local nonprofit about its services as a volunteer"],
    "graphic-designer": [
        "Designed a brand identity for a fictional coffee shop as a course project, applied to 15 items",
        "Designed 40 social media graphics during a summer internship",
        "Designed posters for 6 shows at a local theater as a volunteer"],
    "content-designer": [
        "Rewrote the error messages of a sample app for a course project and tested them with 6 people",
        "Wrote the interface text for 20 screens during a summer internship",
        "Rewrote 15 pages of a local charity’s website in plain language as a volunteer"],
    "video-motion": [
        "Made a 60-second animated short as a course project, shown at a student film festival",
        "Edited 12 short social videos during a summer internship",
        "Made 5 videos for a local animal shelter as a volunteer"],
    "audio": [
        "Recorded and mixed a 5-song record for a local band as a course project",
        "Set up microphones for about 10 sessions a week during a studio internship",
        "Ran live sound for 20 community theater shows as a volunteer"],
    # marketing and communications
    "marketing-manager": [
        "Planned a marketing campaign for a local coffee shop as a course project with a budget of $500",
        "Scheduled 30 marketing emails during a summer internship",
        "Ran the social accounts of a student society, growing them to 1,200 followers"],
    "product-marketing": [
        "Wrote a launch plan for a fictional app as a course project and tested its message with 20 students",
        "Wrote 4 competitor briefs for the sales team during a summer internship",
        "Rewrote a nonprofit’s website copy as a volunteer; sign-ups rose 15%"],
    "growth-marketing": [
        "Ran paid ads for a personal online shop that brought its first 40 orders",
        "Set up 6 A/B tests on landing pages during a summer internship",
        "Grew the newsletter of a local nonprofit to 900 subscribers as a volunteer"],
    "content-writer": [
        "Wrote a personal blog of 30 articles on personal finance",
        "Wrote 10 blog posts during a summer internship, all published",
        "Wrote the newsletter for a local library as a volunteer, sent to 2,000 readers"],
    "seo": [
        "Grew a personal blog to 3,000 visits a month from search",
        "Wrote titles and descriptions for 200 pages during a summer internship",
        "Fixed 40 broken links on a charity’s website as a volunteer"],
    "advertising": [
        "Earned 2 ad platform certificates through free online courses",
        "Built 50 ad variations for search and social during a summer internship",
        "Ran a small ad campaign for a charity event as a volunteer that sold 150 tickets"],
    "social-media": [
        "Grew a personal short-video account to 4,000 followers",
        "Scheduled 15 posts a week during a summer internship",
        "Ran a local food bank’s social accounts as a volunteer, growing followers from 600 to 1,500"],
    "community-manager": [
        "Started an online study group that grew to 250 members",
        "Moderated a forum of 10,000 members during a summer internship",
        "Organized 8 meetups for a local hobby group as a volunteer"],
    "communications": [
        "Wrote 12 news stories for the student newspaper",
        "Drafted 6 press releases during a summer internship",
        "Wrote the monthly newsletter of a local charity, sent to 1,500 supporters"],
    "events": [
        "Planned a charity dinner for 150 guests as a course project",
        "Booked venues and suppliers for 10 events during a summer internship",
        "Ran registration for a 1,000-person community festival as a volunteer"],
    "ecommerce": [
        "Ran a small online shop selling prints, with 120 orders in a year",
        "Updated 300 product listings during a summer internship",
        "Set up an online store for a charity shop as a volunteer with its first 80 items"],
    # sales
    "solutions-engineer": [
        "Built a demo app on a public API for a course project and presented it to 30 classmates",
        "Ran 10 product demos during a summer internship alongside senior engineers",
        "Set up a ticketing system for a nonprofit as a volunteer, used by its 15 staff"],
    "account-executive": [
        "Ran 20 practice discovery calls in a sales course",
        "Booked 12 meetings during a summer sales internship",
        "Raised $5,000 for a local charity by phone as a volunteer"],
    "sales-development": [
        "Completed a 4-week sales bootcamp with daily cold-call practice",
        "Booked 8 qualified meetings during a summer sales internship",
        "Raised $3,000 for a student charity drive by calling alumni"],
    "account-manager": [
        "Ran 10 role-play renewal calls in a customer relationship course",
        "Prepared quarterly reviews for 20 accounts during a summer internship",
        "Managed 15 sponsors for a student festival as a volunteer"],
    "sales-manager": [
        "Completed a 10-week sales leadership course for new managers",
        "Coached 3 new sellers as a senior representative until each reached full target",
        "Led a team of 10 volunteers in a fundraising drive for a local charity"],
    "sales-representative": [
        "Completed a 4-week sales training course with role-play customer calls",
        "Sold $40,000 of products during a summer sales internship",
        "Sold 300 raffle tickets for a school fundraiser as a volunteer"],
    "sales-operations": [
        "Built a sales dashboard in {bi:Tableau} for a course project from 2 years of sample data",
        "Cleaned 5,000 duplicate records in {crm:the CRM} during a summer internship",
        "Built a donor tracker for a local charity as a volunteer covering 600 donors"],
    "business-development": [
        "Researched 50 potential partners for a fictional startup as a course project",
        "Built a list of 100 target partners during a summer internship",
        "Signed 8 local sponsors for a student festival as a volunteer"],
    "solutions-architect": [
        "Built 3 practice designs on {cloud:AWS} while earning a cloud architecture certificate",
        "Drew the architecture for 4 customer proposals during a summer internship",
        "Designed a low-cost hosting setup for a nonprofit as a volunteer that costs $15 a month"],
    "sales-engineer": [
        "Built 3 demo scenarios on a free analytics tool for a course project",
        "Ran 8 demos during a summer internship alongside a senior sales engineer",
        "Trained 6 staff of a nonprofit on their new booking system as a volunteer"],
    "retail": [
        "Ran a stall at a school market that sold 200 items",
        "Served about 80 customers a shift in a holiday season job",
        "Sorted and priced about 500 donated items a month at a charity shop as a volunteer"],
    # customer service
    "customer-success-manager": [
        "Wrote a sample onboarding plan for 3 kinds of customer in a customer success course",
        "Onboarded 15 small customers during a summer internship",
        "Answered about 20 member questions a week for a local sports club as a volunteer"],
    "technical-account-manager": [
        "Documented 5 setups on {cloud:AWS} while earning a cloud certificate",
        "Prepared 10 technical review decks during a summer internship",
        "Helped 12 small businesses set up their websites as a volunteer"],
    "customer-support": [
        "Completed a 4-week customer service course with written and phone practice",
        "Answered about 30 customer chats a day during a summer job",
        "Answered a local charity’s help line for 6 hours a week as a volunteer"],
    "implementation": [
        "Configured 3 practice projects in a software implementation course",
        "Supported 5 customer setups during a summer internship",
        "Moved a charity’s 1,200 contacts into a new system as a volunteer"],
    # accounting and finance
    "accounting": [
        "Closed 3 practice months for a sample company in a bookkeeping course",
        "Reconciled 12 bank accounts each month during a summer internship",
        "Kept the books of a local youth club as a volunteer, about 200 entries a month"],
    "financial-analyst": [
        "Built a 3-statement model of a public company for a course project",
        "Updated the monthly budget report for 8 departments during a summer internship",
        "Managed the budget of a student society of 200 members"],
    "tax": [
        "Prepared 2 practice corporate returns in a corporate tax course",
        "Prepared workpapers for 15 corporate returns during a summer internship",
        "Prepared 60 personal tax returns at a free tax clinic as a volunteer"],
    "treasury": [
        "Built a 13-week cash forecast for a course case study",
        "Reconciled 20 bank accounts daily during a summer internship",
        "Managed $15,000 a year of cash for a student society"],
    "payroll": [
        "Ran 3 practice payroll cycles in a payroll course",
        "Checked timesheets for 300 employees each week during a summer internship",
        "Ran payroll for a small nonprofit of 12 staff as a volunteer"],
    "audit": [
        "Tested 20 controls for a practice case in an auditing course",
        "Tested 50 expense claims for policy breaches during a summer internship",
        "Checked 400 transactions of a local sports club as its volunteer auditor"],
    "investment": [
        "Valued 3 listed companies with a discounted cash flow model for a course project",
        "Screened 80 companies for the deal team during a summer internship",
        "Helped 4 local startups build their first financial models as a volunteer"],
    "trader": [
        "Traded a simulated portfolio for 6 months as a course project, inside every risk limit",
        "Booked about 200 trades a day during a summer internship on a trading desk",
        "Ran a university investment club of 40 students, writing a weekly market note"],
    "insurance": [
        "Priced 10 practice policies in an introductory insurance course",
        "Prepared files for 150 policy renewals during a summer internship",
        "Helped 30 families file home insurance claims after a flood as a volunteer"],
    "lending": [
        "Analyzed the financial statements of 5 companies for a corporate finance course",
        "Spread financial statements for 40 loan applications during a summer internship",
        "Reviewed 30 microloan applications as a volunteer for a community lender"],
    "procurement": [
        "Compared 5 supplier bids for a course case study and wrote a recommendation",
        "Raised about 60 purchase orders a week during a summer internship",
        "Sourced food for a charity kitchen as a volunteer, saving $2,000 a year"],
    # legal and compliance
    "legal-counsel": [
        "Drafted 4 commercial contracts in a law school drafting course",
        "Reviewed 30 supplier contracts during a summer internship with an in-house legal team",
        "Advised 20 small businesses on lease terms at a law school clinic"],
    "paralegal": [
        "Completed a 6-month paralegal certificate course",
        "Filed 40 documents with courts and registries during a summer internship",
        "Helped 25 tenants fill in court forms as a volunteer at a legal aid clinic"],
    "compliance": [
        "Reviewed 20 practice cases in an anti-money-laundering certificate course",
        "Checked 300 customer files during a summer internship",
        "Updated 5 policies of a local charity as a volunteer"],
    "policy": [
        "Wrote a 15-page policy paper on data privacy for a graduate course",
        "Tracked 50 bills for a trade association during a summer internship",
        "Wrote 3 submissions to the city council as a volunteer for a housing group"],
    # HR and recruiting
    "recruiter": [
        "Wrote 5 sample job postings in a recruiting course",
        "Scheduled about 40 interviews a week during a summer internship",
        "Recruited 30 volunteers for a community festival"],
    "technical-recruiter": [
        "Sourced 100 engineers for a practice search in a recruiting course",
        "Screened 60 engineering applicants during a summer internship",
        "Matched 20 career changers with volunteer mentors for a coding bootcamp"],
    "human-resources": [
        "Wrote an onboarding plan for a 50-person company in an HR fundamentals course",
        "Onboarded 25 new hires during a summer internship",
        "Ran onboarding for 80 volunteers at a food bank"],
    "compensation-benefits": [
        "Built a salary benchmark of 20 jobs from public pay data for a course project",
        "Matched 150 jobs to market survey data during a summer internship",
        "Compared 3 health plans for a small nonprofit as a volunteer"],
    "training": [
        "Designed a 3-module online course in an instructional design class",
        "Scheduled 30 training sessions during a summer internship",
        "Taught computer basics to 40 older adults as a volunteer"],
    # operations and administration
    "operations-manager": [
        "Mapped a local bakery’s ordering process for a course project and removed 2 steps",
        "Tracked about 500 orders a week during a summer internship",
        "Organized the storeroom of a youth sports club as a volunteer, tracking 300 items"],
    "executive-assistant": [
        "Completed a 6-week office administration course",
        "Managed the calendars of 2 managers during a summer internship",
        "Organized the meetings of a 9-member volunteer board"],
    "workplace": [
        "Planned an office layout for 30 desks in a facilities management course",
        "Answered about 20 office requests a day during a summer internship",
        "Ran room bookings for a community center as a volunteer, about 50 a month"],
    "supply-chain": [
        "Built a demand forecast from 2 years of store sales for a course project",
        "Counted and reconciled stock of 400 items during a summer internship",
        "Planned 12 delivery routes a week for a food bank as a volunteer"],
    "ehs": [
        "Completed a 30-hour workplace safety course",
        "Ran 25 safety inspections during a summer internship at a factory",
        "Wrote the safety plan for a 2,000-person community festival as a volunteer"],
    # hardware and engineering
    "hardware-engineer": [
        "Designed a 4-layer circuit board for a course project that worked on the first build",
        "Tested 30 prototype boards during a summer internship",
        "Built 10 sensor kits for a high school robotics club as a volunteer"],
    "mechanical-engineer": [
        "Designed a drone frame in CAD for a capstone project, 20% lighter than the kit frame",
        "Made 25 part drawings during a summer internship, all released to suppliers",
        "Built a wheelchair ramp for a community center as a volunteer in 3 weekends"],
    "electrical-engineer": [
        "Designed a solar charger for a course project that charges a phone in 3 hours",
        "Tested 20 power boards during a summer internship",
        "Rewired 24 stage lights at a community theater as a volunteer"],
    "optics": [
        "Measured 5 lens types on an optical bench in a lab course",
        "Aligned 40 laser assemblies during a summer internship",
        "Ran telescope nights for an astronomy club as a volunteer, about 300 visitors a year"],
    "materials-engineer": [
        "Tested the tensile strength of 30 samples in a materials lab course",
        "Prepared 100 samples for microscopy during a summer internship",
        "Ran materials science demos for 200 school students as a volunteer"],
    "robotics": [
        "Built a line-following robot in {lang:C++} for a course project that finished the track in 40 s",
        "Wrote 15 simulation scenarios during a summer internship",
        "Coached a high school robotics team of 12 students as a volunteer"],
    "manufacturing": [
        "Ran a time study on 3 assembly steps in a lean manufacturing course",
        "Measured cycle times at 5 stations during a summer internship for a line rebalance",
        "Organized a tool library of 150 tools for a community workshop as a volunteer"],
    "test-engineer": [
        "Built an automated bench test in {lang:Python} for a course project that checks a board in 30 s",
        "Ran 200 tests on prototype units during a summer internship",
        "Tested 15 donated laptops for a charity as a volunteer"],
    "aerospace": [
        "Wrote flight control code for a student rocket that reached 3,000 m",
        "Ran 100 simulation cases during a summer internship",
        "Mentored a high school model rocket club of 15 students as a volunteer"],
    "technician": [
        "Completed a 1-year technical course in electrical maintenance",
        "Assisted on about 20 repairs a week as an apprentice",
        "Fixed 30 bikes at a community bike shop as a volunteer"],
    "field-service": [
        "Completed a 6-month course in electronics service",
        "Went on 50 service visits with senior engineers during a summer internship",
        "Installed internet access at 4 community centers as a volunteer"],
    "construction": [
        "Scheduled a 3-story building for a construction management course",
        "Tracked 200 requests for information on a hospital project during a summer internship",
        "Built 2 homes with a volunteer housing group"],
    # writing
    "technical-writer": [
        "Wrote a 20-page user guide for a course project app",
        "Documented 15 API endpoints during a summer internship",
        "Rewrote 3 setup guides for an open-source project as a volunteer"],
    # science and healthcare
    "life-sciences": [
        "Ran 20 experiments for a final-year research project",
        "Prepared about 50 samples a week during a summer lab internship",
        "Taught a weekly science club for 15 school students as a volunteer"],
    "healthcare": [
        "Completed a 12-week healthcare administration course",
        "Scheduled about 60 patient visits a day during a summer internship",
        "Volunteered 200 hours at a hospital front desk"],
    "nursing": [
        "Completed 800 hours of clinical rotations in medical, surgical and pediatric units",
        "Cared for up to 4 patients a shift under supervision in a final-year placement",
        "Worked 20 hours a week as a nursing assistant during studies"],
    "mental-health": [
        "Completed 700 hours of supervised clinical practice in a master’s program",
        "Saw 12 clients a week under supervision during a counseling internship",
        "Answered a crisis text line for 4 hours a week as a volunteer"],
    "clinical-research": [
        "Completed a 10-week clinical research certificate, good clinical practice included",
        "Entered data for 60 study participants during a summer internship",
        "Helped run a health survey of 400 people as a volunteer"],
    # education, hospitality, first jobs, crypto
    "education": [
        "Designed a 4-week practice course in a teaching methods class",
        "Graded about 60 assignments a week as a teaching assistant",
        "Tutored 10 high school students in math as a volunteer"],
    "hospitality": [
        "Completed a 6-month culinary course with a food safety certificate",
        "Cooked on the grill station for about 150 covers a night in a summer job",
        "Cooked weekly meals for 80 people at a community kitchen as a volunteer"],
    "intern": [
        "Built a weather app in {lang:Python} as a first-year project, used by 20 friends",
        "Completed a 6-week summer coding program for students",
        "Taught basic coding to 8 middle school students as a volunteer"],
    "blockchain-engineer": [
        "Built a small blockchain in {lang:Go} for a course project with 3 nodes reaching consensus",
        "Ran 5 test nodes during a summer internship and reported the sync bugs they showed",
        "Fixed 4 issues in an open-source wallet library as a volunteer contributor"],
    "smart-contract-engineer": [
        "Wrote a token contract for a course project with 50 tests that cover every line",
        "Wrote 80 fuzz tests for a lending protocol during a summer internship",
        "Found 2 bugs in public audit contests, both confirmed by the judges"],
}

# kind of work -> what someone years further on has: [leading a team, owning a strategy or a large program, hiring and mentoring
# or a result reached with other teams]
SENIOR = {
    # software
    "software-engineer": [
        "Led a group of 8 engineers through a 9-month rebuild of the order system, shipped with no downtime",
        "Set the testing strategy for 5 teams; production incidents fell from 14 a quarter to 4",
        "Hired 6 engineers and mentored 4 to promotion in 2 years"],
    "backend-engineer": [
        "Led the 6 engineers of the payments platform team; on-call pages fell from 40 a week to 6",
        "Owned the 18-month plan to split the core database, moving 30 services with no data loss",
        "Set API design standards adopted by 9 teams and reviewed every new public endpoint"],
    "frontend-engineer": [
        "Led a frontend team of 6 engineers and hired 3 more in a year",
        "Owned the move of 4 products to one {front:React} component library; new screens ship in half the time",
        "Set web performance budgets with 7 teams; 90% of pages now load in under 2 s on a mid-range phone"],
    "full-stack-engineer": [
        "Led a team of 8 engineers across web and back end that delivered 3 major launches in a year",
        "Owned the 12-month move from one large application to 5 services while shipping features every week",
        "Mentored 5 engineers, 3 of whom were promoted within 18 months"],
    "mobile-engineer": [
        "Led a mobile team of 9 engineers across two platforms, releasing every week for 2 years",
        "Set the mobile architecture now shared by 4 apps; a new screen takes 3 days instead of 2 weeks",
        "Hired 5 mobile engineers through an interview loop I designed and ran for 40 candidates"],
    "qa-engineer": [
        "Led a QA team of 7 across 4 product teams and cut release testing from 3 days to 4 hours",
        "Owned the company’s test strategy; defects found by customers fell 65% in a year",
        "Trained 30 developers to write their own automated tests"],
    "embedded-engineer": [
        "Led a firmware team of 6 that shipped 3 products in 2 years",
        "Owned the firmware update and security plan for 200,000 devices in the field",
        "Ran weekly design reviews with the hardware and app teams; late hardware changes fell by 50%"],
    "engineering-manager": [
        "Led 4 teams and 35 engineers through 5 managers; yearly attrition stayed under 8%",
        "Owned the engineering plan for a $12M product line and delivered 9 of its 10 yearly goals",
        "Grew the organization from 18 to 35 engineers in 18 months with a structured hiring process"],
    "web-developer": [
        "Led a web team of 5 developers running 3 sites with 2 million visits a month",
        "Owned the move of 3 sites to one content system, finished in 7 months",
        "Set coding standards and reviews for 4 outside agencies; defects at launch fell by 60%"],
    "product-engineer": [
        "Led a team of 6 engineers that owns activation; it rose from 40% to 55% in a year",
        "Set up the experiment process used by 5 teams, who ran 70 A/B tests in a year",
        "Mentored 4 engineers to own features from customer interview to release"],
    "systems-software": [
        "Led a team of 6 engineers that owns the storage engine used by 40 services",
        "Owned the 2-year plan to move the platform to a new concurrency model, finished on schedule",
        "Mentored 5 engineers in performance work; each now leads profiling for their own team"],
    "graphics-engineer": [
        "Led a rendering team of 7 engineers across 2 game titles",
        "Owned the renderer plan for a new console generation, shipped in 18 months",
        "Set GPU budgets with 3 art teams; frame-rate complaints after launch fell by 70%"],
    "game-developer": [
        "Led a gameplay team of 8 programmers on a game that sold 1.5 million copies",
        "Owned the gameplay architecture for 2 titles, shared across 3 studios",
        "Hired and mentored 5 programmers, 2 of whom now lead teams"],
    "tech-lead": [
        "Led technical direction for 3 teams and 20 engineers on the payments platform",
        "Owned the 2-year plan to replace the old checkout, delivered in 5 stages with no outage",
        "Ran the engineering interview loop and hired 8 engineers in a year"],
    "software-architect": [
        "Built and led an architecture group of 6 engineers who review every cross-team design",
        "Set the architecture strategy for 30 teams and 250 engineers across 3 products",
        "Led the 2-year move of 200 services to {cloud:AWS} with the platform teams, closing 2 data centers"],
    "developer-advocate": [
        "Led a developer relations team of 6 advocates and writers across 3 regions",
        "Owned the developer program strategy; monthly active developers rose from 8,000 to 30,000",
        "Ran the feedback process between developers and 5 product teams; 60 requests shipped in a year"],
    "automation-engineer": [
        "Led an integrations team of 5 engineers running 150 customer integrations",
        "Owned the integration platform strategy; a new connector takes 3 days instead of 3 weeks",
        "Worked with sales and support to cut escalations about integrations by 60%"],
    "business-systems": [
        "Led a business systems team of 6 supporting finance, sales and HR",
        "Owned the 18-month replacement of the finance system for 400 users, delivered on budget",
        "Set the yearly systems roadmap with 8 department heads; spending on tools fell 15%"],
    # AI and machine learning
    "machine-learning-engineer": [
        "Led a team of 8 machine learning engineers responsible for search and recommendations",
        "Owned the ranking roadmap for 2 years; revenue from recommendations grew 35%",
        "Set the evaluation standard 6 teams use before any model reaches customers"],
    "ai-engineer": [
        "Led a team of 7 engineers that builds the company’s AI features",
        "Owned the AI platform strategy; 12 product teams now ship model features on it",
        "Set cost and quality targets with 5 teams; spending per conversation fell 55%"],
    "forward-deployed-engineer": [
        "Led a group of 6 forward deployed engineers across 15 enterprise accounts",
        "Owned the deployment playbook for every new account; time to first daily use fell from 10 weeks to 5",
        "Turned field work into 8 product features with the product team, now used by 120 accounts"],
    "applied-ai": [
        "Led an applied AI team of 5 that rolled assistants out to 1,200 employees",
        "Owned the company’s AI adoption plan across 9 departments; weekly use reached 80%",
        "Set the review process for every AI workflow with department heads; 4 that showed no gain were stopped early"],
    "computer-vision": [
        "Led a team of 7 that builds the vision models in 3 product lines",
        "Owned the plan to run all vision models on the device, cutting cloud costs by $400K a year",
        "Set up a labeling program with an outside vendor that delivers 50,000 images a month"],
    "mlops": [
        "Led an ML platform team of 8 engineers serving 120 researchers and engineers",
        "Owned the GPU strategy and a compute budget of $15M a year",
        "Set release standards with 6 model teams; failed model releases fell from 12 a year to 2"],
    "research-scientist": [
        "Led a group of 6 scientists; 3 of our methods went into the company’s main model",
        "Set the research agenda for long-context models over 2 years, with 9 papers published",
        "Mentored 8 interns and junior researchers, 5 of whom published as first author"],
    "ai-trainer": [
        "Led a team of 25 annotators and 3 reviewers across 2 languages",
        "Owned the data quality program for a model training project of 50,000 examples",
        "Set review standards with the research team; examples rejected at audit fell from 9% to 2%"],
    # data
    "data-engineer": [
        "Led a data platform team of 7 engineers serving 120 analysts",
        "Owned the move from nightly batches to streaming on {queue:Kafka}; data now arrives within 5 minutes",
        "Set data contracts with 10 product teams; broken pipelines fell from 15 a month to 2"],
    "data-scientist": [
        "Led a team of 6 data scientists working with marketing, product and finance",
        "Owned the experimentation strategy; the company now runs 150 tests a year instead of 30",
        "Built the pricing model used by 3 business units with their finance leads, adding $4M in yearly revenue"],
    "data-analyst": [
        "Led a team of 5 analysts that answers questions for sales, product and finance",
        "Owned the company’s metrics plan; 40 dashboards were replaced by 8 trusted ones",
        "Hired and trained 4 analysts, each handling requests alone within 2 months"],
    "analytics-engineer": [
        "Led an analytics engineering team of 5 that owns 400 shared models",
        "Owned the plan to move all reporting into one modeled layer, finished in 9 months",
        "Set modeling standards with 6 analyst teams; duplicate metrics fell from 70 to 12"],
    "business-analyst": [
        "Led a team of 6 business analysts across finance and operations",
        "Owned the requirements for a $5M system replacement used by 800 people",
        "Set the analysis method used by 4 departments; change requests after sign-off fell by 60%"],
    "quant": [
        "Led a research team of 5 quants on a strategy managing $800M",
        "Owned the research process from idea to live trading; 6 new signals went live in a year",
        "Hired and trained 4 researchers, all of whom shipped a live signal in their first year"],
    "pricing": [
        "Led a pricing team of 4 analysts across 3 product lines",
        "Owned the pricing strategy for a $60M business; average revenue per customer rose 12% in a year",
        "Set discount rules with sales and finance; gross margin rose by 3 points"],
    "research-analyst": [
        "Led a research team of 6 analysts publishing 40 reports a year",
        "Owned the research agenda for 3 sectors followed by 500 clients",
        "Briefed the executive team each quarter; 3 market entries followed from our work"],
    "data-governance": [
        "Led a data governance team of 5 across 4 business units",
        "Owned the data governance program for 3,000 tables and 900 users",
        "Agreed data ownership with 20 department leads; every key table now has a named owner"],
    # cloud, DevOps and IT
    "devops-engineer": [
        "Led a platform team of 7 engineers supporting 25 product teams",
        "Owned the move of 150 services to {orch:Kubernetes} over 14 months with no major outage",
        "Set release standards with 25 teams; deploys rose from 30 a week to 200"],
    "site-reliability-engineer": [
        "Led an SRE team of 8 covering 60 services and a 24-hour on-call rotation",
        "Owned the reliability program; 45 customer-facing services now have service level objectives",
        "Set incident review practice across 12 teams; repeat incidents fell by 70%"],
    "it-support": [
        "Led an IT support team of 6 serving 1,500 employees in 4 offices",
        "Owned the device management rollout for 1,500 laptops, finished in 3 months",
        "Set service targets with HR and finance; employee satisfaction with IT rose from 3.8 to 4.6 out of 5"],
    "systems-engineer": [
        "Led a systems engineering team of 5 supporting 3,000 employees",
        "Owned identity and access for 120 applications and moved all of them to single sign-on",
        "Ran quarterly access reviews with security and HR; active accounts of former employees fell from 90 to 0"],
    "cloud-engineer": [
        "Led a cloud team of 6 engineers running 3 regions and 200 accounts",
        "Owned the cloud cost program; yearly spending fell by $2.5M",
        "Set the account and network standard adopted by 30 product teams"],
    "network-engineer": [
        "Led a network team of 5 engineers covering 30 offices and 2 data centers",
        "Owned the 2-year network refresh with a budget of $4M, delivered on time",
        "Set network standards with the security team; firewall rules fell from 9,000 to 2,500"],
    "database-administrator": [
        "Led a database team of 4 running 300 databases across 3 regions",
        "Owned the move of 80 databases to a managed cloud service with under 10 minutes of downtime each",
        "Set query review with 15 development teams; production incidents caused by queries fell 50%"],
    "data-center": [
        "Led a shift of 12 technicians across 2 data halls",
        "Owned the build-out of a new data hall of 4,000 servers, finished 2 weeks early",
        "Set safety and handover procedures with 3 contractors; incidents fell from 9 a year to 1"],
    "support-engineer": [
        "Led a technical support team of 10 across 3 time zones",
        "Owned the escalation process with engineering; the time to fix a priority bug fell from 12 days to 4",
        "Hired and trained 6 support engineers, all handling advanced cases within 3 months"],
    "system-administrator": [
        "Led a team of 5 administrators running 1,200 servers",
        "Owned the server refresh program, replacing 400 machines in 9 months",
        "Set change rules with 8 development teams; outages caused by changes fell by 60%"],
    # security
    "cybersecurity": [
        "Led a security team of 8 covering application, cloud and incident response",
        "Owned the 3-year security strategy and a budget of $3M",
        "Set security standards with 20 engineering teams; critical findings in production fell 75%"],
    "security-engineer": [
        "Led an application security team of 6 supporting 300 engineers",
        "Owned the secure development program, with a trained security champion in each of 25 teams",
        "Set cloud security rules with platform engineering; public storage buckets fell from 40 to 0"],
    "security-analyst": [
        "Led a security operations team of 9 across 3 shifts",
        "Owned the detection program; coverage of known attack techniques rose from 40% to 85%",
        "Ran 4 joint exercises a year with IT and legal; the time to respond to a breach fell by half"],
    "penetration-tester": [
        "Led a team of 6 penetration testers delivering 120 tests a year",
        "Owned the red team program, running 4 full-scope exercises a year",
        "Trained 10 development teams on secure coding from real test findings; repeat findings fell by 50%"],
    "security-compliance": [
        "Led a GRC team of 5 covering 4 audit frameworks",
        "Owned the compliance roadmap that added ISO 27001 and 2 regional certifications in 18 months",
        "Set control ownership with 12 departments; audit findings fell from 15 to 2"],
    "fraud-risk": [
        "Led a fraud team of 12 analysts across 2 regions",
        "Owned the fraud strategy for $2B in yearly payments; losses fell to 0.09% of volume",
        "Set decline rules with the product and payments teams; good customers wrongly declined fell by 40%"],
    "trust-safety": [
        "Led a trust and safety team of 20 reviewers across 3 shifts",
        "Owned the policy on harassment and hate speech across 2 products",
        "Set review targets with product and legal; serious reports are now acted on within 1 hour"],
    "physical-security": [
        "Led a security team of 40 officers across 6 sites",
        "Owned the security plan for 2 new offices, both opened on schedule",
        "Set emergency procedures with facilities and HR; drill participation rose from 60% to 95%"],
    "privacy": [
        "Led a privacy team of 4 working across product, legal and security",
        "Owned the privacy program for 15 countries and 20 million users",
        "Set privacy review with 10 product teams; every launch now passes review before release, up from 60%"],
    # product and project
    "product-manager": [
        "Led a team of 4 product managers covering onboarding, billing and growth",
        "Owned the product strategy for a $25M line of business that grew 30% a year",
        "Set the planning process for 6 teams; goals delivered on time rose from 55% to 80%"],
    "program-manager": [
        "Led a team of 5 program managers running the company’s largest initiatives",
        "Owned a $20M program across 12 teams that launched in 9 countries",
        "Set the program review used across the company; late launches fell from 40% to 15%"],
    "technical-program-manager": [
        "Led a group of 6 technical program managers across infrastructure and product",
        "Owned the 2-year data center exit program across 20 teams, finished a quarter early",
        "Set the launch review process used by 40 teams; launch rollbacks fell by 70%"],
    "project-manager": [
        "Led a team of 6 project managers delivering 40 projects a year",
        "Owned a $15M portfolio of projects, 90% of them delivered on time",
        "Set the project method used by 5 departments, with one status report and one risk list"],
    "product-operations": [
        "Led a product operations team of 5 supporting 12 product teams",
        "Owned the launch process for 80 releases a year across 3 products",
        "Set up a feedback system with sales and support that routes 10,000 comments a quarter to product teams"],
    "scrum-master": [
        "Coached 6 teams and 3 other scrum masters across 2 products",
        "Owned the move of 8 teams to one shared quarterly planning cycle",
        "Removed about 25 cross-team blockers a quarter through a weekly meeting of team leads"],
    "business-operations": [
        "Led a business operations team of 6 working with every department head",
        "Owned the yearly operating plan for a $200M business",
        "Ran a cost program across 10 departments that saved $4M a year"],
    "chief-of-staff": [
        "Led a team of 4 in the CEO’s office running planning, communications and special projects",
        "Owned yearly planning for a company of 900 employees and 15 departments",
        "Ran the integration of an acquired company of 120 people, finished in 6 months"],
    # design
    "product-designer": [
        "Led a design team of 6 across 3 product areas",
        "Owned the design system strategy; 8 teams now build from one library",
        "Hired 4 designers and started a weekly critique that every designer attends"],
    "ux-researcher": [
        "Led a research team of 5 serving 8 product teams",
        "Owned the research plan for a new product line: 120 studies over 2 years",
        "Trained 30 designers and product managers to run their own usability tests"],
    "graphic-designer": [
        "Led a brand team of 5 designers and 2 illustrators",
        "Owned the merging of 3 product brands into one, rolled out in 6 months",
        "Set brand guidelines used by 4 agencies and 60 marketers"],
    "content-designer": [
        "Led a content design team of 5 across 4 product areas",
        "Owned the voice and terms of the product across 300 screens",
        "Set content review with design and legal; the time to approve a screen fell from 5 days to 1"],
    "video-motion": [
        "Led a video team of 6 producing 100 videos a year",
        "Owned the motion design system used across 3 products and all marketing",
        "Set up a production process with marketing and product that cut the cost of a video by 40%"],
    "audio": [
        "Led an audio team of 6 on 2 released games",
        "Owned the audio pipeline for 4 titles, shared across 2 studios",
        "Hired and trained 3 sound designers and set up review for every sound in the game"],
    # marketing and communications
    "marketing-manager": [
        "Led a marketing team of 12 across brand, content, events and growth",
        "Owned a marketing budget of $6M and a plan that produced 45% of new sales pipeline",
        "Set shared targets with sales; revenue from marketing leads rose from $8M to $14M"],
    "product-marketing": [
        "Led a product marketing team of 5 across 3 product lines",
        "Owned positioning for the move into large companies; enterprise deals rose from 10 to 45 a year",
        "Set the launch process with product and sales used for 25 launches a year"],
    "growth-marketing": [
        "Led a growth team of 7 across paid, lifecycle and referrals",
        "Owned an acquisition budget of $4M a year; the cost of a new customer fell 30%",
        "Ran a testing program with product and data: 120 tests a year, 35 shipped"],
    "content-writer": [
        "Led a content team of 5 writers and editors",
        "Owned the content strategy that grew visits from search from 100,000 to 400,000 a month",
        "Set editorial standards with product and legal for 200 articles a year"],
    "seo": [
        "Led a search team of 6 covering technical work, content and links",
        "Owned the search strategy for 3 sites with 2 million visits a month",
        "Set search checks with engineering and content; new pages are indexed in 2 days instead of 3 weeks"],
    "advertising": [
        "Led a paid media team of 6 managing $15M a year",
        "Owned the channel strategy across 6 networks; return rose from $3.10 to $4.40 for every $1 spent",
        "Set up measurement with finance and data; paid results now match the books within 2%"],
    "social-media": [
        "Led a social team of 5 across 6 networks and 3 regions",
        "Owned the social strategy for a brand with 2 million followers",
        "Set a response process with support; 95% of customer messages are answered within 1 hour"],
    "community-manager": [
        "Led a community team of 5 managing 3 communities with 120,000 members",
        "Owned the community strategy; members who answer questions grew from 200 to 1,400",
        "Set a feedback process with 6 product teams; 40 member requests shipped in a year"],
    "communications": [
        "Led a communications team of 6 covering press, internal and executive communications",
        "Owned the company’s crisis communications plan, used in 3 incidents",
        "Ran communications for a funding round and an acquisition with legal, covered by 40 outlets"],
    "events": [
        "Led an events team of 6 running 80 events a year",
        "Owned an events budget of $3M that returned $8 of pipeline for every $1",
        "Set event plans with sales and marketing; 40% of attendees became qualified leads"],
    "ecommerce": [
        "Led an e-commerce team of 8 across web, marketplaces and merchandising",
        "Owned a $40M online channel that grew 30% a year",
        "Launched on 3 new marketplaces with operations and finance, adding $6M in sales"],
    # sales
    "solutions-engineer": [
        "Led a team of 7 solutions engineers supporting $40M of yearly sales",
        "Owned the proof-of-concept program; the win rate on deals with a proof rose from 35% to 60%",
        "Set up a feedback loop with product; 20 requests from the field shipped in a year"],
    "account-executive": [
        "Led a deal team of 4 on the company’s largest contract, worth $2.4M over 3 years",
        "Owned the enterprise territory for 2 regions and grew its pipeline from $5M to $12M",
        "Mentored 4 new account executives; all reached target in their first year"],
    "sales-development": [
        "Led a team of 8 sales development representatives that booked 140 meetings a month",
        "Owned the outbound strategy for 2 regions; pipeline from outreach rose from $6M to $11M",
        "Trained 15 new representatives; the time to a first booked meeting fell from 3 weeks to 1"],
    "account-manager": [
        "Led a team of 6 account managers covering $30M of yearly revenue",
        "Owned the renewal strategy for the 50 largest accounts; renewals rose from 89% to 95%",
        "Set up account planning with product and support; upgrades rose 30%"],
    "sales-manager": [
        "Led 4 sales managers and 35 sellers across 3 regions",
        "Owned a yearly target of $45M and closed 108% of it",
        "Set territory and pricing rules with marketing and finance; the average deal grew 22%"],
    "sales-representative": [
        "Led a team of 6 sales representatives in the largest territory",
        "Owned the 30 largest customer accounts in the region, worth $3M a year",
        "Trained 10 new representatives on product and negotiation"],
    "sales-operations": [
        "Led a revenue operations team of 7 supporting 200 sellers",
        "Owned the yearly planning of targets and territories for a $120M sales organization",
        "Set one set of pipeline rules with sales, marketing and finance; forecast accuracy reached 95%"],
    "business-development": [
        "Led a partnerships team of 5 across 3 regions",
        "Owned the partner strategy that grew revenue from partners from $4M to $15M",
        "Negotiated a joint launch with 2 partners and the product team that added 20,000 customers"],
    "solutions-architect": [
        "Led a team of 8 solutions architects covering the 60 largest customers",
        "Owned the reference architecture program; 25 designs are now used across sales and support",
        "Set technical win plans with sales and product for deals worth $50M a year"],
    "sales-engineer": [
        "Led a team of 6 sales engineers supporting 30 account executives",
        "Owned the demonstration and proof-of-concept strategy; the technical win rate rose from 38% to 55%",
        "Set up a weekly product review with engineering; 15 gaps that blocked deals were closed in a year"],
    "retail": [
        "Led a shift team of 8 associates in a store with $3M in yearly sales",
        "Owned the store’s visual merchandising plan and planogram checks; sales of featured items rose 20%",
        "Trained 12 new associates and ran stock counts with the warehouse team"],
    # customer service
    "customer-success-manager": [
        "Led a team of 8 customer success managers covering $40M of yearly revenue",
        "Owned the onboarding program for 300 accounts; the time to first value fell from 40 days to 14",
        "Set up early warnings for churn with product and sales; yearly churn fell from 11% to 6%"],
    "technical-account-manager": [
        "Led a team of 6 technical account managers covering 50 enterprise accounts",
        "Owned the escalation process with engineering; priority-one incidents were resolved 40% faster",
        "Set up launch reviews with product and support for 30 enterprise launches a year"],
    "customer-support": [
        "Led a support team of 12 agents across 2 shifts",
        "Owned the help center; 60% of customers now find an answer without a ticket",
        "Set up a bug process with engineering; repeat tickets about known bugs fell by 50%"],
    "implementation": [
        "Led a team of 8 implementation consultants delivering 60 projects a year",
        "Owned the implementation method used across 3 products; projects on time rose from 70% to 90%",
        "Set handovers with sales and support; customers needing rework after going live fell from 20% to 8%"],
    # accounting and finance
    "accounting": [
        "Led an accounting team of 6 across 3 countries",
        "Owned the move to a new accounting system, live in 7 months with no missed close",
        "Set the close calendar with finance and operations; month-end closes in 4 days instead of 10"],
    "financial-analyst": [
        "Led a team of 5 analysts covering planning for the whole company",
        "Owned the long-range plan for a $300M business, presented to the board each year",
        "Set budget rules with 15 department heads; spending came in within 2% of plan"],
    "tax": [
        "Led a tax team of 6 covering 20 countries",
        "Owned the tax planning for 2 acquisitions worth $500M",
        "Set intercompany pricing with finance and legal across 12 entities, accepted by 3 tax authorities"],
    "treasury": [
        "Led a treasury team of 4 managing $800M of cash",
        "Owned the currency hedging program for 15 currencies",
        "Arranged a $150M credit line with 5 banks, working with legal and the finance team"],
    "payroll": [
        "Led a payroll team of 6 paying 8,000 employees in 15 countries",
        "Owned the move to one payroll system for 15 countries, finished in 10 months",
        "Set payroll cut-off dates with HR and finance; late changes fell by 70%"],
    "audit": [
        "Led an internal audit team of 7 delivering 30 audits a year",
        "Owned the risk-based audit plan, approved by the audit committee each year for 4 years",
        "Agreed fixes with 10 department heads; overdue audit actions fell from 40 to 5"],
    "investment": [
        "Led a corporate development team of 4 across 10 deals worth $1.2B",
        "Owned the acquisition strategy for 2 years, in which 5 acquisitions closed",
        "Led integration planning with operations and HR for 3 acquisitions, all on schedule"],
    "trader": [
        "Led a trading desk of 6 traders with a daily volume of $200M",
        "Owned the desk’s risk limits with the risk team, with no limit breach in 3 years",
        "Trained 5 junior traders, 3 of whom now run their own books"],
    "insurance": [
        "Led an underwriting team of 8 writing $60M in premiums a year",
        "Owned the underwriting guidelines for 3 commercial products",
        "Set pricing reviews with the actuarial and claims teams; the loss ratio improved by 5 points"],
    "lending": [
        "Led a credit team of 6 analysts approving $300M of loans a year",
        "Owned the credit policy for small business lending across 2 products",
        "Set approval limits with risk and sales; decisions take 1 day instead of 5 with no rise in defaults"],
    "procurement": [
        "Led a procurement team of 8 managing $150M of yearly spending",
        "Owned the sourcing strategy for 4 categories, saving $12M in 2 years",
        "Set a buying process with finance and legal; 90% of spending now goes to approved suppliers"],
    # legal and compliance
    "legal-counsel": [
        "Led a commercial legal team of 5 lawyers and 2 paralegals",
        "Owned the contracting strategy; 85% of deals now close on the company’s own terms",
        "Set approval rules with sales and finance; legal review takes 3 days instead of 10"],
    "paralegal": [
        "Led a team of 4 paralegals supporting 12 lawyers",
        "Owned the contract management system for 8,000 contracts",
        "Set up an intake process with sales and procurement; every contract request is logged within 1 day"],
    "compliance": [
        "Led a compliance team of 10 across 3 countries",
        "Owned the anti-money-laundering program through 2 regulator inspections with no finding",
        "Set compliance checks with product and operations for 12 new products before launch"],
    "policy": [
        "Led a public policy team of 5 across 3 regions",
        "Owned the policy strategy on 2 major regulations; 8 of our proposals were adopted",
        "Built a coalition of 15 companies and 4 trade groups on one bill"],
    # HR and recruiting
    "recruiter": [
        "Led a recruiting team of 6 that hired 180 people in a year",
        "Owned the hiring plan with finance and department heads as the company grew from 400 to 650",
        "Set interview standards with 25 hiring managers; offer acceptance rose from 72% to 88%"],
    "technical-recruiter": [
        "Led a technical recruiting team of 5 that hired 90 engineers in a year",
        "Owned the engineering hiring strategy across 3 countries",
        "Set the interview loop with engineering leaders; the time to an offer fell from 45 days to 25"],
    "human-resources": [
        "Led a team of 4 HR business partners covering 1,200 employees",
        "Owned the reorganization of 2 business units with 300 people, finished in one quarter",
        "Set up manager training with the leadership team; manager survey scores rose from 3.6 to 4.3"],
    "compensation-benefits": [
        "Led a compensation team of 4 covering 6,000 employees in 12 countries",
        "Owned the equity plan and a yearly pay budget of $40M",
        "Set pay ranges with finance and recruiting; offers above range fell from 25% to 5%"],
    "training": [
        "Led a learning team of 6 serving 5,000 employees",
        "Owned the leadership development program for 300 managers",
        "Set training plans with 8 department heads; the time for a new hire to reach full speed fell 30%"],
    # operations and administration
    "operations-manager": [
        "Led an operations team of 60 across 3 sites",
        "Owned the operations plan for a business with $50M in yearly sales",
        "Set service targets with sales and finance; the cost of handling an order fell 18%"],
    "executive-assistant": [
        "Led a team of 4 assistants supporting the leadership team",
        "Owned the planning of 4 board meetings a year and the yearly leadership off-site",
        "Coordinated the calendars of 8 executives through the yearly planning cycle"],
    "workplace": [
        "Led a workplace team of 10 across 6 offices",
        "Owned a facilities budget of $8M and a 3-year office plan",
        "Set a hybrid office plan with HR and finance that cut office space by 30%"],
    "supply-chain": [
        "Led a supply chain team of 8 across planning and logistics",
        "Owned the network plan for 4 warehouses; delivery cost per order fell 15%",
        "Set a monthly planning meeting with sales and finance; forecast accuracy rose from 70% to 88%"],
    "ehs": [
        "Led an EHS team of 5 across 4 sites",
        "Owned the safety program for 3,000 employees; the injury rate fell 50% in 2 years",
        "Set safety targets with the managers of 4 sites, all met for 3 years running"],
    # hardware and engineering
    "hardware-engineer": [
        "Led a hardware team of 6 engineers on 2 product lines",
        "Owned the hardware roadmap for a product shipping 200,000 units a year",
        "Set design reviews with manufacturing and firmware; board revisions per product fell from 5 to 2"],
    "mechanical-engineer": [
        "Led a team of 7 mechanical engineers on a new product line",
        "Owned the mechanical design of a product that sells 100,000 units a year",
        "Worked with suppliers and quality to cut part cost by 15% across 40 parts"],
    "electrical-engineer": [
        "Led a team of 5 electrical engineers across 3 products",
        "Owned power design for a product family of 8 models",
        "Set certification plans with test and compliance; all 6 products passed at the first attempt"],
    "optics": [
        "Led an optics team of 5 engineers and 3 technicians",
        "Owned the optical design of 3 product generations",
        "Set yield targets with manufacturing; yield across 4 products rose from 75% to 92%"],
    "materials-engineer": [
        "Led a materials team of 6 engineers and technicians",
        "Owned the materials plan for a new product line and qualified 5 materials for it",
        "Set failure analysis practice with quality and suppliers; repeat failures fell by 60%"],
    "robotics": [
        "Led a robotics team of 8 across planning, control and perception",
        "Owned the autonomy roadmap for a fleet of 500 robots",
        "Set field test plans with operations at 6 customer sites"],
    "manufacturing": [
        "Led a manufacturing engineering team of 8 across 3 lines",
        "Owned the launch of a new production line with a budget of $10M",
        "Set quality targets with suppliers and design; scrap across the plant fell from 5% to 2%"],
    "test-engineer": [
        "Led a test team of 6 engineers across 3 products",
        "Owned the validation strategy for a product family of 5 models",
        "Set test plans with design and manufacturing; defects found after release fell 60%"],
    "aerospace": [
        "Led a flight software team of 9 engineers",
        "Owned the guidance and control design for a new vehicle over 3 years",
        "Set test campaigns with hardware and operations for 8 launches, all on time"],
    "technician": [
        "Led a team of 6 technicians across 2 shifts",
        "Owned the maintenance plan for 120 machines; uptime rose from 94% to 98%",
        "Set spare parts levels with purchasing; waits for parts fell from 3 days to 1"],
    "field-service": [
        "Led a team of 10 field engineers across 2 regions",
        "Owned the service plan for 400 installed systems",
        "Set first-visit targets with parts and support; faults fixed at the first visit rose from 70% to 88%"],
    "construction": [
        "Led a project team of 12 on a $120M mixed-use development",
        "Owned a portfolio of 4 projects worth $200M, all delivered within 3% of budget",
        "Set safety plans with 30 subcontractors; no lost-time injury in 1 million hours worked"],
    # writing
    "technical-writer": [
        "Led a documentation team of 5 writers across 4 products",
        "Owned the documentation strategy; support tickets about the documentation fell 40%",
        "Set documentation reviews with 10 engineering teams for every release"],
    # science and healthcare
    "life-sciences": [
        "Led a lab team of 5 associates and technicians",
        "Owned the assay development plan for 2 drug programs",
        "Set lab methods with 3 partner teams; repeated experiments fell by 40%"],
    "healthcare": [
        "Led clinical operations for 200 clinicians in 15 states",
        "Owned the expansion of a telehealth service into 4 new specialties",
        "Set quality measures with medical leaders; follow-up within 7 days rose from 60% to 90% of patients"],
    "nursing": [
        "Led a nursing team of 15 as charge nurse on a 30-bed unit",
        "Owned a fall prevention program; falls on the unit fell by 45%",
        "Set discharge planning with doctors and social workers; the average stay fell by 1 day"],
    "mental-health": [
        "Led clinical supervision for 8 therapists and 4 trainees",
        "Owned the clinical quality program for a service seeing 2,000 clients a year",
        "Set referral pathways with 5 local hospitals; the wait for a first session fell from 6 weeks to 2"],
    "clinical-research": [
        "Led a team of 6 clinical research associates across 2 trials",
        "Owned site monitoring for a 40-site trial in 5 countries",
        "Set monitoring plans with the data management and medical teams; open queries fell by 60%"],
    # education, hospitality, first jobs, crypto
    "education": [
        "Led a team of 8 instructors teaching 2,000 students a year",
        "Owned the curriculum for a 12-week program, rewritten in 6 months",
        "Set assessment standards with 3 departments; pass rates rose from 72% to 85%"],
    "hospitality": [
        "Led a kitchen team of 18 across 2 restaurants",
        "Owned food costs of $1.2M a year, kept at 27% of sales",
        "Set menus with front of house and suppliers; average spend per guest rose 15%"],
    "intern": [
        "Led a team of 5 students that won first place among 40 teams at a university hackathon",
        "Ran the university coding club of 150 members for a year",
        "Mentored 20 first-year students as a teaching assistant for an introductory programming course"],
    "blockchain-engineer": [
        "Led a protocol team of 7 engineers across 2 chains",
        "Owned the upgrade plan for a network of 1,500 nodes, finished with no downtime",
        "Set security reviews with 2 outside audit firms for every release, 12 in a year"],
    "smart-contract-engineer": [
        "Led a smart contract team of 5 across 3 protocols holding $300M",
        "Owned the security process: every release passes 2 outside audits and a 30-day bug bounty",
        "Set upgrade plans with the governance and frontend teams for 6 releases with no incident"],
}

# work where the collector's skill tags say what the employer wants from the person
TECH = {
    "software-engineer", "backend-engineer", "frontend-engineer", "full-stack-engineer", "mobile-engineer", "qa-engineer", "embedded-engineer",
    "engineering-manager", "tech-lead", "web-developer", "product-engineer", "systems-software", "graphics-engineer", "game-developer", "software-architect",
    "developer-advocate", "automation-engineer", "machine-learning-engineer", "ai-engineer", "forward-deployed-engineer", "applied-ai",
    "computer-vision", "mlops", "research-scientist", "data-engineer", "data-scientist", "data-analyst", "analytics-engineer", "quant",
    "data-governance", "devops-engineer", "site-reliability-engineer", "systems-engineer", "cloud-engineer", "network-engineer",
    "database-administrator", "support-engineer", "system-administrator", "cybersecurity", "security-engineer", "security-analyst",
    "penetration-tester", "solutions-engineer", "solutions-architect", "sales-engineer", "technical-account-manager", "robotics", "aerospace",
    "test-engineer", "blockchain-engineer", "smart-contract-engineer", "intern",
}

# A kind of work that appears later and has no entry yet gets its field's lines until somebody writes its own.
FIELD = {
    "software-development": ROLE["software-engineer"], "ai-machine-learning": ROLE["machine-learning-engineer"], "data-analytics": ROLE["data-analyst"],
    "cloud-devops-it": ROLE["devops-engineer"],
    "skilled-trades": ("Maintenance Technician", "preventive maintenance, troubleshooting, safety procedures", [
        "Cut unplanned downtime on 4 production lines from 18 to 7 hours a month with a weekly preventive maintenance plan",
        "Diagnosed and repaired electrical and mechanical faults on 30+ machines, closing 95% of work orders within 24 hours",
        "Led a lockout-tagout refresher for 22 colleagues; the site went 400 days without a lost-time incident",
        "Kept a spare-parts log that cut emergency orders by 40% in one year"]),
    "logistics-transport": ("Warehouse and Logistics Coordinator", "inventory control, shipping, scheduling", [
        "Ran inbound and outbound shipping for a 60,000 sq ft warehouse handling 1,200 orders a day at 99.6% accuracy",
        "Reorganised pick paths and cut average pick time from 4.2 to 2.9 minutes per order",
        "Planned routes for a fleet of 12 vans, lowering fuel cost by 11% in six months",
        "Trained 15 new associates on scanners, safety and the inventory system in their first week"]), "security": ROLE["cybersecurity"], "product-project": ROLE["project-manager"],
    "design-creative": ROLE["product-designer"], "marketing-communications": ROLE["marketing-manager"], "sales": ROLE["account-executive"],
    "customer-service": ROLE["customer-support"], "accounting-finance": ROLE["financial-analyst"], "legal-compliance": ROLE["compliance"],
    "hr-recruiting": ROLE["human-resources"], "operations-administration": ROLE["operations-manager"], "hardware-engineering": ROLE["mechanical-engineer"],
    "writing-translation": ROLE["content-writer"], "science-healthcare": ROLE["life-sciences"], "education-training": ROLE["education"],
    "retail-hospitality": ROLE["retail"], "crypto-web3": ROLE["blockchain-engineer"], "internships-entry-level": ROLE["intern"],
}
SLOT = re.compile(r"\{(\w+):([^}]*)\}")
NOT_VERB = {"The", "A", "An", "I", "My", "Our", "We", "Responsible", "In", "On", "At", "With", "For", "As", "During", "While", "Worked", "Helped"}

MORE_FILE = Path(__file__).with_name("resume_examples_more.json")
MORE = json.loads(MORE_FILE.read_text()) if MORE_FILE.exists() else {}
for slug_, m_ in MORE.items():
    if slug_ in ROLE: continue
    ROLE[slug_] = (m_["title"], m_["plain"], m_["lines"])
    ENTRY[slug_], SENIOR[slug_] = m_["entry"], m_["senior"]
    if m_.get("entry_title"): ENTRY_TITLE[slug_] = m_["entry_title"]
    if m_.get("tech"): TECH.add(slug_)


# Spelling (25 Nov 2026): the lines are written in American English, because the resume and cover letter pages are for the US; the
# UK CV pages turn them into British spelling with uk(). 78 lines had British forms ("optimisation", "modelling", "call centre") that
# showed on the US pages next to American ones. test() fails on a British form in a line. "program" and "license" are left alone by uk():
# a software program and the verb to license are spelled the same in Britain.
UK2US = {"optimisation": "optimization", "optimisations": "optimizations", "optimise": "optimize", "optimised": "optimized", "optimising": "optimizing",
 "modelling": "modeling", "modelled": "modeled", "analyse": "analyze", "analysed": "analyzed", "analysing": "analyzing",
 "centre": "center", "centres": "centers", "programme": "program", "programmes": "programs", "organise": "organize", "organised": "organized",
 "organising": "organizing", "organisation": "organization", "organisations": "organizations", "organisational": "organizational",
 "licence": "license", "licences": "licenses", "enrolment": "enrollment", "enrolments": "enrollments", "prioritise": "prioritize", "prioritised": "prioritized",
 "prioritisation": "prioritization", "summarise": "summarize", "summarised": "summarized", "catalogue": "catalog", "catalogued": "cataloged",
 "catalogues": "catalogs", "behaviour": "behavior", "behavioural": "behavioral", "labour": "labor", "colour": "color", "colours": "colors",
 "favour": "favor", "utilisation": "utilization", "utilised": "utilized", "standardised": "standardized", "standardise": "standardize",
 "recognised": "recognized", "minimised": "minimized", "maximised": "maximized", "customised": "customized", "authorised": "authorized",
 "authorisation": "authorization", "authorisations": "authorizations", "finalised": "finalized", "digitised": "digitized", "travelled": "traveled",
 "cancelled": "canceled", "defence": "defense", "fulfilment": "fulfillment", "specialised": "specialized", "specialise": "specialize",
 "visualisation": "visualization", "visualisations": "visualizations", "harmonised": "harmonized", "centralised": "centralized", "localised": "localized",
 "normalised": "normalized", "categorised": "categorized", "emphasised": "emphasized", "apologised": "apologized", "mobilised": "mobilized",
 "synchronised": "synchronized", "modernised": "modernized", "characterised": "characterized", "stabilised": "stabilized", "neutralised": "neutralized",
 "sanitised": "sanitized", "anonymised": "anonymized", "tokenised": "tokenized", "containerised": "containerized", "virtualised": "virtualized",
 "parallelised": "parallelized", "monetised": "monetized", "incentivised": "incentivized", "itemised": "itemized", "memorised": "memorized",
 "reorganised": "reorganized", "systematised": "systematized", "visualised": "visualized", "optimised": "optimized", "organising": "organizing",
 "specialise": "specialize", "apologised": "apologized", "colouring": "coloring", "favourite": "favorite", "neighbours": "neighbors", "neighbour": "neighbor",
 "memorise": "memorize", "summarising": "summarizing", "summarises": "summarizes", "behaviours": "behaviors", "modernise": "modernize",
 "organises": "organizes", "customises": "customizes", "customise": "customize", "counselling": "counseling", "counsellor": "counselor",
 "counsellors": "counselors", "enrols": "enrolls", "enrol": "enroll", "decentralised": "decentralized"}
_UK_RX = re.compile(r"\b(" + "|".join(sorted(UK2US, key=len, reverse=True)) + r")\b", re.I)
US2UK = {us_: uk_ for uk_, us_ in UK2US.items() if us_ not in ("program", "programs", "license", "licenses")}
_US_RX = re.compile(r"\b(" + "|".join(sorted(US2UK, key=len, reverse=True)) + r")\b", re.I)


def _same_case(old, new):
    return new[:1].upper() + new[1:] if old[:1].isupper() else new


def us(s):
    """British spelling to American, word by word: "Analysed … call centre" -> "Analyzed … call center"."""
    return _UK_RX.sub(lambda m: _same_case(m.group(1), UK2US[m.group(1).lower()]), s)


def uk(s):
    """American spelling to British for the UK CV pages: "optimization" -> "optimisation", "center" -> "centre"."""
    return _US_RX.sub(lambda m: _same_case(m.group(1), US2UK[m.group(1).lower()]), s)


def line_problem(ln):
    """What is wrong with a resume line under the rules of the module docstring, or None."""
    tools = {t for ts in KIND.values() for t in ts} | OFFICE
    if not ln or ln.endswith(".") or not ln[0].isupper(): return "a line starts with a capital and has no full stop at the end"
    if "'" in ln: return "a straight apostrophe: write ’"
    if not all(m.group(1) in KIND for m in SLOT.finditer(ln)) or "{" in SLOT.sub("", ln) or "}" in SLOT.sub("", ln):
        return "a place of a kind not in KIND"
    longest = SLOT.sub(lambda m: max(KIND[m.group(1)] + [m.group(2)], key=len), ln)       # whatever the postings put in the places
    if len(ln) > 160 or len(longest) > 160: return f"{len(longest)} characters with the longest tool in each place, 160 at most"
    bare = sorted(t for t in tools if re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", SLOT.sub("", ln)))
    if bare: return f"names {', '.join(bare)} outside a typed place"
    return None


def asked(slug, tags, n):
    """What the chart shows: the skills today's postings for this work name, [(skill, postings)]. `tags` is ranked, `n` the number of postings."""
    if slug in TECH: return [(t, k) for t, k in tags if k >= max(3, n * 0.04)][:10]
    return [(t, k) for t, k in tags if t in OFFICE and k >= max(3, n * 0.06)][:8]


# Where the example works and studied, when "Example Company" and a bachelor's degree would read wrong (24 Nov 2026). Search Console:
# "cv for residency example" 22 times at 23rd for /cv-examples/fellowship-residency/, whose example was a "Fellow" at "Example Company"
# with "five years' experience in internships and first jobs". A residency CV is a doctor's: hospital posts, rotations, audit,
# research, teaching, a medical degree.
PLACE = {"fellowship-residency": {"org": "Example University Hospital", "org2": "Example General Hospital", "edu": "Medical degree (MBBS or MD)",
                                  "school": "Example Medical School", "intern": "Foundation Doctor", "proj": ("Research, electives and volunteering", "Example Medical School"),
                                  "summary": "{title} with five years of clinical and research experience since medical school. Strongest in {three}."}}


def and_list(items, n=3):
    """Up to n skills as a phrase: "month-end close, reconciliations and US GAAP". Skills without an "and" of their own come first, and a
    comma goes before the last "and" when one still has it, so "Strongest in month-end close, reconciliations and accounts payable and
    receivable" (69 examples read like that, 24 Nov 2026) cannot happen."""
    items = [x.strip() for x in items if x and x.strip()]
    pick = sorted(items, key=lambda x: " and " in x)[:n]
    pick = [x for x in items if x in pick][:n]
    if len(pick) < 2: return pick[0] if pick else ""
    return ", ".join(pick[:-1]) + (", and " if any(" and " in x for x in pick) else " and ") + pick[-1]


def example(slug, name, family, rows, field_name):
    """The example as the resume builder stores it (see `blank` in assets/resume.js). `rows` is what asked() returned."""
    own = slug in ROLE
    title, plain, lines = ROLE.get(slug) or FIELD.get(family) or ROLE["operations-manager"]
    if not own: title = name[:1].upper() + name[1:]
    named = [t for t, _ in rows]
    def fill(m):
        return next((t for t in named if t in KIND[m.group(1)]), m.group(2))
    bullets = [SLOT.sub(fill, ln) for ln in lines]
    plain = [x.strip() for x in plain.split(",")]
    skills = (named[:6] + plain) if slug in TECH else (plain + named[:3])
    seen, out = set(), []
    for x in skills:
        if x.lower() not in seen: seen.add(x.lower()); out.append(x)
    skills = out[:9]
    first = skills[:3] if slug in TECH else plain[:3]
    d = {"name": "Alex Example", "title": title, "email": "alex@example.com", "phone": "", "place": "City, Country", "links": "",
         "summary": f"{title} with five years of experience in {field_name}. Strongest in {and_list(skills if slug in TECH else plain)}.",
         "skills": ", ".join(skills),
         "exp": [{"role": title, "org": "Example Company", "dates": "2022 – now", "text": "\n".join(bullets[:3])},
                 {"role": title, "org": "Another Example Ltd", "dates": "2020 – 2022", "text": bullets[3]}],
         "edu": [{"what": "Bachelor’s degree", "org": "Example University", "dates": "2016 – 2020"}], "tpl": "classic"}
    if slug in PLACE:
        pl_ = PLACE[slug]
        d["summary"] = pl_["summary"].format(title=title, three=and_list(plain))
        d["exp"][0]["org"], d["exp"][1]["org"] = pl_["org"], pl_["org2"]
        d["edu"] = [{"what": pl_["edu"], "org": pl_["school"], "dates": "2014 – 2020"}]
    if slug == "intern":
        d["summary"] = f"Final-year computer science student looking for a first engineering job. Strongest in {first[0]}, {first[1]} and {first[2]}."
        d["exp"] = [{"role": "Software Engineering Intern", "org": "Example Company", "dates": "Summer 2026", "text": bullets[0]},
                    {"role": "Course and student projects", "org": "Example University", "dates": "2023 – 2026", "text": "\n".join(bullets[1:3])},
                    {"role": "Customer Service Assistant, part-time", "org": "Another Example Ltd", "dates": "2023 – 2025", "text": bullets[3]}]
        d["edu"] = [{"what": "BSc Computer Science, expected 2027", "org": "Example University", "dates": "2023 – 2027"}]
    return d


def test():
    for d_ in (ROLE, ENTRY, SENIOR):
        for k_, v_ in d_.items():
            for ln_ in (list(v_[2]) + [v_[1]] if d_ is ROLE else list(v_)):
                assert us(ln_) == ln_, f"{k_}: British spelling in an example line ({ln_!r}); write it the American way, uk() makes the CV page British"
    def check(where, slug, ln):
        """A line as the module docstring asks for it."""
        assert not (why := line_problem(ln)), (where, slug, why, ln)
    for slug, (title, plain, lines) in ROLE.items():
        assert len(lines) == 4 and len(plain.split(",")) >= 3, slug
        assert sum(bool(re.search(r"\d", ln)) for ln in lines) >= 3, slug          # a result without a number is a description
        for ln in lines:
            check("ROLE", slug, ln)
    for where, d in (("ENTRY", ENTRY), ("SENIOR", SENIOR)):
        assert d.keys() == ROLE.keys(), (where, sorted(d.keys() ^ ROLE.keys()))
        for slug, lines in d.items():
            assert len(lines) == 3, (where, slug)
            for ln in lines:
                assert re.search(r"\d", ln), (where, slug, ln)
                check(where, slug, ln)
    new = [ln for d in (ENTRY, SENIOR) for lines in d.values() for ln in lines]
    assert len(new) == len(set(new)), [ln for ln in set(new) if new.count(ln) > 1]
    assert ENTRY_TITLE.keys() <= ROLE.keys(), sorted(ENTRY_TITLE.keys() - ROLE.keys())
    for slug, t in ENTRY_TITLE.items():                                             # only where it is not simply "Junior" + the title
        assert t and t[0].isupper() and t != "Junior " + ROLE[slug][0], (slug, t)
    d = example("data-analyst", "Data analyst", "data-analytics", [("SQL", 80), ("Python", 60), ("Looker", 20)], "data and analytics")
    assert "dashboard in Looker" in d["exp"][0]["text"] and "check in SQL" in d["exp"][0]["text"] and d["skills"].startswith("SQL, Python, Looker, dashboards"), d
    d = example("recruiter", "Recruiter", "hr-recruiting", asked("recruiter", [("Machine Learning", 40), ("Excel", 9)], 100), "HR and recruiting")
    assert "Machine Learning" not in json_of(d) and d["skills"].endswith("Excel"), d
    d = example("brand-new-work", "Brand new work", "sales", [], "sales")
    assert d["title"] == "Brand new work" and "the CRM" in d["exp"][1]["text"], d
    print(f"resume_examples.py: {len(ROLE)} kinds of work, {len(ENTRY)} entry-level and {len(SENIOR)} senior sets, "
          f"{len(ENTRY_TITLE)} beginner titles, all checks passed")


def json_of(d):
    import json
    return json.dumps(d, ensure_ascii=False)


if __name__ == "__main__":
    test()
