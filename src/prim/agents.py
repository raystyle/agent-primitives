"""prim agents 域(批3R 自 cli 拆出):消息域主入口,VERBS 注册表分派

agents = 消息面(to/wait/inbox/read/keys/mode/reload)+ 拓扑动词(desks 别名期共用,
ADR-0007 软拆)+ 透传臂(其余 herdr agent 子命令)。注册表 = 漂移守卫断言面
(手册动词表对 VERBS 键双向断言,tests/test_prim.py)。
"""
from __future__ import annotations
import sys

from . import agents_events, agents_lifecycle, agents_topo, agents_view
from .addressing import resolve
from .engines import herdr_run
from .flags import parse, setup
from .manual import manual
from .runtime_ctx import die, guard


def _view(pos: list[str], g: dict):
    agents_view.agents_view(pos[0] if pos else None)


def _ws_scan(pos: list[str], g: dict):
    # 工作台清点(用户令 2026-10-17):工作台 = 节点 home + ~/repos/* 各 git 仓(对 GitHub 项目)
    from .agents_ws_scan import scan
    scan(pos[0] if pos else None, g)


def _yolo(pos: list[str], g: dict):
    # 四家 CLI yolo 检测与翻台(用户令 2026-10-17):裸/审计 = 全舰队屏面检测;
    # yolo <id> --yes = 冷翻(用户级配置 + /exit + fresh 起)
    from .agents_yolo import yolo_main
    yolo_main(pos, g)


def _wait(pos: list[str], g: dict):
    agents_events.wait_inbox(pos, g, "wait")


def _inbox(pos: list[str], g: dict):
    agents_events.wait_inbox(pos, g, "inbox")


VERBS: dict = {
    "view": _view,
    "list": agents_view.list_json,
    "machines": agents_view.machines_table,
    "workbenches": _ws_scan,
    "ws": _ws_scan,
    "yolo": _yolo,
    "read": agents_events.read,
    "to": agents_events.to,
    "wait": _wait,
    "inbox": _inbox,
    "start": agents_lifecycle.start,
    "close": agents_lifecycle.close,
    "reload": agents_lifecycle.reload,
    "shell": agents_topo.shell,
    "dev": agents_topo.dev,
    "split": agents_topo.split,
    "tab": agents_topo.tab,
    "zoom": agents_topo.zoom,
    "run": agents_topo.run,
    "keys": agents_topo.keys,
    "mode": agents_topo.mode,
    "wt": agents_topo.wt,
    "trust": agents_topo.trust,
    "sync": agents_topo.sync,
}

# herdr agent 透传允许表外的子命令走 else 臂(契约:herdr agent 动词透传)


def agents_main():
    g, verb, pos = parse(sys.argv[1:])
    setup("agents", g)
    from .flags import handle_globals
    handle_globals(g, manual("agents"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is not None:
        return handler(pos, g)
    # 透传(允许表 = herdr agent 子命令)
    if not pos:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
    m, pane = resolve(pos[0])
    r = herdr_run(None if m in ("", "local") else m, "agent", verb, pane, *pos[1:])
    print(r.stdout or r.stderr)
    sys.exit(r.returncode)


agents_main = guard(agents_main)
