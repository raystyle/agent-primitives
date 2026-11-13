"""prim agents 视图面(批3R 自 cli 拆出):agents_view(消息面表)/ desk_view(拓扑真视图)
与 desks 域入口(ADR-0007 拓扑面软拆:view 自有,余动词透传 agents 同实现)。"""
from __future__ import annotations
import json
import sys

from . import runtime_ctx
from .addressing import _agents_of, _machine_labels
from .engines import herdr_json, herdr_run
from .flags import parse, setup
from .manual import manual
from .runtime_ctx import eprint, emit_ok, guard


def _shell_only_panes(machine: str) -> list[dict]:
    """扫 pane 面找无 agent 的空格(用户令 2026-10-17:所有 pane 必须有 agent,空 pane = 异常态)。"""
    m = None if machine in ("", "local") else machine
    r = herdr_json(m, "pane", "list", timeout=20)
    panes = r.get("result", {}).get("panes") if isinstance(r, dict) else None
    if not panes:
        return []
    return [p for p in panes if not p.get("agent")]


# 自制 TUI 屏面判标(非 agent 但有活跃程序,不是空壳)
TUI_MARKERS: tuple[str, ...] = (
    "数据链路", "  #  Help", "q 退出", "q quit", "│ File │", "NCURSES",
)


def _is_tui_pane(machine: str, pane: dict) -> bool:
    """空 pane 再判:屏面有 TUI 特征 = 自制监控/操作台,非异常态。"""
    m = None if machine in ("", "local") else machine
    pid = pane.get("pane_id", "")
    r = herdr_run(m, "pane", "read", pid, "--source", "visible", "--lines", "20", timeout=10)
    tail = "\n".join((r.stdout or "").splitlines()[-20:])
    return any(mk in tail for mk in TUI_MARKERS)


def agents_view(machine: str | None):
    rows = _agents_of(machine or None)
    if not machine:
        rows = [("local", a) for a in rows]
        dead = []
        strays = []
        # local 首拍已入行;此循环只走远程机(local 再遍 = 行双列,2026-10-17 实测根修)
        for lab in _machine_labels():
            got = _agents_of(lab, timeout=12)
            if not got:
                dead.append(lab)
                continue
            rows += [(lab, a) for a in got]
            strays += [(lab, p) for p in _shell_only_panes(lab)]
        strays = [(l, p) for l, p in strays if not _is_tui_pane(l, p)]
        print(f"{'HOST':<12} {'NAME':<12} {'PANE':<8} {'STATUS':<8} {'KIND':<7} CWD")
        for host, a in rows:
            print(f"{host:<12} {(a.get('name') or '-'):<12} {a.get('pane_id',''):<8} {a.get('agent_status',''):<8} {(a.get('agent') or '-'):<7} {a.get('cwd','')}")
        if strays:
            eprint(f"agents: ⚠ 空 pane {len(strays)} 格(异常态:pane 须有 agent):")
            for lab, p in strays:
                eprint(f"  {lab}:{p.get('pane_id')} cwd={p.get('cwd')}(desks close {lab} {p.get('pane_id')} 或 agents dev 补 agent)")
        if dead:
            eprint(f"agents: 不可达机 {len(dead)} 台跳过({', '.join(dead)});单机详查:agents view <host>")
    else:
        for a in rows:
            print(f"{a.get('pane_id',''):<8} {(a.get('name') or '-'):<12} {a.get('agent_status',''):<8} {a.get('cwd','')}")
        strays = _shell_only_panes(machine)
        if strays:
            eprint(f"agents: ⚠ 空 pane {len(strays)} 格(异常态):")
            for p in strays:
                eprint(f"  {machine}:{p.get('pane_id')} cwd={p.get('cwd')}")


