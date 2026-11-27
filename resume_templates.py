"""The resume templates of the builder, for /resume-templates/ and /resume-templates/<id>/ (27 Nov 2026).

The owner asked to take what CVMaker does well (its /resume-templates/ page brings most of its US search visits: "resume templates",
"free resume templates", "simple / professional / modern resume template", "cv template"). Our edge, said plainly on every page: the PDF
and the Word file are free, with no account; CVMaker charges for the download.

TEMPLATES: one entry per template of assets/resume.js (TPL_NAMES, same ids and order). The look itself is assets/resume.css; build.py
draws each template filled with its own invented person (PEOPLE) through sheet_html(), which writes the same markup as resume.js
sheetHtml(), so the gallery shows exactly what the builder makes. Nothing here is counted or measured: no view counts, no "most popular"
badges (we do not count views), no hiring claims.

Fields: id, name, title (the search phrase the page answers, for its <title> and H1), line (one line, as in the builder), about (two or
three sentences on what the template is for), level (entry, mid, senior: who it suits), style (simple, modern, classic, colour),
font, colour (the template's own), order (the sections in the order the page shows them), ats (what to know for screening software),
suits (kinds of work, each with the role slug of one of our resume examples where we have one), person (a key of PEOPLE), qa (two
questions of its own, on top of the ones every template page answers).
"""
import html

LEVELS = (("entry", "Student or first job"), ("mid", "Experienced"), ("senior", "Senior or manager"))
STYLES = (("simple", "Simple"), ("modern", "Modern"), ("classic", "Classic serif"), ("colour", "With colour"))
STD_ORDER = "Summary, experience, projects, education, certifications, skills, languages"

