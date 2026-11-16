"""prim CLI 装配层(批5c CONTRACT-v2 重构):六入口 + 惰性域路由

CONTRACT-v2(ADR-0003 方案甲,入口 11 → 6):agents / desks / machines / streams /
carry / ctxs。tasks 并入 streams 子面(task view|set|to);shares/pipes/ports 合成
carry;mcps 整域退役(ADR-0001 MCP 边缘化,用户裁定 2026-11-13);desk 单字别名删。

实现分布(依赖恒单向 cli -> 域模块 -> 共享叶子 -> runtime_ctx):
- agents 域:agents.py(VERBS 注册表)+ agents_events/agents_lifecycle/agents_topo/agents_view
- desks 域:agents_view.desk_main(view/start/close 拓扑兜底,退役动词 stub)
- machines 域:machines.py(hc machine 直通)+ runtimes(ark 子面)
- streams 域:streams.py(s5 持久流)+ tasks(子面 task view|set|to)
- carry 域:carry.py(形壳)→ shares/pipes/ports 三模块(域实现单源)
- ctxs 域:ctx(ClickHouse 检索)
- 共享叶子:runtime_ctx(态与信封)/engines(hc+s5)/identity/addressing/gating/flags/manual/deliver/tailcat_base/msg

文法(CONTRACT 五d):<命令> [全局旗标] <动词> [动词旗标] [位置参数]
"""
from __future__ import annotations
import importlib

from .agents import agents_main  # noqa: F401  (已 guard 包裹)
from .agents_view import desk_main  # noqa: F401,E402  (已 guard 包裹)
from .shares import shares_main  # noqa: F401  (已 guard 包裹;carry 域退役 2026-11-16,shares 直入六入口)
from .flags import parse, setup, handle_globals, _val  # noqa: F401  (旧名续命)
from .manual import manual, _pkg_ver  # noqa: F401
from .runtime_ctx import eprint, guard

_LOADERS = {"ctxs": "ctx", "machines": "machines", "streams": "streams"}


def _load(cmd: str):
    """惰性取域入口(域模块按需导入,启动面零引擎触碰)。"""
    mod = _LOADERS.get(cmd, cmd)
    return getattr(importlib.import_module(f"prim.{mod}"), f"{cmd}_main")


streams_main = guard(_load("streams"))
ctxs_main = guard(_load("ctxs"))
machines_main = guard(_load("machines"))
