"""machines 域(批5c CONTRACT-v2):机册 + runtime,hc machine.* 直通 + ark runtime 子面

动词面(view / add / reconnect / run / close / runtime;含退役可见化 stub):
- view/list → hc machine ls --json(直通,净删可达性二次探测:state 字段 hc 自带)
- add → hc machine add --install(直通);reconnect → hc machine login(帮助文自证)
- run/close → hc send/kill machine/t(直通;跨机寻址 = machine/ 前缀)
- runtime(s) → ark 子面(保留;ssh 腿换 hc exec --on,机册三台内)
- 退役 stub:status(并入 view)/rename/remove(hc 直令)/enable/disable(hc 机册无启停态,
  需求再现做本地标记)/pane(对象消失,拓扑归 mod)
机册裁定(批3):三台常驻 hc(lan-mac/lan-linux/lan-ubuntu),机册外节点不进册,ssh 行为不变。
"""
from __future__ import annotations
import sys

from .addressing import _machines_raw
from .engines import hc_json, hc_run
from .flags import bootstrap
from .manual import manual
from .runtime_ctx import die, emit_ok, eprint


def _retired(verb: str, see: str):
    """退役动词 stub(废弃可见化,kubectl 式):usage 退 2 + 指新道。"""
    def _h(pos: list[str], g: dict):
        die("usage", f"动词「{verb}」已退役(ADR-0003 重构);{see}", rc=2)
    return _h


def _view(pos: list[str], g: dict):
    # view = 机册表(hc machine ls;state 即可达性,合并面净删)
    ms = _machines_raw()
    if g.get("json"):
        emit_ok({"status": "ok", "count": len(ms), "machines": ms})
        return
    print(f"{'MACHINE':<14} {'STATE':<12} {'TARGET':<24} VERSION")
    for m in ms:
        print(f"{(m.get('name') or '-'):<14} {(m.get('state') or '-'):<12} "
              f"{(m.get('target') or '-'):<24} {(m.get('version') or '-')}")


def _add(pos: list[str], g: dict):
    # 直通 hc machine add(--install 走批量注册判例;参数面 hc 超集)
    if not pos:
        die("usage", "add <ssh-target> [--name <名>] [--install](注册 ssh 节点;--install 远端缺 hc 即装)", rc=2)
    argv = ["machine", "add", pos[0]]
    if "--name" in pos and pos.index("--name") + 1 < len(pos):
        argv += ["--name", pos[pos.index("--name") + 1]]
    if "--install" in pos:
        argv += ["--install"]
    r = hc_run(*argv, timeout=120)
    out = (r.stdout or "").strip()
    if out:
        print(out[:800])
    if r.returncode != 0:
        die("engine_fail", (r.stderr or out).strip()[:300], rc=1)
    emit_ok({"status": "ok", "verb": "add"})


def _reconnect(pos: list[str], g: dict):
    # 直通 hc machine login(Windows 帮助文自证 reconnect 语义)
    if not pos:
        die("usage", "reconnect <机名>", rc=2)
    r = hc_run("machine", "login", pos[0], timeout=60)
    out = (r.stdout or "").strip()
    if out:
        print(out[:400])
    if r.returncode != 0:
        die("engine_fail", (r.stderr or out).strip()[:300], rc=1)
    emit_ok({"status": "ok", "verb": "reconnect", "machine": pos[0]})


def _run(pos: list[str], g: dict):
    # run <机> <格> <命令...>:hc send machine/<格>(贴进格回车;跨机寻址原生)
    (len(pos) >= 3) or die("usage", "run <节点> <格> <命令...>(格内跑命令,hc send)", rc=2)
    machine, pane, cmd = pos[0], pos[1], pos[2:]
    r = hc_run("send", f"{machine}/{pane}", " ".join(cmd), timeout=60)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
    emit_ok({"status": "ok", "machine": machine, "pane": pane, "cmd": cmd})


def _close(pos: list[str], g: dict):
    # close <机> <格>:hc kill machine/<格>(直关;agent 在跑请先 agents close 走优雅退场)
    (len(pos) >= 2) or die("usage", "close <节点> <格>(直关格;agent 在跑请先 agents close 走优雅退场)", rc=2)
    machine, pane = pos[0], pos[1]
    r = hc_run("kill", f"{machine}/{pane}", timeout=30)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
    print(f"machines: 已关 {machine}/{pane}")
    emit_ok({"status": "ok", "machine": machine, "pane": pane, "closed": True})


def _runtime(pos: list[str], g: dict):
    # runtime 子面:agent 运行时环境检查与管理,骑 ark;栈真源 = 仓根 runtimes.toml
    from .runtimes import runtime_main
    runtime_main(pos, g)


VERBS: dict = {
    "view": _view,
    "add": _add, "reconnect": _reconnect,
    "run": _run, "close": _close,
    "runtime": _runtime,
    # ---- 退役可见化(命运表;stub 不删,help/CTA 指新道) ----
    "status": _retired("status", "状态面并入 machines view(hc machine ls 的 state 字段)"),
    "list": _retired("list", "清单即 view(动词标准统一 2026-11-16)"),
    "runtimes": _retired("runtimes", "复数别名删,单数 runtime(动词标准统一 2026-11-16)"),
    "rename": _retired("rename", "直令 hc machine rename <机> <新名>"),
    "remove": _retired("remove", "直令 hc machine rm <机>"),
    "enable": _retired("enable", "三台常驻机册裁定(ADR-0003):hc 机册无启停态,需求再现做本地标记"),
    "disable": _retired("disable", "三台常驻机册裁定(ADR-0003):hc 机册无启停态,需求再现做本地标记"),
    "pane": _retired("pane", "herdr pane 子面对象消失(hc 面 = 终端面);拓扑归 mod GUI"),
}


def machines_main():
    g, verb, pos = bootstrap("machines", manual("machines"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」(view/add/reconnect/run/close/runtime);--llms 看手册", rc=2)
    return handler(pos, g)
