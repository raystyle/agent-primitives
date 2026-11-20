"""agent_primitives tasks 域(批3R 拆出;批5c 并入 streams 子面):持久任务,hst task 全局遥控(引擎 hst)

入口已并入 streams(`streams task view|set|to`,CONTRACT-v2:任务即流);本模块留实现
与内部 VERBS(streams 子面分派 + 判例用例面)。hst 跨机腿 hc 化(命运表:pending 流 +
hc send 唤醒受体,消 herdr plugin action 依赖)。
"""
from __future__ import annotations
import os
import subprocess

from . import flags
from .addressing import _agents_of, _machine_labels
from .deliver import ToSpec, run_to
from .engines import hc_run, s5_append
from .gating import gate
from .identity import host_label
from .manual import manual
from .runtime_ctx import die, emit_ok


def _view(pos: list[str], g: dict):
    # 实时任务面:上半 = fleet 状态总览(hc ls,含远机);下半 = 本机各仓 hst task show 直读;
    # 远机任务文本不经 ssh(零 ssh 纪律),经 agents read <id> 读屏即得
    machine = pos[0] if pos else None
    ags = _agents_of(None if machine in (None, "local") else machine)
    if not machine:
        fleet = [("local", a) for a in ags]
        for lab in _machine_labels():
            fleet += [(lab, a) for a in _agents_of(lab)]
    else:
        fleet = [("local" if machine == "local" else machine, a) for a in ags]
    print(f"{'':<1}{'HOST':<12} {'NAME':<24} {'ST':<5} CWD")
    for host, a in fleet:
        if not a.get("agent"):
            continue
        st = a.get("agent_status", "")
        mark = "*" if st == "working" else " "
        print(f"{mark}{host:<12}{(a.get('name') or a.get('pane_id','')):<24}[{st[:4]}] {a.get('cwd','')}")
    print("-- 本机实时任务(hst task show 直读;远机任务经 agents read <id> 看屏):")
    for host, a in fleet:
        if not a.get("agent") or host != "local":
            continue
        cwd = a.get("cwd") or ""
        if not cwd or cwd == os.path.expanduser("~") or not os.path.isdir(cwd):
            continue
        try:
            ag = a.get("agent") or "claude"
            if os.name == "nt":
                rp = subprocess.run(["hst", "task", "show", "--agent", ag], capture_output=True, text=True,
                                    cwd=cwd, timeout=10, encoding="utf-8", errors="replace")
            else:
                rp = subprocess.run(["bash", "-lc", f"hst task show --agent {ag}"], capture_output=True, text=True,
                                    cwd=cwd, timeout=10, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            continue
        out = (rp.stdout or "").strip()
        if out:
            # 2.15.0 show 首行恒 present 旗;取 task.text 行见「在跑什么」(漂移单 D6)
            tl = next((l for l in out.splitlines() if "task.text" in l), "")
            shown = tl[:100] if tl else ("(无 task)" if "present=false" in out.splitlines()[0] else out.splitlines()[0][:100])
            print(f"  {a.get('name') or a.get('pane_id','')}: {shown}")


def hst_task_set(machine: str, cwd: str, text: str, agent: str = "claude", pane: str = ""):
    """hst task set(本机直跑,--agent 会话隔离;远机走 pending 流 + hc send 唤醒受体)。"""
    import shlex
    if machine in ("", "local"):
        if os.name == "nt":
            # win 直跑 hst.exe + cwd 参(bash 包装道在 win 解析到 WSL bash 会翻车,弃)
            r = subprocess.run(["hst", "task", "set", "--agent", agent, text],
                               capture_output=True, text=True, cwd=cwd, timeout=15,
                               encoding="utf-8", errors="replace")
        else:
            r = subprocess.run(["bash", "-lc", f"hst task set --agent {shlex.quote(agent)} {shlex.quote(text)}"],
                               capture_output=True, text=True, cwd=cwd, timeout=15,
                               encoding="utf-8", errors="replace")
        if r.returncode != 0:
            die("engine_fail", f"hst task set 失败:{(r.stderr or '')[:100]}")
    else:
        # 协议形:pending 流 + hc send 唤醒受体(零 ssh;herdr plugin action 依赖已消)
        import time as _t
        tid = str(_t.time_ns())
        s5_append(f"tasks/pending/{machine}", f"{host_label()}|{text}|{cwd}|{tid}|{agent}")
        if pane:
            addr = f"{machine}/{pane}" if "/" not in pane else pane
            hc_run("send", addr,
                   f"tasks pending 已入流 tasks/pending/{machine}(tid={tid};受体插件 apply)",
                   timeout=30)


def _set(pos: list[str], g: dict):
    """D9:set = OPERATE 只写不扰,绕门控;知会归 to(三段文法)。"""
    if len(pos) < 2:
        die("usage", "set <id> <文本>", rc=2)
    from .addressing import resolve
    m, addr = resolve(pos[0])
    text = " ".join(pos[1:])
    from .addressing import pane_cwd
    cwd = pane_cwd(m, addr)
    _kind = next((x.get("agent") or "claude" for x in _agents_of(m) if x.get("hc_address") == addr), "claude")
    hst_task_set(m, cwd, text, _kind, pane=addr)
    emit_ok({"status": "delivered", "target": f"{m}:{addr.rsplit('/', 1)[-1]}", "task": text})


def _pre(m: str, pane: str, pos: list[str]) -> dict:
    from .addressing import pane_cwd
    text = " ".join(pos[1:])
    cwd = pane_cwd(m, pane)
    _kind = next((x.get("agent") or "claude" for x in _agents_of(m) if x.get("hc_address") == pane), "claude")
    hst_task_set(m, cwd, text, _kind, pane=pane)
    return {"cwd": cwd}


_TO = ToSpec(
    domain="tasks",
    usage="to <id> <文本>",
    min_args=2,
    pre_before_gate=False,   # 拒投不设任务
    exit_on_fail=False,      # 非 delivered 不退 1(冻结行为)
    fail_to_stderr=False,    # 失败面仍是 stdout 单条 print(冻结行为)
    pre=_pre,
    deferred_note=lambda c: f"{host_label()}|mode=deferred|domain=tasks|任务「{' '.join(c['pos'][1:])}」待设(--force 重发)",
    deferred_msg=lambda c: "tasks: 目标存在操作对话框,已拒投并代记",
    deferred_payload=lambda c: {"status": "deferred", "target": f"{c['m']}:{c['pane'].rsplit('/', 1)[-1]}"},
    envelope_kw=lambda c: {"cwd": c["cwd"], "body": " ".join(c["pos"][1:])},
    use_line=lambda c, my: "streams task view",
    ok_payload=lambda c, st: {"status": st, "target": f"{c['m']}:{c['pane'].rsplit('/', 1)[-1]}", "cwd": c["cwd"]},
    success_msg=lambda c, st: f"tasks: 已设置(target={c['m']}, cwd={c['cwd']}) 并投出",
    fail_msg=lambda c, st: f"tasks: 已设置(target={c['m']}, cwd={c['cwd']});投递 {st}",
)

VERBS = {"view": _view, "set": _set,
         "to": lambda pos, g: run_to("tasks", pos, _TO)}


def task_main(pos: list[str], g: dict):
    """streams task 子面分派(CONTRACT-v2:tasks 并入 streams,任务即流)。"""
    from .runtime_ctx import die as _die
    sub = pos[0] if pos else "view"
    rest = pos[1:]
    h = VERBS.get(sub)
    if h is None:
        _die("usage", f"task 未知子动词「{sub}」(view/set/to);--llms 看手册", rc=2)
    return h(rest, g)
