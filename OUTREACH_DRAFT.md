# Письмо компаниям: черновик на утверждение владельцу (17 нояб. 2026)

Ничего не отправлено. Это текст и порядок действий; рассылка начнётся только после вашего «да» на текст.

## Зачем

На сайте вакансии 6 000+ компаний, и почти ни одна из них о нас не знает. Письмо говорит компании три вещи: её вакансии уже у нас,
страницу компании можно забрать бесплатно, а если нужно больше откликов — есть продвижение. Это главный способ получить первых
платящих работодателей (план на $1 млн, `REVENUE_PLAN_2027.md`).

## Кому и как

- **Кому:** компаниям, чьи вакансии уже на сайте. Только на общие адреса с их собственных сайтов (careers@, jobs@, recruiting@, talent@, hr@).
  Личные адреса сотрудников не собираем и на них не пишем.
- **Откуда:** с отдельного ящика, например hello@jobseveryhour.com, чтобы не рисковать репутацией support@ (с него уходят
  подтверждения почты и оповещения).
- **Сколько:** 50 писем в день первую неделю, потом до 100–150. Одна компания получает одно письмо и одно напоминание через 7 дней, не больше.
- **Отписка:** ссылка в каждом письме; отписавшимся не пишем никогда.
- **Законы:** в США такие деловые письма разрешены при настоящем отправителе, почтовом адресе и отписке (CAN-SPAM). В ЕС и Великобритании
  пишем только на общие корпоративные адреса и только по делу их вакансий.

## Что нужно до старта

1. Ваше «да» на текст ниже (или правки).
2. Цифра просмотров в письме: **пока без неё.** Я посчитал по обычному журналу сервера за 16 ноября (ничего нового о посетителях
   не записывается): страницы вакансий открыли 69 599 раз, но из них людьми только 94 раза (39 человек); остальное роботы
   (GPTBot 37 600, ClaudeBot 22 939, Amazonbot 8 921). На 6 000 компаний это ноль просмотров почти у каждой, такая цифра в письме
   работала бы против нас. Поэтому в первой волне письмо говорит только о числе вакансий компании на сайте. Строку о просмотрах
   включим, когда у компании наберётся хотя бы 50 открытий людьми за 14 дней. Считает это скрипт `views.py` (на сервере, по тому же журналу).
   Проверка 17 ноября: за 4 дня, что сайт на новом сервере, люди открыли страницы вакансий 290 раз (роботы 341 813 раз); больше всех у GitLab
   и Clera, по 11 открытий. Ни одна компания до 50 не дошла.
3. Почтовый адрес отправителя для подписи (требование CAN-SPAM): нужен реальный адрес или абонентский ящик.
4. Отдельный почтовый ящик hello@ и запись SPF/DKIM для него (сделаю, когда утвердите).

## Текст письма (английский, как будет отправлено)

**Subject:** Your {N} open jobs are listed on Jobs Every Hour

Hello,

{Company}'s {N} open jobs are listed on Jobs Every Hour (jobseveryhour.com). We read them from your own careers page every hour,
and every "Apply" button sends the candidate straight to your site. It costs you nothing, and you do not need to do anything.

{Only for a company with 50 or more opens by people in 14 days; left out in the first wave:} In the last 14 days your job pages were opened {V} times on our site.

Two things you can do, if you want:

1. Take over your company page, free: add your logo and a few lines about the company, list the places where you hire, and see
   how many people view each job and click Apply. It takes two minutes: {link to the company page}
2. Get more applicants for a role that is hard to fill: a boost puts the job above the others in its lists for 30 days, from $99,
   one payment, nothing renews.

If a job on the page is wrong or should come down, reply to this email and we will fix it the same day.

{Sender name}
Jobs Every Hour · jobseveryhour.com
{postal address}

You are receiving this once because your company's public job postings are listed on our site. Unsubscribe: {link}

## Напоминание через 7 дней (только тем, кто не ответил и не отписался)

**Subject:** Re: Your {N} open jobs are listed on Jobs Every Hour

Hello, a short follow-up: {Company}'s page on Jobs Every Hour is still unclaimed. Claiming it is free and takes two minutes:
{link}. If this is not for you, there is nothing to do, and we will not write again.

{Sender name}, Jobs Every Hour
Unsubscribe: {link}

## Что будет измеряться

Открытия писем не отслеживаем (без пикселей). Считаем только: сколько компаний забрали страницу, сколько купили продвижение,
сколько отписались. Если отписок больше 2% или есть жалобы на спам, рассылку останавливаем и меняем текст.
