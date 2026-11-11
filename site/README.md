# Site

audit.betterbukidnon.org: React, TypeScript and Tailwind CSS, built with Vite. Not deployed yet.

```
cd site
npm install
npm run dev        # http://localhost:5173, reloads on every save
npm run build      # data, type check, then dist/
```

## Deploy

[`wrangler.jsonc`](wrangler.jsonc) names the Cloudflare project `audit-bukidnon` and serves `dist/`, with
`index.html` for every path that isn't a file. Build first, then deploy to one of the two:

```
npx wrangler deploy                                              # Workers
npx wrangler pages deploy dist --project-name audit-bukidnon     # Pages
```

For builds on push, set the root directory to `site` and the build command to `npm run build`
(Workers deploy command `npx wrangler deploy`; Pages output directory `dist`). `.node-version` pins
Node 24 for both (Vite 8 needs 20.19 or 22.12 and up). Pages skips
`wrangler.jsonc` (it has no `pages_build_output_dir`) and needs nothing more, because with no
`404.html` it already serves `index.html` for unknown paths.

## Data

`npm run dev` and `npm run build` first run [`scripts/build-data.mjs`](scripts/build-data.mjs), which
reads the CSVs in [`../data`](../data) and writes `public/data/` (not in git):

| File | Holds |
| --- | --- |
| `index.json` | Every government's summary per year (Home and Compare), the corrections, the list of downloads |
| `gov/<slug>.json` | One government: every figure and quote, each with its source (report URL, part, item, page) |
| `csv/` | The CSVs themselves, for the Data page's downloads |

The CSVs are the record ([docs/phase1-data.md](../docs/phase1-data.md)). The script only reshapes
them, and stops with an error if a report is missing something the site shows. To change a figure,
change the CSV (or `extract_phase1.py`), never the JSON.

## Code

| What | Where |
| --- | --- |
| Pages | `src/pages/`: Home, Government (`/<slug>`, `?cy=2023` for a year), Compare, About, DataPage |
| Shared parts | `src/components/`: verdict badge, source line, quotes, notes, KPI row |
| Every visible string, in `en`, `fil` and `ceb` | `src/strings.ts`. A key missing from `fil` or `ceb` fails the type check |
| Tokens (colors, fonts, page width) | `src/index.css`, as Tailwind theme values: `bg-paper`, `text-ink-3`, `font-hero`, `max-w-page` |
| Light and dark | `src/index.css` redefines the color tokens under `[data-theme='dark']`. The reader's choice is saved as `ar-theme`; until they choose, the device's setting decides. `index.html` sets it before the first paint, `src/theme.ts` after. Use a token, never a fixed color like `text-white`, or it won't change with the theme |
| Class lists used in several places | `src/ui.ts` |
| Routing | `src/router.tsx`, a small path router. In production the host must serve `index.html` for every path |

## Rules

- Keep the [data rules](../docs/data-rules.md): every figure links to its source, COA's words are
  quoted, years sit side by side, no scores or rankings, no names.
- Same identity as the other Better Bukidnon trackers (`../bukidnon-infra-projects`,
  `.claude/skills/design-system`): white paper, ink rules, the teal subnav band, Figtree, Inter and
  JetBrains Mono, square corners, `↗` for external links.
- Don't pair two classes that set the same thing (`cx(ui.sectionH, 'mb-0')`): Tailwind's stylesheet
  order decides which wins. Add a variant in `src/ui.ts` instead.
- The Filipino and Cebuano strings are first drafts until a native speaker reviews them.

## Checking

At 1366px and 390px wide (render the page in a 390px `<iframe>`; desktop Chrome won't go that
narrow): EN, FIL and CEB all switch, light and dark both read well, nothing scrolls sideways, and
the console shows no errors. A new color pair should pass WCAG AA (4.5:1) in both themes.