TEMPLATES = [
    dict(id="classic", name="Classic", title="Classic resume template", line="Serif text, calm headings, for any field",
         about="The traditional resume: a serif body that reads like a printed letter, sans-serif headings with a thin rule, dates on the right. It fits almost any job and any employer, from a bank to a school.",
         level=("mid", "senior"), style=("classic",), font="Georgia for the text, Inter for the name and headings", colour="Black (you can pick another)",
         order=STD_ORDER, ats="Plain text in one column with headings an applicant tracking system expects (Summary, Experience, Education, Skills). The rule under a heading is a border, not a picture.",
         suits=[("Project management", "project-manager"), ("Operations", "operations-manager"), ("Finance and accounting", "senior-accountant"), ("Office and administration", "office-manager")],
         person="thomas", qa=[("Is a classic resume template still a good choice?", "Yes. Recruiters read a classic layout without effort, and screening software reads its one column of text cleanly. What makes a resume stand out is the results in it, not the design.")]),
    dict(id="modern", name="Modern", title="Modern resume template", line="Clean sans-serif, a bar on each heading",
         about="A clean sans-serif page with a short bar beside each heading instead of a rule underneath. It looks current without columns, icons or photos, so it stays readable for screening software.",
         level=("entry", "mid"), style=("modern",), font="Inter throughout", colour="Black bars (you can pick another colour)",
         order=STD_ORDER, ats="One column of real text; the bar beside each heading is a border, so the heading text stays a plain word the software can find.",
         suits=[("Data and analytics", "data-analyst"), ("Marketing", "marketing-manager"), ("Software and IT", "software-engineer"), ("Customer success", "customer-success-manager")],
         person="ethan", qa=[("What makes a resume template look modern?", "A sans-serif font, more white space, fewer lines and one accent at most. Two-column layouts with skill bars and icons look modern too, but screening software often reads them out of order, so this template keeps one column.")]),
    dict(id="simple", name="Simple", title="Simple resume template", line="The plainest page: Arial, bold headings, no lines",
         about="Nothing but the text: Arial, bold headings, no lines, no colour. It is the safest choice for any applicant tracking system and for a job where the resume is printed or faxed, and it never looks out of place.",
         level=("entry", "mid", "senior"), style=("simple",), font="Arial throughout", colour="None (you can colour the headings)",
         order=STD_ORDER, ats="As plain as a resume gets: one font, one column, headings in bold. It is close to the plain-text version many application forms ask you to paste.",
         suits=[("Healthcare support", "nursing"), ("Retail and service", "retail-sales-associate"), ("Warehouse and logistics", "warehouse-associate"), ("Administration", "executive-assistant")],
         person="maria", qa=[("What is the simplest resume format?", "One column with your name and contact line at the top, then your experience in reverse order with a few results each, your education and your skills. This template is exactly that, in Arial with bold headings.")]),
    dict(id="professional", name="Professional", title="Professional resume template", line="Serif, small capitals, a rule under the header",
         about="A formal page for finance, law, consulting and other fields where a resume is expected to look like a document: a serif name in a dark slate colour, a rule under the header, headings in small capitals.",
         level=("mid", "senior"), style=("classic", "colour"), font="Georgia for the name, the headings and the text", colour="Dark slate (you can pick another)",
         order=STD_ORDER, ats="Small capitals are a font style of ordinary letters, so the software reads “Experience” as the word it is. One column, real text.",
         suits=[("Accounting", "senior-accountant"), ("Finance", "financial-analyst"), ("Legal", "paralegal"), ("Consulting", "technology-consultant")],
         person="priya", qa=[("What does a professional resume template look like?", "One column, a serif or plain sans-serif font, the name and contact details at the top, consistent dates on the right and no photo, graphics or skill bars. The look says careful; the results under each job do the rest.")]),
    dict(id="compact", name="Compact", title="One-page resume template", line="Smaller type that fits more on one page",
         about="Smaller type and tighter spacing, so three jobs, a summary and a full skills line still fit on one page. Use it when the content is right but runs a few lines over.",
         level=("mid", "senior"), style=("simple", "modern"), font="Inter at 12.5 px (about 9.5 pt)", colour="Black (you can pick another)",
         order=STD_ORDER, ats="The same single column as the others, only smaller. Keep the text size at 9.5 pt or more so a recruiter can read it printed.",
         suits=[("Customer success", "customer-success-manager"), ("Sales", "account-executive"), ("Operations", "operations-analyst"), ("IT support", "it-support")],
         person="morgan", qa=[("How do I fit my resume on one page?", "Cut each older job to its one or two strongest results, drop the objective line, keep the skills to one line and use this template's smaller type. The builder shows the page count as you type, so you can see when it fits.")]),
    dict(id="executive", name="Executive", title="Executive resume template", line="Centred name and headings, for senior roles",
         about="A centred serif name and centred headings with a rule above each, for directors, vice presidents and other senior roles. It reads as calm and confident, and leaves room for a two-page career.",
         level=("senior",), style=("classic",), font="Georgia for the name, Inter for the headings", colour="Black (you can pick another)",
         order=STD_ORDER, ats="Centring changes where the text sits, not how it is read: the order of the words stays the same, so screening software reads it as it reads the others.",
         suits=[("Operations leadership", "operations-manager"), ("Sales leadership", "vp-sales"), ("Engineering leadership", "vp-engineering"), ("General management", "general-manager")],
         person="catherine", qa=[("Should an executive resume be two pages?", "Often, yes: fifteen or more years of senior work rarely fit on one page with results. Put the strongest results on the first page, keep roles older than about fifteen years to a line each, and stop at two pages.")]),
    dict(id="student", name="Student", title="Student resume template", line="Education and projects first, for a first job",
         about="For students, school leavers and anyone looking for a first job: education comes first, then projects, then any work, so the page leads with what you have. It suits a high school, college or internship resume.",
         level=("entry",), style=("modern", "colour"), font="Inter throughout", colour="Blue headings (you can pick another)",
         order="Summary, education, projects, experience, skills, certifications, languages", ats="The usual section names in a different order: screening software reads each section by its heading, so putting Education first changes nothing for it.",
         suits=[("Internships", "intern"), ("Summer internships", "summer-intern"), ("Engineering internships", "engineering-intern"), ("Retail and first jobs", "retail-sales-associate")],
         person="jamie", qa=[("What should a student put on a resume with no work experience?", "School and the grades or honours worth naming, projects (class, personal or volunteer) with what came of them, clubs and teams, part-time or summer work of any kind, and skills. This template puts education and projects first for that reason.")]),
    dict(id="creative", name="Creative", title="Creative resume template", line="A coloured header band, the rest plain",
         about="A coloured band across the top with your name in white, and a plain page under it. It gives designers, marketers and content people some personality without the columns and graphics that confuse screening software.",
         level=("entry", "mid"), style=("modern", "colour"), font="Inter throughout", colour="Deep teal band (you can pick another)",
         order=STD_ORDER, ats="The band is a background colour behind ordinary text: the name and contact details stay text that the software reads. Avoid putting your contact details in a picture or a page header, where some systems do not look.",
         suits=[("Graphic design", "graphic-designer"), ("Content and writing", "content-writer"), ("Social media", "social-media"), ("Brand marketing", "brand-marketing")],
         person="daniel", qa=[("Are creative resume templates ATS-friendly?", "Many are not: two columns, icons, skill bars and text in pictures can come out scrambled or empty. A creative template can still be safe if the design is colour and type on one column of real text, as this one is.")]),
    dict(id="elegant", name="Elegant", title="Elegant resume template", line="Serif throughout, centred, thin rules",
         about="Serif type throughout, a name in spaced capitals and headings between two thin rules. It suits law, hospitality, education and other fields where a resume is read closely and a refined look helps.",
         level=("mid", "senior"), style=("classic",), font="Georgia throughout", colour="Dark grey (you can pick another)",
         order=STD_ORDER, ats="The thin rules are borders drawn by the page, not characters or pictures, so the headings stay plain words.",
         suits=[("Legal", "paralegal"), ("Hospitality", "hospitality"), ("Education", "education"), ("Executive support", "executive-assistant")],
         person="sophie", qa=[("Which font looks most elegant on a resume?", "A classic serif such as Georgia, Garamond or Times New Roman at 10.5 to 12 pt. This template uses Georgia, which every computer has, so the PDF and the Word file look the same everywhere.")]),
    dict(id="bold", name="Bold", title="Bold resume template", line="A large name and heavy headings",
         about="A large, heavy name and short thick underlines under the headings: a confident page for sales, business development and other jobs where presence counts.",
         level=("entry", "mid"), style=("modern",), font="Inter in heavy weights", colour="Black, with black underlines (you can pick a colour)",
         order=STD_ORDER, ats="Heavy weights are the same letters, only thicker. One column, standard headings.",
         suits=[("Sales", "sales-representative"), ("Account management", "account-manager"), ("Business development", "business-development"), ("Recruiting", "recruiter")],
         person="marcus", qa=[("Is it good to have a bold name at the top of a resume?", "Yes: the name is the one thing a recruiter should remember, and a larger name makes the top third of the page easy to scan. Keep the contact line plain and right under it.")]),
    dict(id="fresh", name="Fresh", title="Colorful resume template", line="Teal headings on a light band",
         about="Teal headings on a light tinted band, and the name in the same colour. It is the most colourful of the templates and still one column, for healthcare, education, nonprofit and service jobs.",
         level=("entry", "mid"), style=("modern", "colour"), font="Inter throughout", colour="Teal (you can pick another)",
         order=STD_ORDER, ats="The tint is a background behind the heading text, which stays text. Colour is fine for screening software; it is the layout (columns, tables, pictures) that causes problems.",
         suits=[("Nursing", "nursing"), ("Healthcare", "healthcare"), ("Nonprofit", "nonprofit"), ("Customer support", "customer-support")],
         person="aisha", qa=[("Can a resume have colour?", "Yes. One accent colour on the name and the headings is safe for screening software and prints well in grey. Keep the text itself black and avoid light colours that disappear on paper.")]),
    dict(id="heritage", name="Heritage", title="Serif resume template", line="Burgundy and serif, a double rule",
         about="A burgundy serif name, an italic headline and a double rule under each heading: a traditional page with some warmth, for teachers, librarians, writers and academic staff.",
         level=("mid", "senior"), style=("classic", "colour"), font="Georgia throughout", colour="Burgundy (you can pick another)",
         order=STD_ORDER, ats="The double rule is a border style; the italic headline is plain text in italics. Both are read like any other text.",
         suits=[("Teaching", "education"), ("Writing and editing", "content-writer"), ("Training", "corporate-trainer"), ("Communications", "communications")],
         person="eleanor", qa=[("Is a serif font good for a resume?", "Yes. Serif fonts such as Georgia read well on paper and look traditional; sans-serif fonts look more current on screen. Either is fine for screening software, as long as it is a common font.")]),
    dict(id="developer", name="Developer", title="Software developer resume template", line="Monospace type, for engineers",
         about="Monospace type and headings written like Markdown (## Experience): a page that looks at home in engineering, with the same plain structure recruiters and screening software expect.",
         level=("entry", "mid", "senior"), style=("modern",), font="JetBrains Mono throughout", colour="Black (you can pick another)",
         order=STD_ORDER, ats="The “## ” before each heading is drawn by the page, not typed, so the heading reads as “Experience”. Monospace type runs wider: keep bullets short.",
         suits=[("Software engineering", "software-engineer"), ("Backend", "backend-engineer"), ("DevOps", "devops-engineer"), ("Data engineering", "data-engineer")],
         person="ravi", qa=[("What should a software engineer resume include?", "Your stack in the skills line, a link to your code (GitHub or a portfolio), and under each job two to four results with numbers: latency cut, users served, incidents reduced, releases per week. Projects matter if you are early in your career.")]),
    dict(id="timeline", name="Timeline", title="Chronological resume template", line="Dates and time in each job on the left",
         about="A reverse-chronological resume with the dates in a column on the left and the time in each job counted for you (2 yrs 4 mos), and the total at the top of Experience. It makes a steady record easy to see.",
         level=("mid", "senior"), style=("modern",), font="Inter throughout", colour="Grey headings (you can pick a colour)",
         order=STD_ORDER, ats="The dates sit beside each job in the same text flow, date first, as many application forms list them. In the Word file they are a simple two-cell row.",
         suits=[("Warehouse and logistics", "warehouse-associate"), ("Manufacturing", "production-supervisor"), ("Trades", "maintenance-technician"), ("Supply chain", "supply-chain")],
         person="lucas", qa=[("What is a chronological resume?", "A resume that lists your jobs from the most recent back, each with its dates. It is the format recruiters expect and the one screening software reads best; this template adds the time in each job beside the dates.")]),
    dict(id="minimal", name="Minimal", title="Minimalist resume template", line="Light lines and space, for design and product",
         about="Light grey lines, generous margins between sections and a quiet grey for the headings. A minimalist page for product, design and research roles, where the resume itself is judged as a piece of design.",
         level=("mid", "senior"), style=("simple", "modern"), font="Inter throughout", colour="Grey (you can pick a colour)",
         order=STD_ORDER, ats="Minimal design is the friendliest kind for screening software: one column, plain headings, nothing to misread.",
         suits=[("Product design", "product-designer"), ("UX research", "ux-researcher"), ("Product management", "product-manager"), ("UX design", "ux-designer")],
         person="daniel2", qa=[("What is a minimalist resume?", "A resume with one font, plenty of space, few lines and no graphics, so the content carries it. It suits design and product roles, and it is also among the safest layouts for screening software.")]),
    dict(id="accent", name="Accent", title="Business resume template", line="Navy name and headings, for sales and business",
         about="A navy name, navy headings and job titles: a business-like page with one colour, for sales, account management, business and finance roles.",
         level=("mid", "senior"), style=("modern", "colour"), font="Inter throughout", colour="Navy (you can pick another)",
         order=STD_ORDER, ats="One colour on ordinary text; the layout is the plain single column screening software reads cleanly.",
         suits=[("Sales management", "sales-manager"), ("Account executive", "account-executive"), ("Business analysis", "business-analyst"), ("Finance", "finance-manager")],
         person="hannah", qa=[("What colour is best for a business resume?", "Navy, dark grey or another dark, quiet colour on the name and the headings, with the text in black. Dark colours read well on screen and print clearly in grey.")]),
]

