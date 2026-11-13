"""prim agents 拓扑面(批3R 拆出;批5c hc 化瘦形):mode / run / keys / shell / dev / trust

命运表落点:run/keys/shell 直通(hc send / hc keys / hc run);dev 重塑(起腿 hc 化,
blocked_after_start 判标库保留);split/tab/zoom/wt/sync 退役(归 mod GUI / hc machine,
stub 见 agents.py 注册表);trust 本体在 gating(判标库),按键腿 hc keys。
"""
from __future__ import annotations
import os
import sys

from .addressing import resolve, terms
from .agents_lifecycle import run_bg
from .engines import hc_run, s5_cmd, s5_is_wsl, wsl_path
from .flags import _val
from .gating import agents_trust, blocked_after_start, dismiss_block_hint
from .identity import caller_pane, host_label
from .runtime_ctx import die, emit_ok, eprint

# 四家 CLI 命令名(冷翻/起格用;hc 模板名同形)
CLI_CMD = {"claude": "claude", "codex": "codex", "kimi": "kimi", "grok": "grok"}


def _subprocess_run(cmd: list[str], **kw):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def shell(pos: list[str], g: dict):
    """agents shell <机> <仓路径>:hc run 无 argv = 该机 shell,--cwd 落仓(直通)。"""
    if len(pos) < 2:
        die("usage", "shell <机> <仓库路径>", rc=2)
    m, repo = pos[0], pos[1]
    argv = ["run", "--bg", "--no-notify", "--outlive-parent", "--cwd", repo]
    if m and m not in ("", "local"):
        argv += ["--on", m]
    r, addr = run_bg(argv)
    if r.returncode != 0 or not addr:
        eprint(f"agents shell: 开台失败({m} {repo}):{(r.stderr or r.stdout or '').strip()[:120]}")
        sys.exit(1)
    print(addr)
    sys.exit(0)


def dev(pos: list[str], g: dict):
    """agents dev <机> <仓路径> [--kind 类]:起 agent 于该仓(起腿 hc run;启动后阻塞检测保留)。"""
    if len(pos) < 2:
        die("usage", "dev <机> <仓库路径> [--kind 类]", rc=2)
    m, repo = pos[0], pos[1]
    kind = _val(pos, "--kind", "claude")
    if kind not in CLI_CMD:
        die("usage", f"kind「{kind}」不在四家面(claude/codex/grok/kimi)", rc=2)
    label = repo.replace("\\", "/").rstrip("/").split("/")[-1]
    # 编号 = 出生序号:该台该类型现役最大号 + 1,不复用(命名标准 2026-10-15 裁 2)
    import re as _re
    _pref = f"{label}-{kind}-"
    _seqs = [int(_mm.group(1)) for r0 in terms(refresh=True)
             if (r0.get("name") or "").startswith(_pref)
             and (_mm := _re.match(rf"^{_re.escape(_pref)}([0-9]{{1,2}})$", r0["name"]))]
    _seq = (max(_seqs) + 1) if _seqs else 1
    name = f"{_pref}{_seq}"
    argv = ["run", "--bg", "--name", name, "--cwd", repo]
    if m and m not in ("", "local"):
        argv += ["--on", m]
    argv += [CLI_CMD[kind]]
    r, addr = run_bg(argv)
    if r.returncode != 0 or not addr:
        eprint(f"agents dev: 起格失败({m} {repo}):{(r.stderr or r.stdout or '').strip()[:120]}")
        sys.exit(1)
    print(addr)
    eprint(f"agents dev: {name}({kind})已起 @{addr}")
    # 启动后阻塞检测(不是启动就不管 TUI 阻不阻塞)
    hit = blocked_after_start(m, addr, kind, wait_s=30)
    if hit:
        for line in dismiss_block_hint(hit):
            eprint(line)
        emit_ok({"status": "blocked", "pane": addr, "kind": kind, "marker": hit["marker"],
                 "cta": "人工放行(↓+Enter)或 --force 投递"})
        sys.exit(1)
    emit_ok({"status": "delivered", "pane": addr, "kind": kind})


def run(pos: list[str], g: dict):
    """agents run <id> <命令...>:hc send 贴进格回车(直通;pane run 壳退役)。"""
    if len(pos) < 2:
        die("usage", "run <id> <command...>(run a command in a pane)", rc=2)
    m, addr = resolve(pos[0])
    hc_run("send", addr, " ".join(pos[1:]), timeout=30)
    emit_ok({"status": "delivered", "target": pos[0], "command": " ".join(pos[1:])})


def keys(pos: list[str], g: dict):
    """agents keys <id> <键>...:hc keys 一次多发(直通;逐键循环退役)。"""
    if len(pos) < 2:
        die("usage", "keys <id> <键>...", rc=2)
    m, addr = resolve(pos[0])
    hc_run("keys", addr, *pos[1:], timeout=15)
    eprint(f"agents: 已发键 {' '.join(pos[1:])} → {m}:{addr.rsplit('/', 1)[-1]}")


def mode(pos: list[str], g: dict):
    """agents mode <dnd|away|online> [until]:presence 声明(s5 键覆盖写;prim 独有协议)。"""
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


def trust(pos: list[str], g: dict):
    """agents trust:信任屏放行(判标库在 gating;按键腿 hc keys 一次多发)。"""
    agents_trust(None)
