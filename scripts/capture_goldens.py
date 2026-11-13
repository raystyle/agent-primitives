"""再生 tests/goldens 六入口 --llms 金样(手动道;批5a 迁移形)。

用法:cd prim && uv run python scripts/capture_goldens.py
金样是契约冻结的执法基线(ADR-0008):改手册面前先过放行点裁定,改后跑本件再生,
diff 面入评审。agents/desks/tasks/machines 四金样随批5b 迁入后扩为十一入口。
"""
import contextlib
import io
import sys
from pathlib import Path

PRIM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRIM_ROOT / "src"))

from prim import cli  # noqa: E402

MAIN_ATTR = {"shares": "shares_main", "streams": "streams_main",
             "pipes": "pipes_main", "ports": "ports_main", "ctxs": "ctxs_main",
             "mcps": "mcps_main"}


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
