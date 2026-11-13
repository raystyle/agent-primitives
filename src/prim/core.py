"""prim core 门面(批3R 拆分后旧入口续命层;批5a 迁移形:agents 域缺失件降级处理)

实体已拆六叶子:runtime_ctx(全局态与信封)、engines(herdr/s5/wsl/杀树)、
identity(本机标签与调用方身份)、addressing(寻址)、gating(TUI 判标与门控投递)、
flags(解析与旗标)。本文件仅 re-export 旧名(`from .core import X` 全兼容);
全局态读写一律走 runtime_ctx(本模块 __getattr__ 动态转发读,setup 已改写真源)。

批5a 迁移注记:mcps/ctx 域旧代码走 core.die/emit_ok 面,继续兼容;agents 域专属
符号(_ts_nodename/caller 族/gate 判标)已随共享叶子迁入,5b 域(agents/desks/
tasks/machines)未迁,core 不 re-export 其入口。
"""
from __future__ import annotations

from .runtime_ctx import eprint, emit_error, emit_ok, die
from .engines import (_find_bin, herdr, s5, s5_cmd, _wsl_exec, wsl_path, host_path,
                      _kill_tree, herdr_run, herdr_json)
from .identity import _ts_nodename, host_label, _my_cell, _my_alias, caller_pane, caller_addr
from .addressing import (Target, resolve, _machine_labels, _agents_of, _find_by_name,
                         pane_cwd, target_status)
from .gating import (TUI_DIALOGS, gate, deliver_prompt, agents_trust, blocked_after_start,
                     dismiss_block_hint)

# 旧名续命(gating 正名对)
_agents_trust = agents_trust
_blocked_after_start = blocked_after_start
_dismiss_block_hint = dismiss_block_hint


def __getattr__(name: str):
    """全局态动态转发(读):core.CMD_NAME 等不再落本模块静态绑定。"""
    from . import runtime_ctx
    if hasattr(runtime_ctx, name):
        return getattr(runtime_ctx, name)
    raise AttributeError(f"module 'prim.core' has no attribute {name!r}")
