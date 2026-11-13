"""prim agents 域(批3R 拆出;批5c CONTRACT-v2 重构):消息域主入口,VERBS 注册表分派

CONTRACT-v2 动词面(15):view / read / to / wait / inbox / mode / start / close /
reload / trust / yolo / run / shell / dev / keys。
退役可见化(命运表):list/machines/ws/workbenches/split/tab/zoom/wt/sync 注册表留
stub,usage 退 2 指新道(kubectl 废弃可见化纪律)。
"""
from __future__ import annotations
import sys

from . import agents_events, agents_lifecycle, agents_topo, agents_view
from .flags import parse as _parse, setup as _setup
from .manual import manual
from .runtime_ctx import die, guard


def _view(pos: list[str], g: dict):
    agents_view.agents_view(pos[0] if pos else None)


def _ws_scan(pos: list[str], g: dict):
    # 工作台清点(命运表保留裁定):工作台 = 节点 home + ~/repos/* 各 git 仓;
    # 跨机腿 hc 化(机册三台 hc exec --on,机册外保持原 ssh 道)
    from .agents_ws_scan import scan
    scan(pos[0] if pos else None, g)


def _yolo(pos: list[str], g: dict):
    # 四家 CLI yolo 检测与翻台:裸/审计 = 全舰队屏面检测;yolo <id> --yes = 冷翻
    from .agents_yolo import yolo_main
    yolo_main(pos, g)


def _wait(pos: list[str], g: dict):
    agents_events.wait_inbox(pos, g, "wait")


def _inbox(pos: list[str], g: dict):
    agents_events.wait_inbox(pos, g, "inbox")


def _retired(verb: str, see: str):
    """退役动词 stub(废弃可见化,kubectl 式):usage 退 2 + 指新道。"""
    def _h(pos: list[str], g: dict):
        die("usage", f"动词「{verb}」已退役(ADR-0003 重构);{see}", rc=2)
    return _h


VERBS: dict = {
    "view": _view,
    "workbenches": _ws_scan,
    "read": agents_events.read,
    "to": agents_events.to,
    "wait": _wait,
    "inbox": _inbox,
    "mode": agents_topo.mode,
    "start": agents_lifecycle.start,
    "close": agents_lifecycle.close,
    "reload": agents_lifecycle.reload,
    "trust": agents_topo.trust,
    "yolo": _yolo,
    "run": agents_topo.run,
    "shell": agents_topo.shell,
    "dev": agents_topo.dev,
    "keys": agents_topo.keys,
    # ---- 退役可见化(命运表;stub 不删,help/CTA 指新道) ----
    "list": _retired("list", "JSON 行形并入 agents view --json(hc ls --json)"),
    "machines": _retired("machines", "机册面归 machines view(hc machine ls)"),
    "sync": _retired("sync", "机册注册走 hc machine add --install(批3 实证一把过)"),
    "split": _retired("split", "开格拓扑归 herdr-app mod GUI(ADR-0003)"),
    "tab": _retired("tab", "tab 面归 herdr-app mod GUI(ADR-0003)"),
    "zoom": _retired("zoom", "焦点面归 herdr-app mod GUI(ADR-0003)"),
    "wt": _retired("wt", "显示面归 herdr-app mod GUI(ADR-0003)"),
}


def agents_main():
    g, verb, pos = _parse(sys.argv[1:])
    _setup("agents", g)
    from .flags import handle_globals
    handle_globals(g, manual("agents"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is not None:
        return handler(pos, g)
    die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)


agents_main = guard(agents_main)
