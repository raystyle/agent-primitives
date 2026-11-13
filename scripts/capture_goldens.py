"""再生 tests/goldens 六入口 --llms 金样(手动道;批5c CONTRACT-v2 形)。

用法:cd prim && uv run python scripts/capture_goldens.py
金样按 ADR-0003 决策 5:重构回归参照(不再是不可 rebaseline 的冻结面);
旧十一入口金样归档 tests/goldens/archive-v1/(迁移证据);diff 面入评审。
"""
import contextlib
import io
import sys
from pathlib import Path

PRIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRIM_ROOT / "src"))

from prim import cli  # noqa: E402

MAIN_ATTR = {"agents": "agents_main", "desks": "desk_main", "machines": "machines_main",
             "streams": "streams_main", "carry": "carry_main", "ctxs": "ctxs_main"}


def main() -> None:
    out_dir = PRIM_ROOT / "tests" / "goldens"
    out_dir.mkdir(parents=True, exist_ok=True)
    for entry, attr in MAIN_ATTR.items():
        fn = getattr(cli, attr)
        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = [entry, "--llms"]
        try:
            with contextlib.redirect_stdout(buf):
                try:
                    fn()
                except SystemExit:
                    pass
        finally:
            sys.argv = old_argv
        (out_dir / f"{entry}.llms").write_bytes(buf.getvalue().encode("utf-8"))
        print(f"{entry}: {len(buf.getvalue())} chars")


if __name__ == "__main__":
    main()
