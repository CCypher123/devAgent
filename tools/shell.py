import os,json
import subprocess
from pydantic import BaseModel, Field
from langchain.tools import tool


class RunShellArgs(BaseModel):
    cmd: str = Field(description="Shell command to run inside workspace/")
    timeout_s: int = Field(default=30, ge=1, le=120)


@tool(args_schema=RunShellArgs)
def run_shell(cmd: str, timeout_s: int = 30) -> str:
    """Run a shell command inside the sandboxed workspace/ directory.
        Returns JSON with cmd, cwd, returncode, and output.
    """
    workdir = os.path.abspath("workspace")
    os.makedirs(workdir, exist_ok=True)

    blocked = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(b in cmd for b in blocked):
        raise ValueError("Blocked dangerous command")

    p = subprocess.run(
        cmd,
        cwd=workdir,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_s,
        text=True,
    )

    payload = {
        "cmd": cmd,
        "cwd": workdir,
        "returncode": p.returncode,
        "output": (p.stdout or "")[-8000:],
    }
    return json.dumps(payload, ensure_ascii=False)