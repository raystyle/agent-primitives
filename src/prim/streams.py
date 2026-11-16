"""prim streams 域(批3R 拆出;批5c CONTRACT-v2):流域,S2 持久流(引擎 s5;room 即房间)
+ tasks 子面(任务即流:`streams task view|set|to`,tasks 入口随入口重组退役)。"""
from __future__ import annotations
import json
import os
import sys

from . import flags
from .deliver import ToSpec, run_to
from .engines import s5_append, s5_cmd, s5_tail, s5_tail_streams
from .identity import _my_alias, host_label
from .manual import manual
from .runtime_ctx import die, emit_ok
from .shares import shares_put


def _file_slice(pos: list[str]) -> tuple[str, str]:
    """--file <文件> [--lines N:M] 抽出:上传入 S3,回 (正文附注, 余参数)。
    日志类文件不整读入消息体:消息只带键引用与切片区间,取用行可直达。"""
    _v = flags.val
    fp = _v(pos, "--file", "")
    if not fp:
        return "", pos
    lines = _v(pos, "--lines", "")
    rest = [p for i, p in enumerate(pos)
            if p not in ("--file", "--lines")
            and (i == 0 or pos[i - 1] not in ("--file", "--lines"))]
    if not os.path.isfile(fp):
        die("usage", f"文件不存在:{fp}", rc=2)
    total = sum(1 for _ in open(fp, "rb"))
    key = shares_put(fp)
    span = f"行 {lines}(共 {total})" if lines else f"共 {total} 行"
    note = f"[文件] {os.path.basename(fp)} -> {key}({span});取文件 shares get {key}"
    from .runtime_ctx import eprint
    eprint(f"streams: 文件已上架 {key}({span})")
    return note, rest


def _retired_rooms(pos: list[str], g: dict):
    die("usage", "动词「rooms」已退役(ADR-0003 重构+动词标准统一 2026-11-16);清单即裸 view(streams view = 房间清单)", rc=2)


def _rooms(pos: list[str], g: dict):
    rooms: dict = {}
    dm_count = 0
    for x in s5_tail_streams():
        n = x.get("name", "")
        if n == "fleet":
            rooms[n] = "全舰队回执主频道"
        elif n.startswith("room/"):
            rooms[n[5:]] = "房间"
        elif n.startswith("dm/"):
            dm_count += 1
    if dm_count:
        rooms["dm"] = f"私信专线族:{dm_count}"
    if not rooms:
        print("(无在册房间;room <名> <消息> 说第一句即建)")
    for n, d in rooms.items():
        print(f"{n:<28} {d}")


def _view(pos: list[str], g: dict):
    # 裸 view = 房间清单(用户裁定 2026-11-16:与 agents/desks/machines 的 view 对齐;rooms 退役)
    plain = [p0 for p0 in pos if not p0.startswith("-")]
    if not plain and "--from" not in pos and "--resume" not in pos:
        return _rooms(pos, g)
    if "-f" in pos or "--follow" in pos:
        stream = next((p0 for p0 in pos if not p0.startswith("-")), "")
        if not stream:
            die("usage", "view <流名> -f(流式跟随,Ctrl+C 退 130)", rc=2)
        import subprocess as sp
        r = sp.call(s5_cmd() + ["tail", stream, "-f"])  # 活透传不捕获
        sys.exit(130 if r in (130, 2) else r)
    stream = pos[0] if pos else None
    seq = None
    n = 100
    resume = "--resume" in pos
    if "--from" in pos and pos.index("--from") + 1 < len(pos):
        seq = int(pos[pos.index("--from") + 1])
    for flag in ("-n", "--lines"):
        if flag in pos and pos.index(flag) + 1 < len(pos):
            n = int(pos[pos.index(flag) + 1])
            break
    if resume:
        cur = os.path.expanduser(os.path.join("~/.local/state/prim/cursor", stream))
        if os.path.isfile(cur):
            seq = int(open(cur).read().strip() or "0")
    print("-- 流列表:")
    for x in s5_tail_streams():
        print(json.dumps(x, ensure_ascii=False))
    if stream:
        rows = s5_tail(stream, n, seq)
        print(f"-- 流「{stream}」读({f'from={seq} ' if seq is not None else ''}最近 {n}):")
        for x in rows:
            print(json.dumps(x, ensure_ascii=False))
        last = rows[-1].get("seq_num") if rows else None
        if last is not None:
            cur = os.path.expanduser(os.path.join("~/.local/state/prim/cursor", stream))
            os.makedirs(os.path.dirname(cur), exist_ok=True)  # 流名含斜杠时父链全建
            open(cur, "w").write(str(last))


