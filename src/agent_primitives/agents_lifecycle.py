"""agent_primitives agents 生命周期(批3R 拆出;批5c hc 化):start / close / reload

start = 命名标准收口(标准形校验 + 全舰队唯一扫;起腿 = hc run --name --cwd,唯一性 hc 管);
close = 优雅退场状态机(/exit 经 hc send → shell exit → 格自消;hc kill 语义有损不作主力);
reload = 同 session 重进(四家 resume 形在册 + 失败回滚裸形;hc 化后落新格,hc run 回新址)。
"""
from __future__ import annotations
import sys
import time

from . import runtime_ctx
from .addressing import resolve, row_of, terms
from .engines import hc_run
from .flags import _val
from .runtime_ctx import die, emit_ok, eprint

# 四家模板面(hc run <模板名> 起对应 agent;hc templates 角色化,批6 收口)
_KIND_TEMPLATE = {"claude": "claude", "codex": "codex", "grok": "grok", "kimi": "kimi", "pi": "pi"}


def run_bg(argv: list[str], timeout: int = 60) -> tuple[object, str]:
    """hc run --bg 起格:回 (CompletedProcess, 新格 hc_address)(stdout RunResult JSON 取 address)。"""
    r = hc_run(*argv, timeout=timeout)
    addr = ""
    try:
        import json as _json
        d = _json.loads(r.stdout or "{}")
        addr = str(d.get("address") or "") if isinstance(d, dict) else ""
    except Exception:
        addr = ""
    return r, addr


def start(pos: list[str], g: dict):
    """agents start <名> --kind <类> [--cwd DIR] [--machine 机]
    起腿 hc 化(命运表重塑):hc run <模板名> --name <名> --cwd <DIR> [--on <机>]。"""
    if not pos:
        die("usage", "start <名> --kind <类> [--cwd DIR] [--machine 机]", rc=2)
    name = pos[0]
    import re as _re
    # 命名标准定稿:start 拒新非标形(标准形禁下划线);唯一扫 = hc ls 一发(hc run --name 亦自拒)
    if not _re.match(r"^[a-z][a-z0-9-]{0,30}-(claude|codex|grok|kimi|pi)(-[0-9]{1,2})?$", name):
        die("usage", f"起名「{name}」非标准形(标准 = 台标签-agent类型-编号,字母开头禁下划线,编号 1-99 出生序号)",
            "存量名兼容在册;新起照标准形(如 myws-claude-1)", rc=2)
    if any((r.get("name") or "") == name for r in terms(refresh=True)):
        die("usage", f"起名「{name}」与在役 agent 撞名(全舰队唯一扫)",
            "agents view 查全局格表换名", rc=2)
    kind = _val(pos, "--kind", "claude")
    cwd = _val(pos, "--cwd", "")
    m = _val(pos, "--machine", "")
    template = _KIND_TEMPLATE.get(kind)
    if not template:
        die("usage", f"kind「{kind}」不在四家面(claude/codex/grok/kimi/pi)", rc=2)
    argv = ["run", "--bg", "--name", name]
    if cwd:
        argv += ["--cwd", cwd]
    if m and m not in ("", "local"):
        argv += ["--on", m]
    argv += [template]
    r, addr = run_bg(argv)
    if r.returncode != 0:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
    print((r.stdout or "").strip()[:600] or f"agents: 已起 {name}({kind}){f' @{addr}' if addr else ''}")
    emit_ok({"status": "delivered", "target": f"{m or 'local'}:{name}", "kind": kind,
             "pane": addr})


def close(pos: list[str], g: dict):
    """agents close <id>:优雅退场状态机(/exit 会话持久化 → shell exit 格自消)。
    hc kill 语义有损(挂断+升级,非优雅),只作末段兜底(命运表保留裁定)。"""
    if not pos:
        die("usage", "close <id>(agent 优雅退场后 shell exit,格自消)", rc=2)
    m, addr = resolve(pos[0])
    row = row_of(addr, refresh=False) or {}
    # 1) agent 在跑 -> 优雅退场(/exit 会话持久化)
    if row.get("agent") and row.get("state") == "live":
        hc_run("send", addr, "/exit", timeout=30)
        for _ in range(15):
            time.sleep(2)
            r2 = row_of(addr)
            if not r2 or r2.get("state") != "live" or not r2.get("agent"):
                break
    # 2) 裸格输入 exit(shell 退出格自消);仍在则 hc kill 兜底
    hc_run("send", addr, "exit", timeout=15)
    for _ in range(10):
        time.sleep(1)
        r2 = row_of(addr)
        if not r2 or r2.get("state") != "live":
            print(f"agents: 已关 {m}:{addr.rsplit('/', 1)[-1]}(shell exit,格自消)")
            emit_ok({"status": "delivered", "target": f"{m}:{addr.rsplit('/', 1)[-1]}", "method": "shell-exit"})
            return
    rk = hc_run("kill", addr, timeout=15)
    if rk.returncode == 0:
        print(f"agents: 已关 {m}:{addr.rsplit('/', 1)[-1]}(hc kill 兜底)")
        emit_ok({"status": "delivered", "target": f"{m}:{addr.rsplit('/', 1)[-1]}", "method": "kill"})
        return
    die("engine_fail", f"close {m}:{addr.rsplit('/', 1)[-1]} 退场与兜底皆败:{(rk.stderr or rk.stdout or '').strip()[:80]};下一步:agents view 人工核", rc=1)