# The invented people who fill the pictures. Names, companies and numbers are made up for this site; phone numbers are in the 555-01xx
# range set aside for fiction; every email is at example.com.
PEOPLE = {
    "thomas": dict(name="Thomas Reed", title="Project Manager", email="thomas.reed@example.com", phone="(555) 010-0131", place="Columbus, OH", links="linkedin.com/in/thomas-reed-example",
        summary="Project manager with eight years in construction and facilities projects. Delivers on budget: 23 projects worth $41M since 2019, 21 of them on or ahead of schedule.",
        skills="Project planning, Budgeting, Risk management, MS Project, Smartsheet, Vendor management, PMP",
        exp=[dict(role="Senior Project Manager", org="Harbor Line Builders", dates="Apr 2021 – now", text="Led 11 office fit-out projects worth $18M, 10 finished on or before the planned date\nCut change-order costs by 27% with a weekly design review between the client, architect and site team\nMentored 3 assistant project managers; two now run projects of their own"),
             dict(role="Project Manager", org="Midwest Facility Group", dates="Jun 2017 – Mar 2021", text="Ran 12 facility upgrades for hospitals and schools, each under 1% over budget\nIntroduced a shared schedule in Smartsheet that cut status meetings from 5 hours a week to 2")],
        edu=[dict(what="B.S. in Construction Management", org="Ohio State University", dates="2017")], cert=[dict(name="Project Management Professional (PMP)", org="PMI", date="2020")]),
    "ethan": dict(name="Ethan Brooks", title="Data Analyst", email="ethan.brooks@example.com", phone="(555) 010-0142", place="Chicago, IL", links="github.com/ethan-brooks-example",
        summary="Data analyst with four years in retail and e-commerce. Builds the reports teams act on: a weekly sales dashboard read by 60 store managers and a churn model that saved $1.1M a year.",
        skills="SQL, Python, Tableau, Excel, dbt, A/B testing, Snowflake, Statistics",
        exp=[dict(role="Data Analyst", org="Lakeview Retail", dates="Feb 2023 – now", text="Built a weekly sales dashboard in Tableau now used by 60 store managers, replacing 14 spreadsheets\nFound the 3 product pages behind 40% of abandoned carts; their redesign lifted checkout rate by 6%\nAutomated the month-end inventory report in Python, from 2 days of work to 20 minutes"),
             dict(role="Junior Data Analyst", org="Northfield Commerce", dates="Jul 2021 – Jan 2023", text="Wrote 120 SQL queries for marketing, finance and support, documented in a shared library\nRan 9 A/B tests on email campaigns; the winning subject lines raised opens by 18%")],
        edu=[dict(what="B.S. in Economics", org="University of Illinois", dates="2021")]),
    "maria": dict(name="Maria Santos", title="Medical Assistant", email="maria.santos@example.com", phone="(555) 010-0153", place="San Antonio, TX", links="",
        summary="Certified medical assistant with five years in busy family practices. Rooms 30 or more patients a day, keeps records accurate and puts nervous patients at ease, in English and Spanish.",
        skills="Patient intake, Vital signs, Phlebotomy, EKG, Epic EHR, Scheduling, Insurance verification, Bilingual English and Spanish",
        exp=[dict(role="Medical Assistant", org="Riverside Family Clinic", dates="Mar 2022 – now", text="Room 30 to 35 patients a day for 4 physicians: vitals, history and medication lists in Epic\nDraw blood and run EKGs; 99% of samples accepted by the lab on the first try\nCut no-shows from 14% to 8% with reminder calls in English and Spanish"),
             dict(role="Medical Assistant", org="Alamo Pediatrics", dates="Aug 2019 – Feb 2022", text="Gave vaccines and kept immunization records for about 25 children a day\nVerified insurance for new patients and cut claim denials for missing details by half")],
        edu=[dict(what="Medical Assistant Diploma", org="San Antonio College", dates="2019")], cert=[dict(name="Certified Medical Assistant (CMA)", org="AAMA", date="2019")],
        lang=[dict(name="English", level="Native"), dict(name="Spanish", level="Fluent")]),
    "priya": dict(name="Priya Nair", title="Senior Accountant", email="priya.nair@example.com", phone="(555) 010-0164", place="Charlotte, NC", links="linkedin.com/in/priya-nair-example",
        summary="CPA with seven years in corporate accounting. Closes the books in 5 days instead of 9, and has led two clean audits in a row for a $300M manufacturer.",
        skills="Month-end close, GAAP, Account reconciliation, NetSuite, Excel, SOX controls, Audit preparation, Variance analysis",
        exp=[dict(role="Senior Accountant", org="Carolina Precision Parts", dates="May 2022 – now", text="Cut the month-end close from 9 working days to 5 by moving 40 reconciliations into NetSuite\nPrepared the schedules for 2 external audits with no adjustments and no findings\nTrained 4 staff accountants on revenue recognition under ASC 606"),
             dict(role="Staff Accountant", org="Piedmont Health Partners", dates="Sep 2018 – Apr 2022", text="Reconciled 60 balance sheet accounts a month across 3 entities\nFound $210,000 in duplicate vendor payments and recovered all of it within a quarter")],
        edu=[dict(what="Master of Accountancy", org="UNC Charlotte", dates="2018")], cert=[dict(name="Certified Public Accountant (CPA)", org="North Carolina State Board", date="2020")]),
    "morgan": dict(name="Morgan Lee", title="Customer Success Manager", email="morgan.lee@example.com", phone="(555) 010-0175", place="Denver, CO", links="linkedin.com/in/morgan-lee-example",
        summary="Customer success manager with six years in B2B software. Keeps 120 accounts growing: renewals at 94% and expansion revenue up 31% last year.",
        skills="Account management, Onboarding, Renewals, Salesforce, Gainsight, Zendesk, SQL, Training, QBRs",
        exp=[dict(role="Customer Success Manager", org="Brightpath Software", dates="Mar 2022 – now", text="Kept renewals at 94% across 120 mid-market accounts worth $6.8M a year\nCut onboarding time from 45 days to 28 with a shared launch plan for every new customer\nGrew expansion revenue 31% in 2025 by running quarterly business reviews with the 30 largest accounts"),
             dict(role="Customer Success Associate", org="Summit Payroll", dates="Jan 2020 – Feb 2022", text="Answered about 40 customer tickets a day with a 96% satisfaction score\nWrote 25 help articles that cut repeat questions on payroll setup by a third"),
             dict(role="Account Coordinator", org="Northside Media", dates="Jun 2018 – Dec 2019", text="Prepared monthly reports for 40 advertising clients")],
        edu=[dict(what="B.A. in Communication", org="University of Colorado", dates="2018")]),
    "catherine": dict(name="Catherine Hale", title="Director of Operations", email="catherine.hale@example.com", phone="(555) 010-0186", place="Atlanta, GA", links="linkedin.com/in/catherine-hale-example",
        summary="Operations leader with 16 years in distribution and logistics. Runs 4 sites and 600 people; cut cost per order by 22% while on-time delivery rose to 98.5%.",
        skills="Operations strategy, P&L ownership, Lean, Warehouse management systems, Labor planning, Vendor negotiation, Change management",
        exp=[dict(role="Director of Operations", org="Southern Freight Distribution", dates="2019 – now", text="Lead 4 distribution centers and 600 employees with a $95M operating budget\nCut cost per order by 22% in three years with new slotting, labor planning and a WMS upgrade\nRaised on-time delivery from 91% to 98.5% and kept it there for 8 quarters"),
             dict(role="Senior Operations Manager", org="Peachtree Supply Co.", dates="2013 – 2019", text="Opened a 400,000 sq ft fulfilment center on schedule and 4% under budget\nBuilt a safety program that brought recordable injuries down by 60%")],
        edu=[dict(what="MBA", org="Emory University", dates="2012"), dict(what="B.S. in Industrial Engineering", org="Georgia Tech", dates="2008")]),
    "jamie": dict(name="Jamie Chen", title="Computer Science Student", email="jamie.chen@example.com", phone="(555) 010-0197", place="Seattle, WA", links="github.com/jamie-chen-example",
        summary="Third-year computer science student looking for a summer 2027 software engineering internship. Built a course planner used by 1,200 students and tutor 15 first-year students a week.",
        skills="Python, Java, JavaScript, React, SQL, Git, Data structures",
        edu=[dict(what="B.S. in Computer Science, GPA 3.7", org="University of Washington", dates="2024 – 2028"), dict(what="High school diploma, valedictorian", org="Lincoln High School", dates="2024")],
        proj=[dict(name="Course planner web app", link="github.com/jamie-chen-example/planner", text="Built with React and Python; 1,200 students used it to plan 3,400 schedules in its first term"),
              dict(name="Campus bike-share data study", link="", text="Cleaned 2 years of trip data in Python and showed the city where 5 new stations would get the most use")],
        exp=[dict(role="Peer Tutor", org="University of Washington", dates="Sep 2025 – now", text="Tutor 15 first-year students a week in Java and data structures"),
             dict(role="Cashier (summer)", org="Green Market Grocery", dates="Jun 2023 – Aug 2024", text="Served about 200 customers a shift with a balanced till every night")]),
    "daniel": dict(name="Daniel Okafor", title="Marketing Designer", email="daniel.okafor@example.com", phone="(555) 010-0108", place="Brooklyn, NY", links="danielokafor.example.com",
        summary="Marketing designer with five years in consumer brands. Designs campaigns that sell: the 2025 spring campaign brought 38% more site visits than the year before.",
        skills="Brand design, Campaign design, Figma, Adobe Creative Suite, Motion graphics, Social media assets, Art direction",
        exp=[dict(role="Marketing Designer", org="Hudson & Pine", dates="Jan 2023 – now", text="Designed 4 seasonal campaigns across web, email and social; spring 2025 drove 38% more site visits than spring 2024\nBuilt a library of 300 social templates in Figma, cutting the time to a new post from 3 hours to 40 minutes\nArt-directed 6 product shoots on budgets under $15,000 each"),
             dict(role="Junior Designer", org="Bright Ideas Studio", dates="Jul 2021 – Dec 2022", text="Designed packaging for 12 products sold in 900 stores\nMade 50 short motion pieces for client social accounts")],
        edu=[dict(what="BFA in Graphic Design", org="Pratt Institute", dates="2021")]),
    "sophie": dict(name="Sophie Laurent", title="Paralegal", email="sophie.laurent@example.com", phone="(555) 010-0119", place="Boston, MA", links="linkedin.com/in/sophie-laurent-example",
        summary="Litigation paralegal with six years at mid-size firms. Manages discovery for cases with up to 400,000 documents and has never missed a filing deadline.",
        skills="Legal research, E-discovery, Relativity, Westlaw, Case management, Court filings, Document review, Deposition preparation",
        exp=[dict(role="Senior Paralegal", org="Whitmore & Associates", dates="Oct 2021 – now", text="Run discovery for 8 active cases at a time, including one with 400,000 documents in Relativity\nPrepared 30 deposition binders and exhibits for trial in the last two years\nFiled more than 500 documents in state and federal courts with no missed deadline"),
             dict(role="Paralegal", org="Beacon Hill Legal Group", dates="Jun 2019 – Sep 2021", text="Researched case law in Westlaw for 4 attorneys and drafted first versions of 60 motions\nSet up a deadline calendar shared by the whole litigation team")],
        edu=[dict(what="B.A. in Political Science", org="Boston University", dates="2019")], cert=[dict(name="Paralegal Certificate", org="Northeastern University", date="2019")]),
    "marcus": dict(name="Marcus Hill", title="Sales Representative", email="marcus.hill@example.com", phone="(555) 010-0120", place="Phoenix, AZ", links="linkedin.com/in/marcus-hill-example",
        summary="Sales representative with four years in B2B equipment sales. Closed $2.4M in new business in 2025, 132% of quota, and ranked first of 18 reps.",
        skills="Prospecting, Cold calling, Negotiation, Salesforce, HubSpot, Pipeline management, Product demos",
        exp=[dict(role="Sales Representative", org="Desert Office Systems", dates="Feb 2023 – now", text="Closed $2.4M in new business in 2025, 132% of quota, first of 18 reps\nBuilt a pipeline of 140 accounts in a new territory within 6 months\nRaised the demo-to-close rate from 18% to 27% with a shorter, customer-led demo"),
             dict(role="Sales Development Representative", org="Valley Tech Supply", dates="Jun 2021 – Jan 2023", text="Booked 25 meetings a month for 3 account executives, 115% of target\nMade about 60 calls a day and kept the CRM notes up to date")],
        edu=[dict(what="B.S. in Business Administration", org="Arizona State University", dates="2021")]),
    "aisha": dict(name="Aisha Bello", title="Registered Nurse", email="aisha.bello@example.com", phone="(555) 010-0121", place="Houston, TX", links="",
        summary="Registered nurse with five years on a 32-bed medical-surgical unit. Cares for 5 to 6 patients a shift, precepts new nurses and led the unit's fall-prevention project.",
        skills="Patient assessment, Medication administration, IV therapy, Wound care, Epic, Patient education, BLS, ACLS",
        exp=[dict(role="Registered Nurse, Medical-Surgical", org="Gulf Coast Medical Center", dates="Jul 2021 – now", text="Care for 5 to 6 patients a shift on a 32-bed unit, from admission to discharge\nLed a fall-prevention project that cut patient falls on the unit by 41% in a year\nPrecepted 7 newly graduated nurses through their first 12 weeks"),
             dict(role="Patient Care Technician", org="Bayou City Hospital", dates="Jan 2019 – Jun 2021", text="Took vitals, drew blood and helped about 12 patients a shift with daily care")],
        edu=[dict(what="Bachelor of Science in Nursing", org="University of Houston", dates="2021")], cert=[dict(name="Registered Nurse license", org="Texas Board of Nursing", date="2021"), dict(name="ACLS", org="American Heart Association", date="2025")]),
    "eleanor": dict(name="Eleanor Grant", title="High School English Teacher", email="eleanor.grant@example.com", phone="(555) 010-0132", place="Portland, OR", links="",
        summary="English teacher with nine years in public high schools. Teaches 150 students a year; her students' pass rate on the state writing test rose from 71% to 88%.",
        skills="Curriculum design, Differentiated instruction, Classroom management, Google Classroom, Writing assessment, Parent communication",
        exp=[dict(role="English Teacher, Grades 10–12", org="Cedar Ridge High School", dates="2019 – now", text="Teach 5 sections of English, about 150 students a year, including one AP class\nRaised the pass rate on the state writing test from 71% to 88% in four years with weekly writing workshops\nStarted the school's literary magazine; 60 students have published in it"),
             dict(role="English Teacher, Grade 9", org="Willamette Middle and High School", dates="2016 – 2019", text="Wrote a 9th-grade reading unit adopted by all 6 English teachers in the district")],
        edu=[dict(what="M.A. in Teaching", org="Portland State University", dates="2016"), dict(what="B.A. in English", org="University of Oregon", dates="2015")], cert=[dict(name="Oregon Teaching License, English", org="TSPC", date="2016")]),
    "ravi": dict(name="Ravi Kumar", title="Backend Software Engineer", email="ravi.kumar@example.com", phone="(555) 010-0143", place="Austin, TX", links="github.com/ravi-kumar-example",
        summary="Backend engineer with six years building payment and order systems in Go and Python. Keeps services fast and boring: 99.98% uptime and p95 latency under 120 ms.",
        skills="Go, Python, PostgreSQL, Kafka, Kubernetes, AWS, gRPC, Terraform",
        exp=[dict(role="Senior Software Engineer", org="Lonestar Payments", dates="Mar 2022 – now", text="Rebuilt the payment authorization service in Go; p95 latency fell from 340 ms to 110 ms\nMoved 14 services to Kubernetes on AWS with no customer-facing downtime\nCut paging alerts by 60% by fixing the 10 noisiest checks and adding runbooks"),
             dict(role="Software Engineer", org="Trailhead Commerce", dates="Jun 2019 – Feb 2022", text="Built the order event pipeline on Kafka, handling 3M events a day\nWrote the PostgreSQL migration plan that moved 2 TB of data with 15 minutes of read-only time")],
        edu=[dict(what="B.S. in Computer Science", org="Texas A&M University", dates="2019")]),
    "lucas": dict(name="Lucas Romero", title="Warehouse Supervisor", email="lucas.romero@example.com", phone="(555) 010-0154", place="Indianapolis, IN", links="",
        summary="Warehouse supervisor with seven years in distribution. Leads a night shift of 35 that ships 12,000 orders with 99.6% accuracy.",
        skills="Team leadership, Inventory control, WMS, Forklift certified, OSHA safety, Shipping and receiving, Scheduling",
        exp=[dict(role="Warehouse Supervisor, Night Shift", org="Crossroads Distribution", dates="Apr 2022 – now", text="Lead 35 associates who pick and ship about 12,000 orders a night at 99.6% accuracy\nCut overtime hours by 30% with a new shift schedule built around order volume\nRan 400 days without a lost-time injury"),
             dict(role="Lead Warehouse Associate", org="Hoosier Logistics", dates="Mar 2019 – Mar 2022", text="Trained 40 new associates on picking, packing and the scanner system"),
             dict(role="Warehouse Associate", org="Hoosier Logistics", dates="Jun 2017 – Feb 2019", text="Picked and packed about 250 orders a shift")],
        edu=[dict(what="High school diploma", org="Arsenal Technical High School", dates="2017")], cert=[dict(name="Forklift Operator Certification", org="OSHA-compliant program", date="2018")]),
    "daniel2": dict(name="Noah Fischer", title="Product Designer", email="noah.fischer@example.com", phone="(555) 010-0165", place="San Francisco, CA", links="noahfischer.example.com",
        summary="Product designer with six years in consumer apps. Designs simple flows that measure well: the new sign-up flow raised completion from 52% to 71%.",
        skills="Product design, Interaction design, User research, Prototyping, Figma, Design systems, Usability testing",
        exp=[dict(role="Senior Product Designer", org="Tidewater Apps", dates="Aug 2022 – now", text="Redesigned the sign-up flow; completion rose from 52% to 71% in its first month\nBuilt the design system of 120 components now used by 5 product teams\nRan 40 usability sessions a year and shared what we learned in a monthly digest"),
             dict(role="Product Designer", org="Fogline Health", dates="Jun 2019 – Jul 2022", text="Designed the appointment booking app used by 300,000 patients\nCut support tickets about booking by 35% with clearer error messages")],
        edu=[dict(what="B.A. in Interaction Design", org="California College of the Arts", dates="2019")]),
    "hannah": dict(name="Hannah Weiss", title="Sales Manager", email="hannah.weiss@example.com", phone="(555) 010-0176", place="Minneapolis, MN", links="linkedin.com/in/hannah-weiss-example",
        summary="Sales manager with ten years in B2B software sales. Leads a team of 9 that grew new revenue from $6M to $9.5M in two years.",
        skills="Sales leadership, Forecasting, Coaching, Salesforce, Territory planning, Enterprise sales, Negotiation",
        exp=[dict(role="Sales Manager", org="Northstar Software", dates="Jan 2022 – now", text="Lead 9 account executives; new revenue grew from $6M to $9.5M in two years\nBrought forecast accuracy to within 5% for 7 quarters in a row\nHired and coached 5 reps; 4 reached quota in their first year"),
             dict(role="Senior Account Executive", org="Lakes Data Systems", dates="2016 – 2021", text="Closed 38 enterprise deals worth $14M, 120% of quota on average")],
        edu=[dict(what="B.A. in Business", org="University of Minnesota", dates="2015")]),
}

