"""What each skill is, in words a person outside tech understands.

The skill names on job postings are jargon. Someone changing careers, a recruiter or a student should be able to read the
skills page without a dictionary, so every skill gets a group and one plain line. The line is a phrase without a subject:
it reads as "Python: a programming language…" on the skill's own page and starts with a capital letter in lists.
A skill missing from INFO still gets a page; it is listed under "Other skills" without a description.
"""

GROUPS = [
    ("languages", "Programming languages", "The languages software is written in."),
    ("web", "Websites and apps", "Kits and platforms for building what people see and tap."),
    ("ai", "AI and machine learning", "Building programs that learn from data or work with language and images."),
    ("data", "Data and analytics", "Collecting data, storing it in one place and turning it into answers."),
    ("databases", "Databases", "Where apps keep their data."),
    ("cloud", "Cloud and operations", "Keeping software running, on rented servers, for everyone at once."),
    ("testing", "Testing", "Checking automatically that software still works."),
    ("work", "Design and teamwork", "How teams design products and organise the work."),
    ("business", "Sales, marketing and business software", "The systems sales, support, finance and HR teams live in."),
    ("crypto", "Crypto and finance", "Blockchains, trading and the rules around money."),
    ("hardware", "Hardware and robotics", "Software for chips, devices and machines."),
]

