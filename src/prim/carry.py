"""prim carry 域(批5c CONTRACT-v2 新入口):同构搬运三合一(shares + pipes + ports)

域内动词面不变,入口重组只并形:`carry put|get|open|close|send|to|fwd`(裸形)+
`carry shares|pipes|ports <动词>`(显式道,消歧逃生口)。域实现沿用 shares/pipes/ports
三模块(VERBS 单源);信封 domain 段保持三域实名(shares/pipes/ports),meta.command = carry。
裸形分派:put/get → shares;send → pipes;fwd → ports;open 无参 = pipes / 带参 = ports;
close 双域状态档联合寻址(唯一命中即关);to 按首参形路由(文件 → shares,spec 形 → ports,
余者 usage 指显式道)。
"""
from __future__ import annotations
import os
import re
import sys

from . import pipes, ports, shares
from . import tailcat_base as tb
from .flags import parse, setup
from .manual import manual
from .runtime_ctx import die, emit_ok, guard

# 子域注册(域实现单源;carry 是形壳)
SUBDOMAINS = {"shares": shares, "pipes": pipes, "ports": ports}
# 裸动词唯一分派表(to 三域同构须显式;open/close 二义走路由)
_UNIQUE = {"put": shares, "get": shares, "fwd": ports, "send": pipes}
# ports spec 形:8080,8443 端口表 / 5555:IP:5555 服务侧映射 / all / exit-node
_SPEC = re.compile(r"^(\d+(,\d+)*|\d+:[^:]+:\d+|all|exit-node)$")


def _route_open(pos: list[str], g: dict):
    # open 无参 = pipes(管道免参);带 spec = ports
    if not pos:
        return pipes.VERBS["open"](pos, g)
    return ports.VERBS["open"](pos, g)


def _route_close(pos: list[str], g: dict):
    if not pos:
        die("usage", "close <地址或pid>(pipes/ports 双域联合寻址;或显式 carry pipes|ports close <址>)", rc=2)
    q = pos[0]
    hit_p = next((r for r in tb.alive("pipes") if str(r["pid"]) == q or r["addr"] == q), None)
    hit_o = next((r for r in tb.alive("ports") if str(r["pid"]) == q or r["addr"] == q), None)
    if hit_p and hit_o:
        die("usage", f"「{q}」pipes 与 ports 各有一命中,消歧:carry pipes close {q} / carry ports close {q}", rc=2)
    if hit_p:
        return tb.close_match("pipes", q, "carry pipes view")
    if hit_o:
        return tb.close_match("ports", q, "carry ports view")
    die("not_found", f"未匹配管道或映射({q})", [{"command": "carry view", "description": "查本机搬运面"}])


def _route_to(pos: list[str], g: dict):
    if not pos:
        die("usage", "to <id> ...(三域同构:文件 → shares;spec → ports;裸 id → pipes;或显式 carry <域> to ...)", rc=2)
    if len(pos) == 1:
        return pipes.VERBS["to"](pos, g)
    first = pos[1]
    if os.path.isfile(first):
        return shares.VERBS["to"](pos, g)
    if _SPEC.match(first):
        return ports.VERBS["to"](pos, g)
    die("usage", f"「{first}」既非文件亦非 ports spec 形;显式道:carry shares to <id> <文件> / carry pipes to <id> / carry ports to <id> <spec>", rc=2)


def _route_view(pos: list[str], g: dict):
    # 三面合一总览:shares 键表(前 20)+ 本机活管道 + 本机端口映射;--shares/--pipes/--ports 择面;
    # 位置参(机名)= pipes/ports 公开行(s5 room/pipe-live、room/port-live 过滤)
    from .engines import s5_ls, s5_tail
    sel_shares = "--shares" in pos
    sel_pipes = "--pipes" in pos
    sel_ports = "--ports" in pos
    any_sel = sel_shares or sel_pipes or sel_ports
    host = next((p for p in pos if not p.startswith("-")), None)
    if sel_shares or not any_sel:
        print("-- share 资源(share/ 前缀,前 20):")
        for x in s5_ls("share/")[:20]:
            print(f"  {x.get('key', x)}")
    if sel_pipes or not any_sel:
        print("-- 本机活动管道:")
        rows = tb.alive("pipes")
        for r in rows:
            print(f"  pid={r['pid']} addr={r['addr']} log={r['log']}")
        if not rows:
            print("  (无)")
        if host:
            pub = [x for x in s5_tail("room/pipe-live", 30)
                   if str(x.get("body", "")).startswith(f"{host}|pid=")]
            print(f"-- {host} 管道公开行:")
            for x in pub[-8:]:
                print(f"  {x.get('body')}")
    if sel_ports or not any_sel:
        print("-- 本机活动端口映射:")
        rows = tb.alive("ports")
        for r in rows:
            print(f"  pid={r['pid']} spec={r.get('spec','')} addr={r['addr']} log={r['log']}")
        if not rows:
            print("  (无)")
        if host:
            pub = [x for x in s5_tail("room/port-live", 30)
                   if str(x.get("body", "")).startswith(f"{host}|pid=")]
            print(f"-- {host} 端口映射公开行:")
            for x in pub[-8:]:
                print(f"  {x.get('body')}")
    emit_ok({"status": "ok", "host": host or "local"})


def carry_main():
    g, verb, pos = parse(sys.argv[1:])
    setup("carry", g)
    from .flags import handle_globals
    handle_globals(g, manual("carry"))
    if verb in SUBDOMAINS:
        # carry shares put x → 子域 VERBS(域内动词面不变)
        sub = SUBDOMAINS[verb]
        subverb = pos[0] if pos else "view"
        h = sub.VERBS.get(subverb)
        if h is None:
            die("usage", f"carry {verb} 未知动词「{subverb}」;--llms 看手册", rc=2)
        return h(pos[1:], g)
    if verb is None:
        die("usage", "carry <shares|pipes|ports> <动词> [参数...](同构搬运三合一;裸形 put|get|open|close|send|to|fwd|view;--llms 看手册)", rc=2)
    if verb == "to":
        return _route_to(pos, g)
    if verb == "open":
        return _route_open(pos, g)
    if verb == "close":
        return _route_close(pos, g)
    if verb == "view":
        return _route_view(pos, g)
    mod = _UNIQUE.get(verb)
    if mod is not None:
        return mod.VERBS[verb](pos, g)
    die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)


carry_main = guard(carry_main)
