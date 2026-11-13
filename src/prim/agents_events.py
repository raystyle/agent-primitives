"""prim agents 事件道(批3R 自 cli 拆出):read / to / wait / inbox

to = 自由文投递(无模板,CONTRACT 六)+ dm 双写镜像(3.9.0 事件道)+ engine_fail
定向诊断(3.9.1);wait/inbox = dm 流入站信封事件面(引擎级轮询,agent 不再盲等)。
"""
from __future__ import annotations
import sys
import time

from .addressing import _agents_of, resolve, target_status
from .engines import herdr_run, s5_append, s5_tail, s5_tail_streams
from .flags import _val
from .gating import deliver_prompt, gate
from .identity import _my_alias, caller_addr, host_label
from .runtime_ctx import die, emit_ok, eprint


def read(pos: list[str], g: dict):
    # 收件面(隐式):读格内容;目标在跑则内候到闲/完成或超时;状态随出
    if not pos:
        die("usage", "read <id> [--lines N] [--timeout S]", rc=2)
    m, pane = resolve(pos[0])
    lines = _val(pos, "--lines", "20")
    try:
        secs = int(_val(pos, "--timeout", "90"))
    except ValueError:
        die("usage", "--timeout 须为秒数", rc=2)
    deadline = time.time() + secs
    route = None if m in ("", "local") else m
    while True:
        st = target_status(m, pane)
        r = herdr_run(route, "agent", "read", pane,
                      "--source", "recent-unwrapped", "--lines", lines, timeout=max(secs, 5) + 10)
        content = (r.stdout or "").strip()
        if st != "working" or time.time() >= deadline:
            if content:
                print(content)
                emit_ok({"status": "timeout-working" if st == "working" else st, "target": f"{m}:{pane}"})
            else:
                die("engine_fail", f"read {m}:{pane} 无内容且状态 {st};目标可能清屏或引擎忙,--timeout 加长重试", rc=1)
            break
        time.sleep(5)


def to(pos: list[str], g: dict):
    """agents to:自由文无模板,不走 deliver.run_to(dm 镜像与定向诊断是本域独有面)。"""
    if len(pos) < 2:
        die("usage", f"to <id> <文本> [--force]", rc=2)
    m, pane = resolve(pos[0])
    text = " ".join(pos[1:])
    blocked = gate(m, pane)
    if blocked:
        try:
            s5_append(f"room/deferred/{pane}", f"{host_label()}|mode=deferred|domain=agents|「{text[:80]}」待投递(--force 重发)")
            eprint(f"agents: 目标存在操作对话框,已拒投并代记 room/deferred/{pane};下一步:--force 跳过门控重发")
        except Exception:
            eprint(f"agents: 目标存在操作对话框,已拒投;下一步:--force 重发,或以 streams append 记流")
        emit_ok({"status": "deferred", "target": f"{m}:{pane}"})
        sys.exit(1)
    from .msg import MsgEnvelope
    src = caller_addr()
    src_host, src_agent = (src.split(":", 1) + [""])[:2]
    dst_alias0 = next((a.get("name") for a in _agents_of(None if m in ("", "local") else m)
                       if a.get("pane_id") == pane), None)
    dst_c0 = (f"{host_label() if m in ('', 'local') else m}:{dst_alias0}" if dst_alias0 else pos[0])
    env = MsgEnvelope(domain="agents", src_host=src_host, src_pane=src_agent,
                      dst=dst_c0, body=text)
    # 双轨制(用户令 2026-10-15):from=机器:agent别名,取用行 = bare alias直答
    _alias = _my_alias()
    use = (f"agents to {_alias} reply" if _alias
           else (f"agents to {src_host}:{src_agent} reply" if src_agent
                 else f"agents view, locate the sender pane on {src_host}, then agents to <node:agent-alias> reply"))
    st = deliver_prompt(m, pane, env.render(use))
    if st == "delivered":
        # dm 双写(2026-10-23 用户令:agents 绑定 streams,回信事件道):
        # 出站信封镜像进 dm 对流,对端回信同样镜像,wait/inbox 即事件面
        # 3.9.1 修:pair 走 canonical 目标(机:别名,格回退),同一收方不同写法同一条流,不再劈叉
        try:
            me_host = src_host if src_host != "local" else host_label()
            me_c = f"{me_host}:{_alias}" if _alias else me_host
            pair = sorted([me_c, dst_c0])
            one_line = f"{env.fieldline()} | {env.body} | {use}"
            s5_append(f"dm/{pair[0]}/{pair[1]}", one_line)
        except Exception:
            pass  # 镜像失败不拦投递主面(wait 面自然缺此条,主投递不受损)
        print(f"agents: 已投递,目标已开始处理(target={m}:{pane})")
        emit_ok({"status": st, "target": f"{m}:{pane}"})
    else:
        # 3.9.1 修:engine_fail 定向诊断(远程机在册但别名不在该机 = 寻址错非引擎错)
        if st == "engine_fail" and m not in ("", "local"):
            ags = _agents_of(m)
            names = [a.get("name") or a.get("pane_id") for a in ags if a.get("name")]
            if names:
                eprint(f"agents: {m} 在册但投递失败;该机命名格:{', '.join(names[:8])};核对 id 或 agents view {m}")
        else:
            eprint(f"agents: 投递状态 {st}(target={m}:{pane});下一步:检查目标与引擎后重试")
        emit_ok({"status": st, "target": f"{m}:{pane}"})
        sys.exit(1)


