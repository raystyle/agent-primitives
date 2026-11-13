"""prim CLI 装配层(批5a 迁移形,herdr-ccoe):5a 六入口 + 惰性域路由

批5a 范围(PLAN-ai-ccoe-migration):shares/streams/pipes/ports/ctxs/mcps 六域 + 共享叶子。
agents/desks/tasks/machines 三域在 5b 迁入;pyproject scripts 只挂 5a 六入口(契约
十一入口语义不变,其余四入口随 5b 补齐;CONTRACT.md 随 5b 一并迁)。

实现分布(依赖恒单向 cli -> 域模块 -> 共享叶子 -> runtime_ctx):
- 五域:shares/streams/pipes/ports 各自模块(VERBS + deliver.run_to)/ ctxs:ctx / mcps:mcps
- 共享叶子:runtime_ctx(态与信封)/engines/identity/addressing/gating/flags/manual/deliver/tailcat_base/msg
- agents_view:pipes/ports view 臂复用其 agents_view(消息面表)——5a 带入,5b 归位 agents 域

文法(CONTRACT 五d):<命令> [全局旗标] <动词> [动词旗标] [位置参数]
"""
from __future__ import annotations
import importlib

from .flags import parse, setup, handle_globals, _val  # noqa: F401  (旧名续命)
from .manual import manual, _pkg_ver  # noqa: F401
from .runtime_ctx import eprint, guard

_LOADERS = {"ctxs": "ctx", "mcps": "mcps",
            "shares": "shares", "streams": "streams",
            "pipes": "pipes", "ports": "ports"}


def _load(cmd: str):
    """惰性取域入口(域模块按需导入,启动面零引擎触碰)。"""
    mod = _LOADERS.get(cmd, cmd)
    return getattr(importlib.import_module(f"prim.{mod}"), f"{cmd}_main")


shares_main = guard(_load("shares"))
streams_main = guard(_load("streams"))
pipes_main = guard(_load("pipes"))
ports_main = guard(_load("ports"))
ctxs_main = guard(_load("ctxs"))
mcps_main = guard(_load("mcps"))