# Every template page answers these, in its own words (the name is put in)
COMMON_QA = [
    ("Is the {name} resume template free?", "Yes. Fill it in in the resume builder and download it as a PDF or a Word file for free, with no account, no trial and no watermark. Nothing you type is uploaded: the resume stays in your browser."),
    ("Can I change the colour and the font of the {name} template?", "Yes, under Design in the builder: one of eight heading colours or the template's own, the template's font or Inter, Arial, Georgia or Times New Roman, the text size, the line spacing, and US Letter or A4 paper."),
]

MONTH_RX = None


def e(s):
    return html.escape(str(s or ""), quote=True)


def _lines(t):
    return [ln.lstrip("-•* ").strip() for ln in str(t or "").split("\n") if ln.lstrip("-•* ").strip()]


def _ul(t):
    ls = _lines(t)
    return "<ul>" + "".join(f"<li>{e(ln)}</li>" for ln in ls) + "</ul>" if ls else ""


def _months(dates):
    """'Apr 2021 – now' -> months in the job (the last month counts), as resume.js months(); 0 when the dates cannot be read."""
    import datetime, re
    mon = dict(jan=1, feb=2, mar=3, apr=4, may=5, jun=6, jul=7, aug=8, sep=9, oct=10, nov=11, dec=12)
    def ym(t, end):
        t = t.strip().lower()
        if re.search(r"now|present|current|today", t):
            d = datetime.date.today(); return d.year, d.month
        m = re.search(r"(\d{1,2})\s*[/.]\s*(\d{4})", t)
        if m: return int(m.group(2)), int(m.group(1))
        m = re.search(r"([a-z]{3})[a-z]*\.?\s+(\d{4})", t)
        if m and m.group(1) in mon: return int(m.group(2)), mon[m.group(1)]
        m = re.search(r"(\d{4})", t)
        return (int(m.group(1)), 12 if end else 1) if m else None
    parts = re.split(r"\s*(?:–|—|-|\bto\b)\s*(?=[a-z0-9])", str(dates or ""), flags=re.I)
    if len(parts) < 2: return None
    a, b = ym(parts[0], False), ym(parts[-1], True)
    if not a or not b: return None
    r = (a[0] * 12 + a[1], b[0] * 12 + b[1])
    return r if r[1] >= r[0] and r[1] - r[0] < 600 else None


