"""prim 门控与投递(批3R 自 core/cli 合拆):TUI 判标族 + gate + 原子投递 + 信任屏放行

契约(CONTRACT 一节门控语义 + 五b 状态回调):DELIVER 前查目标态;--force 任意参数位
识别绕门控;投递 status 四态 delivered|engine_fail|deferred|stalled。
扫屏判标三处归一(gate / _blocked_after_start / _agents_trust 共用 TUI_DIALOGS 尾窗扫描)。
"""
from __future__ import annotations
import time

from .addressing import _agents_of
from .engines import herdr_run


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


def gate(machine: str, pane: str) -> str | None:
    """投递门控 v2(用户令 2026-10-13:不看状态字段,看 TUI 实况,四家 TUI 判标族):
    读格可见内容,有操作对话框(信任屏/权限屏/模式选择)即拒;输入框空着即可投
    (busy 态各家 TUI 会排队消息,不是拒投理由)。返回 None = 可投。"""
    from . import runtime_ctx
    if runtime_ctx.FORCE:
        return None
    m = None if machine in ("", "local") else machine
    kind = ""
    for a in _agents_of(m):
        if a.get("pane_id") == pane:
            kind = a.get("agent") or ""
            break
    r = herdr_run(m, "agent", "read", pane, "--source", "visible", "--lines", "40", timeout=15)
    screen = r.stdout or ""
    markers = _screen_markers(kind)
    hit = next((mk for mk in markers if mk in _tail(screen)), None)
    if hit:
        return f"dialog({hit[:24]})"
    return None


def deliver_prompt(machine: str, pane: str, text: str) -> str:
    """原子化投递:--wait --until working 15s。返回 status 四态之一。"""
    m = None if machine in ("", "local") else machine
    r = herdr_run(m, "agent", "prompt", pane, text, "--wait", "--until", "working", "--timeout", "15000", timeout=25)
    if r.returncode == 0:
        return "delivered"
    err = (r.stderr or r.stdout or "").strip()
    if "agent_blocked" in err:
        return "deferred"
    if "timeout" in err or "stalled" in err:
        return "stalled"
    return "engine_fail"


def agents_trust(machine: str | None):
    """信任屏放行:blocked/unknown 格扫屏按键(shell v2.8 判标同源移植)。"""
    ags = _agents_of(machine)
    pending = [a for a in ags if a.get("agent_status", "") in ("blocked", "unknown")]
    if not pending:
        print("agents trust: 无待放行格")
        return
    m_label = machine or "local"
    for a in pending:
        pane = a.get("pane_id", "")
        r = herdr_run(None if m_label in ("", "local") else m_label,
                      "agent", "read", pane, "--source", "visible")
        screen = r.stdout or ""
        acted = False
        if "Yes, I trust this folder" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "down")
            time.sleep(1)
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} claude 已下移确认(2.x 形)")
            acted = True
        elif "Yes, allow external imports" in screen or ("Enter to confirm" in screen and "Esc to cancel" in screen):
            herdr_run(machine, "agent", "send-keys", pane, "down")
            time.sleep(1)
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} claude 确认屏放行(通用形)")
            acted = True
        elif "Do you trust the files in this folder" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} claude 已确认(经典形)")
            acted = True
        elif "Trust this folder?" in screen or "Do you trust the contents of this directory" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} codex 已确认")
            acted = True
        elif "Trust the authors of this folder" in screen:
            herdr_run(machine, "agent", "send-keys", pane, "y")
            time.sleep(1)
            herdr_run(machine, "agent", "send-keys", pane, "enter")
            print(f"agents trust: {pane} grok 已答 y")
            acted = True
        if not acted:
            print(f"agents trust: {pane} 无已知信任屏(文案变体,人工核)")


def blocked_after_start(m: str, pane: str, kind: str, wait_s: int = 30) -> dict | None:
    """启动后阻塞检测(用户令 2026-10-17):轮询屏面到 wait_s;命中对话框 = 返回 {marker, kind}(CTA = dismiss_block_hint)。
    alt-screen 读空(claude TUI 主屏)不算可投,靠 status + tail markers;返回 None = 无阻塞。"""
    import time as _t
    from . import runtime_ctx
    if runtime_ctx.FORCE:
        return None
    hm = None if m in ("", "local") else m
    markers = _screen_markers(kind)
    deadline = _t.time() + wait_s
    while _t.time() < deadline:
        r = herdr_run(hm, "agent", "read", pane, "--source", "visible", "--lines", "40", timeout=15)
        screen = r.stdout or ""
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
