"""prim CLI 装配层(批5b 迁移形,herdr-ccoe):十一入口 + 惰性域路由

批5b 范围(PLAN-ai-ccoe-migration):agents/desks/desk/tasks/machines 四入口补齐,
CONTRACT.md 迁入,pyproject scripts 合拢十一入口(契约十一入口语义不动)。

实现分布(依赖恒单向 cli -> 域模块 -> 共享叶子 -> runtime_ctx):
- agents 域:agents.py(VERBS 注册表)+ agents_events/agents_lifecycle/agents_topo/agents_view
- desks 域:agents_view.desk_main(view 自有拓扑,余动词透传 agents,ADR-0007 软拆 alias 期)
- 五域:shares/streams/tasks/pipes/ports 各自模块(VERBS + deliver.run_to)
- machines 域:machines.py(原 nodes,ADR-0007 正名)/ ctxs:ctx / mcps:mcps
- 共享叶子:runtime_ctx(态与信封)/engines/identity/addressing/gating/flags/manual/deliver/tailcat_base/msg

文法(CONTRACT 五d):<命令> [全局旗标] <动词> [动词旗标] [位置参数]
"""
from __future__ import annotations
import importlib

from .agents import agents_main  # noqa: F401  (已 guard 包裹)
from .agents_view import desk_view, agents_view  # noqa: F401  (视图函数旧名续命)
from .flags import parse, setup, handle_globals, _val  # noqa: F401  (旧名续命)
from .manual import manual, _pkg_ver  # noqa: F401
from .runtime_ctx import eprint, guard

_LOADERS = {"ctxs": "ctx", "machines": "machines", "mcps": "mcps",
            "shares": "shares", "streams": "streams", "tasks": "tasks",
            "pipes": "pipes", "ports": "ports"}


def _load(cmd: str):
    """惰性取域入口(域模块按需导入,启动面零引擎触碰)。"""
    mod = _LOADERS.get(cmd, cmd)
    return getattr(importlib.import_module(f"prim.{mod}"), f"{cmd}_main")


shares_main = guard(_load("shares"))
streams_main = guard(_load("streams"))
tasks_main = guard(_load("tasks"))
pipes_main = guard(_load("pipes"))
ports_main = guard(_load("ports"))
ctxs_main = guard(_load("ctxs"))
mcps_main = guard(_load("mcps"))
machines_main = guard(_load("machines"))

from .agents_view import desk_main  # noqa: F401,E402  (已 guard 包裹)