INFO = {
    # languages
    "Python": ("languages", "a programming language that is easy to read, used for data work, AI and the server side of websites"),
    "JavaScript": ("languages", "the language that runs in every web browser and makes pages interactive"),
    "TypeScript": ("languages", "JavaScript with extra checks that catch mistakes before the code runs"),
    "Java": ("languages", "a long-established language for large business systems and Android apps"),
    "Go": ("languages", "a language from Google for fast, simple server programs"),
    "Rust": ("languages", "a language for fast programs that must not crash, from browsers to blockchains"),
    "C++": ("languages", "a fast, low-level language behind games, trading systems and devices"),
    "C#": ("languages", "Microsoft’s language for business software and Unity games"),
    "Kotlin": ("languages", "the main language for Android apps today"),
    "Swift": ("languages", "Apple’s language for iPhone, iPad and Mac apps"),
    "Ruby": ("languages", "a language known for building web products quickly, usually with Rails"),
    "PHP": ("languages", "a language that runs much of the web, including WordPress"),
    "Scala": ("languages", "a language used for heavy data processing, often with Spark"),
    "Elixir": ("languages", "a language for systems that serve many people at once, such as chats"),
    "Bash": ("languages", "short scripts that tell a Linux or Mac computer what to do"),
    "Perl": ("languages", "an older scripting language, still found in long-running systems"),
    "MATLAB": ("languages", "software for engineering maths, simulations and signal processing"),
    "Objective-C": ("languages", "the older language of Apple apps, before Swift"),
    # websites and apps
    "React": ("web", "the most widely used kit for building website interfaces"),
    "Next.js": ("web", "a way to build complete websites with React"),
    "Vue": ("web", "a kit for building website interfaces, an alternative to React"),
    "Angular": ("web", "Google’s kit for building large web applications"),
    "Svelte": ("web", "a newer, lighter kit for building website interfaces"),
    "Node.js": ("web", "lets JavaScript run on a server, not only in the browser"),
    "Django": ("web", "a Python kit for building websites together with their admin side"),
    "Flask": ("web", "a small Python kit for simple web services"),
    "FastAPI": ("web", "a Python kit for building fast web services"),
    "Rails": ("web", "a Ruby kit for building web products quickly"),
    "Laravel": ("web", "the most popular PHP kit for building websites"),
    "Spring": ("web", "the standard Java kit for business web systems"),
    ".NET": ("web", "Microsoft’s platform for building business software"),
    "GraphQL": ("web", "a way for an app to ask a server for exactly the data it needs"),
    "gRPC": ("web", "a fast way for programs inside a company to talk to each other"),
    "WebAssembly": ("web", "lets heavy programs, such as editors and games, run inside a browser"),
    "React Native": ("web", "one codebase for both iPhone and Android apps, built with React"),
    "Flutter": ("web", "Google’s kit for building iPhone and Android apps from one codebase"),
    "iOS": ("web", "building apps for iPhone and iPad"),
    "Android": ("web", "building apps for Android phones and tablets"),
    "Unity": ("web", "an engine for making games and 3D apps"),
    "Unreal Engine": ("web", "an engine for high-end games and 3D graphics"),
    # AI
    "AI": ("ai", "roles that build artificial intelligence or put it into a product"),
    "Machine Learning": ("ai", "teaching programs to find patterns in data and make predictions"),
    "LLM": ("ai", "large language models, the technology behind ChatGPT and similar assistants"),
    "RAG": ("ai", "a way to let an AI assistant answer from a company’s own documents"),
    "LangChain": ("ai", "a kit for building apps on top of language models"),
    "PyTorch": ("ai", "the most used kit for building and training AI models"),
    "TensorFlow": ("ai", "Google’s kit for building and training AI models"),
    "Computer Vision": ("ai", "teaching computers to understand photos and video"),
    "NLP": ("ai", "teaching computers to understand and write human language"),
    "CUDA": ("ai", "Nvidia’s tools for running heavy calculations on graphics cards"),
    # data
    "SQL": ("data", "the language for asking a database questions, used by analysts and engineers alike"),
    "Excel": ("data", "spreadsheets, still the everyday tool in finance and operations"),
    "Tableau": ("data", "software for turning data into charts and dashboards"),
    "Power BI": ("data", "Microsoft’s software for charts and dashboards"),
    "Looker": ("data", "Google’s software for company dashboards"),
    "Pandas": ("data", "a Python tool for working with tables of data"),
    "Spark": ("data", "a system for processing very large amounts of data"),
    "Hadoop": ("data", "an older system for storing and processing very large amounts of data"),
    "Kafka": ("data", "a system that passes streams of events between programs as they happen"),
    "Airflow": ("data", "a scheduler that runs data jobs in the right order"),
    "dbt": ("data", "a tool analysts use to clean and prepare data with SQL"),
    "Snowflake": ("data", "a cloud data warehouse: one place for all of a company’s data"),
    "BigQuery": ("data", "Google’s cloud data warehouse"),
    "Redshift": ("data", "Amazon’s cloud data warehouse"),
    "Databricks": ("data", "a cloud platform for data engineering and machine learning"),
    "ClickHouse": ("data", "a database built for very fast reports on huge tables"),
    # databases
    "PostgreSQL": ("databases", "a popular free database for storing an app’s data"),
    "MySQL": ("databases", "a widely used free database, common behind websites"),
    "MongoDB": ("databases", "a database that stores data as flexible documents instead of tables"),
    "Redis": ("databases", "a very fast in-memory store, used to speed apps up"),
    "Elasticsearch": ("databases", "a search engine companies run over their own data and logs"),
    "DynamoDB": ("databases", "Amazon’s database for apps with very heavy traffic"),
    # cloud and operations
    "AWS": ("cloud", "Amazon’s cloud: rented servers and services that most startups run on"),
    "GCP": ("cloud", "Google’s cloud: rented servers and services"),
    "Azure": ("cloud", "Microsoft’s cloud: rented servers and services"),
    "Docker": ("cloud", "packs a program with everything it needs, so it runs the same anywhere"),
    "Kubernetes": ("cloud", "runs many such packages across many servers and adds more when traffic grows"),
    "Terraform": ("cloud", "describes servers and cloud settings as code, so they can be recreated exactly"),
    "Ansible": ("cloud", "sets up and updates many servers automatically"),
    "Linux": ("cloud", "the operating system that runs most servers"),
    "CI/CD": ("cloud", "automatic testing and release of code each time it changes"),
    "Jenkins": ("cloud", "a long-used tool for automatic builds and releases"),
    "GitHub Actions": ("cloud", "GitHub’s built-in tool for automatic tests and releases"),
    "Datadog": ("cloud", "a service that watches systems and warns when something breaks"),
    "Prometheus": ("cloud", "a free tool that collects measurements from running systems"),
    "Grafana": ("cloud", "dashboards that show how systems are doing"),
    "OpenTelemetry": ("cloud", "a common standard for collecting data about how software behaves"),
    # testing
    "Playwright": ("testing", "a tool that clicks through a website automatically to test it"),
    "Selenium": ("testing", "the long-standing tool for automatic website testing"),
    "Cypress": ("testing", "a tool for automatic testing of web apps"),
    # design and teamwork
    "Figma": ("work", "the standard design tool for apps and websites"),
    "Jira": ("work", "a task tracker used by most software teams"),
    "Agile": ("work", "a way of working in short cycles with frequent releases"),
    # business software
    "Salesforce": ("business", "the most used system for tracking customers and sales"),
    "HubSpot": ("business", "software for marketing, sales and customer records"),
    "SEO": ("business", "getting a website to rank higher in Google"),
    "Zendesk": ("business", "software for handling customer support requests"),
    "NetSuite": ("business", "accounting and finance software for growing companies"),
    "Workday": ("business", "HR and payroll software for large companies"),
    "SAP": ("business", "software that runs finance and supply chains at large companies"),
    "Shopify": ("business", "a platform for running online stores"),
    # crypto and finance
    "Solidity": ("crypto", "the language for programs on Ethereum and similar blockchains"),
    "Smart contracts": ("crypto", "programs that run on a blockchain and move money by fixed rules"),
    "DeFi": ("crypto", "financial services, such as lending and trading, built on blockchains"),
    "NFT": ("crypto", "digital items whose ownership is recorded on a blockchain"),
    "Ethereum": ("crypto", "the largest blockchain for apps and smart contracts"),
    "Solana": ("crypto", "a fast blockchain, popular for trading and consumer apps"),
    "Zero-knowledge": ("crypto", "cryptography that proves something is true without revealing the data behind it"),
    "Trading": ("crypto", "buying and selling assets, and the systems built for it"),
    "AML/KYC": ("crypto", "checks that customers are who they say they are and that money is not being laundered"),
    # hardware and robotics
    "Embedded C": ("hardware", "C written for the small computers inside devices and machines"),
    "Verilog": ("hardware", "a language for describing computer chips"),
    "ROS": ("hardware", "the standard software kit for programming robots"),
}


