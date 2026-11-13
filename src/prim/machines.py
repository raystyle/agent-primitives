"""machines 域:herdr machine 系列封装(第九原语;2026-10-24 ADR-0007 由 nodes 更名,nodes 别名已淘汰)

machine = 舰队节点(ssh 注册的远端 herdr 实例)。动词面与 herdr machine
一一对应:list/status/add/rename/remove/enable/disable/reconnect;机册真源
在 herdr(win 侧),本域是机册管理的原语面(agents.machines 只是只读快照)。
"""
from __future__ import annotations
from . import core
import json
import os
import sys
from .core import die, emit_ok, eprint, herdr_json, herdr_run

# herdr machine 动词透传族(label 寻址优先,profile-id 亦收)
_PASS = {"status", "reconnect", "add", "rename", "remove", "enable", "disable"}


def _machines_raw() -> list[dict]:
    d = herdr_json(None, "machine", "list", "--json")
    if isinstance(d, dict):
        d = d.get("result", {}).get("machines") or d.get("machines") or []
    return [x for x in d if isinstance(x, dict)]


def _lookup(query: str) -> dict | None:
    """label 或 profile-id 寻址一台机。"""
    for m in _machines_raw():
        if m.get("label") == query or m.get("id") == query:
            return m
    return None


def _view(pos: list[str], g: dict):
    # view = list 同面(册表 + 可达性);--json 出原册
    ms = _machines_raw()
    if g.get("json"):
        emit_ok({"status": "ok", "count": len(ms), "machines": ms})
        return
    print(f"{'MACHINE':<14} {'PROFILE-ID':<34} {'SSH':<22} {'SESSION':<10} STATE")
    for m in ms:
        print(f"{(m.get('label') or '-'):<14} {(m.get('id') or '-'):<34} "
              f"{(m.get('target') or '-'):<22} "
              f"{(m.get('session') or 'default'):<10} "
              f"{('enabled' if m.get('enabled', True) else 'disabled')}")
    # 可达性(status 面合并进 view;离线机 fail-soft 不挂整面)
    try:
        st = herdr_json(None, "machine", "status", "--json", timeout=20)
        states = {}
        if isinstance(st, dict):
            st = st.get("result", {}).get("machines") or st.get("machines") or []
        for x in st if isinstance(st, list) else []:
            if isinstance(x, dict):
                states[x.get("label") or x.get("id")] = x.get("status") or x.get("reachable")
        for m in ms:
            lab = m.get("label")
            if lab in states:
                print(f"  {lab}: {states[lab]}")
    except Exception:
        eprint("machines: 可达性探测失败(herdr machine status 不可用);单机详查: machines status <名>")


def _status(pos: list[str], g: dict):
    # 无参 = 全量状态;带参 = 单机(label 或 id)
    args = ["machine", "status"] + (pos if pos else [])
    args += ["--json"]
    r = herdr_run(None, *args, timeout=30)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout).strip()[:200], rc=1)
    try:
        d = json.loads(r.stdout)
        rows = d.get("result", {}).get("machines") or d.get("machines") or []
    except Exception:
        rows = []
    for x in rows if isinstance(rows, list) else []:
        if isinstance(x, dict):
            print(f"{(x.get('label') or '-'):<14} {x.get('status') or x.get('reachable')}")
    emit_ok({"status": "ok", "count": len(rows)})


def _pass(pos: list[str], g: dict, verb: str):
    # 透传族:add/rename/remove/enable/disable/reconnect
    # 写面预检:rename/remove/enable/disable 先解析目标(label 补 id)
    args = ["machine", verb]
    if verb in ("rename", "remove", "enable", "disable", "reconnect") and pos:
        m = _lookup(pos[0])
        args += [m.get("id") if m else pos[0]]
        args += pos[1:]
    else:
        args += pos
    r = herdr_run(None, *args, timeout=60)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout).strip()[:300], rc=1)
    out = (r.stdout or "").strip()
    if out:
        print(out)
    emit_ok({"status": "ok", "verb": verb})


def _run(pos: list[str], g: dict):
    (len(pos) >= 3) or die("usage", "run <节点> <格> <命令...>(格内跑命令,herdr pane run)", rc=2)
    machine, pane, cmd = pos[0], pos[1], pos[2:]
    r = herdr_run(machine, "pane", "run", pane, *cmd, timeout=60)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout).strip()[:200], rc=1)
    if (r.stdout or "").strip():
        print(r.stdout.strip()[-1500:])
    emit_ok({"status": "ok", "machine": machine, "pane": pane, "cmd": cmd})


def _close(pos: list[str], g: dict):
    (len(pos) >= 2) or die("usage", "close <节点> <格>(直关格;agent 在跑请先 agents close 走优雅退场)", rc=2)
    machine, pane = pos[0], pos[1]
    r = herdr_run(machine, "pane", "close", pane, timeout=30)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout).strip()[:200], rc=1)
    print(f"machines: 已关 {machine}:{pane}")
    emit_ok({"status": "ok", "machine": machine, "pane": pane, "closed": True})


def _pane(pos: list[str], g: dict):
    # pane <节点> <herdr pane 子面...>:list/get/read/split/send-keys/... 直透
    (len(pos) >= 2) or die("usage", "pane <节点> <子面...>(herdr pane 直透)", rc=2)
    machine = pos[0]
    r = herdr_run(machine, "pane", *pos[1:], timeout=60)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout).strip()[:200], rc=1)
    out = (r.stdout or "").strip()
    if out:
        print(out[-3000:])


def _runtime(pos: list[str], g: dict):
    # runtime 子面(用户令 2026-10-17:不立新原语,收 machines 下):agent 运行时环境
    # 检查与管理,骑 ark;栈真源 = 仓根 runtimes.toml(仓 agent 自定);--machine 跨机
    from .runtimes import runtime_main
    runtime_main(pos, g)


VERBS: dict = {
    "view": _view, "list": _view, "status": _status, "runtime": _runtime, "runtimes": _runtime,
    "run": _run, "close": _close, "pane": _pane,
    **{k: (lambda pos, g, _v=k: _pass(pos, g, _v)) for k in _PASS},
}


def machines_main():
    from . import flags
    from .manual import manual
    g, verb, pos = flags.bootstrap(flags.entry_name("machines"), manual("machines"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」(view/status/add/rename/remove/enable/disable/reconnect)", rc=2)
    return handler(pos, g)
