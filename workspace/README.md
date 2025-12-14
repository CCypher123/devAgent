# arXiv CS Daily (static demo)

A small static website that shows the newest **3** arXiv papers for two CS categories:

- `cs.AI` (Artificial Intelligence)
- `cs.AR` (Hardware Architecture)

Because fetching from `https://export.arxiv.org/api/query` in a browser often hits CORS restrictions, this repo **pre-fetches** data and commits it as JSON + generated HTML.

## Pages

- `index.html` – homepage with category navigation + newest 3 papers per category
- `categories/cs.AI.html`, `categories/cs.AR.html` – category listings
- `papers/*.html` – **per-paper detail pages** (3 per category) with citation blocks + copy button

## Data source

- arXiv Atom API: `https://export.arxiv.org/api/query`

Queries used:

- `?search_query=cat:<CATEGORY>&sortBy=submittedDate&sortOrder=descending&max_results=3`

## Regenerate (optional)

Requirements: Node.js 18+ (for built-in `fetch`).

```bash
node scripts/fetch_arxiv.mjs
```

This will rewrite:

- `data/cs.AI.json`, `data/cs.AR.json`
- `categories/cs.AI.html`, `categories/cs.AR.html`
- `papers/cs.AI-1.html` ... `papers/cs.AR-3.html`
- `index.html`

## Serve locally

Any static server works. Example:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/index.html`.