def wait_inbox(pos: list[str], g: dict, verb: str):
    # 事件驱动收件面(2026-10-23 用户令:文字回信走 streams 事件道):
    # wait = 阻塞等新入站信封(dm 流,引擎级轮询,agent 不再盲等);inbox = 非阻塞收件单
    if not pos:
        pos = []
    me_addr = caller_addr()
    alias_c = _my_alias() or ""
    short = me_addr.split(":", 1)[1] if ":" in me_addr else me_addr
    me_host_c = host_label()
    forms = [f for f in {me_addr, alias_c, short, f"{me_host_c}:{alias_c}" if alias_c else ""} if f]
    fromf = _val(pos, "--from", "")
    streams = []
    for x in s5_tail_streams():
        n = x.get("name", "")
        if n and any(f and f in n for f in forms):
            streams.append(n)
    if not streams:
        if verb == "inbox":
            print("(dm 流无入站;收到 agents to 回信后此处即现)")
            emit_ok({"status": "empty", "streams": []})
        else:
            emit_ok({"status": "timeout", "streams": []})
            sys.exit(1)
        return
    from .msg import parse_fieldline

    def _inbound(body: str) -> bool:
        fl = next((l for l in body.splitlines() if l.startswith("from=")), "")
        if not fl:
            return False  # 非信封条目(streams dm 裸文)不走事件面,streams view 直读
        d = parse_fieldline(fl)
        to, frm = d.get("to", ""), d.get("from", "")
        mine = to in forms or any(to.endswith(":" + f) for f in forms if f)
        if frm == me_addr or frm in forms:
            return False  # 自己的出站镜像
        if fromf and fromf not in frm:
            return False
        return mine

    cursors: dict[str, int] = {}
    for n in streams:
        es = s5_tail(n, 1)
        cursors[n] = es[-1]["seq_num"] if es else 0
    if verb == "inbox":
        shown = 0
        for n in streams:
            for e in s5_tail(n, 20):
                if _inbound(e.get("body") or ""):
                    print(f"== {n} seq={e.get('seq_num')} ==")
                    print(e.get("body") or "")
                    shown += 1
        emit_ok({"status": "listed", "count": shown})
        return
    try:
        secs = int(_val(pos, "--timeout", "300"))
    except ValueError:
        die("usage", "--timeout 须为秒数", rc=2)
    deadline = time.time() + secs
    while time.time() < deadline:
        for n in streams:
            es = s5_tail(n, 50, cursors.get(n, 0))
            for e in es:
                if e.get("seq_num", 0) <= cursors.get(n, 0):
                    continue
                cursors[n] = e.get("seq_num", 0)
                if _inbound(e.get("body") or ""):
                    print(f"== {n} seq={e.get('seq_num')} ==")
                    print(e.get("body") or "")
                    emit_ok({"status": "received", "stream": n, "seq": e.get("seq_num")})
                    return
        time.sleep(2)
    emit_ok({"status": "timeout", "streams": streams})
    sys.exit(1)
