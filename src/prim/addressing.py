"""prim 寻址(批5c hc 化):id 三产生式解析 + 机册标签 + 终端表

契约(CONTRACT 一节):裸名(全局按 name 寻址,首选)> 机:名或格(显式形)>
local: 前缀 = 本机;裸格址非法。多名命中 = not_found(研究裁定)。
hc 化(ADR-0003):`hc ls --json` 一发含本机 + 各 connected 机终端(machine/t7 形),
全局扫零逐机 spawn;hc run --name 唯一性 hc 管,prim 只做标准形校验与撞名扫。
行形归一(消费方沿用旧键):name/pane_id(机内短址)/hc_address(全形)/agent(kind)/
agent_status(status.state)/cwd/machine/state。
"""
from __future__ import annotations
import os
from dataclasses import dataclass

from .engines import hc_json
from .identity import host_label
from .runtime_ctx import die

# 终端前景程序 = 裸 shell(空格异常态判据;TUI 特征另行豁免)
SHELL_PROGRAMS = {"bash", "zsh", "sh", "fish", "nu", "pwsh", "powershell", "powershell.exe",
                  "cmd", "cmd.exe", "wsl", "wsl.exe"}
_KINDS = ("claude", "codex", "grok", "kimi", "pi")


@dataclass
class Target:
    machine: str  # "" = 本机
    rest: str      # 名或格


def _kind_of(app: str) -> str:
    """前景程序名 → agent kind(claude-code → claude);非四家原样(如 bash)。"""
    low = (app or "").lower()
    for k in _KINDS:
        if k in low:
            return k
    return os.path.basename(low or "")


def normalize_term(t: dict) -> dict:
    """hc Terminal 行 → prim 归一行(pane_id = 机内短址,hc_address = 全形)。
    status 双形兼容:CLI --json = 扁平字符串("working");RPC Terminal = 7501 对象。"""
    addr = t.get("address", "")
    machine, short = ("", addr)
    if "/" in addr:
        machine, short = addr.split("/", 1)
    st = t.get("status")
    argv0 = (t.get("argv") or [""])[0] or ""
    if isinstance(st, dict):
        state = st.get("state", "")
        kind = st.get("kind") or ""
        app = st.get("app") or os.path.basename(argv0)
    else:
        state = str(st or "")
        kind = ""
        app = t.get("agent") or os.path.basename(argv0)
    return {
        "pane_id": short,
        "hc_address": addr,
        "machine": machine or "local",
        "name": t.get("name") or "",
        "agent": _kind_of(app),
        "app": app,
        "agent_status": state,
        "blocked_kind": kind,
        "state": t.get("state", ""),
        "cwd": t.get("cwd", ""),
        "title": t.get("title", "") or "",
        "turn": t.get("turn"),
    }


_HC_LS: dict | None = None


def hc_ls(all_: bool = False, timeout: int = 30, refresh: bool = False) -> dict:
    """hc ls --json(ListResult:terminals + machines);批内缓存免逐动词多发。"""
    global _HC_LS
    if refresh or _HC_LS is None or all_:
        d = hc_json("ls", *(["--all"] if all_ else []), timeout=timeout)
        _HC_LS = d if isinstance(d, dict) else {}
    return _HC_LS


def terms(all_: bool = False, refresh: bool = False) -> list[dict]:
    """归一终端行(live 优先;all_ 含 finished)。"""
    ts = hc_ls(all_=all_, refresh=refresh).get("terminals") or []
    return [normalize_term(t) for t in ts if isinstance(t, dict)]


def _machine_labels() -> list[str]:
    """在册机标签(hc machine ls;hc 机册无 enabled 态,全部在列)。"""
    d = hc_json("machine", "ls", timeout=20)
    rows = d.get("machines", []) if isinstance(d, dict) else []
    out = []
    for x in rows:
        if isinstance(x, dict) and x.get("name"):
            out.append(x["name"])
    return [l for l in out if l != "local"]


def _machines_raw() -> list[dict]:
    """机册原行(hc machine ls)。"""
    d = hc_json("machine", "ls", timeout=20)
    if isinstance(d, dict):
        return [x for x in (d.get("machines") or []) if isinstance(x, dict)]
    return []


def _agents_of(machine: str | None, timeout: int = 30) -> list[dict]:
    """机域终端行:None/""/local = 本机;机标签 = 该机(machine/ 前缀行)。"""
    rows = terms()
    if machine in (None, "", "local"):
        return [r for r in rows if r["machine"] == "local"]
    return [r for r in rows if r["machine"] == machine]


def _match(row: dict, name: str) -> bool:
    return name in (row.get("name"), row.get("pane_id"), row.get("hc_address"))


def resolve(id_str: str) -> tuple[str, str]:
    """→ (machine 标签, hc_address 全形)。裸名全局一发扫;机:名或格按域扫;
    解析失败 die not_found(CTA agents view)。"""
    if ":" in id_str:
        m, rest = id_str.split(":", 1)
        if m == "local" or m == host_label():
            scope = "local"
        elif m in _machine_labels():
            scope = m
        else:
            die("not_found", f"机器「{m}」不在册", [{"command": "machines view", "description": "列在网机器"}])
        for r in _agents_of(scope):
            if _match(r, rest):
                return scope, r["hc_address"]
        die("not_found", f"{m}:{rest} 无此格或 agent",
            [{"command": "agents view" if scope == "local" else f"agents view {scope}", "description": "查格表"}])
    # 无冒号:全局按名扫(一发 hc ls;多名命中 = not_found)
    hits = [r for r in terms() if _match(r, id_str)]
    if len(hits) > 1:
        die("not_found", f"「{id_str}」多名命中({len(hits)} 格)",
            [{"command": "agents view", "description": "查全局格表"}])
    if hits:
        return hits[0]["machine"], hits[0]["hc_address"]
    die("not_found", f"全局未找到 agent「{id_str}」", [{"command": "agents view", "description": "查全局格表"}])


def _find_by_name(machine: str, name: str) -> tuple[str, str] | None:
    """machine ""=本机;命中名或机内短址 → (machine or "local", hc_address)。"""
    for r in _agents_of(machine or None):
        if _match(r, name):
            return (machine or "local"), r["hc_address"]
    return None


def row_of(addr: str, refresh: bool = True) -> dict | None:
    """按 hc_address 找归一行(态查询单点;默认 refresh:轮询面须见活态,
    缓存仅服务同一动词内的初次寻址)。"""
    for r in terms(refresh=refresh):
        if r["hc_address"] == addr:
            return r
    return None


def pane_cwd(machine: str, addr: str) -> str:
    r = row_of(addr, refresh=False) or {}
    return r.get("cwd") or os.path.expanduser("~")


def target_status(machine: str, addr: str) -> str:
    r = row_of(addr, refresh=False) or {}
    return r.get("agent_status") or "unknown"
