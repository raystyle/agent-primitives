"""prim agents 视图面(批3R 拆出;批5c hc 化):agents_view(消息面表)/ desk_view(拓扑视图)
与 desks 域入口(CONTRACT-v2:view/start/close 三动词;split/tab/zoom/wt 退役 → mod GUI)。

视图数据 = hc ls --json 一发(terminals 全机 machine/t7 形);空格异常态告警保留
(pane 须有 agent;TUI 特征豁免)。desks view = 树形兜底(窗台/tab 线索 = where 字段)。
"""
from __future__ import annotations
import json
import os
import sys

from . import runtime_ctx
from .addressing import _agents_of, _machine_labels, terms
from .engines import hc_run
from .flags import parse, setup
from .manual import manual
from .runtime_ctx import die, eprint, emit_ok, guard

# 自制 TUI 屏面判标(非 agent 但有活跃程序,不是空壳)
TUI_MARKERS: tuple[str, ...] = (
    "数据链路", "  #  Help", "q 退出", "q quit", "│ File │", "NCURSES",
)


def _is_tui_pane(addr: str) -> bool:
    """空 pane 再判:屏面有 TUI 特征 = 自制监控/操作台,非异常态。"""
    r = hc_run("read", addr, "--lines", "20", timeout=10)
    tail = "\n".join((r.stdout or "").splitlines()[-20:])
    return any(mk in tail for mk in TUI_MARKERS)


def agents_view(machine: str | None):
    """消息面 agent 表:HOST NAME PANE STATUS KIND CWD;空 pane 异常态告警(hc ls 过滤)。"""
    rows = _agents_of(machine or None)
    header = f"{'HOST':<12} {'NAME':<12} {'PANE':<10} {'STATUS':<8} {'KIND':<7} CWD"
    if machine not in (None, "", "local"):
        for a in rows:
            print(f"{a.get('name') or '-':<12} {a.get('pane_id',''):<10} {a.get('agent_status',''):<8} {a.get('cwd','')}")
        return
    print(header)
    for a in rows:
        print(f"{a['machine']:<12} {(a.get('name') or '-'):<12} {a.get('pane_id',''):<10} "
              f"{a.get('agent_status',''):<8} {(a.get('agent') or '-'):<7} {a.get('cwd','')}")
    # 空格异常态(仅 live;finished = 正常退场;shell 前景再判 TUI 豁免)
    strays = [r for r in terms()
              if r["state"] == "live" and not r.get("agent")
              and (r.get("app") or "").lower() in _shell_like()]
    strays = [s for s in strays if not _is_tui_pane(s["hc_address"])]
    if strays:
        eprint(f"agents: ⚠ 空 pane {len(strays)} 格(异常态:pane 须有 agent):")
        for p in strays:
            eprint(f"  {p['hc_address']} cwd={p.get('cwd')}(agents close {p['hc_address']} 或 agents dev 补 agent)")


def _shell_like() -> set[str]:
    return {"bash", "zsh", "sh", "fish", "nu", "pwsh", "powershell", "powershell.exe",
            "cmd", "cmd.exe", "wsl", "wsl.exe"}


def desk_view(machine: str | None):
    """desks view:拓扑视图兜底(树形呈现主力 = mod GUI,ADR-0003)。
    数据 = hc ls(where 字段带 工作区 / tab 线索);▍ 焦点不可判(hc 无 focus 面)即不标。"""
    rows = terms()
    if machine not in (None, "", "local"):
        rows = [r for r in rows if r["machine"] == machine]
    lines: list[str] = []
    json_rows: list[dict] = []
    for r in rows:
        where = r.get("title") or ""
        lines.append(f"{'' if r['machine'] == 'local' else r['machine'] + ':'}{r.get('pane_id',''):<10}"
                     f"{(r.get('agent') or '-'):<7}{r.get('agent_status') or '?':<8}{where[:38]}")
        json_rows.append({"machine": r["machine"], "pane": r["pane_id"], "hc_address": r["hc_address"],
                          "kind": r.get("agent") or "-", "status": r.get("agent_status") or "?",
                          "where": where, "cwd": r.get("cwd", ""), "state": r.get("state", "")})
    if not lines:
        eprint("desks: 无工位可列(机不可达或零工位)")
    if not runtime_ctx.JSON_MODE:
        print("\n".join(lines))
    emit_ok({"panes": json_rows})


def machines_table(pos: list[str], g: dict):
    """(退役)机册快照表:见 machines view。"""
    from .engines import hc_json
    d = hc_json("machine", "ls", timeout=20)
    rows = d.get("machines", []) if isinstance(d, dict) else []
    print(f"{'MACHINE':<14} {'STATE':<12} TARGET")
    for m0 in rows:
        print(f"{m0.get('name', '-'):<14} {m0.get('state', '-'):<12} {m0.get('target', '-')}")


def _retired(verb: str, see: str):
    """退役动词 stub(废弃可见化,kubectl 式):usage 退 2 + 指新道。"""
    def _h(pos: list[str], g: dict):
        die("usage", f"动词「{verb}」已退役(ADR-0003 重构);{see}", rc=2)
    return _h


def _start(pos: list[str], g: dict):
    from .agents_lifecycle import start
    start(pos, g)


def _close(pos: list[str], g: dict):
    from .agents_lifecycle import close
    close(pos, g)


def desk_main():
    """desks 域(CONTRACT-v2:view / start / close 三动词;拓扑兜底,主力让位 mod GUI)。
    split/tab/zoom/wt/shell/dev/ws/yolo/trust/desk 退役:help/CTA 可见化指新道。"""
    if len(sys.argv) > 1 and sys.argv[1] in ("--llms", "--help", "-h"):
        print(manual("desks"))
        return
    argv = sys.argv[1:]
    g, verb, pos = parse(argv)
    # 信封 meta.command 与错误前缀按真实入口名(win shim 带 .exe,splitext 剥)
    import os
    setup(os.path.splitext(os.path.basename(sys.argv[0]))[0] or "desks", g)
    if verb in (None, "view"):
        host = pos[0] if pos and not pos[0].startswith("-") else None
        return desk_view(host)
    if verb == "start":
        return _start(pos, g)
    if verb == "close":
        return _close(pos, g)
    if verb in ("split", "tab", "zoom", "wt"):
        return _retired(verb, "拓扑归 herdr-app mod GUI(ADR-0003);消息面同形动词走 agents")()
    die("usage", f"未知动词「{verb}」(view/start/close);--llms 看手册", rc=2)


desk_main = guard(desk_main)
