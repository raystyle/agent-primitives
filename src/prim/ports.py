"""prim ports 域(批3R 自 domains 拆出):端口映射域,tailcat serve(任意节点转发)"""
from __future__ import annotations
import sys

from . import flags
from . import tailcat_base as tb
from .deliver import ToSpec, run_to
from .engines import s5_tail
from .identity import host_label
from .manual import manual
from .runtime_ctx import die, emit_ok


def ports_alive() -> list[dict]:
    return tb.alive("ports")


def ports_view(machine: str | None):
    if machine:
        rows = [x for x in s5_tail("room/port-live", 30)
                if str(x.get("body", "")).startswith(f"{machine}|pid=")]
        print(f"-- {machine} 端口映射公开行(room/port-live,无地址):")
        for x in rows[-8:]:
            print(f"  {x.get('body')}")
        if not rows:
            print("  (无)")
        return
    from .agents_view import agents_view
    agents_view(None)
    print("-- 本机活动端口映射:")
    rows = ports_alive()
    for r in rows:
        print(f"pid={r['pid']} spec={r['spec']} addr={r['addr']} log={r['log']}")
    if not rows:
        print("  (无)")


def use_line(spec: str, addr: str) -> str:
    """取用行(grok F1 修):数字 spec 全端口枚举成可执行 forward;非数字 spec(all/
    exit-node)无 concrete 客户端口可代选,出指引形(exit-node 远端 = ip:port)。"""
    ports = []
    for part in spec.split(","):
        head = part.split(":")[0]
        if head.isdigit():
            ports.append(head)
    if ports:
        return "ports fwd " + addr + " " + " ".join(f"0:{p}" for p in ports)
    if spec == "exit-node":
        return f"ports fwd {addr} 0:<server-ip>:<port>"
    return f"ports fwd {addr} 0:<port>"


def _view(pos: list[str], g: dict):
    ports_view(pos[0] if pos else None)


def _open(pos: list[str], g: dict):
    if "--keep" in pos:
        die("usage", "ports 无 --keep(映射常驻至 close,无超时自关)", rc=2)
    if not pos:
        die("usage", "open <spec>(spec = 8080,8443 端口表 / 5555:IP:5555 服务侧映射 / all / exit-node)", rc=2)
    spec = ",".join(pos)
    pid, addr = tb.open_listener("ports", spec)
    if addr:
        print(f"ports: 已开 spec={spec} addr={addr}(日志见 {tb.statedir('ports')}/log.{pid}.txt)")
        tb.fw_cta()
        emit_ok({"status": "delivered", "spec": spec, "addr": addr, "pid": pid})
    else:
        die("engine_fail", "tailcat 地址未取到", rc=1)


def _close(pos: list[str], g: dict):
    if not pos:
        die("usage", "close <地址或pid>", rc=2)
    tb.close_match("ports", pos[0], "ports view")


def _fwd(pos: list[str], g: dict):
    # 收方动词(2026-10-15 用户令关缺口):本地起听转发到对方映射口;
    # 引擎 tailcat 藏进原语;Ctrl+C 停
    if len(pos) < 2:
        die("usage", "fwd <addr> <local>:<remote-port> ...(local listener;0 = free port;Ctrl+C to stop)", rc=2)
    import subprocess as sp
    sys.exit(sp.call([tb.tailcat_bin(), "forward", *pos]))


def _pre(m: str, pane: str, pos: list[str]) -> dict:
    spec_args = [x for x in pos if x != "--force"]
    spec = ",".join(spec_args[1:])
    pid, addr = tb.open_listener("ports", spec)
    if not addr:
        die("engine_fail", "tailcat 地址未取到(映射未开)", rc=1)
    tb.fw_cta()
    return {"pid": pid, "addr": addr, "spec": spec, "use": use_line(spec, addr)}


_TO = ToSpec(
    domain="ports",
    usage="to <id> <spec> [--force](=open+模板知会)",
    min_args=2,
    pre_before_gate=True,   # 拒投也先开映射(映射已在,人可用)
    pre=_pre,
    deferred_note=lambda c: f"{host_label()}|mode=deferred|domain=ports|端口映射 {c['addr']}({c['spec']}) 待达(--force 重发)",
    deferred_msg=lambda c: f"ports: 目标存在操作对话框,已拒投;映射已开 addr={c['addr']};已代记",
    deferred_payload=lambda c: {"status": "deferred", "target": f"{c['m']}:{c['pane']}", "addr": c["addr"]},
    envelope_kw=lambda c: {"addr": c["addr"], "body": f"opened port mapping {c['spec']}"},
    use_line=lambda c, my: c["use"],
    ok_payload=lambda c, st: {"status": st, "target": f"{c['m']}:{c['pane']}", "addr": c["addr"], "spec": c["spec"], "pid": c["pid"]},
    success_msg=lambda c, st: (f"ports: 已投递(target={c['m']}:{c['pane']})(addr={c['addr']};spec={c['spec']};"
                               f"pid={c['pid']};关闭:ports close {c['addr']})"),
    fail_msg=lambda c, st: f"ports: 投递状态 {st}(target={c['m']}:{c['pane']}, addr={c['addr']})",
)


def _to(pos: list[str], g: dict):
    if "--keep" in pos:
        die("usage", "ports 无 --keep(映射常驻至 close,无超时自关)", rc=2)
    run_to("ports", pos, _TO)


VERBS = {"view": _view, "open": _open, "close": _close, "fwd": _fwd, "to": _to}


def ports_main():
    g, verb, pos = flags.bootstrap("ports", manual("ports"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
    handler(pos, g)
