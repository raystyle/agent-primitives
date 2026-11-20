"""agent_primitives DELIVER 单点(批3R:五域 to 臂脚手架归一)

六处逐字重复的 to 模板(resolve -> gate -> 前置动作 -> 拒投代记 -> MsgEnvelope ->
deliver_prompt -> status 信封 -> 条件退 1)收编为 run_to;域差异经 ToSpec 声明:
前置动作(files 先上架/streams 先入流/pipes 与 ports 先开听/tasks 先 hst set)、
信封域字段、取用行、deferred 文案、ok 载荷键序(契约:字段插入序即契约,逐域保序)。
agents to 不走本道:自由文无模板 + dm 镜像 + engine_fail 定向诊断(见 agents_events)。
"""
from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import Callable

from .addressing import resolve
from .engines import s5_append
from .gating import deliver_prompt, gate
from .identity import _my_alias, caller_addr
from .runtime_ctx import die, emit_ok, eprint


@dataclass
class ToSpec:
    domain: str
    usage: str                       # 参数不足的 usage 文(cta 走 --llms)
    min_args: int = 2
    gated: bool = True               # tasks set 直写绕门控,to 走门控
    pre_before_gate: bool = False    # files(先上架)/pipes/ports(先开听)= True;
                                     #  streams(拒投不入流)/tasks(拒投不设)= False
    exit_on_fail: bool = True        # tasks to 非 delivered 不退 1(冻结行为)
    fail_to_stderr: bool = True      # tasks 失败面仍是 stdout 单条 print(冻结行为)
    pre: Callable[[str, str, list], dict] = None        # (m, pane, pos) -> ctx;可内部 die
    deferred_note: Callable[[dict], str] = None         # 代记流正文(ctx 恒有 pos)
    deferred_msg: Callable[[dict], str] = None          # 人读拒投提示
    deferred_payload: Callable[[dict], dict] = None     # 拒投 --json data
    envelope_kw: Callable[[dict], dict] = None          # MsgEnvelope 域字段
    use_line: Callable[[dict, str], str] = None         # (ctx, my) -> use 行
    ok_payload: Callable[[dict, str], dict] = None      # (ctx, st) -> data(键序即契约)
    success_msg: Callable[[dict, str], str] = None
    fail_msg: Callable[[dict, str], str] = None


def run_to(cmd: str, pos: list[str], spec: ToSpec):
    """五域 to 臂单点。行为逐字保持各域原臂(含键序与退出码差异)。"""
    if len(pos) < spec.min_args:
        die("usage", spec.usage, rc=2)
    m, pane = resolve(pos[0])
    blocked = gate(m, pane) if spec.gated else None
    ctx: dict = {"pos": pos, "m": m, "pane": pane}
    if not blocked or spec.pre_before_gate:
        if spec.pre:
            ctx.update(spec.pre(m, pane, pos))
    if blocked:
        s5_append(f"room/deferred/{pane}", spec.deferred_note(ctx))
        eprint(spec.deferred_msg(ctx))
        emit_ok(spec.deferred_payload(ctx))
        sys.exit(1)
    src = caller_addr()
    src_host, src_pane = (src.split(":", 1) + [""])[:2]
    from .msg import MsgEnvelope
    env = MsgEnvelope(domain=spec.domain, src_host=src_host, src_pane=src_pane,
                      dst=pos[0], **spec.envelope_kw(ctx))
    my = _my_alias() or f"{src_host}:{src_pane}"
    msg = env.render(spec.use_line(ctx, my))
    st = deliver_prompt(m, pane, msg)
    if st == "delivered":
        print(spec.success_msg(ctx, st))
    elif spec.fail_to_stderr:
        eprint(spec.fail_msg(ctx, st))
    else:
        print(spec.fail_msg(ctx, st))
    emit_ok(spec.ok_payload(ctx, st))
    if st != "delivered" and spec.exit_on_fail:
        sys.exit(1)
