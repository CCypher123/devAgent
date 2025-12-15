# Multi-Agent Coding Agent 

This repository contains a **multi-agent Coding Agent** built with [LangGraph] and OpenAI models.  
Given a natural-language task description, the system generates a complete project under the `workspace/` directory.

---

## 1. Project Architecture

### 1.1 Dataflow

The system is implemented as a **LangGraph** state machine with the following nodes:

```text
START
  ↓
analyzer      → parse the natural language task and optionally produce a lightweight spec
  ↓
researcher    → optional: web search + web fetch to build an evidence_pack
  ↓
coder         → generate all project files into workspace/ using filesystem tools
  ↓
evaluator     → optional tests / static checks; may send state back to coder for a small number of fix iterations
  ↙      ↘
coder      reviewer
               ↓
              END
```

The orchestrator is the **graph itself** .

Flow control is handled via conditional edges and simple routing logic.

### 1.2 Agents

All agents use the same OpenAI model (configured via `OPENAI_MODEL`) but with different system prompts and tools.

#### analyzer

- Input: `task` (natural-language description).
- Output: a **lightweight spec** (e.g., project type, expected files, rough acceptance criteria).
- It does **not** call tools and is intentionally conservative to keep behavior stable.

#### researcher

- Tools: 
  - `web_search` – Tavily-based web search.
  - `web_fetch` – HTTP fetch + HTML-to-text extraction.
- Controlled by `enable_research` flag in the state:
  - If `enable_research = False` (default for demos): `researcher` is a NO-OP and simply passes through the state.
  - If `True`: 
    - Issues a small number of `web_search` and `web_fetch` calls,
    - Summarizes docs into an `evidence_pack` with `sources`, `notes`, `gotchas`, and `recommended_examples`.

For the course demos, **key API details (e.g., arXiv API usage)** are usually given directly in the task to prioritize stability; `researcher` is a “capability hook” that can be enabled when desired.

#### coder

- Tools:
  - `write_file` – create/overwrite files in `workspace/`.
  - `read_file` – read existing files.
  - `list_dir` – inspect directory structure.
  - `web_fetch` – (optionally) fetch raw API responses to embed into static output.
- Behavior:
  - Given `task` (and optionally `spec` / `evidence_pack` / previous `test_log`), generates a complete project under `workspace/`.
  - Uses a one-shot or few-shot loop of tool calls (with a cap on iterations).
  - Keeps a `written` set inside one run to avoid writing the same file twice in a single pass.

#### evaluator

- Tools:
  - `run_shell` – run shell commands inside `workspace/` (`python <file>.py`, etc.).
  - `list_dir`, `read_file` – used for simple structural checks.
- Behavior:
  - If `test_targets` is empty:
    - Marks `tests_passed = True`, `test_log = "no tests requested"` and returns.
  - If `test_targets` is non-empty:
    - Runs `python <target>` for each `.py` path listed.
    - Assembles logs and sets `tests_passed` accordingly.
  - Optionally, for **arxiv-specific** runs, a lightweight static check can be implemented, e.g.:
    - Ensure a `papers/` directory exists.
    - Ensure at least one `papers/*.html` file contains `citation-block` and `copy-btn`.

Routing:

- If `tests_passed == False` and `iter < MAX_FIX_ITERS`:
  - Route back to `coder` for a fix iteration.
- Otherwise:
  - Route to `reviewer`.

#### reviewer

- Tools:
  - `list_dir` – see the final structure of `workspace/`.
- Behavior:
  - Summarizes:
    - Whether the spec/acceptance criteria appear satisfied.
    - Project structure and readability.
    - Test results (`tests_passed` / `test_log`).
    - 2–4 concrete improvement suggestions.
  - Output is a  review stored in `state.review`, which is displayed in the and Web UI.

---

## 2. Tools

All tools are registered in `tools/init.py` and accessed via `TOOLS_BY_NAME`:

- Filesystem:
  - `write_file(path, content)` – write file relative to `workspace/`.
  - `read_file(path)` – read text content.
  - `list_dir(path)` – list directory contents.
- Shell:
  - `run_shell(cmd, timeout_s)` – run shell commands inside `workspace/`.
- Web:
  - `web_fetch(url, timeout_s, max_chars)` – HTTP GET, sanitize HTML with BeautifulSoup, return JSON with `url`, `status`, `text`.
  - `web_search(query, max_results)` – Tavily search, normalized to:
    - `[{ "title": ..., "url": ..., "snippet": ... }, ...]`.

---

## 3. Setup Instructions

### 3.1 Python environment

Use Python 3.10 (recommended) and install dependencies:

```bash
pip install -r requirements.txt
```

### 3.2 Environment variables

Create a `properties.env` file at the project root.

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.2
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=devAgent
TAVILY_API_KEY=
```

The agents load this file via:

```python
from dotenv import load_dotenv
load_dotenv("properties.env")
```

---

## 4. Running the System

### Running with the Web UI

There is a simple Flask-based Web UI for interactive usage.

Start the server:

```bash
python server.py
```

Open in a browser:

- http://127.0.0.1:5001

The UI provides:

- A large text area for the natural language **task description**.
- A chips to auto-fill the course test task:
  - “arXiv CS Daily”
- A toggle: **“Enable Researcher”**
  - Off (recommended for demos): `enable_research=False`.
  - On: `enable_research=True`, allowing the `researcher` node to call Tavily and fetch docs.
- A “Run Task” button, which posts to `/api/run_task` and shows:
  - `tests_passed` (as colored pill: green/red/gray).
  - `iter` (number of iterations).
  - The final Chinese `review` text.

---

## 5. Example Scenario

### Example : arXiv CS Daily

1. Run `python server.py`.
2. Open `http://127.0.0.1:5000`.
3. Click the “arXiv CS Daily” preset chip; you will see a task like:

   ```text
   Build an 'arXiv CS Daily' static website with:
   - A homepage for domain-specific navigation by CS categories.
   - Category pages listing daily papers with title/authors/abstract/date and real PDF links.
   - Dedicated paper detail pages with citation blocks and a copy button.
   - Fetch real-time data from arXiv API (https://export.arxiv.org/api/query).
   Deliver a complete repo in workspace/.
   ```

4. Leave “Enable Researcher” off (for a stable run) and click **Run Task**.
5. After the graph finishes:
   - `tests_passed` should be `True` (no explicit tests requested for the static site).
   - `review` will summarize whether the generated site satisfies the arXiv requirements.
   - Generated site structure (example):

     ```text
     workspace/
       index.html              # homepage with navigation to AI / AR
       categories/
         ai.html               # AI category listing
         ar.html               # AR category listing
       papers/
         <paper-id-1>.html     # per-paper detail pages, with citation blocks
         <paper-id-2>.html
         ...
       assets/
         style.css
         script.js             # copy-to-clipboard for citation blocks
     ```

6. Open `workspace/index.html` in a browser to inspect the result.

