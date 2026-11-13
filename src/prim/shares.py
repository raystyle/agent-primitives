"""prim shares 域(批3R 自 domains 拆出):文件域,S3 中转(引擎 s5;内容哈希键)"""
from __future__ import annotations
import hashlib
import json
import os
import sys

from . import flags
from .deliver import ToSpec, run_to
from .engines import s5_is_wsl, s5_ls, s5_run
from .identity import host_label
from .manual import manual
from .runtime_ctx import die, emit_ok


def shares_put(filepath: str) -> str:
    if not os.path.isfile(filepath):
        die("usage", f"文件不存在:{filepath}", rc=2)
    h = hashlib.md5(open(filepath, "rb").read(65536)).hexdigest()[:10]
    base = os.path.basename(filepath)
    key = f"share/{host_label()}/{h}/{base}"
    from .engines import wsl_path
    r = s5_run("put", wsl_path(filepath) if s5_is_wsl() else filepath, key)
    if r.returncode != 0:
        die("engine_fail", f"s5 put 失败:{(r.stderr or '').strip()[:120]}", rc=1)
    return key


def _view(pos: list[str], g: dict):
    print("-- share 资源(share/ 前缀):")
    for x in s5_ls("share/"):
        print(json.dumps(x, ensure_ascii=False))


def _put(pos: list[str], g: dict):
    if not pos:
        die("usage", "put <文件>", rc=2)
    key = shares_put(pos[0])
    print(f"shares: 已上架 {key}")
    emit_ok({"status": "delivered", "key": key})


def _get(pos: list[str], g: dict):
    if not pos:
        die("usage", "get <键> [--output 名]", rc=2)
    key = pos[0]
    out = None
    if "--output" in pos and pos.index("--output") + 1 < len(pos):
        out = pos[pos.index("--output") + 1]
    elif "-o" in pos and pos.index("-o") + 1 < len(pos):
        out = pos[pos.index("-o") + 1]
    if not out:
        out = key.split("/")[-1]
    from .engines import wsl_path
    r = s5_run("get", "-o", wsl_path(out) if s5_is_wsl() else out, key)
    if r.returncode != 0:
        die("engine_fail", f"s5 get 失败:{(r.stderr or '').strip()[:120]}", rc=1)
    if s5_is_wsl():
        from .engines import host_path
        out = host_path(out)
    print(f"shares: 已取回 {out}")
    emit_ok({"status": "delivered", "key": key, "output": out})


def _pre(m: str, pane: str, pos: list[str]) -> dict:
    # 先上架再判 blocked(研究裁定:文件已在,人可取)
    return {"key": shares_put(pos[1])}


_TO = ToSpec(
    domain="shares",
    usage="to <id> <文件> [--force]",
    min_args=2,
    pre_before_gate=True,
    pre=_pre,
    deferred_note=lambda c: f"{host_label()}|mode=deferred|domain=shares|文件 {c['key']} 待达(--force 重发)",
    deferred_msg=lambda c: f"shares: 目标存在操作对话框,已拒投;文件已上架 {c['key']};已代记 room/deferred/{c['pane']}",
    deferred_payload=lambda c: {"status": "deferred", "target": f"{c['m']}:{c['pane']}", "key": c["key"]},
    envelope_kw=lambda c: {"key": c["key"], "name": os.path.basename(c["pos"][1])},
    use_line=lambda c, my: f"agents to {my} reply",
    ok_payload=lambda c, st: {"status": st, "target": f"{c['m']}:{c['pane']}", "key": c["key"], "name": os.path.basename(c["pos"][1])},
    success_msg=lambda c, st: f"shares: 已投递,目标已开始处理(target={c['m']}:{c['pane']}, key={c['key']})",
    fail_msg=lambda c, st: f"shares: 投递 {st}({c['m']}:{c['pane']})key={c['key']}",
)

VERBS = {"view": _view, "put": _put, "get": _get,
         "to": lambda pos, g: run_to("shares", pos, _TO)}


def shares_main():
    g, verb, pos = flags.bootstrap("shares", manual("shares"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is None:
        die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
    handler(pos, g)
