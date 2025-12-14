# server.py
import os
from flask import Flask, request, jsonify, render_template_string

from graph_app import build_app

# 构建 LangGraph 应用（全局复用，避免每次请求都重新建图）
graph_app = build_app()

app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Coding Agent Playground</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.15);
      --border: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --error: #fca5a5;
      --success: #6ee7b7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #1d2537 0, #020617 60%, #000 100%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: stretch;
      justify-content: center;
      padding: 24px;
    }
    .shell {
      width: 100%;
      max-width: 1100px;
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.2fr);
      gap: 20px;
    }
    @media (max-width: 900px) {
      .shell {
        grid-template-columns: minmax(0, 1fr);
      }
    }
    .panel {
      background: linear-gradient(145deg, rgba(15,23,42,0.95), rgba(17,24,39,0.98));
      border-radius: 16px;
      border: 1px solid var(--border);
      padding: 18px 18px 16px;
      box-shadow: 0 18px 45px rgba(0,0,0,0.6);
    }
    .panel-header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 12px;
    }
    .panel-title {
      font-size: 1rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .panel-title span.dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 10px rgba(56,189,248, 0.8);
    }
    .panel-subtitle {
      font-size: 0.8rem;
      color: var(--muted);
    }
    .badge {
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--muted);
      background: radial-gradient(circle, rgba(56,189,248,0.16), transparent 65%);
    }

    label {
      display: block;
      font-size: 0.8rem;
      color: var(--muted);
      margin-bottom: 4px;
    }

    textarea {
      width: 100%;
      min-height: 180px;
      resize: vertical;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #020617;
      color: var(--text);
      padding: 10px 12px;
      font-size: 0.9rem;
      line-height: 1.4;
      outline: none;
      box-shadow: inset 0 0 0 1px rgba(15,23,42,0.8);
    }
    textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px rgba(56,189,248,0.5);
    }

    .preset-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 8px 0 10px;
    }
    .chip {
      font-size: 0.75rem;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--border);
      background: rgba(15,23,42,0.8);
      color: var(--muted);
      cursor: pointer;
    }
    .chip:hover {
      border-color: var(--accent);
      color: var(--accent);
    }

    .controls {
      margin-top: 10px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .btn {
      border-radius: 999px;
      padding: 7px 16px;
      border: none;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: transform 0.08s ease, box-shadow 0.08s ease, background 0.1s ease;
    }
    .btn-primary {
      background: linear-gradient(135deg, #38bdf8, #22c55e);
      color: #020617;
      box-shadow: 0 6px 18px rgba(34,197,94,0.4);
    }
    .btn-primary:hover {
      transform: translateY(-1px);
      box-shadow: 0 10px 28px rgba(34,197,94,0.55);
    }
    .btn-ghost {
      background: transparent;
      color: var(--muted);
    }
    .btn-ghost:hover {
      color: var(--accent);
    }
    .status {
      font-size: 0.8rem;
      color: var(--muted);
    }

    .output-box {
      background: #020617;
      border-radius: 10px;
      border: 1px solid var(--border);
      padding: 10px 12px;
      font-size: 0.82rem;
      line-height: 1.5;
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
    }

    .pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
    }
    .pill {
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 999px;
      border: 1px solid var(--border);
    }
    .pill.ok {
      color: var(--success);
      border-color: rgba(110,231,183,0.6);
      background: rgba(16,185,129,0.06);
    }
    .pill.fail {
      color: var(--error);
      border-color: rgba(248,113,113,0.6);
      background: rgba(248,113,113,0.06);
    }
    .pill.meta {
      color: var(--muted);
      background: rgba(15,23,42,0.9);
    }

    code.inline {
      padding: 2px 4px;
      border-radius: 4px;
      background: rgba(15,23,42,0.9);
      font-size: 0.8rem;
    }
  </style>
</head>
<body>
  <div class="shell">
    <!-- 左侧：任务输入 -->
    <section class="panel">
      <header class="panel-header">
        <div class="panel-title">
          <span class="dot"></span>
          <span>Coding Agent 任务输入</span>
        </div>
        <span class="badge">multi-agent · LangGraph</span>
      </header>

      <div>
        <label for="task-input">自然语言任务描述</label>
        <textarea id="task-input" placeholder="例如：构建一个“arXiv CS Daily”静态网站，包含首页、分类页、论文详情页，并实时从 arXiv API 拉取 CS 论文数据……"></textarea>

        <div class="preset-row">
          <button class="chip" type="button" onclick="fillPreset('arxiv')">填入 arXiv CS Daily 用例</button>
        </div>
        <!-- 新增开关行 -->
        <div style="margin-top:8px; display:flex; align-items:center; justify-content:space-between; gap:8px;">
          <label style="display:flex; align-items:center; gap:6px; font-size:0.8rem; color:var(--muted); cursor:pointer;">
            <input id="research-toggle" type="checkbox" style="accent-color:#38bdf8;">
            <span>启用 Researcher（web_search + web_fetch）</span>
          </label>
          <span style="font-size:0.75rem; color:var(--muted);">
            arXiv 建议关闭以保持稳定
          </span>
        </div>
        <div class="controls">
          <div class="status" id="status-text">空闲</div>
          <div style="display: flex; gap: 6px;">
            <button class="btn btn-ghost" type="button" onclick="clearTask()">清空</button>
            <button class="btn btn-primary" type="button" onclick="runTask()">
              运行任务
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 右侧：结果输出 -->
    <section class="panel">
      <header class="panel-header">
        <div class="panel-title">
          <span class="dot"></span>
          <span>Agent 运行结果</span>
        </div>
        <div class="panel-subtitle">显示 <code class="inline">tests_passed</code> 和中文 review</div>
      </header>

      <div class="pill-row" id="meta-row" style="display:none;">
        <span class="pill meta" id="iter-pill"></span>
        <span class="pill" id="tests-pill"></span>
      </div>

      <div class="output-box" id="output-box">
        这里会显示本次任务的评审结果（review）以及简单的测试状态。
      </div>
    </section>
  </div>

  <script>
    const statusText = document.getElementById('status-text');
    const outputBox = document.getElementById('output-box');
    const testsPill = document.getElementById('tests-pill');
    const iterPill = document.getElementById('iter-pill');
    const metaRow = document.getElementById('meta-row');

    function clearTask() {
      document.getElementById('task-input').value = '';
      statusText.textContent = '空闲';
      outputBox.textContent = '这里会显示本次任务的评审结果（review）以及简单的测试状态。';
      metaRow.style.display = 'none';
    }

    function fillPreset(type) {
      const textarea = document.getElementById('task-input');
      if (type === 'arxiv') {
        textarea.value = `Build an 'arXiv CS Daily' static website with:
- A homepage for domain-specific navigation by CS categories. In the demo only AI and AR categories are required. Each category may have 3 papers.
- Category pages listing daily papers with title/authors/abstract/date and real PDF links.
- Dedicated paper detail pages with citation blocks and a copy button.You MUST create a per-paper detail HTML page for each listed paper!!!
- Fetch real-time data from arXiv baseAPI (https://export.arxiv.org/api/query).
- You build a request by appending standard URL query parameters, e.g.:
{base}?search_query=...&start=...&max_results=...&sortBy=...&sortOrder=...
	1.	search_query
	•	Set to cat:<CATEGORY>
	•	Example: search_query=cat:cs.AI
	2.	sortBy
	•	Set to submittedDate (to get newest submissions)
	•	Example: sortBy=submittedDate
	3.	sortOrder
	•	Set to descending (newest first)
	•	Example: sortOrder=descending
	4.	max_results
	•	Set to 3 (return 3 entries)
	•	Example: max_results=3
	The response is Atom XML. Each paper is an <entry>.
	Response format
	•	The API returns Atom XML.
	•	Each paper is an <entry> element under <feed>.

For each <entry>, extract these fields
	1.	Title
	•	XML path: <entry><title>
	•	Normalize by trimming whitespace/newlines.
	2.	Abstract page URL (canonical arXiv link)
	•	XML path: <entry><id>
	•	This is typically an https://arxiv.org/abs/... URL.
	3.	PDF URL
	•	Inside <entry>, there are multiple <link> tags.
	•	Choose the link where attribute type="application/pdf".
	•	Often also has title="pdf".
	•	Rule: pdfUrl = first <link> with @type == "application/pdf"
Fallback (if no pdf link found)
	•	If you have absUrl like https://arxiv.org/abs/XXXX.XXXXXvN,
convert to PDF URL by:
	•	replace /abs/ → /pdf/
	•	append .pdf
	•	Example: https://arxiv.org/abs/2412.01234v2 → https://arxiv.org/pdf/2412.01234v2.pdf
	4.	Published / Updated time (optional but commonly useful)
	•	published: <entry><published>
	•	updated: <entry><updated>
	5.	Authors (optional but commonly useful)
	•	XML path: multiple <entry><author><name>
	•	Collect all <name> values into an array.
	6.	Abstract text (optional)
	•	XML path: <entry><summary>
	•	Trim whitespace/newlines.
Attention: you will meet CORS issues when fetching data from arXiv API directly in the browser. So you MUST search the data first and than write in demo frontend
Deliver a complete repo in workspace/.`;
      } 
    }

    async function runTask() {
  const task = document.getElementById('task-input').value.trim();
  if (!task) {
    alert('请先输入任务内容');
    return;
  }
  const enableResearch = document.getElementById('research-toggle').checked;

  statusText.textContent = '运行中…（可能需要等待一会儿）';
  statusText.style.color = '#e5e7eb';
  outputBox.textContent = 'Agent 正在执行任务，请稍候…';
  metaRow.style.display = 'none';

  try {
    const resp = await fetch('/api/run_task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, enable_research: enableResearch })
    });

    if (!resp.ok) {
      const txt = await resp.text();
      throw new Error('HTTP ' + resp.status + ': ' + txt);
    }

    const data = await resp.json();
    const passed = data.tests_passed;
    const review = data.review || '(无 review 内容)';
    const iter = data.iter;

    statusText.textContent = '已完成';
    statusText.style.color = '#6ee7b7';

    metaRow.style.display = 'flex';
    iterPill.textContent = typeof iter === 'number'
      ? ('迭代次数: ' + iter)
      : '迭代次数: N/A';

    if (passed === true) {
      testsPill.textContent = 'tests_passed: True';
      testsPill.className = 'pill ok';
    } else if (passed === false) {
      testsPill.textContent = 'tests_passed: False';
      testsPill.className = 'pill fail';
    } else {
      testsPill.textContent = 'tests_passed: N/A';
      testsPill.className = 'pill meta';
    }

    outputBox.textContent = review;
  } catch (err) {
    console.error(err);
    statusText.textContent = '出错';
    statusText.style.color = '#fca5a5';
    outputBox.textContent = '调用出错：' + err.message;
    metaRow.style.display = 'none';
  }
}
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML)


@app.route("/api/run_task", methods=["POST"])
def run_task():
    data = request.get_json(silent=True) or {}
    task = (data.get("task") or "").strip()
    if not task:
        return jsonify({"error": "task is required"}), 400

    # 从前端读取 enable_research（可能不存在，默认为 False）
    enable_research = bool(data.get("enable_research"))

    init_state = {
        "task": task,
        # 这里无论 True/False 都可以写上；researcher_node 自己看布尔值。
        "enable_research": enable_research,
    }

    result = graph_app.invoke(init_state)

    return jsonify({
        "tests_passed": result.get("tests_passed"),
        "review": result.get("review"),
        "iter": result.get("iter"),
    })


if __name__ == "__main__":
    # 默认监听 http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=5001, debug=True)