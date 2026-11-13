"""prim 运行时全局态与输出信封(批3R 自 core 拆出;单一可变点 = setup() 写,emit 族读)

契约:CONTRACT 三节(stdout 恒纯数据;错误一律 stderr;--json 单行信封 ok/data/meta,
字段插入序即契约)。CMD_NAME = 信封 meta.command 与错误前缀;setup 按真实入口名写。
"""
from __future__ import annotations
import json
import sys

# stdout/stderr 恒 utf-8(win 控制台缺省 GBK,屏面 unicode 会让 agent 消费面挂死)
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

# ---------- 全局态(每命令入口经 flags.setup() 重置) ----------

CMD_NAME = "agents"
JSON_MODE = False
FORCE = False


def eprint(*a):
    print(*a, file=sys.stderr)


def emit_error(code: str, message: str, cta: list[dict] | None = None):
    """错误分道:stderr 单行 JSON(doc-cli 形);人读形前缀 + CTA 下一步行(三节承诺,批2R 补)。退出码由调用方定。"""
    obj = {"code": code, "message": message}
    if cta:
        obj["cta"] = cta
    if JSON_MODE:
        eprint(json.dumps(obj, ensure_ascii=False))
    else:
        eprint(f"{CMD_NAME}: {message}")
        if cta:
            hint = cta if isinstance(cta, str) else "; ".join(
                str(d.get("command") or d.get("description") or "") for d in cta if isinstance(d, dict))
            if hint:
                eprint(f"下一步:{hint}")


def emit_ok(data: dict):
    """成功信封:--json 时 stdout 单行 {ok,data,meta};人读形由调用方打印。"""
    if JSON_MODE:
        print(json.dumps({"ok": True, "data": data, "meta": {"command": CMD_NAME}}, ensure_ascii=False))


def die(code: str, message: str, cta: list[dict] | None = None, rc: int = 1):
    emit_error(code, message, cta)
    sys.exit(rc)


def guard(fn):
    """顶层 Ctrl+C 净化:单行退出码 130,不出 traceback(孙进程收割在引擎 spawn 层)。"""
    import functools
    import sys as _sys

    @functools.wraps(fn)
    def _w(*a, **kw):
        try:
            fn(*a, **kw)
        except KeyboardInterrupt:
            eprint(f"{CMD_NAME}: 已中断(Ctrl+C)")
            _sys.exit(130)
    return _w
