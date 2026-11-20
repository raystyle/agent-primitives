"""agent_primitives 旗标与入口序言(批3R 自 cli/mcps/runtimes 三处合一)

契约(CONTRACT 五d):<命令> [全局旗标] <动词> [动词旗标] [位置参数];全局七旗标
任意槽;-- 逃生口;--force 投递专属任意槽;未知词 usage 退 2 禁静默 shift。
setup 按真实入口名写 runtime_ctx(win shim 带 .exe,splitext 剥)。
"""
from __future__ import annotations
import os
import sys

from . import runtime_ctx

GLOBAL_FLAGS = {"--help": "help", "-h": "help", "--llms": "llms", "--json": "json",
                "--format": "format", "--full-output": "full", "--filter-output": "filter",
                "--schema": "schema"}
DELIVER_FLAG = "--force"


def parse(argv: list[str]) -> tuple[dict, str | None, list[str]]:
    """扫描全部词:全局旗标任意槽抽出;-- 逃生;剩余 = [动词?] + 位置参数。"""
    g: dict = {}
    rest: list[str] = []
    escape = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if escape:
            rest.append(a); i += 1; continue
        if a == "--":
            escape = True; i += 1; continue
        if a in GLOBAL_FLAGS:
            k = GLOBAL_FLAGS[a]
            if k == "format" and i + 1 < len(argv):
                g[k] = argv[i + 1]; i += 2; continue
            if k == "filter" and i + 1 < len(argv):
                g[k] = argv[i + 1]; i += 2; continue
            g[k] = True; i += 1; continue
        if a == DELIVER_FLAG:
            g["force"] = True; i += 1; continue
        rest.append(a); i += 1
    verb = rest[0] if rest and not rest[0].startswith("-") else None
    pos = rest[1:] if verb else rest
    return g, verb, pos


def setup(cmd: str, g: dict):
    runtime_ctx.CMD_NAME = cmd
    runtime_ctx.JSON_MODE = bool(g.get("json") or g.get("format") == "json")
    runtime_ctx.FORCE = bool(g.get("force"))


def handle_globals(g: dict, manual_text: str) -> bool:
    if g.get("help"):
        print(manual_text); sys.exit(0)
    if g.get("llms"):
        print(manual_text); sys.exit(0)
    return False


def entry_name(fallback: str) -> str:
    """真实入口名(win shim 带 .exe,splitext 剥;批2R 信封实名修正的单点)。"""
    return os.path.splitext(os.path.basename(sys.argv[0]))[0] or fallback


def bootstrap(cmd: str, manual_text: str) -> tuple[dict, str | None, list[str]]:
    """域入口序言单点(批3R 收编八处五行序言):parse + setup + handle_globals。
    cmd 传本域入口名(信封实名需求处传 flags.entry_name(<名>)。"""
    g, verb, pos = parse(sys.argv[1:])
    setup(cmd, g)
    handle_globals(g, manual_text)
    return g, verb, pos


# ---------- 动词旗标取值(三套取值器合一;行为各保持原样) ----------

def val(pos: list[str], flag: str, default: str = "") -> str:
    """动词旗标取值:--flag 值 任意槽;--flag=值 前缀形(cli._val 原形)。"""
    if flag in pos:
        i = pos.index(flag)
        if i + 1 < len(pos):
            return pos[i + 1]
    for p in pos:
        if p.startswith(flag + "="):
            return p.split("=", 1)[1]
    return default


# 兼容别名(旧名续命,域模块迁完可收)
_val = val


def flag_value(flag: str):
    """argv 直取 <flag> <值> 或 <flag>=<值>(runtimes 原形)。"""
    for i, a in enumerate(sys.argv):
        if a == flag and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def timeout_flag(g_default: float, cap: float = 600.0) -> float:
    """--timeout 旗标覆盖,上限 cap(mcps 原形,与 vmi-mcp wait 对齐)。"""
    v = flag_value("--timeout")
    if v is not None:
        try:
            return min(float(v), cap)
        except ValueError:
            pass
    return g_default
