# Design study: what the best sites do that we did not (2026-11-13)

Asked by the owner: "look at how the biggest sites do design, not only job sites; I am not talking about colours".
22 sites were opened at desktop width and three job sites at phone width: Stripe, Linear, Vercel, Notion, Gologin, Coinbase,
Kraken, Phantom, Uniswap, Indeed, LinkedIn (guest pages), Glassdoor, Wellfound, Levels.fyi, Welcome to the Jungle, YC jobs,
RemoteOK, Wise, NerdWallet, GitHub. Nothing is copied from them; these are patterns.

## The changes, in order of effect (✅ done, 📋 open)

1. ✅ **Home hero: less pitch, more tool.** One mono line of facts above the headline, a short paragraph, a two-field search
   (what, where), one row of links. Indeed's home is one screen with a two-field search; Uniswap puts the working form in the hero.
2. ✅ **Job rows in fixed columns:** logo, title with company and place, pay (mono, right-aligned), tags, age. Pay lines up down
   the list; a faint dash holds the column when pay is not stated. Levels.fyi and RemoteOK keep pay, tags and age in columns.
3. ✅ **Search page: filters in one row on top**, the less used ones under "More filters", the list on the left and a wide preview
   on the right, a smaller page title. ✅ Applied filters are removable chips above the list, with "Clear all" (2026-11-13).
4. ✅ **Job page: the decision first.** The pay stated in the posting on a scale with the category median marked, then Apply and
   Save, then the facts.
5. ✅ **Company page:** a sticky bar of anchors with counts, fact tiles with a small label over the value, a lead written from
   the postings. ✅ Pay by field with the number of postings behind each figure (2026-11-13).
6. ✅ **Hub pages: no row of five big numbers.** The figures are one mono line with their date and source. ✅ "Related", "Compare with" and similar
   runs are labelled rows (label left, links right, "More" last) (2026-11-14).
7. ✅ **Tools show a result at once** ("Show an example"). ✅ Sub-navigation row on tool pages (2026-11-13). ✅ The questions in two columns (2026-11-14).
8. ✅ **Tools index: break the grid** (2026-11-13: three wide rows plus a ruled list with an example on the right). Two tools as wide rows with a working mini version, the rest as a ruled two-column list with
   a sample result on the right.
9. ✅ **Home pacing:** the second list of new jobs is gone; categories, roles, locations and companies share one tabbed block;
   the highest-paid list sits on a full-width dark band. ✅ Section headers with the heading left, one plain sentence beside it and the "all" link right (2026-11-14, five home sections; `section(..., sub=)`).
10. ✅ **Two type sizes by purpose:** 28–36px section headings on pages that explain (pages with the "On this page" list, guides), 24–32px on pages that list (2026-11-15).
11. ✅ **The board in the hero shows pay**, and its tabs (Latest, Remote, With salary, Entry-level) swap the list in place (2026-11-14).
12. ✅ **A line of provenance instead of badges and ratings:** "checked on … against employer career pages", linked to the method.
13. ✅ **Header:** six items (was eight). ✅ Menus under Resume, Tools and Pricing (2026-11-14): a panel with a line of plain text per link on wide screens, the links under each item in the phone menu; built by `site.js`, so the 49,000 pages carry no extra bytes. ✅ "/" puts the cursor in the search box.
14. 📋 **Footer:** five short columns, then directory rows (by skill, by location, by category), then the stamp. Deferred: the rows would add about 1 KB to each of 49,000 pages (about 50 MB) while the site is at 911 of 950 MiB; after the server.

## How job sites lay things out (for item 3 and 5)

- Search: Indeed and Glassdoor use two fields in one bar; filters are a row of small dropdown chips; the list is about 410px wide
  with a sticky detail pane beside it. On phones the chips scroll sideways and the pane disappears.
- A result row: title first (18px), then company and place; pay with its source; a bookmark at the right. Levels.fyi and Wellfound
  group rows by company.
- Job detail: title, company, place, pay, Apply and Save are always visible; the description follows.
- Company page: tabs with counts, fact tiles, salaries by role with sample sizes.

## What they avoid

Identical card grids (they use product fragments, tables and ruled lists), a pill badge over the headline, four big numbers,
sticker shadows and blobs, centred symmetry everywhere, filler copy, empty states (tools open with working numbers).

## Small motion worth having

A sticky header with a blur behind it; sticky detail pane and sub-navigation; hover as a tint or a 2px rule, never a lift;
tabs without scripts; "/" focuses search; chips that scroll sideways on phones.

## dLocal and Ashby (the owner, 17 Nov 2026: "look, especially at dlocal: the design is great, a lot can be taken for different pages")

Looked at on 17 Nov 2026 at 1440 px: dlocal.com (home) and ashbyhq.com (home). What to take is the way the page is built, in our
own colours and type (ink, paper, one green; Schibsted Grotesk and Public Sans). Not their blue, pictures, wording or logo.

What makes dLocal read as expensive:
1. **A framed canvas.** The hero and the big bands are panels with a large corner radius (about 24 px), set in from the edges of
   the window, instead of full-width stripes. The page reads as a few large objects, not a long sheet.
2. **A label above every section title.** A small pill ("Solutions", "Coverage") says what the section is before the headline.
3. **Two-weight headlines.** The headline is set light (weight 400) and the two or three words that carry the meaning are bold:
   "Flexible **payment solutions** for every need". Size 40 px for sections, 70 px for the hero, letter-spacing about -0.05em.
4. **One sentence of numbers.** "In 2025 dLocal processed $41 billion" as a headline, then four figures in a row under it. Our own
   figures are stronger than theirs for this: open jobs, companies, checked every hour, new in three days.
5. **Section header in three parts:** headline on the left, one or two lines of text in the middle, one pill button on the right.
6. **Pill buttons with an arrow in a circle** for the one action of a block; text links with an arrow for the rest.
7. **Rows that open** (icon, name, plus sign) for a list of products, one of them open with its text and picture.
8. **Cards with a figure on glass:** a picture card for a region with three small tiles of numbers on it and one link.
9. **A strip of customer logos** right under the hero. We have the logos of the companies whose jobs we list.
10. **A lot of air:** 120 to 160 px between sections, short lines of text, nothing touching anything.

What Ashby adds: a one-line announcement pill above the headline; the headline in near-black on white with nothing else; a grid of
customer logos in grey; product tabs under the hero that switch one large screenshot; one customer quote with a name and a photo
(we have no customers to quote yet: leave that out, never invent one).

Where each goes on our site (plan, PLAN_RU.md): the home page, /post-a-job/, /pricing/, /plus/, the account's first screen and its
overview, the tools hub, /about/, then the section titles of every page family (label + two-weight headline are one change in
`section()`).
