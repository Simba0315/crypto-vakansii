# Upwork: что взять для Hiring Right Now (дизайн и не только)

Дата исследования: 14.11.2026. Страницы Upwork читались во встроенном браузере (обычный запрос скриптом получил 403, сайт закрыт от скриптов). Без регистрации и входа.

## 1. Вывод в 5 строках

1. Дизайн Upwork «дорогой» за счёт простоты: белый фон, почти чёрный текст, один зелёный, заголовки средней жирности с плотной разрядкой, живые цифры у каждой роли («16,925+ available»), большие скруглённые фото. Всё это можно повторить своим цветом без сервера.
2. Главный SEO-приём Upwork: одна схема на тысячи ролей. Страница роли + дочерние «стоимость», «шаблон вакансии», «вопросы для собеседования» + страны и города. У нас уже есть материал на такую тройку, не хватает шаблона вакансии и связки.
3. Из своих данных мы честно можем сделать «<skill> jobs» с живым числом, «freelance/contract <skill> jobs», «<роль> hourly rate» по вакансиям с указанной ставкой, «<роль> jobs in <город>» там, где вакансий достаточно.
4. Самая сильная находка: Upwork отключил RSS-ленты в августе 2024, а оповещения о вакансиях у него только на платном тарифе $19.99 в месяц. Бесплатные RSS-ленты и сохранённые поиски у нас делаются без сервера и могут стать нашим отличием.
5. Деньги: из моделей Upwork нам подходит только «выделенная вакансия» для работодателя (за крипту, сначала вручную). Connects, комиссии и подписка для соискателей нам не подходят.

## 2. Дизайн

### 2.1 Главная страница upwork.com (прочитано 14.11.2026, https://www.upwork.com/)

Порядок блоков сверху вниз:
1. Шапка: логотип, меню «Hire talent ˅», «Get outcomes ˅», «Find work ˅», «Why Upwork ˅», «Pricing», «Enterprise», значок поиска, «Log in», зелёная кнопка-«таблетка» «Sign up».
2. Узкая светло-зелёная плашка над героем: «Hire the top 1% of talent on Business Plus. Get started ›» (реклама платного тарифа).
3. Герой: большое фото людей за работой в карточке со скруглёнными углами (примерно 24px), белый текст поверх. Переключатель «Hire / Work» (два режима: для нанимателя и для исполнителя). Заголовок «Work at the speed of your ambition», подзаголовок про экспертов, которые используют ИИ, одна зелёная кнопка «Get started →». Поисковой строки в герое нет.
4. Строка доверия: «TRUSTED BY 800,000 CLIENTS» (капслок, мелко).
5. «Find freelancers for every type of work»: вкладки категорий (Dev & IT, AI & Automation, Design & Creative, Marketing, Data & Analytics, Admin & Support, Writing & Content). Под вкладкой сетка 3 колонки из белых плиток: название роли + «16,925+ available» + маленькая стопка из 3 аватарок. Выбранная плитка обведена зелёной рамкой.
6. Под плитками горизонтальная лента карточек исполнителей: фото, имя с первой буквой фамилии («Oleg V.»), город и страна, ставка «$20/hr», рейтинг «5.0», «13 jobs», 2 строки описания, 5 тегов навыков, ссылка «See profile». Внизу «Explore Full Stack Developers» и «View more specialties».
7. «Freelancers by category»: длинный список-перелинковка по 9 группам (AI Services, Development & IT, Design & Creative, Sales & Marketing, Writing & Translation, Admin & Support, Finance & Accounting, Legal, HR & Training, Engineering & Architecture), по 12 ролей в каждой, в каждой строке рейтинг и средняя ставка: «Blockchain Developers - 4.7 / 5 rating, $78/hr», «Recruiters - 4.7 / 5 rating, $38/hr».
8. Новый блок «Free AI project scoping»: «What's your top business priority?» и 6 кнопок-ответов (Save time, Grow revenue, Boost loyalty, Make better decisions, Build something new, Other). Это мини-опрос, который ведёт к подбору.
9. «How it works» с переключателем «For hiring / For finding work», 3 шага: «Posting jobs is always free» (можно сгенерировать описание вакансии ИИ), «Get proposals and hire», «Pay when work is done».
10. «Get insights into freelancer pricing»: калькулятор «We'll calculate the average cost for freelancers with the skills you need» (выбор навыков → средняя цена).
11. «Choose how you want to hire»: 2 тарифа рядом, Basic и Business Plus (с меткой POPULAR), по 5 пунктов «что входит».
12. «Proven results on Upwork», «Trusted by growing businesses»: значки наград G2 (Best Software 2026 Top 50 HR Products, Leader Small Business Winter 2026, Easiest Setup, Easiest To Use и т.д.).
13. Финальный тёмный блок с призывом «Find freelancers who can help you build what's next» и кнопкой.
14. Подвал: колонки «For clients» (How to hire, Talent Marketplace, Project Catalog, Hire an agency, Business Plus, Contract-to-hire, Hire worldwide, Hire in the USA), «For talent» (How to find work, Find freelance jobs worldwide, Find freelance jobs in the USA, Win work with ads, Freelancer Plus), «Resources» (Help & support, Success stories, Upwork reviews, Resources, Blog, Affiliate program, Free Business Tools, Release notes), «Company» (About, Leadership, Investor relations, Careers, Press, Contact, Trust & safety), соцсети, ссылки на приложения iOS и Android, «Sitemap».

