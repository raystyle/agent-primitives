"""prim agents 生命周期(批3R 自 cli 拆出):start / close / reload

start = 命名标准收口(标准形校验 + 全舰队唯一扫);close = 优雅退场状态机
(/exit -> pane run exit -> 格自消);reload = 同格同 session 重进(四家 resume 形
在册 + 失败回滚裸形 + 启动后阻塞检测,v3.1.5/3.1.6 两轮根修)。
"""
from __future__ import annotations
import sys
import time

from . import runtime_ctx
from .addressing import _agents_of, _machine_labels, resolve
from .engines import herdr_json, herdr_run, _json_field
from .flags import _val
from .runtime_ctx import die, emit_ok, eprint


def start(pos: list[str], g: dict):
    # agents start <名> --kind <类> [--pane host:pane] [--cwd DIR] [--machine 机]
    if not pos:
        die("usage", "start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机]", rc=2)
    name = pos[0]
    import re as _re
    # 命名标准定稿(2026-10-15 用户裁六项):start 拒新非标形(标准形禁下划线,
    # 从右解析恒成立);起名时全舰队唯一扫(herdr 只保本机 live 唯一)
    if not _re.match(r"^[a-z][a-z0-9-]{0,30}-(claude|codex|grok|kimi|pi)(-[0-9]{1,2})?$", name):
        die("usage", f"起名「{name}」非标准形(标准 = 台标签-agent类型-编号,字母开头禁下划线,编号 1-99 出生序号)",
            "存量名兼容在册;新起照标准形(如 myws-claude-1)", rc=2)
    taken = {(a.get("name") or "") for a in _agents_of(None)}
    for lab in _machine_labels():
        taken |= {(a.get("name") or "") for a in _agents_of(lab, timeout=8)}
    if name in taken:
        die("usage", f"起名「{name}」与在役 agent 撞名(全舰队唯一扫)",
            "agents view 查全局格表换名", rc=2)
    kind = _val(pos, "--kind", "claude")
    pane = _val(pos, "--pane", "")
    m = _val(pos, "--machine", "")
    # 消费掉旗标与其值,余位 = AGENT_ARGS 透传(经 -- 逃生口进的正文也算)
    consumed = set()
    for i, p in enumerate(pos):
        if p in ("--kind", "--pane", "--machine", "--cwd"):
            consumed.add(i)
            if i + 1 < len(pos):
                consumed.add(i + 1)
    agent_args = [p for i, p in enumerate(pos) if i not in consumed]
    if pane and ":" in pane:
        pre = pane.split(":", 1)[0]
        if pre == "local" or pre in _machine_labels():
            if pre != "local":
                m = m or pre
            pane = pane.split(":", 1)[1]
    args = ["agent", "start", name, "--kind", kind]
    if pane:
        args += ["--pane", pane]
    if agent_args:
        args += ["--"] + agent_args
    r = herdr_run(None if m in ("", "local") else m, *args)
    print(r.stdout or r.stderr)
    sys.exit(r.returncode)


def close(pos: list[str], g: dict):
    # agents close <id>:关格,全 herdr 原生零击杀
    # 序 = agent 优雅退(/exit 持久化)-> 裸格 pane run "exit"(原子送文本+回车)-> 格随 shell 退出自消
    # (evo 批③:写盘中丢稿面已消——本形恒先 /exit 优雅退,shell exit 只是末步;--force 不再需要杀语义)
    if not pos:
        die("usage", "close <id>(agent 优雅退场后 shell exit,格自消)", rc=2)
    m, pane = resolve(pos[0])
    route = None if m in ("", "local") else m
    ag = next((a for a in _agents_of(route) if a.get("pane_id") == pane), None)
    # 1) agent 在跑 -> 优雅退场(/exit 会话持久化,--continue 可接回)
    if ag and ag.get("agent"):
        herdr_run(route, "agent", "prompt", pane, "/exit", timeout=30)
        for _ in range(15):
            time.sleep(2)
            if not any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
                break
    # 2) 裸格输入 exit(pane run = 原子文本+回车),shell 退出格自消
    r = herdr_run(route, "pane", "run", pane, "exit", timeout=15)
    if r.returncode != 0:
        # 兜底:末格尝试 workspace close(herdr 原生)
        ws_id = (ag or {}).get("workspace_id") or ""
        if not ws_id:
            rg = herdr_run(route, "pane", "get", "--pane", pane)
            ws_id = _json_field(rg.stdout, "pane", "workspace_id")
        if ws_id:
            herdr_run(route, "workspace", "close", ws_id)
        else:
            die("engine_fail", f"close {m}:{pane} 面上 exit 与台收皆败:{(r.stderr or r.stdout).strip()[:80]};下一步:agents view 人工核", rc=1)
    for _ in range(10):
        time.sleep(1)
        if pane not in {a.get("pane_id") for a in _agents_of(route)}:
            print(f"agents: 已关 {m}:{pane}(shell exit,格自消)")
            emit_ok({"status": "delivered", "target": f"{m}:{pane}", "method": "pane-run-exit"})
            return
    die("engine_fail", f"close {m}:{pane} 10s 内格未消;下一步:agents view 复核", rc=1)


