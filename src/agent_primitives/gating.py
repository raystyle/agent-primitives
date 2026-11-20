"""agent_primitives 门控与投递(批3R 合拆;批5c 引擎置换 hc):TUI 判标族 + gate + 原子投递 + 信任屏放行

契约(CONTRACT 一节门控语义 + 五b 状态回调):DELIVER 前查目标态;--force 任意参数位
识别绕门控;投递 status 四态 delivered|engine_fail|deferred|stalled。
扫屏判标三处归一(gate / _blocked_after_start / _agents_trust 共用 TUI_DIALOGS 尾窗扫描)。
引擎腿(命运表直通):屏读 = hc read;投递 = hc send(blocked 拒收 → deferred);
按键 = hc keys 一次多发(判标库 prim 独有,按键腿 hc 化)。
"""
from __future__ import annotations
import time

from .addressing import row_of
from .engines import hc_run


# 四家 TUI 操作对话框判标族(实测文案;保守清单,误拒优于误投)
TUI_DIALOGS: dict[str, tuple[str, ...]] = {
    "claude": (
        "Yes, I trust this folder", "Do you trust the files in this folder",
        "Yes, allow external imports", "Enter to confirm", "Esc to cancel",
        "Do you want to proceed", "don't ask again", "permission mode",
        "Select an option", "requires approval",
    ),
    "codex": (
        "Trust this folder?", "Do you trust the contents of this directory",
        "waiting for input", "Approve", "Run command", "select an option",
    ),
    "grok": (
        "Trust the authors of this folder", "Approve?", "Y/n",
        "press y to", "Enter to confirm",
    ),
    "kimi": (
        "Trust this folder", "Don't trust", "approve", "选择", "确认",
    ),
}


def _screen_markers(kind: str) -> tuple[str, ...]:
    """kind 的判标 = 本家加 claude 兜底(gate 与 blocked 共用;批3R 三处归一)。"""
    return TUI_DIALOGS.get(kind, ()) + TUI_DIALOGS.get("claude", ())


def _tail(screen: str, lines: int = 12) -> str:
    """只扫 TUI 尾窗(对话框按钮与页脚区):正文里的文档引用(如信任屏教学文)不算屏上对话框。"""
    return "\n".join(screen.splitlines()[-lines:])


def _read_screen(addr: str, lines: int = 40) -> str:
    """屏读单点(hc read;--lines = 屏上方历史行数,屏面恒在)。"""
    r = hc_run("read", addr, "--lines", str(lines), timeout=15)
    return r.stdout or ""


def gate(machine: str, addr: str) -> str | None:
    """投递门控 v2(不看状态字段,看 TUI 实况,四家 TUI 判标族):
    读格可见内容,有操作对话框(信任屏/权限屏/模式选择)即拒;输入框空着即可投
    (busy 态各家 TUI 会排队消息,不是拒投理由)。返回 None = 可投。"""
    from . import runtime_ctx
    if runtime_ctx.FORCE:
        return None
    kind = (row_of(addr, refresh=False) or {}).get("agent", "")
    screen = _read_screen(addr)
    hit = next((mk for mk in _screen_markers(kind) if mk in _tail(screen)), None)
    if hit:
        return f"dialog({hit[:24]})"
    return None


def deliver_prompt(machine: str, addr: str, text: str) -> str:
    """原子化投递(投递核心一行 hc send,命运表难题 1):
    rc 0 = delivered;hc 拒收(blocked) = deferred;超时 = stalled;余 = engine_fail。"""
    r = hc_run("send", addr, text, timeout=30)
    if r.returncode == 0:
        return "delivered"
    err = (r.stderr or r.stdout or "").strip()
    if "blocked" in err.lower():
        return "deferred"
    if "timeout" in err.lower() or "stalled" in err.lower():
        return "stalled"
    return "engine_fail"


def _keys(addr: str, *keys: str, timeout: int = 15):
    """按键腿单点(hc keys 一次多发,省逐键 spawn)。"""
    return hc_run("keys", addr, *keys, timeout=timeout)


def agents_trust(machine: str | None):
    """信任屏放行:blocked/unknown 格扫屏按键(shell v2.8 判标同源移植)。"""
    from .addressing import _agents_of
    ags = [a for a in _agents_of(machine)
           if a.get("agent_status", "") in ("blocked", "unknown")]
    if not ags:
        print("agents trust: 无待放行格")
        return
    for a in ags:
        addr = a["hc_address"]
        screen = _read_screen(addr, 40)
        acted = False
        if "Yes, I trust this folder" in screen:
            _keys(addr, "down", "enter")
            print(f"agents trust: {addr} claude 已下移确认(2.x 形)")
            acted = True
        elif "Yes, allow external imports" in screen or ("Enter to confirm" in screen and "Esc to cancel" in screen):
            _keys(addr, "down", "enter")
            print(f"agents trust: {addr} claude 确认屏放行(通用形)")
            acted = True
        elif "Do you trust the files in this folder" in screen:
            _keys(addr, "enter")
            print(f"agents trust: {addr} claude 已确认(经典形)")
            acted = True
        elif "Trust this folder?" in screen or "Do you trust the contents of this directory" in screen:
            _keys(addr, "enter")
            print(f"agents trust: {addr} codex 已确认")
            acted = True
        elif "Trust the authors of this folder" in screen:
            _keys(addr, "y", "enter")
            print(f"agents trust: {addr} grok 已答 y")
            acted = True
        if not acted:
            print(f"agents trust: {addr} 无已知信任屏(文案变体,人工核)")


def blocked_after_start(m: str, addr: str, kind: str, wait_s: int = 30) -> dict | None:
    """启动后阻塞检测(不是启动就不管 TUI 阻不阻塞):轮询屏面到 wait_s;
    命中对话框 = 返回 {marker, kind}(CTA = dismiss_block_hint)。
    alt-screen 读空(claude TUI 主屏)不算可投;返回 None = 无阻塞。"""
    import time as _t
    from . import runtime_ctx
    if runtime_ctx.FORCE:
        return None
    markers = _screen_markers(kind)
    deadline = _t.time() + wait_s
    while _t.time() < deadline:
        screen = _read_screen(addr)
        if screen.strip():
            hit = next((mk for mk in markers if mk in _tail(screen)), None)
            if hit:
                return {"marker": hit, "kind": kind}
        _t.sleep(2.5)
    return None


def dismiss_block_hint(hit: dict) -> list[str]:
    """阻塞 CTA 提示(不自动按键:信任屏须人裁)。"""
    return [
        f"agents: 启动后检测到阻塞对话框({hit['marker'][:40]})",
        "下一步:人工放行(下箭头选 Yes + Enter),或 agents to <id> --force 绕门控投递指令",
    ]
