"""agent_primitives core 门面(批3R 拆分后旧入口续命层;批5c CONTRACT-v2:六入口全量)

实体已拆六叶子:runtime_ctx(全局态与信封)、engines(hc/s5/wsl 代役/杀树)、
identity(本机标签与调用方身份)、addressing(寻址)、gating(TUI 判标与门控投递)、
flags(解析与旗标)。本文件仅 re-export 旧名;全局态读写一律走 runtime_ctx
(本模块 __getattr__ 动态转发读,setup 已改写真源)。

批5c 迁移注记:engines 面 hc 化(herdr CLI spawn 退役);mcps 域删域(ADR-0001);
agents_ws_scan/agents_yolo 走 core.die/emit_ok 面继续兼容。
"""
from __future__ import annotations

from .runtime_ctx import eprint, emit_error, emit_ok, die
from .engines import (_find_bin, hc_bin, s5, s5_cmd, _wsl_exec, wsl_path, host_path,
                      _kill_tree, hc_run, hc_json, hc_exec_on, exec_result,
                      json_field as _json_field)
from .identity import _ts_nodename, host_label, _my_cell, _my_alias, caller_pane, caller_addr
from .addressing import (Target, resolve, _machine_labels, _machines_raw, _agents_of,
                         _find_by_name, row_of, pane_cwd, target_status)
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
