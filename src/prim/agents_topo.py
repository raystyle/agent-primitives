"""prim agents 拓扑面(批3R 自 cli 拆出):ws / shell / dev / split / tab / zoom /
run / keys / mode / wt / trust / sync(desks 别名期共用实现点,ADR-0007 软拆)"""
from __future__ import annotations
import os
import sys

from . import runtime_ctx
from .addressing import _agents_of, _machine_labels, resolve, resolve_tab
from .engines import _json_field, herdr_run, s5_cmd, s5_is_wsl, wsl_path
from .flags import _val
from .gating import agents_trust, blocked_after_start, dismiss_block_hint
from .identity import caller_pane, host_label
from .runtime_ctx import die, emit_ok, eprint


def _subprocess_run(cmd: list[str], **kw):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def ws(pos: list[str], g: dict):
    # agents ws <label> [--cwd DIR] [--machine 机] | ws list [机] | ws close <台id> [机]
    sub = pos[0] if pos else "list"
    rest = pos[1:]
    if sub == "list":
        m = rest[0] if rest else ""
        if m and m not in _machine_labels() and m != "local":
            eprint(f"agents: 「{m}」不在册,本机列举(--machine 语义收主机标签;desk ws list 无参 = 本机)")
        r = herdr_run(None if m in ("", "local") else m, "workspace", "list")
        print(r.stdout or r.stderr)
    elif sub == "close":
        if not rest:
            die("usage", "ws close <台id> [机]", rc=2)
        m = rest[1] if len(rest) > 1 else ""
        r = herdr_run(None if m in ("", "local") else m, "workspace", "close", rest[0])
        print(r.stdout or r.stderr)
    else:
        cwd = _val(rest, "--cwd", "")
        m = _val(rest, "--machine", "")
        args = ["workspace", "create", "--label", sub]
        if cwd:
            args += ["--cwd", cwd]
        r = herdr_run(None if m in ("", "local") else m, *args)
        pid = _json_field(r.stdout, "root_pane", "pane_id")
        print(r.stdout or r.stderr)
        if pid:
            eprint(f"agents: 台建 {sub}(root={pid})")


def shell(pos: list[str], g: dict):
    # agents shell <机> <仓绝对路径或仓名>:开该机该仓工作台 shell,回 root pane id
    if len(pos) < 2:
        die("usage", "shell <机> <仓库路径>", rc=2)
    m, repo = pos[0], pos[1]
    label = repo.rstrip("/").split("/")[-1]
    r = herdr_run(m, "workspace", "create", "--label", label, "--cwd", repo)
    pid = _json_field(r.stdout, "root_pane", "pane_id")
    print(pid or (r.stdout or r.stderr))
    sys.exit(0 if pid else 1)


def dev(pos: list[str], g: dict):
    # agents dev <机> <仓库> [--kind 类]:开台并起 agent(名 = 仓名)
    if len(pos) < 2:
        die("usage", "dev <机> <仓库路径> [--kind 类]", rc=2)
    m, repo = pos[0], pos[1]
    kind = _val(pos, "--kind", "claude")
    label = repo.rstrip("/").split("/")[-1]
    r = herdr_run(m, "workspace", "create", "--label", label, "--cwd", repo)
    pid = _json_field(r.stdout, "root_pane", "pane_id")
    if not pid:
        eprint(f"agents dev: 台建失败({m} {repo}):{(r.stderr or r.stdout).strip()[:120]}")
        sys.exit(1)
    r2 = herdr_run(m, "agent", "start", label, "--kind", kind, "--pane", pid)
    print(pid)
    eprint((r2.stdout or r2.stderr).strip()[:200])
    # 启动后阻塞检测(用户令:不是启动就不管 TUI 阻不阻塞)
    hit = blocked_after_start(m, pid, kind, wait_s=30)
    if hit:
        for line in dismiss_block_hint(hit):
            eprint(line)
        emit_ok({"status": "blocked", "pane": pid, "kind": kind, "marker": hit["marker"],
                 "cta": "人工放行(↓+Enter)或 --force 投递"})
        sys.exit(1)


def split(pos: list[str], g: dict):
    # agents split <id> [--direction right|down]
    if not pos:
        die("usage", "split <id> [--direction right|down]", rc=2)
    m, pane = resolve(pos[0])
    d = _val(pos, "--direction", "right")
    r = herdr_run(None if m in ("", "local") else m, "pane", "split", pane, "--direction", d)
    print(r.stdout or r.stderr)
    sys.exit(r.returncode)


