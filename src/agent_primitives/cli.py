"""agent_primitives CLI 装配层(2026-11-18 五入口收敛,2026-11-20 shares 更名 files):files / streams / ctxs / ports / pipes

收敛判据:agents/desks/machines 三域退役——消息与工位归 hc 原生面(hc --skill:
run/ls/get/read/send/wait/put),机册归 hc machine,拓扑归 herdr-app;prim 只留
hc 没有的五个域(文件共享/持久流/对话历史/端口映射/实时字节管道)。
动词对齐 hc:清单 ls、读写 get/put、消息 send、生命周期 start/close
(pipes/ports 的 open→start 更名;view→ls 更名;to→send 更名)。

实现分布(依赖恒单向 cli -> 域模块 -> 共享叶子 -> runtime_ctx):
- files 域:files.py(view/put/get/to)
- streams 域:streams.py(rooms 退役 stub/view/append/to)
- ctxs 域:ctx(view/show 退役 stub/search)
- ports 域:ports.py(view/open/close/fwd/to)
- pipes 域:pipes.py(view/open/close/send/to)
- 共享叶子:runtime_ctx(态与信封)/engines(hc+s5)/identity/addressing/gating/flags/manual/deliver/tailcat_base/msg

文法(CONTRACT 五d):<命令> [全局旗标] <动词> [动词旗标] [位置参数]
"""
from __future__ import annotations
import importlib

from .files import files_main  # noqa: F401  (guard 包裹)
from .flags import parse, setup, handle_globals, _val  # noqa: F401  (旧名续命)
from .manual import manual, _pkg_ver  # noqa: F401
from .runtime_ctx import eprint, guard

_LOADERS = {"ctxs": "ctx", "streams": "streams", "ports": "ports", "pipes": "pipes"}


def _load(cmd: str):
    """惰性取域入口(域模块按需导入,启动面零引擎触碰)。"""
    mod = _LOADERS.get(cmd, cmd)
    return getattr(importlib.import_module(f"agent_primitives.{mod}"), f"{cmd}_main")


streams_main = guard(_load("streams"))
ctxs_main = guard(_load("ctxs"))
ports_main = guard(_load("ports"))
pipes_main = guard(_load("pipes"))
