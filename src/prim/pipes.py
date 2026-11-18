"""prim pipes 域(批3R 自 domains 拆出):临时管道域,tailcat 实时(本机收对方发)"""
from __future__ import annotations
import sys

from . import flags
from . import tailcat_base as tb
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


VERBS = {"ls": _view, "start": _open, "close": _close, "send": _send}  # send=字节写(管道写动作);留痕知会归 streams send(五域消息动词统一)


def pipes_main():
    g, verb, pos = flags.bootstrap("pipes", manual("pipes"))
    verb = verb or "ls"
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
    handler(pos, g)