Разметка для поисковиков на главной: только Organization и WebSite (schema.org). Описание страницы: «world's largest human and AI-powered freelance marketplace».

### 2.2 Меню (мега-меню) (прочитано 14.11.2026, https://www.upwork.com/)

- «Hire talent» раскрывается в большую панель: слева группы (AI, Development, Design, Marketing, Data, Admin, Writing), справа по 10 ролей. У каждой роли две строки: название и короткое пояснение в 3-5 слов. Примеры: «Full-Stack Developers — Front and back end development», «SEO experts — Rank higher, drive organic traffic», «Resume Writers — Resumes that get interviews». Внизу ссылка на все роли (/hire/).
- «Get outcomes» ведёт на страницы-задачи, а не роли: /outcomes/build-website, /outcomes/design-brand, /outcomes/scale-paid-campaigns, /outcomes/automate-business-workflows, /outcomes/customer-support, /outcomes/build-sales-pipeline.
- «Find work» (для исполнителей): такие же группы, но ссылки на /freelance-jobs/<навык>/, тоже с пояснением в 3-5 слов («Python — Scripting, automation, Python», «Data Annotation — Label data that trains AI models»).
- Важная деталь: в меню прямо в HTML лежат ~150 ссылок на страницы ролей и навыков. Для поисковика это сильная внутренняя перелинковка с каждой страницы сайта.

### 2.3 Цвета, шрифт, сетка (снято со стилей главной 14.11.2026)

- Шрифт: «Neue Montreal» (платный гротеск), запасной Arial. Основной текст 14px, межстрочный 21px, лёгкая разрядка 0.56px. Заголовки средней жирности 500 (не жирные 700): H1 героя 42px, H2 разделов 48px и 28-32px. Для заголовков заданы отрицательные разрядки от -0.035em (H1) до -0.01em (H5), то есть крупные заголовки чуть «сжаты» по буквам. Это и даёт «дорогой» вид.
- Цвета: текст почти чёрный #1A1A1A на чистом белом. Фирменный зелёный hsl(113,100%,27%) (около #14A800 / #108A00). Вспомогательная палитра для иллюстраций: очень светлые зелёно-серые фоны #F7FAF7, #F2F7F2, #E8F1E8, тёмный зелёный #13544E, акцентный оранжево-красный #FF4B25, жёлтый #DEBE1A. Ссылки синие.
- Скругления заданы шкалой: 2, 4, 6, 8, 16, 24px. Кнопки-«таблетки» полностью скруглены. Карточки плиток: белые, тонкая серая рамка или лёгкая тень, около 8px.
- Тени лёгкие, один цвет тени (57,73,76) с прозрачностью.

### 2.4 Что делает вид «премиальным» (наблюдение)

1. Мало цветов: белый, почти чёрный, один зелёный. Зелёный только для главных кнопок и выделения.
2. Заголовки средней жирности и плотная разрядка вместо жирного капса.
3. Много воздуха между блоками, один главный призыв на экран.
4. Живые фото людей в больших скруглённых карточках, а не стоковые иконки.
5. Числа рядом с каждой ролью («16,925+ available», «4.8/5, $60/hr»): страница выглядит «живой» и полезной.
6. Сторонние награды (значки G2) и одна крупная цифра доверия вместо десятка.
7. Переключатель «Hire / Work» вместо двух разных главных страниц.

### 2.5 Карточки на страницах навыков и вакансий (прочитано 14.11.2026)

