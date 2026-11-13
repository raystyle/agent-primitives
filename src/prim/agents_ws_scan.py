"""agents 工作台清点(v3.8.0;命运表保留裁定):工作台 = 节点 home + ~/repos/* 各 git 仓。
除 home 外每个本地仓对应一个 GitHub 项目仓(origin)。agents dev <机> <工作台> --kind <类> 起任意 agent。
跨机腿(批5c hc 化):hc 机册三台走 `hc exec --on`;机册外节点保持原 ssh 道(红线不动)。
"""
from __future__ import annotations
import os
import subprocess

from .addressing import _machine_labels
from .core import die, emit_ok, eprint
from .engines import exec_result, hc_exec_on

_SCAN_SH = (
    "for d in \"$HOME\" \"$HOME\"/repos/*/; do"
    " [ -d \"$d/.git\" ] || continue;"
    " u=$(git -C \"$d\" remote get-url origin 2>/dev/null || echo -);"
    " b=$(git -C \"$d\" branch --show-current 2>/dev/null || echo -);"
    " echo \"$d|$u|$b\";"
    " done"
)


def _run(argv: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", "timeout")


def scan(machine: str | None, g: dict) -> None:
    """agents workbenches [机]:列该节点工作台(home + ~/repos/* git 仓 + origin + 分支)。"""
    if machine in (None, "", "local"):
        home = os.path.expanduser("~")
        r = _run(["bash", "-lc", _SCAN_SH])
        rows = _parse(r.stdout)
        if not rows:  # win 本机无 bash 面:os 直扫
            rows = _scan_local(home)
    elif machine in _machine_labels():
        # hc 机册节点:hc exec --on 载扫描脚本(ssh 手搓退役)
        r = exec_result(hc_exec_on(machine, ["bash", "-c", _SCAN_SH], timeout=45))
        rows = _parse(r.stdout)
    else:
        # 机册外:原 ssh 道(机册三台外不改 ssh 行为,红线)
        from .runtimes import _machine_target
        r = _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                  _machine_target(machine), _SCAN_SH], timeout=45)
        rows = _parse(r.stdout)
    if g.get("json"):
        emit_ok({"status": "ok", "machine": machine or "local", "count": len(rows), "workbenches": rows})
        return
    print(f"WORKBENCH{' ' * 6} ORIGIN  BRANCH")
    for w in rows:
        tag = "(home)" if w["is_home"] else ""
        print(f"{w['dir']:<24} {w['origin']:<44} {w['branch']} {tag}")
    print(f"\n{len(rows)} 工作台;起 agent:agents dev {machine or 'local'} <工作台> --kind <claude|codex|grok|kimi>")


def _parse(out: str) -> list[dict]:
    rows = []
    for line in (out or "").splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        d, u, b = parts[0], parts[1], parts[2]
        # home 行 = 目录就是 $HOME 本体(无尾部仓名)
        is_home = d.rstrip("/").endswith("/repos/..") or d.rstrip("/") == "~" or not d.rstrip("/").split("/")[-1]
        rows.append({"dir": d, "origin": u, "branch": b, "is_home": is_home})
    return rows


def _repos_roots(home: str) -> list[str]:
    """repos 根探测:~/repos 优先,win 盘符
epos 次之(linux 主机 ssh 道恒 ~/repos)。"""
    roots = []
    hr = os.path.join(home, "repos")
    if os.path.isdir(hr):
        roots.append(hr)
    if os.name == "nt":
        for drv in "DEFGH":
            p = os.path.join(f"{drv}:" + os.sep, "repos")
            if os.path.isdir(p) and p not in roots:
                roots.append(p)
    return roots


def _scan_local(home: str) -> list[dict]:
    rows = []
    cands = [home]
    for root in _repos_roots(home):
        cands += [os.path.join(root, n) for n in os.listdir(root)]
    for d in cands:
        if not os.path.isdir(os.path.join(d, ".git")):
            continue
        u = subprocess.run(["git", "-C", d, "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=15).stdout.strip() or "-"
        b = subprocess.run(["git", "-C", d, "branch", "--show-current"],
                           capture_output=True, text=True, timeout=15).stdout.strip() or "-"
        rows.append({"dir": d, "origin": u, "branch": b, "is_home": d == home})
    return rows
