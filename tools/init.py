from tools.filesystem import write_file, read_file, list_dir
from tools.shell import run_shell
from tools.web_search import web_search
from tools.web_fetch import web_fetch

TOOLS = [write_file, read_file, list_dir, run_shell, web_search, web_fetch]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}