Карточка вакансии в списке (https://www.upwork.com/freelance-jobs/python/):
- Заголовок-ссылка.
- Строка «Hourly ‐ Posted 1 day ago» (тип оплаты и давность одной строкой).
- Два «факта» с подписью снизу мелким серым: «Less than 30 hrs/week / Hours needed» и «Intermediate / Experience level». Для фиксированной цены вместо часов сумма: «$50 / Fixed-price».
- 2 строки описания с многоточием.
- Теги навыков (до 8 «пилюль»), «See more».
- Внизу списка кнопка «Load more jobs», а не нумерация страниц.

Карточка исполнителя (https://www.upwork.com/hire/python-developers/): имя «Lucio Ricardo M.» + метка «Verified», должность одной строкой, город и страна, «$25/hr», «4.8 (105)», «195 jobs», «$100K+ total earnings», до 15 тегов навыков, абзац о себе, кнопка «View profile».

Страница одной вакансии (пример: https://www.upwork.com/freelance-jobs/apply/Automation-Developer-for-Home-Health-Administrative-Workflows_~022121059344782235803/):
- Заголовок, «Posted yesterday», «Worldwide».
- Полное описание.
- Сетка фактов с иконками: часы в неделю, срок «1-3 months», уровень «Intermediate», вилка «$3.00 - $50.00 Hourly», «Remote Job», «One-time project».
- Навыки тегами.
- Блок «Activity on this job»: Proposals: 50+, Last viewed by client: 7 hours ago, Interviewing: 2, Invites sent: 2, Unanswered invites: 0.
- Блок «About the client»: Member since Sep 19, 2017, страна и город с местным временем «Fairfax 4:44 AM», «$3.3K total spent», «15 hires, 1 active», «50 hours».
- «Explore similar jobs on Upwork» (2-3 похожих), затем «How it works» (3 шага) и цифры доверия.
- В коде: разметка JobPosting (datePosted, employmentType CONTRACTOR/TEMPORARY, directApply true). Заметка: в hiringOrganization стоит сам Upwork, а не наниматель, и разметка продублирована дважды. Нам так делать не надо: у нас настоящий работодатель, его и указываем.

### 2.6 Что конкретно перенести в наш дизайн (не их бренд)

1. Один акцентный цвет только для главной кнопки, ссылки «сейчас» и выделенной плитки. Остальное: белый фон, текст #1A1A1A, серые подписи. Свой цвет оставить свой, не зелёный Upwork.
2. Заголовки жирностью 500 (не 700), крупные H1/H2 с отрицательной разрядкой около -0.03em. Основной текст 14-16px, межстрочный около 1.5.
3. Шрифт: Neue Montreal платный (у Upwork своя версия). Похожий бесплатный гротеск подобрать отдельно (например Inter или Geist, это мой совет, не проверено на нашем сайте).
4. Шкала скруглений: 4px мелочь, 8px карточки, 16px крупные блоки, 24px герой. Кнопки полностью скруглённые.
5. Плитки категорий: название роли + «N open jobs» серым, сетка 3 колонки на компьютере, 1 на телефоне; выбранная плитка с рамкой акцентного цвета.
6. Под крупными цифрами всегда подпись мелким серым («Hours needed», «Experience level»): так факт читается за секунду.
7. Над героем узкая тонированная плашка с одним предложением и ссылкой (у них реклама тарифа; у нас, например, «Новое: бесплатные RSS-ленты по навыку»).
8. Блоки разделов на очень светлом тонированном фоне (у Upwork #F7FAF7 / #F2F7F2), чередовать с белым.
9. Внизу главной большой тёмный блок с одним призывом.
10. Подвал из 4 колонок: «Для соискателей», «Для работодателей», «Ресурсы» (инструменты, гиды, статьи), «О нас»; ссылка «Sitemap».

## 3. Семейства страниц для поиска (SEO)

Upwork строит десятки тысяч страниц по одной схеме: «навык/роль» × «тип страницы» × «место». Все примеры ниже открыты 14.11.2026.

### 3.1 «Найти работу по навыку»: /freelance-jobs/<навык>/
Пример: https://www.upwork.com/freelance-jobs/python/
- Заголовок страницы: «Python Freelance Jobs: Work Remote & Earn Online». H1 «Find the Best Python Jobs».
- Описание для поиска с живой цифрой: «Browse 1,527 open jobs and land a remote Python job today...».
- Сверху «4.9/5 On average from 2M+ reviews» (как специалисты оценивают клиентов).
- «Check out a sample of the 1,527 Python jobs posted on Upwork» и 10 карточек свежих вакансий, «Load more jobs».
- Блок «Python Developers on Upwork can earn $20–$45/hr. Median hourly rates (USD)».
- Длинный текст-гид: «How to Become a Freelance Python Developer», «What does ... do?», «What skills do I need?», «Core job responsibilities», «Should I get a degree or certification?» (с названиями сертификатов).
- Перелинковка: «Find jobs for other in-demand skills» (16 соседних навыков: Django, PyTorch, Machine Learning...) и «Similar Python Skills» (16 ссылок на страницы найма).
- Разметка: только хлебные крошки (BreadcrumbList).
- Страна: https://www.upwork.com/freelance-jobs/united-states/ «Find the Best Jobs in the United States», «sample of the 27,545 jobs».
- Страница вакансии: /freelance-jobs/apply/<Заголовок-через-дефисы>_~<id>/ (открыта для поиска, есть JobPosting).

Можем ли мы честно сделать: ДА, у нас это уже частично есть (страницы навыков и ролей). Взять: живую цифру в title/description («Browse 1,527 open Python jobs»), блок медианной ставки из наших же вакансий, гид «как стать X», два блока перелинковки «соседние навыки» и «похожие роли». Отдельное семейство «Freelance and contract <skill> jobs» можно собрать из наших вакансий с типом contract/freelance/part-time (без сервера, если тип занятости есть в данных).

### 3.2 «Нанять специалиста»: /hire/<роль>/
Пример: https://www.upwork.com/hire/python-developers/
- Title «Best Freelance Python Developers for Hire (Nov 2026) - Upwork» (месяц и год в заголовке, обновляется каждый месяц).
- «Clients rate our Python Developers 4.8/5 Based on 44,897 client reviews».
- 4 карточки исполнителей, «How it works» (Post a job, Hire top talent fast, Collaborate easily, Payment simplified), отзывы.
- «Resources to help you hire»: 3 ссылки на дочерние страницы (стоимость, шаблон описания вакансии, вопросы для собеседования).
- «Python developer hiring guide»: что делает, как нанять в 4 шага (Craft a targeted job post, Filter and evaluate, Interview, Agree on scope).
- «How much does hiring a Python developer cost?»: $20-$40/час и 5 типовых проектов с ценой: скрипт автоматизации $250-$1,500, веб-приложение или API $1,000-$6,000, конвейер данных $750-$4,000, ИИ-интеграция $1,500-$8,000, поддержка $1,500-$5,000.
- FAQ: «Is hiring a Python developer worth it?», «Are Python developers still in demand in 2026?», «What should a Python developer's rate include?».
- «Top Countries for Python Developers»: 16 ссылок на страны.
- Разметка: CollectionPage + BreadcrumbList.

### 3.3 Дочерние страницы роли (одна схема на каждую из тысяч ролей)
- Стоимость: /hire/<роль>/cost/. Пример https://www.upwork.com/hire/python-developers/cost/ : «Python Developers on Upwork Cost $20–$40/hr», «How much does a Python Developer cost?», ссылки «под $30 / под $100 / под $250» на готовые услуги, «See rates for other in-demand skills» (16 ссылок), сноска «data represents typical hourly rate ranges of certain historical contracts». Страница короткая.
  Заметка: на странице работы та же роль показана как $20–$45/hr, на странице стоимости $20–$40/hr. Цифры у них не сходятся.
- Шаблон описания вакансии: /hire/<роль>/job-description/. Пример https://www.upwork.com/hire/python-developers/job-description/ : «Python Developer Job Description Template» (title с «2026»): Job overview, Key responsibilities, Qualifications and skills, About our company, как написать, FAQ «What is the typical Python developer's salary?».
- Вопросы для собеседования: /hire/<роль>/interview-questions/ (ссылка есть на странице роли, сама страница не открывалась, не проверено).
- Старый формат статей о стоимости: https://www.upwork.com/hiring/for-clients/how-much-does-it-cost-to-hire-wordpress-developer/ (по выдаче поиска).

### 3.4 Место: роль × страна × город
- Страна: /hire/<роль>/<код страны>/, пример https://www.upwork.com/hire/python-consultants/tr/ (ссылки со страницы роли, 14.11.2026).
- Город: /hire/<роль>/us/<город-штат>/, примеры https://www.upwork.com/hire/media-buyers/us/new-york-ny/ , https://www.upwork.com/hire/audio-engineers/us/new-york-ny/ , https://www.upwork.com/hire/new-york-freelancers/us/new-york-ny/ (по выдаче поиска 14.11.2026). Есть и старый вариант /hire/photo-editors/new-york-us/ (по выдаче).
- Заголовки по шаблону «Hire the Best <роль> in New York, NY». По выдаче на части таких страниц тексты выглядят шаблонными: это риск «тонких» страниц.
- Подвал главной: «Hire in the USA» /hire/us/ и «Find freelance jobs in the USA» /freelance-jobs/united-states/.

### 3.5 Задача вместо роли: /outcomes/<задача>
Из меню «Get outcomes»: /outcomes/build-website, /outcomes/design-brand, /outcomes/automate-business-workflows и др. Страница отвечает на «мне нужно сделать X», а не «мне нужен специалист Y» (сами страницы не открывались, содержание не проверено).

### 3.6 Статьи, сравнения и бесплатные инструменты
- Resource Center https://www.upwork.com/resources (14.11.2026): рубрики Small Business Insights, AI Services, Hiring & Management, Work & Career. Сверху «Explore popular topics»: «Upwork vs. Fiverr», «Best freelance websites», «Online jobs for students». Среди статей есть страницы, которые ловят запросы соискателей: /resources/best-job-search-website, /resources/best-linkedin-alternatives, /resources/upwork-hourly-rates, /resources/how-to-hire-freelancers. У каждой статьи видна дата.
- Бесплатные инструменты https://www.upwork.com/tools (14.11.2026): 16 калькуляторов в 3 группах. Budget: Marketing Budget, Staffing Agency, Startup Cost, Website Cost, Website Design Cost. Business Planning: Conversion Rate, CPM, Profit Margin, YouTube Money, Cost of Vacancy. For Freelancers: Connects, Fiverr Fee, Freelance Rate, Freelance Tax, Toptal Fee, Upwork Fee. Адреса вида /tools/<имя>-calculator.
  Интересно: Upwork делает калькуляторы комиссий своих конкурентов (Fiverr, Toptal). Это ловит поисковые запросы по чужим брендам.

### 3.7 Что из этого мы можем построить честно из своих данных

| Семейство Upwork | Наш честный аналог | Из каких данных | Сервер |
|---|---|---|---|
| /freelance-jobs/<навык>/ | «<навык> jobs», живое число в title и description, «Load more», гид «как стать», 2 блока перелинковки | наши вакансии | без сервера |
| то же, но тип работы | «Freelance and contract <навык> jobs», «Part-time <навык> jobs» | поле типа занятости в вакансиях (если есть) | без сервера |
| /hire/<роль>/cost/ | «<роль> hourly rate» и «<роль> salary»: медиана и вилка, «по N вакансиям с указанной почасовой оплатой, обновлено <дата>» | вакансии, где работодатель сам написал ставку | без сервера |
| /hire/<роль>/job-description/ | «<роль> job description template» с кнопкой «скопировать» | наши гиды для работодателей + типичные навыки из вакансий | без сервера |
| /hire/<роль>/interview-questions/ | у нас уже есть вопросы для собеседования: связать их тройкой с зарплатой и шаблоном | есть | без сервера |
| /hire/<роль>/<страна>/, /us/<город>/ | «<роль> jobs in <город>» только там, где у нас ≥ 10-20 живых вакансий, чтобы не было пустых страниц | вакансии с местом | без сервера |
| /outcomes/<задача> | для работодателей «Hire for <задача>» (например «hire to build a website»), ведёт на гиды и шаблоны | гиды | без сервера |
| /tools/ | дополнить наши 34 инструмента калькуляторами, которых нет: Upwork Fee, Fiverr Fee, Cost of Vacancy, Freelance Rate, Freelance Tax (проверить, каких у нас ещё нет) | формулы | без сервера |
| /resources/ сравнения | «Best job search websites», «LinkedIn alternatives», «Upwork vs Fiverr for job seekers» с честным разбором | редакционная работа | без сервера |
| /hire/<роль>/ с карточками людей | НЕ делать: у нас нет исполнителей и отзывов | — | не наш бизнес |

Предупреждения по опыту Upwork:
- По выдаче поиска часть их городских страниц шаблонная («тонкая»). Делать страницы места только при достаточном числе вакансий.
- У Upwork одна и та же ставка Python в двух местах разная ($20–$45 и $20–$40). Нам считать цифру в одном месте и показывать везде одинаково, с датой и числом вакансий.

## 4. Функции, которые подходят доске вакансий без биржи

### 4.1 Подсказки по ставке и бюджету
- На странице роли: «How much does hiring a Python developer cost?» и 5 типовых проектов с ценой (https://www.upwork.com/hire/python-developers/, 14.11.2026).
- На главной: «Get insights into freelancer pricing — We'll calculate the average cost for freelancers with the skills you need» (https://www.upwork.com/, 14.11.2026).
- Сноска о методе: «This data represents typical hourly rate ranges of certain historical contracts worldwide» (https://www.upwork.com/hire/python-developers/cost/, 14.11.2026).
Нам: виджет «Сколько платят <роль>?» на главной и на страницах ролей, по нашим вакансиям, с честной сноской «по N вакансиям, где работодатель указал оплату».

### 4.2 Шаблоны и генератор описания вакансии
- Шаблоны /hire/<роль>/job-description/ (см. 3.3).
- «Job Post Generator powered by AI»: работодатель пишет 1-2 предложения, ИИ делает черновик (https://www.upwork.com/pricing/client, 14.11.2026).
- С лета 2025 при создании вакансии Upwork сразу оценивает «силу» описания и даёт советы (https://www.upwork.com/press/releases/upwork-updates-summer-2025-release, пресс-релиз от 23.07.2025, прочитано 14.11.2026).
Нам: генератор описания по шаблону прямо в браузере (без ИИ) + проверка «силы» описания по списку правил (есть ли зарплата, место, удалёнка, обязанности, навыки). Это без сервера. Вариант с ИИ требует сервера и ключа.

### 4.3 Знаки доверия (как Job Success и значки)
- Job Success Score: процент, обновляется ежедневно, считается по контрактам за 6, 12 и 24 месяца. 90%+ хорошо, ниже 79% плохо (https://support.upwork.com/hc/en-us/articles/38437362753171-What-is-a-Job-Success-Score, 14.11.2026).
- Значки исполнителей: Rising Talent, Top Rated (JSS ≥ 90%), Top Rated Plus, Expert-Vetted (верхний 1%, видят только клиенты Business Plus и Enterprise) (по выдаче поиска, https://support.upwork.com/hc/en-us/articles/211063568-Top-Rated-and-Rising-Talent и https://www.upwork.com/resources/talent-badges-explained, 14.11.2026; сами статьи не открывались).
- На странице тарифов: «ID-verified talent only», «Verified reviews and work history», «talent badges» (https://www.upwork.com/pricing/client, 14.11.2026).
Нам: людей мы не оцениваем, но можем честно оценивать вакансии и работодателей по своим данным. Примеры значков на вакансии: «Salary shown» (зарплата указана), «Direct from careers page» (взято с сайта работодателя), «New» (меньше 24 часов), «Still open, checked 1 h ago». У работодателя: «Actively hiring: 12 new jobs in 7 days», «Pays transparently: 80% of jobs show pay». Метод объяснить на отдельной странице. Без сервера.

### 4.4 Что показывают на странице вакансии
Upwork показывает: «Proposals: 50+», «Last viewed by client: 7 hours ago», «Interviewing: 2», «Invites sent», а о клиенте: дату регистрации, страну и местное время, потрачено «$3.3K», «15 hires», часы (см. 2.5).
Нам честно доступно: «Впервые замечена на сайте работодателя: дата», «Проверена: N минут назад», «Открыта N дней», «У этого работодателя N открытых вакансий у нас», города, ссылка на страницу карьеры, местное время офиса (если город известен), «похожие вакансии». Число откликов мы не знаем: не выдумывать.

### 4.5 Сохранённые поиски, оповещения, приложение
- Upwork отключил RSS с вакансиями после 20.08.2024 и предлагает вместо него сохранённые поиски, настройки уведомлений, письма-дайджесты (только для Rising Talent и Top Rated) и рекомендации (https://support.upwork.com/hc/en-us/articles/52052528243731-RSS-deprecation, 14.11.2026).
- Мгновенные оповещения о вакансиях только на платном Freelancer Plus и только если вы уже отправляли отклик; можно выбрать почту или приложение, фильтр «почасовая/фикс», минимальную ставку (https://support.upwork.com/hc/en-us/articles/36001273797907-Get-instant-job-alerts, 14.11.2026).
- Из-за этого есть платные сторонние сервисы оповещений по Upwork (WorkAlert for Upwork в App Store, Vollna, GigRadar) (по выдаче поиска, 14.11.2026).
- Фильтры поиска работы: уровень опыта, дата публикации, число откликов, история клиента; «Save jobs for later» (https://www.upwork.com/pricing/freelancer, 14.11.2026).
- Приложение: по справке Upwork «почти всё, что на компьютере», уведомления о приглашениях и сообщениях (по выдаче поиска, не проверено).
Нам: это главная возможность. Бесплатные RSS-ленты по навыку, роли, городу и компании Upwork закрыл, а мы можем отдавать их бесплатно, файлами, которые обновляются каждый час вместе с сайтом (без сервера). Сохранённые поиски и «избранные вакансии» можно хранить в браузере человека без аккаунта (без сервера). Письма-оповещения требуют сервера или стороннего сервиса.

### 4.6 ИИ-функции Upwork 2025–2026
- Uma («Mindful AI», теперь «AI work agent»). По пресс-релизу 23.07.2025 Uma «powering a majority of new client job posts». Летом 2025 добавлены «instant interviews» (Uma проводит собеседование по вопросам клиента и пишет сводку), видеовстречи со сводками и расшифровкой, умный поиск с подсказками, оценка «силы» вакансии (https://www.upwork.com/press/releases/upwork-updates-summer-2025-release, 14.11.2026).
- Весна 2026 (блог от 05.05.2026): сводки истории работ исполнителя, «Uma Recruiter shortlisting» (подборка лучших кандидатов за 6 часов, теперь и на бесплатном Basic), «Upwork app in ChatGPT», генератор договора прямо из видеовстречи, сводки рабочего дневника, а также «reimagined homepage» (главная показывает новые ИИ-роли и востребованные навыки) и новая навигация (https://www.upwork.com/blog/updates-spring-2026, 14.11.2026).
- На главной новый блок «Free AI project scoping» с вопросом «What's your top business priority?» (https://www.upwork.com/, 14.11.2026).
- Отдельного продукта под названием «AI proposal writer» на страницах Upwork я не нашёл (не проверено). В Freelancer Plus есть «proposal insights»: конкуренция, как ваша ставка соотносится с другими и с бюджетом клиента (https://www.upwork.com/pricing/freelancer, 14.11.2026).
Нам без сервера: раздел «новые ИИ-роли» на главной по нашим данным (какие названия ролей растут за месяц), мини-опрос «Какая у вас цель?» с переходом на нужные страницы. С сервером: ИИ-сопроводительное письмо к резюме, ИИ-генератор вакансии.

## 5. Деньги (только как идеи, цены со страниц Upwork)

Для исполнителей (https://www.upwork.com/pricing/freelancer, 14.11.2026):
- Basic $0 в месяц. Freelancer Plus $19.99 в месяц: 100 Connects в месяц, персональные оповещения о вакансиях, «proposal insights», 0% комиссии со своих клиентов, настройка профиля, безлимитный доступ к Uma.
- Connects: «виртуальные жетоны» для отклика на вакансию и для рекламы (поднятие отклика, значок доступности). Докупка $0.15 за штуку.
- Сколько Connects стоит один отклик: по сторонним сайтам от 2 до 16+, у популярных до 40 (по выдаче, сторонние источники противоречат друг другу, не проверено).
- Платная реклама себя: «Boost your proposal visibility», «Boost your profile», «Availability badge» (до +70% приглашений, по их словам).
- Комиссия с заработка исполнителя от 0% до 15%.
- Их цифры для продажи подписки: «Why 120,000+ freelancers choose Plus», «+40% More contracts», «+7% Higher earnings», «+28% More job invites».

Для нанимателей (https://www.upwork.com/pricing/client, 14.11.2026):
- Basic: 5% сбора с каждой выплаты (3% для части клиентов из США при оплате со счёта) + разовый сбор за начало контракта от $0.99 до $14.99.
- Business Plus: 10% сбора (8% со счёта в США), подборки кандидатов от ИИ, доступ к верхнему 1%, общий счёт команды, отсрочка оплаты 30 дней (только США), 60 приглашений на вакансию вместо 30, 15 личных сообщений в день вместо 5. Сбор за начало контракта нет, кроме фиксированных контрактов до $100 (до $4.99).
- Featured Job (выделенная вакансия): значок, верхние места в ленте подходящих исполнителей, показ в письмах Top Rated и Rising Talent, до 70 приглашений в день, «50% more proposals», можно бесплатно продлить ещё 2 раза (https://support.upwork.com/hc/en-us/articles/115010165067-Featured-Jobs-attract-top-talent и https://support.upwork.com/hc/en-us/articles/34866995283219-Featured-Job-Posts-Frequently-Asked-Question, 14.11.2026). Цена на страницах не указана: по выдаче поиска справка говорит, что цена зависит от спроса и видна при оплате; на форуме 2019-2020 годов называли $29.99 (не проверено, устарело).

Что из этого подходит нам:
- Выделенная вакансия для работодателя (как Featured Job): значок, место вверху страницы навыка, показ в RSS и рассылке. Оплата криптой. Пока заявок мало, можно вручную (без сервера); автоматически нужен сервер.
- Спонсор страницы навыка или города: «Хотите нанять Python-разработчика? Разместите вакансию» (вручную, без сервера).
- Платная подписка для соискателя на оповещения, как Freelancer Plus: не советую. Наше отличие как раз в том, что оповещения бесплатные, а у Upwork они платные.
- Connects, плата за отклик, комиссия с контракта, эскроу: не наш бизнес (мы не принимаем отклики, отклик идёт на сайт работодателя).

## 6. Что взять нам, по порядку

Отметки: «без сервера» = можно сделать на нынешнем статичном сайте; «нужен сервер» = когда включим сервер; «не наш бизнес» = не берём.
Что из этого у нас уже есть, я не проверял по сайту: сначала сверить, чтобы не делать дважды.

1. Бесплатные RSS-ленты вакансий по навыку, роли, городу и компании, обновляются каждый час вместе с сайтом. Upwork закрыл RSS в 2024 году, а оповещения у него платные ($19.99 в месяц). Повод для письма на сайты-списки и для ссылок. — без сервера
2. Карточка вакансии по образцу Upwork: тип оплаты и давность в одной строке («Hourly · Posted 2 h ago»), два факта с подписями (оплата / уровень или удалёнка), 3-6 тегов навыков, кнопка «Load more». — без сервера
3. Блок на странице вакансии из честных данных: «впервые замечена», «проверена N минут назад», «открыта N дней», «О работодателе» (сколько у нас открытых вакансий, города, ссылка на страницу карьеры, местное время), «Похожие вакансии». Без выдуманного числа откликов. — без сервера
4. Тройка страниц на каждую роль, связанная одним блоком «Resources to help you hire»: зарплата/ставка, шаблон описания вакансии, вопросы для собеседования. Интервью-вопросы и гиды у нас уже есть: добавить шаблон и связку. — без сервера
5. Страницы «<роль> hourly rate» и блок «Median hourly rate» на страницах навыков: только из вакансий, где ставка указана, с числом вакансий и датой. Одна цифра на весь сайт. — без сервера
6. Страницы «Freelance and contract <навык> jobs» (и part-time), если тип занятости есть в данных. — без сервера
7. Мега-меню: роль + пояснение в 3-5 слов + число открытых вакансий. Сильная внутренняя перелинковка. — без сервера
8. Главная по схеме Upwork: переключатель «Find a job / Hire», вкладки категорий с плитками «N open jobs», виджет «Сколько платят <роль>?», одна крупная цифра доверия («45,000+ jobs from employers' own careers pages, updated hourly»), мини-опрос «Какая у вас цель?». — без сервера
9. Дизайн-приёмы (см. 2.6): один акцентный цвет, почти чёрный текст, заголовки 500 с плотной разрядкой, шкала скруглений, светлые тонированные фоны блоков, большие скруглённые фото. — без сервера
10. Значки доверия на вакансиях и работодателях из своих данных («Salary shown», «Direct from careers page», «Actively hiring») и страница «как мы это считаем». — без сервера
11. Месяц и год в title страниц со списками вакансий («(November 2026)»), только там, где страница реально обновляется. — без сервера
12. Избранные вакансии и сохранённые поиски в браузере человека, без аккаунта. — без сервера
13. Страницы «<роль> jobs in <город>» только при достаточном числе вакансий. — без сервера
14. Новые калькуляторы к нашим 34: Upwork Fee, Fiverr Fee, Cost of Vacancy, Freelance Rate, Freelance Tax (каких нет). — без сервера
15. Разметка: JobPosting с настоящим работодателем (у Upwork там стоит сам Upwork и разметка задвоена), BreadcrumbList, CollectionPage на списках. — без сервера
16. Генератор описания вакансии по шаблону и проверка «силы» описания по правилам, в браузере. — без сервера; версия с ИИ — нужен сервер
17. Статьи-сравнения для соискателей: «Best job search websites», «LinkedIn alternatives», с датой и честным разбором. — без сервера
18. Выделенные вакансии для работодателей за крипту. — вручную без сервера, автоматически нужен сервер
19. Письма-оповещения и Telegram по навыкам. — нужен сервер (или сторонний сервис рассылки по RSS)
20. Кабинет работодателя, аккаунты соискателей, ИИ-сопроводительное письмо. — нужен сервер
21. Профили исполнителей, рейтинги и Job Success, Connects, плата за отклик, комиссия с контракта, эскроу, ИИ-собеседования, рабочий дневник. — не наш бизнес

## 7. Источники (все прочитаны 14.11.2026)

Страницы Upwork, открытые во встроенном браузере (обычный запрос получил 403):
- https://www.upwork.com/ — главная, меню, стили, подвал
- https://www.upwork.com/freelance-jobs/python/ — страница навыка для соискателя
- https://www.upwork.com/freelance-jobs/apply/Automation-Developer-for-Home-Health-Administrative-Workflows_~022121059344782235803/ — страница вакансии
- https://www.upwork.com/freelance-jobs/united-states/ — страница страны
- https://www.upwork.com/hire/python-developers/ — страница роли для нанимателя
- https://www.upwork.com/hire/python-developers/cost/ — страница стоимости
- https://www.upwork.com/hire/python-developers/job-description/ — шаблон вакансии
- https://www.upwork.com/pricing/client — тарифы нанимателей
- https://www.upwork.com/pricing/freelancer — тарифы исполнителей
- https://www.upwork.com/tools — бесплатные калькуляторы
- https://www.upwork.com/resources — статьи
- https://www.upwork.com/blog/updates-spring-2026 — обновления весны 2026
- https://www.upwork.com/press/releases/upwork-updates-summer-2025-release — пресс-релиз 23.07.2025
- https://www.upwork.com/about/brand/universal-design-primitives — принципы бренда
- https://support.upwork.com/hc/en-us/articles/38437362753171-What-is-a-Job-Success-Score
- https://support.upwork.com/hc/en-us/articles/115010165067-Featured-Jobs-attract-top-talent
- https://support.upwork.com/hc/en-us/articles/34866995283219-Featured-Job-Posts-Frequently-Asked-Question
- https://support.upwork.com/hc/en-us/articles/52052528243731-RSS-deprecation
- https://support.upwork.com/hc/en-us/articles/36001273797907-Get-instant-job-alerts

Только по выдаче поиска (сами страницы не открывались):
- Городские страницы: https://www.upwork.com/hire/media-buyers/us/new-york-ny/ , https://www.upwork.com/hire/new-york-freelancers/us/new-york-ny/ , https://www.upwork.com/hire/photo-editors/new-york-us/
- Старая статья о стоимости: https://www.upwork.com/hiring/for-clients/how-much-does-it-cost-to-hire-wordpress-developer/
- Значки: https://support.upwork.com/hc/en-us/articles/211063568-Top-Rated-and-Rising-Talent , https://www.upwork.com/resources/talent-badges-explained
- Цена Connects за отклик (сторонние): https://gigradar.io/blog/upwork-connects-cost-per-hire , https://snipework.com/answers/how-many-connects-do-upwork-proposals-cost
- Старая цена Featured Job $29.99 (форум): https://community.upwork.com/t5/Clients/Is-Upwork-s-featured-job-posting-upgrade-useful/m-p/697018
- Сторонние оповещения: https://apps.apple.com/us/app/id1632149723 (WorkAlert for Upwork)
- Ребрендинг: https://portorocha.com/upwork (2021, шрифт Neue Montreal + засечный Upwork Rza), https://www.upwork.com/about/brand/typography (один шрифт PP Upwork Neue Montreal, запасной Helvetica Neue), https://lbbonline.com/news/upwork-builds-for-the-future-of-work-with-new-global-design-system-and-visual-identity (система 2024 года от NOT Wieden+Kennedy)