def _span(n):
    y, m = divmod(n, 12)
    return " ".join(x for x in ((f"{y} yr" + ("s" if y != 1 else "")) if y else "", (f"{m} mo" + ("s" if m != 1 else "")) if m else "") if x)


def sheet_html(d, tpl):
    """The inner HTML of a sheet (class "rbs tpl-<tpl>"), the same markup as resume.js sheetHtml(), so the gallery shows what the builder makes."""
    contact = " · ".join(e(x) for x in [d.get("email"), d.get("phone"), d.get("place")] + [s.strip() for s in str(d.get("links") or "").split(",")] if x)
    tl, spans = tpl == "timeline", []
    exp = ""
    for x in d.get("exp") or []:
        if tl:
            r = _months(x["dates"]); spans.append(r)
            n = r[1] - r[0] + 1 if r else 0
            exp += (f'<div class="pv-item pv-tl"><div class="pv-when">{e(x["dates"])}' + (f"<span>{_span(n)}</span>" if n else "") + '</div><div class="pv-what">'
                    + (f'<strong>{e(x["org"])}</strong>' if x.get("org") else "") + (f'<b>{e(x["role"])}</b>' if x.get("role") else "") + _ul(x.get("text")) + "</div></div>")
        else:
            exp += f'<div class="pv-item"><div class="pv-top"><strong>{e(x["role"])}' + (f', {e(x["org"])}' if x.get("org") else "") + f'</strong><span>{e(x["dates"])}</span></div>{_ul(x.get("text"))}</div>'
    proj = "".join(f'<div class="pv-item"><div class="pv-top"><strong>{e(x["name"])}</strong><span>{e(x.get("link"))}</span></div>{_ul(x.get("text"))}</div>' for x in d.get("proj") or [])
    cert = "".join(f'<div class="pv-item"><div class="pv-top"><strong>{e(x["name"])}' + (f', {e(x["org"])}' if x.get("org") else "") + f'</strong><span>{e(x.get("date"))}</span></div></div>' for x in d.get("cert") or [])
    edu = "".join(f'<div class="pv-item"><div class="pv-top"><strong>{e(x["what"])}' + (f', {e(x["org"])}' if x.get("org") else "") + f'</strong><span>{e(x.get("dates"))}</span></div></div>' for x in d.get("edu") or [])
    lang = [e(x["name"]) + (f' ({e(x["level"])})' if x.get("level") else "") for x in d.get("lang") or []]
    skills = [s.strip() for s in str(d.get("skills") or "").split(",") if s.strip()]
    total = 0
    rs = sorted(r for r in spans if r)
    cur = None
    for r in rs:
        if cur and r[0] <= cur[1] + 1: cur = (cur[0], max(cur[1], r[1]))
        else:
            if cur: total += cur[1] - cur[0] + 1
            cur = r
    if cur: total += cur[1] - cur[0] + 1
    S = {"summary": f'<p class="pv-h">Summary</p><p>{e(d["summary"])}</p>' if d.get("summary") else "",
         "exp": ('<p class="pv-h">Experience' + (f" <small>{_span(total)}</small>" if tl and total else "") + "</p>" + exp) if exp else "",
         "proj": '<p class="pv-h">Projects</p>' + "" + proj if proj else "", "edu": '<p class="pv-h">Education</p>' + "" + edu if edu else "", "cert": '<p class="pv-h">Certifications</p>' + "" + cert if cert else "",
         "skills": ('<p class="pv-h">Skills</p>' + "" + ('<p class="pv-tags">' + "".join(f"<span>{e(k)}</span>" for k in skills) + "</p>" if tl else "<p>" + " · ".join(e(k) for k in skills) + "</p>")) if skills else "",
         "lang": '<p class="pv-h">Languages</p>' + "<p>" + " · ".join(lang) + "</p>" if lang else "", "interests": f'<p class="pv-h">Interests</p><p>{e(d["interests"])}</p>' if d.get("interests") else ""}
    order = ["summary", "edu", "proj", "exp", "skills", "cert", "lang", "interests"] if tpl == "student" else ["summary", "exp", "proj", "edu", "cert", "skills", "lang", "interests"]
    return (f'<div class="pv-head"><p class="pv-name">{e(d.get("name") or "Your name")}</p>' + (f'<p class="pv-title">{e(d["title"])}</p>' if d.get("title") else "")
            + (f'<p class="pv-contact">{contact}</p>' if contact else "") + "</div>" + "".join(S[k] for k in order))


