"""Example resumes, one per kind of work.

Resume builders get most of their search traffic from pages like "data analyst resume example". Ours differ in one thing: next to
the example stands what employers ask for in today's open postings for that work, counted on every build.

The example itself is invented and says so: a made-up person ("Alex Example"), made-up employers and made-up numbers. Every kind
of work has its own entry in ROLE: the title the person carries, the skills in plain words, four achievements. An achievement is
written the way a good resume line is: a verb first, one result, one number.

A tool may stand in a line only through a typed place such as {lang:Python}: the first skill of that kind that today's postings
for the role really name goes there, and the word after the colon is used when they name none. Never put a skill into a line any
other way: "designed a housing in Python" is what a place without a kind produces.

The skill tags of the collector are all technical. For work in TECH they say what the employer wants and lead the skills line and
the chart. For other work a tag mostly describes the employer (a recruiter's posting at a machine learning company), so only the
office tools in OFFICE are counted there.
"""
import re

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
        "Raised answer accuracy from 72% to 91% on 1,500 real questions by adding retrieval from the help centre",
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
    "computer-vision": ("Computer Vision Engineer", "image models, data labelling, model optimisation", [
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
    "data-engineer": ("Data Engineer", "data modelling, pipelines, data quality", [
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
    "analytics-engineer": ("Analytics Engineer", "data modelling, testing, documentation", [
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
    "pricing": ("Pricing Analyst", "price testing, elasticity analysis, financial modelling, competitor research", [
        "Ran 6 price tests; a new plan structure raised revenue per customer by 11% with no rise in cancellations",
        "Built a model of price sensitivity for 40 products from 2 years of sales",
        "Cut the average discount given by sales from 22% to 14% with a clear approval table",
        "Tracked 15 competitors’ prices each month; 3 findings changed our own"]),
    "research-analyst": ("Research Analyst", "desk research, interviews, data analysis, report writing", [
        "Wrote 24 research reports a year read by 300 clients",
        "Sized a new market at $400M from public filings and 30 interviews; the company entered it the next year",
        "Built a database of 500 competitors, updated each quarter",
        "Briefed the leadership team each month in 5 pages"]),
    "data-governance": ("Data Governance Analyst", "data catalogues, data quality rules, access policies", [
        "Catalogued 1,200 tables with an owner and a description for each; finding the right table takes minutes instead of hours",
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
        "Cut software licence costs by $210K by removing unused seats"]),
    "cloud-engineer": ("Cloud Engineer", "networking, infrastructure as code, cost control", [
        "Built the {cloud:AWS} foundation for 60 services: networks, accounts and access rules, all in {iac:Terraform}",
        "Cut the cloud bill by 27% with reserved capacity and by switching off idle resources",
        "Moved 25 services out of a data centre with under 10 minutes of downtime each",
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
    "cybersecurity": ("Security Engineer", "threat modelling, vulnerability management, incident response", [
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
    "product-manager": ("Product Manager", "roadmaps, customer interviews, prioritisation, A/B tests, writing specifications", [
        "Led the launch of saved searches; weekly active users rose 18% in two months",
        "Ran 25 customer interviews and cut the sign-up form from 11 fields to 4; completion went from 52% to 71%",
        "Retired 3 features used by under 1% of customers, which freed a third of the support queue",
        "Set the yearly plan for a team of 8 and delivered 5 of its 6 goals"]),
    "program-manager": ("Program Manager", "planning, risk tracking, stakeholder updates, budgeting", [
        "Ran a programme of 7 teams and 60 people that launched in 4 countries on the planned date",
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
        "Built the beta programme: 300 customers, 12 betas a year"]),
    "scrum-master": ("Scrum Master", "sprint planning, retrospectives, backlog refinement, removing blockers", [
        "Coached 3 teams; the share of sprint commitments delivered rose from 61% to 88%",
        "Cut the average time a task waits on another team from 6 days to 2",
        "Ran 70 retrospectives; 45 agreed actions were completed",
        "Shortened the release cycle from monthly to fortnightly"]),
    "business-operations": ("Business Operations Manager", "financial modelling, process design, planning cycles, reporting", [
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
        "Grew the referral programme to 22% of new sign-ups"]),
    "content-writer": ("Content Writer", "long-form articles, editing, search optimisation, interviews", [
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
    "community-manager": ("Community Manager", "moderation, events, member programmes, feedback reports", [
        "Grew the community from 5,000 to 28,000 members with 35% active each month",
        "Ran 40 online events a year with an average of 300 people",
        "Built an ambassador programme of 60 members who answer 45% of questions",
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
    "retail": ("Sales Associate", "customer service, till handling, stock control, visual merchandising", [
        "Served about 120 customers a shift and kept the store’s satisfaction score above 90%",
        "Sold 15% above the store average over a year",
        "Counted the till and banked the takings with no discrepancy in 14 months",
        "Trained 5 new team members on the till and on returns"]),
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
    "financial-analyst": ("Financial Analyst", "forecasting, budgeting, financial modelling, variance analysis", [
        "Built a forecast that stayed within 3% of actual revenue for six quarters",
        "Ran the yearly budget for 14 departments, finished 2 weeks earlier than the year before",
        "Modelled 3 pricing options for the board; the one chosen added $2M in yearly revenue",
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
    "investment": ("Corporate Development Associate", "valuation, financial modelling, due diligence, deal execution", [
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
        "Took the anti-money-laundering programme through a regulator’s inspection with no findings",
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
    "human-resources": ("HR Business Partner", "employee relations, performance management, organisation design, employment law", [
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
        "Built a programme for new managers; 120 finished it in a year"]),
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
        "Organised 2 company off-sites for 150 people within budget"]),
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
        "Analysed returned units and fixed the 3 commonest causes of failure; returns fell by 40%"]),
    "electrical-engineer": ("Electrical Engineer", "circuit design, power electronics, circuit board layout, lab testing", [
        "Designed a power supply board that is 94% efficient, up from 88%",
        "Passed electromagnetic compatibility testing at the first attempt on 3 products",
        "Cut the board’s part count from 210 to 160",
        "Wrote the test procedure used on the production line; test time per unit fell from 6 minutes to 2"]),
    "optics": ("Optical Engineer", "optical design, alignment, laser systems, optical testing", [
        "Designed a lens assembly that raised coupling efficiency from 61% to 78%",
        "Built an alignment process that cut assembly time for each unit from 3 hours to 40 minutes",
        "Characterised 12 laser designs and chose the one now in production",
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
    "mental-health": ("Licensed Therapist", "assessment, treatment planning, cognitive behavioural therapy, clinical documentation", [
        "Saw about 25 clients a week by video; 78% completed their treatment plan",
        "Measured outcomes with standard questionnaires; 64% of clients showed reliable improvement",
        "Completed clinical notes within 24 hours of every session",
        "Supervised 3 trainee therapists"]),
    "clinical-research": ("Clinical Research Associate", "study protocols, site monitoring, good clinical practice, regulatory submissions", [
        "Monitored 12 study sites across 3 trials; all met their enrolment targets",
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
        "Organised a student event for 200 people on a budget of $1,500",
        "Worked 15 hours a week during studies, handling about 30 customer requests a shift"]),
    "blockchain-engineer": ("Blockchain Engineer", "consensus, cryptography, node operation, security review", [
        "Built a wallet service in {lang:Go} that signs 2 million transactions a month with no loss of funds",
        "Cut the time for a node to sync from 9 hours to 50 minutes",
        "Added support for 6 chains, each in under 3 weeks",
        "Fixed 11 findings from two outside audits before launch"]),
    "smart-contract-engineer": ("Smart Contract Engineer", "testing, gas optimisation, security audits", [
        "Wrote and shipped 6 smart contracts that hold $40M, with no incident",
        "Cut the gas used by the main contract by 27%",
        "Wrote 400 tests, fuzz tests among them, that cover every line",
        "Fixed 11 findings from two outside audits before launch"]),
}

# work where the collector's skill tags say what the employer wants from the person
TECH = {
    "software-engineer", "backend-engineer", "frontend-engineer", "full-stack-engineer", "mobile-engineer", "qa-engineer", "embedded-engineer",
    "engineering-manager", "web-developer", "product-engineer", "systems-software", "graphics-engineer", "game-developer", "software-architect",
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
    "cloud-devops-it": ROLE["devops-engineer"], "security": ROLE["cybersecurity"], "product-project": ROLE["project-manager"],
    "design-creative": ROLE["product-designer"], "marketing-communications": ROLE["marketing-manager"], "sales": ROLE["account-executive"],
    "customer-service": ROLE["customer-support"], "accounting-finance": ROLE["financial-analyst"], "legal-compliance": ROLE["compliance"],
    "hr-recruiting": ROLE["human-resources"], "operations-administration": ROLE["operations-manager"], "hardware-engineering": ROLE["mechanical-engineer"],
    "writing-translation": ROLE["content-writer"], "science-healthcare": ROLE["life-sciences"], "education-training": ROLE["education"],
    "retail-hospitality": ROLE["retail"], "crypto-web3": ROLE["blockchain-engineer"], "internships-entry-level": ROLE["intern"],
}
SLOT = re.compile(r"\{(\w+):([^}]*)\}")


def asked(slug, tags, n):
    """What the chart shows: the skills today's postings for this work name, [(skill, postings)]. `tags` is ranked, `n` the number of postings."""
    if slug in TECH: return [(t, k) for t, k in tags if k >= max(3, n * 0.04)][:10]
    return [(t, k) for t, k in tags if t in OFFICE and k >= max(3, n * 0.06)][:8]


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
         "summary": f"{title} with five years of experience in {field_name}. Strongest in {first[0]}, {first[1]} and {first[2]}.",
         "skills": ", ".join(skills),
         "exp": [{"role": title, "org": "Example Company", "dates": "2022 – now", "text": "\n".join(bullets[:3])},
                 {"role": title, "org": "Another Example Ltd", "dates": "2020 – 2022", "text": bullets[3]}],
         "edu": [{"what": "Bachelor’s degree", "org": "Example University", "dates": "2016 – 2020"}], "tpl": "classic"}
    if slug == "intern":
        d["summary"] = f"Final-year computer science student looking for a first engineering job. Strongest in {first[0]}, {first[1]} and {first[2]}."
        d["exp"] = [{"role": "Software Engineering Intern", "org": "Example Company", "dates": "Summer 2026", "text": bullets[0]},
                    {"role": "Course and student projects", "org": "Example University", "dates": "2023 – 2026", "text": "\n".join(bullets[1:3])},
                    {"role": "Customer Service Assistant, part-time", "org": "Another Example Ltd", "dates": "2023 – 2025", "text": bullets[3]}]
        d["edu"] = [{"what": "BSc Computer Science, expected 2027", "org": "Example University", "dates": "2023 – 2027"}]
    return d


def test():
    for slug, (title, plain, lines) in ROLE.items():
        assert len(lines) == 4 and len(plain.split(",")) >= 3, slug
        assert sum(bool(re.search(r"\d", ln)) for ln in lines) >= 3, slug          # a result without a number is a description
        for ln in lines:
            assert not ln.endswith(".") and ln[0].isupper() and "'" not in ln, (slug, ln)
            assert all(m.group(1) in KIND for m in SLOT.finditer(ln)) and "{" not in SLOT.sub("", ln), (slug, ln)
    d = example("data-analyst", "Data analyst", "data-analytics", [("SQL", 80), ("Python", 60), ("Looker", 20)], "data and analytics")
    assert "dashboard in Looker" in d["exp"][0]["text"] and "check in SQL" in d["exp"][0]["text"] and d["skills"].startswith("SQL, Python, Looker, dashboards"), d
    d = example("recruiter", "Recruiter", "hr-recruiting", asked("recruiter", [("Machine Learning", 40), ("Excel", 9)], 100), "HR and recruiting")
    assert "Machine Learning" not in json_of(d) and d["skills"].endswith("Excel"), d
    d = example("brand-new-work", "Brand new work", "sales", [], "sales")
    assert d["title"] == "Brand new work" and "the CRM" in d["exp"][1]["text"], d
    print(f"resume_examples.py: {len(ROLE)} kinds of work, all checks passed")


def json_of(d):
    import json
    return json.dumps(d, ensure_ascii=False)


if __name__ == "__main__":
    test()