def tab(pos: list[str], g: dict):
    # agents tab list [机] | create <机> [--label 名] | close <机:tabid>
    sub = pos[0] if pos else "list"
    rest = pos[1:]
    if sub == "list":
        m = rest[0] if rest else ""
        if m and m not in _machine_labels() and m != "local":
            eprint(f"agents: 「{m}」不在册,本机列举(--machine 语义收主机标签;desk ws list 无参 = 本机)")
        r = herdr_run(None if m in ("", "local") else m, "tab", "list")
        print(r.stdout or r.stderr)
    elif sub == "create":
        if not rest:
            die("usage", "tab create <机> [--label 名]", rc=2)
        m = rest[0]
        args = ["tab", "create"] + rest[1:]
        if "--workspace" not in rest[1:]:
            args += ["--workspace", m] if False else []
        r = herdr_run(m, *args)
        print(r.stdout or r.stderr)
    elif sub == "close":
        if not rest:
            die("usage", "tab close <机:tabid>", rc=2)
        m, tid = resolve_tab(rest[0])
        r = herdr_run(m, "tab", "close", tid)
        print(r.stdout or r.stderr)
    else:
        die("usage", "tab list|create|close", rc=2)


def zoom(pos: list[str], g: dict):
    if not pos:
        die("usage", "zoom <id>", rc=2)
    m, pane = resolve(pos[0])
    r = herdr_run(None if m in ("", "local") else m, "pane", "zoom", pane)
    print(r.stdout or r.stderr)
    sys.exit(r.returncode)


def run(pos: list[str], g: dict):
    # agents run <id> <命令...>(格内跑命令;herdr pane run 原语壳)
    if len(pos) < 2:
        die("usage", "run <id> <command...>(run a command in a pane)", rc=2)
    target = pos[0]
    m, pane = (target.split(":", 1) + [""])[:2] if ":" in target else ("local", target)
    herdr_run(None if m in ("", "local") else m, "pane", "run", pane, *pos[1:])
    emit_ok({"status": "delivered", "target": target, "command": " ".join(pos[1:])})


def keys(pos: list[str], g: dict):
    # agents keys <id> <键>...:send-keys 串(本机优先;跨机机: 形直发)
    if len(pos) < 2:
        die("usage", "keys <id> <键>...", rc=2)
    target = pos[0]
    if ":" in target:
        m, pane = target.split(":", 1)[0], target.split(":", 1)[1]
    else:
        from .addressing import _find_by_name
        hit = _find_by_name("", target)
        m, pane = (hit or ("local", target))
    for k in pos[1:]:
        herdr_run(None if m in ("", "local") else m, "agent", "send-keys", pane, k)
    eprint(f"agents: 已发键 {' '.join(pos[1:])} → {m}:{pane}")


def mode(pos: list[str], g: dict):
    # agents mode <dnd|away|online> [until](本机 presence 声明,shares 键覆盖写)
    if not pos or pos[0] not in ("dnd", "away", "online"):
        die("usage", "mode <dnd|away|online> [until=ISO时刻]", rc=2)
    import tempfile
    modearg = pos[0]
    until = _val(pos, "until", pos[1] if len(pos) > 1 else "")
    pane = caller_pane()
    key = f"share/presence/{host_label()}/{pane}"
    tmp = os.path.join(tempfile.gettempdir(), f"prim-presence-{pane.replace(':', '_')}")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"mode={modearg}\nuntil={until}\n")
    r = _subprocess_run(s5_cmd() + ["put", wsl_path(tmp) if s5_is_wsl() else tmp, key])
    try:
        os.remove(tmp)
    except OSError:
        pass
    if r.returncode == 0:
        print(f"agents: presence={modearg}{' until=' + until if until else ''}(key={key})")
    else:
        die("engine_fail", f"presence 写败:{(r.stderr or '').strip()[:100]}", rc=1)


def wt(pos: list[str], g: dict):
    # agents wt [机] [--title 名]:总台本窗开 tab 显示该机 herdr 视图
    # (wt 是显示面:本窗 = -w 0;在册机走 ssh -t;win 专属动词)
    if os.name != "nt":
        die("usage", "wt 动词为 Windows Terminal 专属;linux/macos 用 herdr 本体", rc=2)
    target = pos[0] if pos else "local"
    title = _val(pos, "--title", "")
    if target in ("", "local"):
        args = ["wt", "-w", "0", "new-tab", "--title", title or "herdr", "herdr"]
    elif target in _machine_labels():
        args = ["wt", "-w", "0", "new-tab", "--title", title or target, "ssh", "-t", target, "herdr"]
    else:
        die("usage", "wt [机] [--title 名](本窗开 tab 显示该机 herdr;机表 = agents machines)", rc=2)
    r = _subprocess_run(args)
    ok = r.returncode == 0
    print(f"agents: wt tab 已开({target},本窗)" if ok else f"agents: wt 开败:{(r.stderr or r.stdout).strip()[:80]}")
    emit_ok({"status": "delivered" if ok else "engine_fail", "view": target})
    if not ok:
        sys.exit(1)


def trust(pos: list[str], g: dict):
    # 信任屏放行:全机 blocked/unknown 格扫屏按键(判标库 shell v2.8 同源)
    agents_trust(None)


def sync(pos: list[str], g: dict):
    # agents sync [机]:mesh 补注册(每端跑一次,把本机 server 注册进对端机册)
    m = pos[0] if pos else ""
    r = herdr_run(None if m in ("", "local") else m, "machine", "list", "--json")
    print(r.stdout or r.stderr)
    eprint("agents sync: 机册注册面 = 各端互注册;新端走 G011 第 8 步 machine add")
