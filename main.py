import os
from graph_app import build_app

if __name__ == "__main__":
    os.makedirs("workspace", exist_ok=True)

    app = build_app()

    # 任务 A：你的作业 test case（arXiv CS Daily）
    arxiv_task = """
Build an 'arXiv CS Daily' static website with:
- A homepage for domain-specific navigation by CS categories. In the demo only AI and AR categories are required. Each category may have 3 papers.
- Category pages listing daily papers with title/authors/abstract/date and real PDF links.
- Dedicated paper detail pages with citation blocks and a copy button.
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
	•	Set to 5 (return 5 entries)
	•	Example: max_results=5
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
Deliver a complete repo in workspace/.
"""

    # 任务 B：第二个任务（用来证明通用性，强烈建议你保留）
    portfolio_task = """
Build a simple personal portfolio static website:
- index.html: about me + links
- projects.html: list 3 projects with descriptions
- contact.html: email + social links
No external data. Deliver in workspace/.
"""

    init_state = {"task": arxiv_task}  # 改成 portfolio_task 就能证明通用性
    result = app.invoke(init_state
                        ,config={"recursion_limit": 100})

    print("=== DONE ===")
    print("Tests passed:", result.get("tests_passed"))
    print("Review:\n", result.get("review", ""))