def reload(pos: list[str], g: dict):
    """agents reload <id>:无痛刷新(退出 agent -> 同格同 session 重进 -> 技能/插件重载)
    原语自修正:名字自动按 herdr 规则矫正;重进失败自动回滚试裸形。"""
    if not pos:
        die("usage", "reload <id>(同会话重进,重载技能与插件;重载铁律:旧进程等于旧技能)", rc=2)
    m, pane = resolve(pos[0])
    route = None if m in ("", "local") else m
    ag = next((a for a in _agents_of(route) if a.get("pane_id") == pane), None)
    if not ag:
        die("not_found", f"{m}:{pane} 无 agent 在跑", [{"command": "agents view", "description": "查全局格表"}])
    # 可翻门(2026-10-13 idle 门,2026-10-15 修):idle/done 皆可翻(done = 活完等单,
    # 与 idle 同为安全态;互相翻台批实证 done 被拒是误伤);working/blocked 拒,--force 过
    st = ag.get("agent_status") or "unknown"
    if st not in ("idle", "done") and not runtime_ctx.FORCE:
        die("deferred",
            f"reload 目标状态 {st}(非 idle),翻台拒绝;下一步:候其 idle 再 reload,或 --force 强翻",
            [{"command": "agents read " + pos[0], "description": "看目标在做什么"}], rc=1)
    kind = ag.get("agent") or "claude"
    # 台标签真源 = herdr workspace label(用户令 2026-10-13:herdr api 可自定义);退化 cwd 仓名
    label = ""
    for w in herdr_json(route, "workspace", "list"):
        if isinstance(w, dict) and w.get("workspace_id") == ag.get("workspace_id"):
            label = w.get("label") or ""
            break
    if not label:
        label = (ag.get("cwd") or "").replace("\\", "/").rstrip("/").split("/")[-1]
    import re as _re2
    label = _re2.sub(r"[^a-z0-9-]", "-", (label or "ws").lower())[:20] or "ws"
    # 编号 = 出生序号(命名标准 2026-10-15 裁 2):该台该类型现役最大号 + 1,不复用
    _pref = f"{label}-{kind}-"
    _seqs = [int(_m.group(1)) for a0 in _agents_of(None)
             if (a0.get("name") or "").startswith(_pref)
             and (_m := _re2.match(rf"^{_re2.escape(_pref)}([0-9]{{1,2}})$", a0["name"]))]
    _seq = (max(_seqs) + 1) if _seqs else 1
    raw = ag.get("name") or f"{_pref}{_seq}"
    # 名字保真(用户令 + evo 批②):存量名(含下划线非标形)一律保名重用,防身份断裂;
    # 仅无名字才派生标准形;非法字符名才自修正并信封披露 old-name
    if raw and _re2.match(r"^[a-z0-9_][a-z0-9_-]{0,31}$", raw):
        name = raw
    elif raw:
        name = _re2.sub(r"[^a-z0-9_-]", "-", raw.lower())[:32].strip("-") or f"{label}-{kind}-1"
    else:
        name = f"{label}-{kind}-1"
    if name != raw:
        eprint(f"agents: 名字「{raw}」不合 herdr 规则,自修正为「{name}」(信封披露 old-name={raw})")
    # 1) 干净退场;CC 带任务格 /exit 弹三选一(Exit and stop tasks),扫屏选 1 + enter
    herdr_run(route, "agent", "prompt", pane, "/exit", timeout=30)
    for _ in range(8):  # 对话框扫描窗 16s
        time.sleep(2)
        rr = herdr_run(route, "agent", "read", pane, "--source", "visible", "--lines", "12", timeout=10)
        if "Exit and stop tasks" in (rr.stdout or ""):
            herdr_run(route, "agent", "send-keys", pane, "1", timeout=10)
            time.sleep(1)
            herdr_run(route, "agent", "send-keys", pane, "enter", timeout=10)
            break
    exited = False
    for _ in range(30):  # 肥会话(数十万 token)/exit 落盘慢,窗 30s 放宽 60s
        time.sleep(2)
        if not any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
            exited = True
            break
    if not exited:
        die("engine_fail", f"{m}:{pane} 退出超时(60s);下一步:人工查屏(该家 TUI 退出形可能非 /exit)", rc=1)
    # 2) 同 session 重进(四家 resume 形在册);失败自回滚裸形再试一次
    # claude 形根修(2026-10-14 实证定谳):/exit 后 daemon 把会话留成后台
    # (--fork-session --resume 进程在册),--continue 撞「最近会话在后台跑」即拒;
    # 正形 = --resume 出会话选择画面,补一发 Enter 接最近会话(用户裁定 2026-10-14)
    rargs = {"claude": ["--resume"], "codex": ["resume", "--last"],
             "grok": ["--continue"], "kimi": ["--continue"]}.get(kind)
    if not rargs:
        die("usage", f"kind「{kind}」无 resume 形在册;下一步:人工重进后 agents start 补名", rc=2)
    post_keys = ["enter"] if kind == "claude" else []  # claude: 选择画面回车接最近

    def _pane_started(wait_s: int = 20) -> bool:
        # claude 启动面(插件/MCP 加载)常超 herdr 探测窗;轮询等注册而非单探
        for _ in range(max(1, wait_s // 2)):
            if any(a.get("pane_id") == pane and a.get("agent") for a in _agents_of(route)):
                return True
            time.sleep(2)
        return False

    def _start(*extra: str, timeout: int = 150, startup_ms: int = 120000) -> "subprocess.CompletedProcess":
        # herdr 探测窗缺省 30s;claude 插件/MCP 启动面常超窗 -> 提到 120s(批147 根因)
        return herdr_run(route, "agent", "start", name, "--kind", kind, "--pane", pane,
                         "--timeout", str(startup_ms),
                         *(["--", *extra] if extra else []), timeout=timeout)

    r = _start(*rargs)
    # 判定以 herdr 回执 JSON 为准(其退出码恒 0,timeout 也走 stdout error 形,rc 不可信)
    ok = "agent_started" in (r.stdout or "")
    fresh = False
    if not ok and _pane_started():
        # herdr startup 探测窗超时/瞬态失败,但格上 agent 已在起;不回滚
        ok = True
        eprint("agents: start 回执超时但格上 agent 已在起(恢复慢于探测窗,非失败;不回滚)")
    elif not ok:
        eprint(f"agents: resume 形重进失败,首发回执:{(r.stderr or r.stdout or '').strip()[:200]}")
        eprint("agents: 自回滚裸形(新会话)再试")
        r = _start()
        fresh = True
        ok = ("agent_started" in (r.stdout or "")) or _pane_started()
    # claude 形:agent 就绪即在选择画面,补 ENTER 击键接最近会话(agent send-keys 面)
    if ok and not fresh and post_keys:
        time.sleep(3)
        for k in post_keys:
            herdr_run(route, "agent", "send-keys", pane, k, timeout=15)
    print(r.stdout or r.stderr)
    emit_ok({"status": "delivered" if ok else "engine_fail",
             "target": f"{m}:{pane}", "kind": kind, "name": name,
             "resume": (" ".join(rargs) if not fresh else "fresh-session") if ok else "none"})
    if not ok:
        sys.exit(1)