def reload(pos: list[str], g: dict):
    """agents reload <id>:无痛刷新(退出 agent -> 同 session 重进 -> 技能/插件重载)
    原语自修正:名字自动矫正;重进失败自动回滚裸形。hc 化注记:重进落新格(hc run 回新址)。"""
    if not pos:
        die("usage", "reload <id>(同会话重进,重载技能与插件;重载铁律:旧进程等于旧技能)", rc=2)
    m, addr = resolve(pos[0])
    ag = row_of(addr, refresh=False)
    if not ag or not ag.get("agent") or ag.get("state") != "live":
        die("not_found", f"{m}:{addr.rsplit('/', 1)[-1]} 无 agent 在跑", [{"command": "agents view", "description": "查全局格表"}])
    # 可翻门:idle/done 皆可翻(done = 活完等单);working/blocked 拒,--force 过
    st = ag.get("agent_status") or "unknown"
    if st not in ("idle", "done") and not runtime_ctx.FORCE:
        die("deferred",
            f"reload 目标状态 {st}(非 idle),翻台拒绝;下一步:候其 idle 再 reload,或 --force 强翻",
            [{"command": "agents read " + pos[0], "description": "看目标在做什么"}], rc=1)
    kind = ag.get("agent") or "claude"
    # 台标签退化 cwd 仓名(hc 化后无 workspace 面,label 走 cwd 派生)
    import re as _re2
    label = (ag.get("cwd") or "").replace("\\", "/").rstrip("/").split("/")[-1]
    label = _re2.sub(r"[^a-z0-9-]", "-", (label or "ws").lower())[:20] or "ws"
    # 名字保真:存量名一律保名重用,防身份断裂;无名字才派生标准形
    raw = ag.get("name") or ""
    if raw and _re2.match(r"^[a-z0-9_][a-z0-9_-]{0,31}$", raw):
        name = raw
    elif raw:
        name = _re2.sub(r"[^a-z0-9_-]", "-", raw.lower())[:32].strip("-") or f"{label}-{kind}-1"
    else:
        name = f"{label}-{kind}-1"
    if name != raw:
        eprint(f"agents: 名字「{raw}」不合规则,自修正为「{name}」(信封披露 old-name={raw})")
    # 1) 干净退场;CC 带任务格 /exit 弹三选一(Exit and stop tasks),扫屏选 1 + enter
    hc_run("send", addr, "/exit", timeout=30)
    for _ in range(8):  # 对话框扫描窗 16s
        time.sleep(2)
        rr = hc_run("read", addr, "--lines", "12", timeout=10)
        if "Exit and stop tasks" in (rr.stdout or ""):
            hc_run("keys", addr, "1", timeout=10)
            time.sleep(1)
            hc_run("keys", addr, "enter", timeout=10)
            break
    exited = False
    for _ in range(30):  # 肥会话(数十万 token)/exit 落盘慢,窗 60s
        time.sleep(2)
        r2 = row_of(addr)
        if not r2 or r2.get("state") != "live" or not r2.get("agent"):
            exited = True
            break
    if not exited:
        die("engine_fail", f"{m}:{addr.rsplit('/', 1)[-1]} 退出超时(60s);下一步:人工查屏(该家 TUI 退出形可能非 /exit)", rc=1)
    # 2) 同 session 重进:hc run <kind> --cwd <原cwd> --name <保名>;resume 形作 CLI 首参
    rargs = {"claude": ["--resume"], "codex": ["resume", "--last"],
             "grok": ["--continue"], "kimi": ["--continue"]}.get(kind)
    if not rargs:
        die("usage", f"kind「{kind}」无 resume 形在册;下一步:人工重进后 agents start 补名", rc=2)
    cwd = ag.get("cwd") or ""
    post_keys = ["enter"] if kind == "claude" else []  # claude: 选择画面回车接最近

    def _started(new_addr: str, wait_s: int = 20) -> bool:
        # 新格注册轮询(hc 探测窗缺省 30s;claude 插件/MCP 启动面常超窗)
        for _ in range(max(1, wait_s // 2)):
            r2 = row_of(new_addr)
            if r2 and r2.get("state") == "live" and r2.get("agent"):
                return True
            time.sleep(2)
        return False

    def _start(*extra: str, timeout: int = 150):
        argv = ["run", "--bg", "--name", name]
        if cwd:
            argv += ["--cwd", cwd]
        if m and m not in ("", "local"):
            argv += ["--on", m]
        argv += [kind] + list(extra)
        return run_bg(argv, timeout=timeout)

    r, new_addr = _start(*rargs)
    ok = r.returncode == 0
    fresh = False
    if not ok and new_addr and _started(new_addr):
        ok = True
        eprint("agents: start 回执超时但格上 agent 已在起(恢复慢于探测窗,非失败;不回滚)")
    elif not ok:
        eprint(f"agents: resume 形重进失败,首发回执:{(r.stderr or r.stdout or '').strip()[:200]}")
        eprint("agents: 自回滚裸形(新会话)再试")
        r, new_addr = _start()
        fresh = True
        ok = (r.returncode == 0) or bool(new_addr and _started(new_addr))
    # claude 形:agent 就绪即在选择画面,补 ENTER 击键接最近会话
    if ok and not fresh and post_keys and new_addr:
        time.sleep(3)
        for k in post_keys:
            hc_run("keys", new_addr, k, timeout=15)
    if r.returncode != 0 and not ok:
        die("engine_fail", (r.stderr or r.stdout or "").strip()[:200], rc=1)
    print((r.stdout or "").strip()[:400] or f"agents: 已重进 {name}({kind}){f' @{new_addr}' if new_addr else ''}")
    emit_ok({"status": "delivered" if ok else "engine_fail",
             "target": f"{m}:{addr.rsplit('/', 1)[-1]}", "kind": kind, "name": name,
             "pane": new_addr,
             "resume": (" ".join(rargs) if not fresh else "fresh-session") if ok else "none"})
    if not ok:
        sys.exit(1)