def plain(skill):
    """The plain line for a skill as a sentence, or an empty string."""
    d = INFO.get(skill, ("", ""))[1]
    return d[0].upper() + d[1:] + "." if d else ""


# The same for job categories: who works in each, in plain words.
CATEGORIES = {
    "engineering": "people who write, test and run software and hardware: developers, DevOps, QA, machine learning and hardware engineers",
    "security": "people who protect systems and data: security engineers, analysts, penetration testers and incident response",
    "product": "people who decide what gets built and why: product managers, product owners and program managers",
    "design": "people who shape how a product looks and works: product, UX and brand designers, researchers and writers",
    "sales-bd": "people who bring in customers and partners: account executives, sales engineers, business development and partnerships",
    "marketing": "people who make a product known: growth, content, brand, events, community and developer relations",
    "support": "people who help customers after the sale: support, customer success, onboarding and technical account managers",
    "compliance-legal": "lawyers and specialists who keep a company inside the rules: legal counsel, compliance, risk, policy and privacy",
    "finance": "people who manage the money: accounting, financial planning, treasury, tax and, at trading firms, traders and quants",
    "people": "people who hire and look after staff: recruiters, HR partners, people operations and workplace teams",
    "data-research": "people who turn data into answers: analysts, data scientists, data engineers and researchers",
    "operations": "people who keep the business running day to day: operations, supply chain, IT, facilities and administration",
    "healthcare": "people who treat and look after patients, in person or online: nurses, physicians, therapists, pharmacists and care coordinators",
    "manufacturing": "people who build, test and maintain physical things: technicians, machinists, welders, production and maintenance crews, inspectors",
    "supply-chain": "people who buy the parts and move the goods: sourcing, procurement, planning, warehouses, logistics and fleets",
    "retail": "people who serve customers in a shop, a cafe or a hotel: store staff, key holders, shift leads, cooks and front-desk teams",
    "education": "people who teach: teachers, tutors, instructors, curriculum writers and the teams that train a company's own staff",
    "consulting": "people who set a product up for a customer and advise how to use it: consultants, implementation and solutions specialists, engagement managers",
    "other": "roles whose title did not fit any of the other groups",
}


def plain_cat(slug):
    d = CATEGORIES.get(slug, "")
    return d[0].upper() + d[1:] + "." if d else ""