def _append(pos: list[str], g: dict):
    if len(pos) < 2:
        # 流式会话(S2 范式):无消息 = stdin 逐行追加(cat x | streams append <流>)
        if len(pos) == 1:
            import subprocess as sp
            r = sp.call(s5_cmd() + ["append", pos[0]])  # stdin 直通
            sys.exit(r)
        die("usage", "append <流> <消息>(或 stdin 管道:cat x | streams append <流>)", rc=2)
    body = f"{host_label()}|{pos[1]}"
    if s5_append(pos[0], body):
        print(f"streams: 已追加 → {pos[0]}")
        emit_ok({"status": "delivered", "stream": pos[0]})
    else:
        die("engine_fail", "s5 append 失败", rc=1)


def _pre(m: str, pane: str, pos: list[str]) -> dict:
    stream, body = pos[1], pos[2]
    if not s5_append(stream, f"{host_label()}|{body}"):
        die("engine_fail", "s5 append 失败", rc=1)
    return {"stream": stream, "body": body}


_TO = ToSpec(
    domain="streams",
    usage="to <id> <流> <消息> [--force]",
    min_args=3,
    pre_before_gate=False,  # 拒投不入流(消息不先 append)
    pre=_pre,
    deferred_note=lambda c: f"{host_label()}|mode=deferred|domain=streams|流 {c['pos'][1]} 消息待递(--force 重发)",
    deferred_msg=lambda c: "streams: 目标存在操作对话框,已拒投并代记",
    deferred_payload=lambda c: {"status": "deferred", "target": f"{c['m']}:{c['pane']}", "stream": c["pos"][1]},
    envelope_kw=lambda c: {"stream": c["stream"], "body": c["body"]},
    use_line=lambda c, my: f"agents to {my} reply (stream {c['stream']} attached)",
    ok_payload=lambda c, st: {"status": st, "target": f"{c['m']}:{c['pane']}", "stream": c["stream"]},
    success_msg=lambda c, st: f"streams: 已投递,目标已开始处理(target={c['m']}:{c['pane']}, stream={c['stream']})",
    fail_msg=lambda c, st: f"streams: 投递状态 {st}(target={c['m']}:{c['pane']})",
)


def _room_dm_rewrite(verb: str, pos: list[str]) -> tuple[str, list[str]]:
    """room/dm 前置改写(用户令 2026-10-15 房间抽象):房间即流,动词面按房间思考。"""
    if verb == "room":
        if not pos:
            die("usage", "room <房名> [消息] [-f] [--file <文件> [--lines N:M]]", rc=2)
        room = pos[0]
        stream = room if room == "fleet" else f"room/{room}"
        if "-f" in pos or "--follow" in pos:
            pos = [p0 for p0 in pos if p0 not in ("-f", "--follow")]
            return "view", [stream, "-f"]
        if len(pos) >= 2:
            note, rest = _file_slice(pos)
            text = " ".join(rest[1:]) if len(rest) >= 2 else ""
            body = " | ".join(x for x in (text, note) if x) or note
            return "append", [stream, body]
        return "view", [stream]
    if verb == "dm":
        if len(pos) < 2:
            die("usage", "dm <对方别名> <消息> [--file <文件> [--lines N:M]]", rc=2)
        peer = pos[0]
        me = _my_alias() or host_label()
        pair = sorted([me, peer])
        stream = f"dm/{pair[0]}/{pair[1]}"
        note, rest = _file_slice(pos)
        text = " ".join(rest[1:]) if len(rest) >= 2 else ""
        body = " | ".join(x for x in (text, note) if x) or note
        return "append", [stream, body]
    return verb, pos


VERBS = {"rooms": _retired_rooms, "view": _view, "append": _append,
         "to": lambda pos, g: run_to("streams", pos, _TO)}


def streams_main():
    g, verb, pos = flags.bootstrap("streams", manual("streams"))
    verb = verb or "view"
    verb, pos = _room_dm_rewrite(verb, pos)
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」(room/dm/view/append/to);--llms 看手册", rc=2)
    handler(pos, g)
