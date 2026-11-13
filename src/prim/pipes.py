"""prim pipes 域(批3R 自 domains 拆出):临时管道域,tailcat 实时(本机收对方发)"""
from __future__ import annotations
import sys

from . import flags
from . import tailcat_base as tb
from .deliver import ToSpec, run_to
from .engines import s5_tail
from .identity import host_label
from .manual import manual
from .runtime_ctx import die, emit_ok


def pipes_alive() -> list[dict]:
    return tb.alive("pipes")


def pipes_view(machine: str | None):
    if machine:
        rows = [x for x in s5_tail("room/pipe-live", 30)
                if str(x.get("body", "")).startswith(f"{machine}|pid=")]
        print(f"-- {machine} 管道公开行(room/pipe-live,无地址):")
        for x in rows[-8:]:
            print(f"  {x.get('body')}")
        if not rows:
            print("  (无)")
        return
    from .agents_view import agents_view
    agents_view(None)
    print("-- 本机活动管道:")
    rows = pipes_alive()
    for r in rows:
        print(f"pid={r['pid']} addr={r['addr']} log={r['log']}")
    if not rows:
        print("  (无)")


def _view(pos: list[str], g: dict):
    pipes_view(pos[0] if pos else None)


def _open(pos: list[str], g: dict):
    if "--keep" in pos:
        die("usage", "pipes 无 --keep(管道常驻至 close)", rc=2)
    pid, addr = tb.open_listener("pipes")
    if addr:
        print(f"pipes: 已开 addr={addr}(日志见 {tb.statedir('pipes')}/log.{pid}.txt)")
        tb.fw_cta()
        emit_ok({"status": "delivered", "addr": addr, "pid": pid})
    else:
        die("engine_fail", "tailcat 地址未取到", rc=1)


def _close(pos: list[str], g: dict):
    if not pos:
        die("usage", "close <地址或pid>", rc=2)
    tb.close_match("pipes", pos[0], "pipes view")


def _send(pos: list[str], g: dict):
    # 收方动词(2026-10-15 用户令关缺口):连对方管道发数据,stdin 直通;
    # 引擎 tailcat 藏进原语,取用行不再漏引擎名
    if not pos:
        die("usage", "send <addr>(pipe stdin to the peer;e.g. echo x | pipes send <addr>)", rc=2)
    import subprocess as sp
    sys.exit(sp.call([tb.tailcat_bin(), pos[0]]))


def _pre(m: str, pane: str, pos: list[str]) -> dict:
    pid, addr = tb.open_listener("pipes")
    if not addr:
        die("engine_fail", "tailcat 地址未取到(管道未开)", rc=1)
    tb.fw_cta()
    return {"pid": pid, "addr": addr}


_TO = ToSpec(
    domain="pipes",
    usage="to <id> [--force](=open+模板知会)",
    min_args=1,
    pre_before_gate=True,   # 拒投也先开听(管道已在,人可用)
    pre=_pre,
    deferred_note=lambda c: f"{host_label()}|mode=deferred|domain=pipes|管道 {c['addr']} 待达(--force 重发)",
    deferred_msg=lambda c: f"pipes: 目标存在操作对话框,已拒投;管道已开启 addr={c['addr']};已代记",
    deferred_payload=lambda c: {"status": "deferred", "target": f"{c['m']}:{c['pane']}", "addr": c["addr"]},
    envelope_kw=lambda c: {"addr": c["addr"]},
    use_line=lambda c, my: f"pipes send {c['addr']}",
    ok_payload=lambda c, st: {"status": st, "target": f"{c['m']}:{c['pane']}", "addr": c["addr"], "pid": c["pid"]},
    success_msg=lambda c, st: (f"pipes: 已投递(target={c['m']}:{c['pane']})(addr={c['addr']};pid={c['pid']};"
                               f"关闭:pipes close {c['addr']};发数据:pipes send {c['addr']})"),
    fail_msg=lambda c, st: f"pipes: 投递状态 {st}(target={c['m']}:{c['pane']}, addr={c['addr']})",
)


def _to(pos: list[str], g: dict):
    if "--keep" in pos:
        die("usage", "pipes 无 --keep(管道常驻至 close)", rc=2)
    if not pos:
        die("usage", "to <id> [--force](=open+模板知会)", rc=2)
    run_to("pipes", pos, _TO)


VERBS = {"view": _view, "open": _open, "close": _close, "send": _send, "to": _to}


def pipes_main():
    g, verb, pos = flags.bootstrap("pipes", manual("pipes"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
    handler(pos, g)
