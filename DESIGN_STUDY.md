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
   on the right, a smaller page title. 📋 Still to do: applied filters as removable chips.
4. ✅ **Job page: the decision first.** The pay stated in the posting on a scale with the category median marked, then Apply and
   Save, then the facts.
5. ✅ **Company page:** a sticky bar of anchors with counts, fact tiles with a small label over the value, a lead written from
   the postings. 📋 Still to do: pay by role with the number of postings behind each figure.
6. ✅ **Hub pages: no row of five big numbers.** The figures are one mono line with their date and source. 📋 Still to do: the
   "Related" and "Compare with" runs as labelled rows (label left, links right, "More" last).
7. ✅ **Tools show a result at once** ("Show an example"). 📋 Still to do: a sub-navigation under the header on tool pages and the
   questions in two columns.
8. ✅ **Tools index: break the grid** (2026-11-13: three wide rows plus a ruled list with an example on the right). Two tools as wide rows with a working mini version, the rest as a ruled two-column list with
   a sample result on the right.
9. ✅ **Home pacing:** the second list of new jobs is gone; categories, roles, locations and companies share one tabbed block;
   the highest-paid list sits on a full-width dark band. 📋 Still to do: section headers with the heading left and one sentence
   plus the "all" link right.
10. 📋 **Two type sizes by purpose:** 36–40px section headings on pages that explain, 24–28px on pages that list.
11. ✅ **The board in the hero shows pay.** 📋 Still to do: tabs (Just posted, Highest paid, Remote).
12. ✅ **A line of provenance instead of badges and ratings:** "checked on … against employer career pages", linked to the method.
13. ✅ **Header:** six items (was eight). 📋 Still to do: menus under Jobs, Tools and Resources, and a search field with "/".
14. 📋 **Footer:** five short columns, then directory rows (by skill, by location, by category), then the stamp.

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
