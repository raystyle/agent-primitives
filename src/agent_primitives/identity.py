"""agent_primitives 身份判定(批3R 自 core/domains 合拆):本机标签 + 本进程所在格与回信地址

host_label(用户令 2026-10-15 自适应,不硬编码):PRIM_HOST_LABEL 显式覆盖 >
tailscale 自注册节点名(与机册一致)> hostname 短名兜底。
_my_cell(对齐核验 F6 根修,v3.2.2):CLAUDE_CODE_SESSION_ID 直配 herdr agent_session
优先,cwd 唯一命中兜底,双格同 cwd 不再退化。
"""
from __future__ import annotations
import os
import socket

from .runtime_ctx import eprint

_TS_CACHE: str | None = None


def _ts_nodename() -> str:
    """tailscale 自注册节点名(自适应,零手设):Self.HostName 是 TS 面自报名,
    与舰队机册一致;失败/未装返回空。缓存免每查询起 tailscale。"""
    global _TS_CACHE
    if _TS_CACHE is None:
        _TS_CACHE = ""
        try:
            import subprocess as _sp
            r = _sp.run(["tailscale", "status", "--json"], capture_output=True, text=True,
                        timeout=8, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                import json as _json
                d = _json.loads(r.stdout)
                _TS_CACHE = (d.get("Self") or {}).get("HostName", "") or ""
        except Exception:
            pass
    return _TS_CACHE


def host_label() -> str:
    """本机标签(用户令 2026-10-15:自适应,不硬编码):PRIM_HOST_LABEL 显式覆盖 >
    tailscale 自注册节点名(与机册一致)> hostname 短名(最后兜底)。"""
    env = os.environ.get("PRIM_HOST_LABEL")
    if env:
        return env
    ts = _ts_nodename()
    if ts:
        return ts
    return socket.gethostname().split(".")[0]


def _my_cell() -> dict | None:
    """本进程所在格:优先 CLAUDE_CODE_SESSION_ID 直配 herdr agent_session(精确,无 cwd 歧义);
    缺则 cwd 唯一命中兜底(多格同 cwd = 歧义 None)。对齐核验 F6 根修。"""
    from .addressing import _agents_of
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    ags = _agents_of(None)
    if sid:
        for a in ags:
            v = a.get("agent_session")
            if (isinstance(v, dict) and v.get("value") == sid) or v == sid:
                return a
    cwd = os.getcwd()
    hits = [a for a in ags if a.get("cwd") == cwd]
    return hits[0] if len(hits) == 1 else None


def _my_alias() -> str | None:
    """本格的 agent 别名(名即消息面路由键);无格或无名 = None。"""
    c = _my_cell()
    return c.get("name") if c and c.get("name") else None


def caller_pane() -> str:
    """本机格 pane id(presence 键等窗格操作面专用);身份判定同 _my_cell。"""
    c = _my_cell()
    return c.get("pane_id", "unknown") if c else "unknown"


def caller_addr() -> str:
    """调用方回信地址(双轨制,用户令 2026-10-15:消息收发用 机:agent别名,
    窗格操作才用 机:格)。身份 = CLAUDE_CODE_SESSION_ID 直配 herdr agent_session
    (精确),cwd 唯一命中兜底;名即路由键;真 hostname 永不进路由位。"""
    c = _my_cell()
    mach = host_label()
    if c:
        if c.get("name"):
            return f"{mach}:{c['name']}"
        eprint(f"agents: 发话格 {c.get('pane_id')} 无别名,信封退化 机:格 形(正名:herdr agent rename)")
        return f"{mach}:{c.get('pane_id','')}"
    eprint("agents: 调用方所在格未定(session 未配且 cwd 无唯一命中),回信地址退化为机名")
    return mach