def desk_view(machine: str | None):
    """desk view:拓扑面真视图(ADR-0007 desk/agents 分职)。数据 = herdr pane list 全格(含非 agent 格),
    按 窗台(workspace, w 编号) -> tab -> 工位(pane) 三层分组;焦点工位 ▍ 标记(TUI 焦点定式);活动列 = terminal_title。
    术语定谳(2026-10-25 用户令):工位/窗格 = pane;工作台/窗台 = workspace(w)。
    与 agents view 分工:agents view = 消息面 agent 表(名/态/类/cwd),desk view = 拓扑(全量工位+活动)。"""
    dead: list[str] = []
    targets: list[tuple[str, str | None]] = [("local", machine or None)] if machine else [("local", None)] + [(lab, lab) for lab in _machine_labels()]
    sections: list[tuple[str, list[dict]]] = []
    for label, m in targets:
        try:
            d = herdr_json(m, "pane", "list", timeout=12)
        except SystemExit:
            dead.append(label)
            continue
        panes = d.get("result", {}).get("panes", []) if isinstance(d, dict) else []
        if not panes:
            if label != "local":
                dead.append(label)
            continue
        sections.append((label, panes))
    json_rows: list[dict] = []
    lines: list[str] = []
    for label, panes in sections:
        ws_map: dict[str, dict[str, list[dict]]] = {}
        for p in panes:
            ws_map.setdefault(p.get("workspace_id", "?"), {}).setdefault(p.get("tab_id", "?"), []).append(p)
        for ws, tabs in sorted(ws_map.items()):
            n_panes = sum(len(v) for v in tabs.values())
            lines.append(f"{'' if label == 'local' else label + ':'}{ws} 窗台 {len(tabs)} tab {n_panes} 工位")
            for tab, plist in sorted(tabs.items()):
                for p in plist:
                    focus = "▍" if p.get("focused") else " "
                    kind = p.get("agent") or "-"
                    st = p.get("agent_status") or "?"
                    title = (p.get("terminal_title_stripped") or "")[:38]
                    lines.append(f"  {tab.split(':')[-1]:<3} {p.get('pane_id', '').split(':')[-1]:<4}{focus}{kind:<7}{st:<8}{title}")
                    json_rows.append({"machine": label, "workspace": ws, "tab": tab, "pane": p.get("pane_id", ""),
                                      "focused": bool(p.get("focused")), "kind": kind, "status": st,
                                      "title": p.get("terminal_title_stripped", ""), "cwd": p.get("cwd", "")})
    if not lines:
        eprint("desk: 无工位可列(机全不可达或零工位)")
    if not runtime_ctx.JSON_MODE:
        print("\n".join(lines))
    if dead:
        eprint(f"desk: 不可达机 {len(dead)} 台跳过({', '.join(dead)});单机详查:desk view <host>")
    emit_ok({"workspaces": json_rows})


def machines_table(pos: list[str], g: dict):
    print(f"{'MACHINE':<12} {'PANE':<8} REACHABLE")
    print(f"{'local':<12} {len(_agents_of(None)):<8} yes")
    for lab in _machine_labels():
        try:
            n = len(_agents_of(lab))
            print(f"{lab:<12} {n:<8} yes")
        except Exception:
            print(f"{lab:<12} {'?':<8} no")


def list_json(pos: list[str], g: dict):
    m = pos[0] if pos else None
    print(json.dumps(_agents_of(m or None), ensure_ascii=False))


def desk_main():
    """desks 域(ADR-0007 拓扑面 + 2026-10-25 复数对齐裁定):工位(pane)/窗台(workspace)操作器。
    主名 desks(全家族复数形),desk 留单字别名(软切期);view = 拓扑真视图(窗台/tab/工位/焦点/活动);
    start/close/split/tab/zoom/ws/shell/dev/wt/yolo/trust 动词与 agents 同实现(软拆 alias 期)。"""
    if len(sys.argv) > 1 and sys.argv[1] in ("--llms", "--help", "-h"):
        print(manual("desks"))
        return
    argv = sys.argv[1:]
    g, verb, pos = parse(argv)
    # 信封 meta.command 与错误前缀按真实入口名(win shim 带 .exe,splitext 剥;批2R 实名修正)
    import os
    setup(os.path.splitext(os.path.basename(sys.argv[0]))[0] or "desks", g)
    # view 动词与裸调用 = desk 自有拓扑视图(与 agents view 消息面表分职);其余动词透传 agents 同实现
    if verb in (None, "view"):
        host = pos[0] if pos and not pos[0].startswith("-") else None
        return desk_view(host)
    from .agents import agents_main
    return agents_main()


desk_main = guard(desk_main)