def sheet(t):
    """The template filled with its person, as the element the gallery and the page show (aria-hidden: the page says in words what it shows)."""
    return f'<div class="rbs tpl-{t["id"]}" aria-hidden="true">{sheet_html(PEOPLE[t["person"]], t["id"])}</div>'


def test(js_text=None):
    ids = [t["id"] for t in TEMPLATES]
    assert len(ids) == len(set(ids)) == 16, ids
    assert all(t["person"] in PEOPLE for t in TEMPLATES)
    assert len({t["person"] for t in TEMPLATES}) == len(TEMPLATES), "each template shows a person of its own"
    assert len({t["title"].lower() for t in TEMPLATES}) == len(TEMPLATES), "one search phrase per page"
    for t in TEMPLATES:
        assert set(t["level"]) <= {k for k, _ in LEVELS} and set(t["style"]) <= {k for k, _ in STYLES}, t["id"]
        assert 2 <= len(t["about"].split(".")) and len(t["qa"]) >= 1 and len(t["suits"]) >= 3, t["id"]
        p = PEOPLE[t["person"]]
        assert p["email"].endswith("@example.com") and "555" in p["phone"], t["id"]
    if js_text is not None:
        import re
        m = re.search(r"var TPLS = \[(.*?)\];", js_text, re.S)
        js_ids = re.findall(r"'(\w+)'", m.group(1)) if m else []
        assert js_ids == ids, ("assets/resume.js TPLS and resume_templates.TEMPLATES differ", js_ids, ids)
    return True


if __name__ == "__main__":
    from pathlib import Path
    test((Path(__file__).parent / "assets" / "resume.js").read_text())
    print(f"resume_templates: {len(TEMPLATES)} templates, {len(PEOPLE)} people, all checks passed")
