"""prim 寻址(批3R 自 core 拆出):id 三产生式解析 + 机册标签 + agent 表

契约(CONTRACT 一节):裸名(全局按 name 寻址,首选)> 机:名或格(显式形)>
local: 前缀 = 本机;裸 pane id 非法。多名命中 = not_found(研究裁定)。
"""
from __future__ import annotations
import os
from dataclasses import dataclass

from .engines import herdr_json
from .identity import host_label
from .runtime_ctx import die


@dataclass
class Target:
    machine: str  # "" = 本机
    rest: str      # 名或格

def resolve(id_str: str) -> tuple[str, str]:
    """裸名全局搜,机:名或格走在册机;解析失败 die not_found。"""
    if ":" in id_str:
        m, rest = id_str.split(":", 1)
        if m == "local" or m == host_label():
            return "local", rest  # 自家在册标签也当本机(机:agent别名 同机寻址合法)
        labels = [x.get("label", "") for x in herdr_json(None, "machine", "list", "--json") if isinstance(x, dict)]
        if m in labels:
            return m, rest
        die("not_found", f"机器「{m}」不在册", [{"command": "agents machines", "description": "列在网机器"}])
    # 无冒号:全局按名搜(本机先,后各在册机)
    hit = _find_by_name("", id_str)
    if hit:
        return hit
    for lab in _machine_labels():
        hit = _find_by_name(lab, id_str)
        if hit:
            return hit
    die("not_found", f"全局未找到 agent「{id_str}」", [{"command": "agents view", "description": "查全局格表"}])

def _machine_labels() -> list[str]:
    out = []
    for x in herdr_json(None, "machine", "list", "--json"):
        if isinstance(x, dict) and x.get("enabled", True):
            out.append(x.get("label", ""))
    return [l for l in out if l and l != "local"]

def _agents_of(machine: str, timeout: int = 30) -> list[dict]:
    d = herdr_json(machine or None, "agent", "list", timeout=timeout)
    if isinstance(d, dict):
        return d.get("result", {}).get("agents", []) or []
    return d if isinstance(d, list) else []

def _find_by_name(machine: str, name: str) -> tuple[str, str] | None:
    """machine ""=本机;命中名或 pane_id → (machine or "local", pane_id)。多名命中 = not_found(研究裁定)。"""
    ags = _agents_of(machine or None)
    hits = [a for a in ags if a.get("name") == name or a.get("pane_id") == name]
    if len(hits) > 1:
        die("not_found", f"「{name}」多名命中({len(hits)} 格)", [{"command": "agents view", "description": "查全局格表"}])
    if hits:
        return (machine or "local"), hits[0].get("pane_id", "")
    return None

def pane_cwd(machine: str, pane: str) -> str:
    for a in _agents_of(None if machine in ("", "local") else machine):
        if a.get("pane_id") == pane:
            return a.get("cwd") or os.path.expanduser("~")
    return os.path.expanduser("~")

def target_status(machine: str, pane: str) -> str:
    for a in _agents_of(None if machine in ("", "local") else machine):
        if a.get("pane_id") == pane:
            return a.get("agent_status", "unknown")
    return "unknown"


def resolve_tab(id_str: str) -> tuple[str, str]:
    """tab id 解析:机:tabid(缺省 local)。"""
    if ":" in id_str:
        m, tid = id_str.split(":", 1)
        if m == "local":
            return "local", tid
        if m in _machine_labels():
            return m, tid
        die("not_found", f"机器「{m}」不在册")
    return "local", id_str
