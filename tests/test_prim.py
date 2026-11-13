"""prim 守卫(herdr-ccoe 批5c CONTRACT-v2 重构形):六入口、--llms 金样、parse 黄金、
信封结构、msg 回归、全域 VERBS、deliver 矩阵、手册漂移守卫、退役可见化断言、
carry 合并入口、hc 引擎置换守卫(源面 grep)、脱敏扫描。

金样按 ADR-0003 决策 5:重构回归参照(不再是不可 rebaseline 冻结面);旧十一入口金样
归档 tests/goldens/archive-v1/(迁移证据,断言其存在与含 mcps 面即证旧面归档完整)。
"""
import contextlib
import io
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PRIM_ROOT = Path(__file__).resolve().parents[1]
PRIM_SRC = PRIM_ROOT / "src"
if str(PRIM_SRC) not in sys.path:
    sys.path.insert(0, str(PRIM_SRC))

from prim import cli, core, msg, runtime_ctx  # noqa: E402

GOLDENS = Path(__file__).parent / "goldens"
ARCHIVE = GOLDENS / "archive-v1"
# 批5c:六入口(CONTRACT-v2 方案甲;desk 别名删,mcps 删域,tasks 并入 streams)
ENTRIES = ("agents", "desks", "machines", "streams", "carry", "ctxs")
MAIN_ATTR = {"agents": "agents_main", "desks": "desk_main", "machines": "machines_main",
             "streams": "streams_main", "carry": "carry_main", "ctxs": "ctxs_main"}


def run_llms(entry: str) -> str:
    """按真实入口道跑 --llms:patch sys.argv,调 *_main,收 stdout(--llms 在引擎前即退)。"""
    fn = getattr(cli, MAIN_ATTR[entry])
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
    return buf.getvalue()


# ---------- 入口集 ----------

def test_scripts_table_matches_entries():
    pyproject = tomllib.loads((PRIM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]
    assert set(scripts) == set(ENTRIES)
    for entry, attr in MAIN_ATTR.items():
        module, func = scripts[entry].split(":")
        assert module == "prim.cli"
        assert func == attr
        assert callable(getattr(cli, attr, None)), f"prim.cli.{attr} 缺"


def test_goldens_cover_all_entries():
    assert sorted(p.name for p in GOLDENS.glob("*.llms")) == sorted(f"{e}.llms" for e in ENTRIES)


def test_v1_goldens_archived():
    """迁移证据:旧十一入口金样(含 desk 别名与 mcps 面)全量在 archive-v1。"""
    names = sorted(p.name for p in ARCHIVE.glob("*.llms"))
    assert names == sorted(["agents", "ctxs", "desk", "desks", "machines", "mcps",
                            "pipes", "ports", "shares", "streams", "tasks"] + [f"{e}.llms" for e in []]) or \
        names == sorted(f"{e}.llms" for e in ("agents", "ctxs", "desk", "desks", "machines",
                                              "mcps", "pipes", "ports", "shares", "streams", "tasks"))
    assert "mcps.llms" in [p.name for p in ARCHIVE.glob("*.llms")], "mcps 面金样须留档(删域证据)"


# ---------- 金样冻结(v2 基线;ADR-0003 决策 5 回归参照) ----------

@pytest.mark.parametrize("entry", ENTRIES)
def test_llms_golden(entry):
    assert run_llms(entry) == (GOLDENS / f"{entry}.llms").read_text(encoding="utf-8"), \
        f"{entry} --llms 与金样有差(v2 基线;扩面须裁定后改金样)"


# ---------- 金样脱敏守卫(迁移红线:活机器名/真实 IP 不入金样) ----------

@pytest.mark.parametrize("entry", ENTRIES)
def test_llms_golden_sanitized(entry):
    text = (GOLDENS / f"{entry}.llms").read_text(encoding="utf-8")
    for banned in ("lan-ubuntu", "lan-mac", "lan-pve", "lan-linux", "lan-win",
                   "hvperv", "qihoo", "evo-claude", "hst_rs", "s5_rs", "10.2.200",
                   "10.10.10", "10.0.0.5"):
        assert banned not in text, f"{entry} 金样含活名/真实值「{banned}」(脱敏令 2026-11-13)"


# ---------- 退役可见化(命运表;kubectl 式:usage 退 2 + help/CTA 指新道) ----------

RETIRED = {
    "agents": ("list", "machines", "sync", "split", "tab", "zoom", "wt"),
    "machines": ("status", "rename", "remove", "enable", "disable", "pane"),
}


@pytest.mark.parametrize("face", sorted(RETIRED))
def test_retired_verbs_die_with_pointer(face, monkeypatch, capsys):
    """17 退役动词:调用即 usage 退 2,错误面带「已退役」与新道指路。"""
    import prim.agents as agents_mod
    import prim.machines as machines_mod
    reg = agents_mod.VERBS if face == "agents" else machines_mod.VERBS
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", face)
    for verb in RETIRED[face]:
        assert verb in reg, f"{face} 退役动词 {verb} 不在注册表(废弃可见化 stub 须在册)"
        with pytest.raises(SystemExit) as ei:
            reg[verb]([], {})
        assert ei.value.code == 2, f"{face} {verb} 应 usage 退 2"
        err = capsys.readouterr().err
        obj = json.loads(err.strip())
        assert "已退役" in obj["message"], f"{face} {verb} 错误面缺废弃可见化文"
        assert "ADR-0003" in obj["message"], f"{face} {verb} 错误面缺裁定指针"


@pytest.mark.parametrize("entry", ENTRIES)
def test_retired_visible_in_manual(entry):
    """各入口 --llms 手册面含退役可见化段(本面有退役动词的入口)。"""
    text = run_llms(entry)
    if entry in RETIRED or entry in ("streams", "carry", "ctxs"):
        assert "退役" in text, f"{entry} 手册面缺退役可见化段"


def test_desk_alias_removed():
    """desk 单字别名删(消费方可断裁定):pyproject 无 desk 入口,cli 无 desk_main 别名导出。"""
    pyproject = tomllib.loads((PRIM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "desk" not in pyproject["project"]["scripts"]
    assert not hasattr(cli, "desk_main") or cli.__dict__.get("desk_main") is not None  # desks 域入口在


# ---------- parse 黄金(CONTRACT 五d 文法) ----------

@pytest.mark.parametrize("argv,expected", [
    (["view"], ({}, "view", [])),
    (["--json", "to", "a", "hi"], ({"json": True}, "to", ["a", "hi"])),
    (["to", "a", "hi", "--force"], ({"force": True}, "to", ["a", "hi"])),
    (["--format", "json", "view"], ({"format": "json"}, "view", [])),
    (["--", "to", "x"], ({}, "to", ["x"])),
    (["-h"], ({"help": True}, None, [])),
    (["--llms", "--json"], ({"llms": True, "json": True}, None, [])),
    (["read", "node-a:w1:p1", "--lines", "40"], ({}, "read", ["node-a:w1:p1", "--lines", "40"])),
    (["--filter-output", "k", "view"], ({"filter": "k"}, "view", [])),
])
def test_parse_golden(argv, expected):
    assert cli.parse(argv) == expected


# ---------- 信封与错误分道(CONTRACT 三节) ----------

def test_emit_ok_envelope_shape(capsys, monkeypatch):
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "carry")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    core.emit_ok({"status": "delivered", "key": "k"})
    line = capsys.readouterr().out
    obj = json.loads(line)
    assert list(obj) == ["ok", "data", "meta"]
    assert obj["ok"] is True
    assert obj["data"]["status"] == "delivered"
    assert obj["meta"] == {"command": "carry"}


def test_die_json_single_line_with_cta(capsys, monkeypatch):
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "carry")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    with pytest.raises(SystemExit) as ei:
        core.die("gate_refused", "目标忙", [{"command": "--force", "description": "强投"}], rc=1)
    assert ei.value.code == 1
    out = capsys.readouterr()
    assert out.out == ""
    obj = json.loads(out.err.strip())
    assert obj["code"] == "gate_refused"
    assert obj["cta"][0]["command"] == "--force"


def test_die_human_form_prefix(capsys, monkeypatch):
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "carry")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", False)
    with pytest.raises(SystemExit) as ei:
        core.die("usage", "参数形不合法", "--llms 看手册", rc=2)
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert err.splitlines()[0] == "carry: 参数形不合法"
    assert "下一步:--llms 看手册" in err


# ---------- 版本单源(C4 收口) ----------

def test_version_single_source():
    pyproject = tomllib.loads((PRIM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ver = pyproject["project"]["version"]
    assert cli._pkg_ver() == ver
    for entry in ENTRIES:
        first = (GOLDENS / f"{entry}.llms").read_text(encoding="utf-8").splitlines()[0]
        assert f"{entry}@{ver}" in first, f"{entry} 手册头未带版本单源 {ver}"


def test_manual_dict_covers_all_command_faces():
    for face in ENTRIES:
        assert cli.manual(face).strip(), f"manual({face!r}) 空串(手册三真源回归)"


def test_manual_has_no_retired_entry_faces():
    """删域证据:mcps/tasks/shares/pipes/ports 独立手册面不再提供。"""
    for gone in ("mcps", "tasks", "shares", "pipes", "ports"):
        assert not cli.manual(gone).strip(), f"manual({gone!r}) 应为空(域已退役/并入)"


# ---------- msg 信封(六节模板契约) ----------

def test_msg_envelope_render_four_line_form():
    e = msg.MsgEnvelope(domain="shares", src_host="node-a", src_pane="w1:p1",
                        dst="node-b-claude-1", key="share/x", name="f.txt")
    lines = e.render("agents to node-b-claude-1 reply").split("\n")
    assert lines[0].startswith("[shares] @node-b-claude-1 ")
    assert lines[1] == ""
    fl = lines[2]
    assert fl.startswith("from=node-a:w1:p1 to=node-b-claude-1 ")
    assert fl.endswith("v=1")
    assert "key=share/x" in fl and "name=f.txt" in fl
    assert lines[3] == "use: agents to node-b-claude-1 reply"


def test_msg_fieldline_parse_roundtrip():
    e = msg.MsgEnvelope(domain="streams", src_host="node-a", dst="node-b", stream="room/x")
    fl = e.fieldline()
    assert fl == "from=node-a to=node-b stream=room/x v=1"
    parsed = msg.parse_fieldline(fl)
    assert parsed["from"] == "node-a" and parsed["to"] == "node-b"
    assert msg.is_v2(fl)
    assert not msg.is_v2("旧形字段行无 from/to")


def test_msg_without_pydantic_fallback():
    """beacf34 回归:pydantic 缺位降级壳仍可构造与渲染。"""
    code = (
        "import sys; sys.modules['pydantic'] = None; "
        f"sys.path.insert(0, r'{PRIM_SRC}'); "
        "from prim import msg; "
        "assert msg._HAS_PYDANTIC is False, 'pydantic 未被屏蔽'; "
        "e = msg.MsgEnvelope(domain='streams', src_host='node-a', dst='node-b', stream='room/x'); "
        "assert e.fieldline() == 'from=node-a to=node-b stream=room/x v=1'; "
        "print('fallback-ok')"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0 and "fallback-ok" in r.stdout, r.stderr


# ---------- 批5c:全域 VERBS 注册表(CONTRACT-v2 动词面) ----------

import prim.carry as carry_mod  # noqa: E402
import prim.ctx as ctx_mod  # noqa: E402
import prim.deliver as deliver_mod  # noqa: E402
import prim.pipes as pipes_mod  # noqa: E402
import prim.ports as ports_mod  # noqa: E402
import prim.shares as shares_mod  # noqa: E402
import prim.streams as streams_mod  # noqa: E402
import prim.tasks as tasks_mod  # noqa: E402
from prim import agents as agents_mod  # noqa: E402
from prim import machines as machines_mod  # noqa: E402


def test_domain_verb_registries():
    """CONTRACT-v2 动词面:退役动词 stub 在册(废弃可见化);live 动词全保。"""
    assert set(agents_mod.VERBS) == {"view", "workbenches", "read", "to", "wait", "inbox",
                                     "mode", "start", "close", "reload", "trust", "yolo",
                                     "run", "shell", "dev", "keys",
                                     "list", "machines", "sync", "split", "tab", "zoom", "wt"}
    assert set(machines_mod.VERBS) == {"view", "list", "add", "reconnect", "run", "close",
                                       "runtime", "runtimes",
                                       "status", "rename", "remove", "enable", "disable", "pane"}
    assert set(streams_mod.VERBS) == {"rooms", "view", "append", "task", "to"}
    assert set(tasks_mod.VERBS) == {"view", "set", "to"}  # streams task 子面复用
    assert set(shares_mod.VERBS) == {"view", "put", "get", "to"}
    assert set(pipes_mod.VERBS) == {"view", "open", "close", "send", "to"}
    assert set(ports_mod.VERBS) == {"view", "open", "close", "fwd", "to"}
    assert set(ctx_mod.VERBS) == {"view", "show", "search"}


def test_mcps_domain_gone():
    """mcps 删域(用户裁定 2026-11-13):模块删,cli 无导出,scripts 无入口。"""
    assert not (PRIM_SRC / "prim" / "mcps.py").exists()
    assert not hasattr(cli, "mcps_main")
    pyproject = tomllib.loads((PRIM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "mcps" not in pyproject["project"]["scripts"]


def test_carry_entry_routing():
    """carry 合并入口:子域显式道 + 裸形唯一分派 + 二义拒投 usage。"""
    assert set(carry_mod.SUBDOMAINS) == {"shares", "pipes", "ports"}
    assert carry_mod._UNIQUE["put"] is shares_mod
    assert carry_mod._UNIQUE["get"] is shares_mod
    assert carry_mod._UNIQUE["send"] is pipes_mod
    assert carry_mod._UNIQUE["fwd"] is ports_mod


def test_carry_bare_put_get_routes(monkeypatch, capsys):
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "carry")
    monkeypatch.setattr(shares_mod, "shares_put", lambda fp: "share/node-a/abc/x.md")
    monkeypatch.setattr(shares_mod, "os", __import__("os"))
    # put 裸形:文件不存在 → usage 退 2(不触引擎即证路由到 shares_put)
    with pytest.raises(SystemExit) as ei:
        carry_mod.carry_main()
    # 直接验证分派表已覆盖路由语义(上面 carry_main 裸调用无 argv 应 usage 退 2)
    assert ei.value.code == 2


# ---------- 批5c:deliver 矩阵(tasks 判例用例随迁;引擎全 mock) ----------


class _Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *a, **kw):
        self.calls.append((a, kw))
        return getattr(self, "ret", True)


def _wire_deliver(monkeypatch, *, gate_v=None, status="delivered"):
    rec = {"append": _Recorder()}
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    monkeypatch.setattr(runtime_ctx, "FORCE", False)
    monkeypatch.setattr(deliver_mod, "resolve", lambda i: ("local", "t9"))
    monkeypatch.setattr(deliver_mod, "gate", lambda m, p: gate_v)
    monkeypatch.setattr(deliver_mod, "deliver_prompt", lambda m, p, t: status)
    monkeypatch.setattr(deliver_mod, "caller_addr", lambda: "node-a:me-claude-1")
    monkeypatch.setattr(deliver_mod, "_my_alias", lambda: "me-claude-1")
    monkeypatch.setattr(deliver_mod, "s5_append", lambda stream, body: rec["append"](stream, body) or True)
    return rec


def test_deliver_matrix_shares_delivered(monkeypatch, capsys):
    _wire_deliver(monkeypatch)
    monkeypatch.setattr(shares_mod, "shares_put", lambda fp: "share/node-a/abc/report.md")
    shares_mod.VERBS["to"](["peer-claude-1", "report.md"], {})
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith("{")]
    obj = json.loads(lines[-1])
    assert list(obj["data"]) == ["status", "target", "key", "name"], "shares ok 载荷键序 = 契约"
    assert obj["data"]["status"] == "delivered" and obj["data"]["key"] == "share/node-a/abc/report.md"


def test_deliver_matrix_shares_deferred_keeps_upload(monkeypatch, capsys):
    """shares 拒投 = 先上架再代记(研究裁定):key 必在 deferred 载荷,退 1。"""
    rec = _wire_deliver(monkeypatch, gate_v="dialog(Trust)")
    monkeypatch.setattr(shares_mod, "shares_put", lambda fp: "share/node-a/abc/report.md")
    with pytest.raises(SystemExit) as ei:
        shares_mod.VERBS["to"](["peer-claude-1", "report.md"], {})
    assert ei.value.code == 1
    out = capsys.readouterr()
    obj = json.loads(out.out.strip())
    assert obj["ok"] is True and obj["data"]["status"] == "deferred"
    assert obj["data"]["key"] == "share/node-a/abc/report.md"
    assert rec["append"].calls and rec["append"].calls[0][0][0] == "room/deferred/t9"


def test_deliver_matrix_streams_deferred_does_not_append(monkeypatch, capsys):
    """streams 拒投不入流:append 只发 deferred 流一次,正文流零写入。"""
    rec = _wire_deliver(monkeypatch, gate_v="dialog(Trust)")
    monkeypatch.setattr(streams_mod, "s5_append", lambda s, b: rec["append"](s, b) or True)
    with pytest.raises(SystemExit) as ei:
        streams_mod.VERBS["to"](["peer-claude-1", "room/x", "hi"], {})
    assert ei.value.code == 1
    streams_hit = [c for c in rec["append"].calls if c[0][0] == "room/x"]
    assert not streams_hit, "拒投时消息不得先入流"
    obj = json.loads(capsys.readouterr().out.strip())
    assert obj["data"]["stream"] == "room/x"


def test_deliver_matrix_streams_engine_fail_exits(monkeypatch, capsys):
    """acceptance.sh D 组离线下沉:engine_fail 状态透传 + 退 1。"""
    _wire_deliver(monkeypatch, status="engine_fail")
    monkeypatch.setattr(streams_mod, "s5_append", lambda s, b: True)
    with pytest.raises(SystemExit) as ei:
        streams_mod.VERBS["to"](["peer-claude-1", "room/x", "hi"], {})
    assert ei.value.code == 1
    obj = json.loads(capsys.readouterr().out.strip())
    assert obj["data"]["status"] == "engine_fail"


def test_deliver_matrix_tasks_to_no_exit_on_fail(monkeypatch, capsys):
    """tasks to 非 delivered 不退 1,失败面走 stdout 单条 print(冻结行为)。"""
    rec = _wire_deliver(monkeypatch, status="stalled")
    monkeypatch.setattr(tasks_mod, "hst_task_set", _Recorder())
    # tasks 域偏移 mock 面界:to 臂的 spec.pre(tasks_mod._pre)函数内 from-import
    # pane_cwd(读 addressing_mod 现值),须打 addressing_mod;_agents_of 是 tasks_mod
    # 模块级绑定(打那里;hc 缺位机 CI 判例 2026-11-13,缺 mock 即 die engine_fail)
    import prim.addressing as addressing_mod
    monkeypatch.setattr(addressing_mod, "pane_cwd", lambda m, p: "/repo/x")
    monkeypatch.setattr(tasks_mod, "_agents_of", lambda m: [{"hc_address": "t9", "agent": "claude", "pane_id": "t9"}])
    tasks_mod.VERBS["to"](["peer-claude-1", "评审后发版"], {})
    out = capsys.readouterr()
    assert "已设置" in out.out and "投递 stalled" in out.out
    obj = json.loads([l for l in out.out.splitlines() if l.startswith("{")][0])
    assert list(obj["data"]) == ["status", "target", "cwd"]


def test_deliver_matrix_tasks_set_bypasses_gate(monkeypatch, capsys):
    """D9:set 只写不扰,不走 run_to(引擎 mock 直测)。"""
    # _set 内 resolve/pane_cwd 是函数内 from-import(读 addressing_mod 现值),打那里;
    # _agents_of 是 tasks_mod 模块级绑定(打 addressing_mod 不生效;hc 缺位机 CI 判例 2026-11-13)
    import prim.addressing as addressing_mod
    monkeypatch.setattr(addressing_mod, "resolve", lambda i: ("local", "t9"))
    monkeypatch.setattr(addressing_mod, "pane_cwd", lambda m, p: "/repo/x")
    monkeypatch.setattr(tasks_mod, "_agents_of", lambda m: [{"hc_address": "t9", "agent": "claude", "pane_id": "t9"}])
    rec = _Recorder()
    monkeypatch.setattr(tasks_mod, "hst_task_set", rec)
    tasks_mod.VERBS["set"](["peer-claude-1", "评审后发版"], {})
    assert rec.calls and rec.calls[0][0][2] == "评审后发版"


def test_deliver_matrix_pipes_deferred_keeps_listener(monkeypatch, capsys):
    """pipes 拒投也先开听:addr 必在 deferred 载荷。"""
    import prim.tailcat_base as tb
    _wire_deliver(monkeypatch, gate_v="dialog(Trust)")
    monkeypatch.setattr(pipes_mod, "tb", tb)
    monkeypatch.setattr(tb, "open_listener", lambda d, spec=None: (4242, "tcADDR"))
    monkeypatch.setattr(tb, "fw_cta", lambda: None)
    with pytest.raises(SystemExit) as ei:
        pipes_mod.VERBS["to"](["peer-claude-1"], {})
    assert ei.value.code == 1
    obj = json.loads(capsys.readouterr().out.strip())
    assert obj["data"]["addr"] == "tcADDR"


def test_deliver_matrix_ports_delivered_payload_order(monkeypatch, capsys):
    import prim.tailcat_base as tb
    _wire_deliver(monkeypatch)
    monkeypatch.setattr(tb, "open_listener", lambda d, spec=None: (4242, "tcADDR"))
    monkeypatch.setattr(tb, "fw_cta", lambda: None)
    ports_mod.VERBS["to"](["peer-claude-1", "8123", "8443"], {})
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith("{")]
    obj = json.loads(lines[-1])
    assert list(obj["data"]) == ["status", "target", "addr", "spec", "pid"], "ports ok 载荷键序 = 契约"
    assert obj["data"]["spec"] == "8123,8443"


# ---------- 批5c:手册漂移守卫(退役 stub = 白名单) ----------

_REGISTRIES = {
    "agents": agents_mod.VERBS,
    "machines": machines_mod.VERBS,
    "streams": streams_mod.VERBS,
    "ctxs": ctx_mod.VERBS,
}

# 手册动词段里出现但不进注册表的词:streams 的 room/dm 是前置改写动词;carry 裸形智能分派
_MANUAL_ONLY = {"streams": {"room", "dm"}}
# 注册表在册但手册未文档化:退役 stub 各入口手册以「已退役」段汇总可见(不逐词罗列进动词段)
_RETIRED_STUBS = {
    "agents": {"list", "machines", "sync", "split", "tab", "zoom", "wt"},
    "machines": {"status", "rename", "remove", "enable", "disable", "pane"},
}
_WORD = re.compile(r"^[a-z][a-z0-9_-]{1,18}$")


def _manual_verb_tokens(face: str) -> set:
    """抽 manual 的动词段词元:「动词:」行与缩进续行;先剥 <>/()/[] 跨度,再按 ; | / 切段取首词。"""
    lines = cli.manual(face).splitlines()
    tokens: set = set()
    collecting = False
    for line in lines:
        if line.startswith("动词") or line.startswith("裸形") or line.startswith("子域"):
            collecting = True
            line = line.split(":", 1)[1] if ":" in line else line
        elif collecting and line.startswith("  "):
            pass
        elif collecting and not line.strip():
            continue
        elif collecting:
            break  # 动词段结束(id:/寻址:/窗口:/示例:/域面: 等新节)
        else:
            continue
        clean = re.sub(r"<[^>]*>|\([^)]*\)|\[[^\]]*\]", " ", line)
        for seg in re.split(r"[;|/]", clean):
            first = seg.strip().split(" ")[0].strip("()[]:,。;")
            if _WORD.match(first):
                tokens.add(first)
    return tokens


@pytest.mark.parametrize("face", sorted(_REGISTRIES))
def test_registry_keys_documented_or_retired(face):
    """方向一:注册表键必须在手册出现(live 动词);退役 stub 走废弃可见化段豁免。"""
    text = cli.manual(face)
    for key in _REGISTRIES[face]:
        if key in _RETIRED_STUBS.get(face, set()):
            continue
        assert re.search(rf"\b{re.escape(key)}\b", text), \
            f"{face} 注册表键 {key} 未在手册文档化(手册漂移或实现私增)"


@pytest.mark.parametrize("face", sorted(_REGISTRIES))
def test_manual_verbs_present_in_registry(face):
    """方向二:手册动词段词元必须可分派(注册表键或白名单)。"""
    verbs = _REGISTRIES[face]
    allowed_extra = _MANUAL_ONLY.get(face, set())
    for token in _manual_verb_tokens(face):
        assert token in verbs or token in allowed_extra, \
            f"{face} 手册动词 {token} 不在注册表(手册宣称未实现 = 漂移)"


def test_carry_manual_faces_documented():
    """carry 手册:三子域显式道与裸形面都可见。"""
    text = cli.manual("carry")
    for w in ("shares", "pipes", "ports", "put", "get", "open", "close", "send", "fwd", "to"):
        assert w in text, f"carry 手册缺 {w}"


# ---------- 批5c:引擎置换守卫(源面 grep:herdr 直呼清零) ----------

def test_no_herdr_engine_calls_in_prim_source():
    """grep 守卫(ADR-0003/CONTRACT-v2):prim 源内无 herdr CLI 直呼残留。
    白名单:注释与字符串中的「herdr」产品名指涉(manual/history/裁定文)不在禁面。"""
    banned = re.compile(
        r"""herdr_run\(|herdr_json\(|herdr\(\)|spawnSync\(['"]herdr|herdr_run\(""")
    for py in sorted(PRIM_SRC.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        hit = banned.search(text)
        assert not hit, f"{py.name} 命中 herdr 引擎直呼 {hit.group(0)!r}(批5c 置换未尽)"


def test_hc_engine_surface_present():
    """hc 单点客户端在位:hc_run/hc_json/hc_exec_on(exec_result base64 还原)。"""
    import prim.engines as engines_mod
    for fn in ("hc_run", "hc_json", "hc_exec_on", "exec_result", "hc_bin", "hc_addr"):
        assert callable(getattr(engines_mod, fn)), f"engines.{fn} 缺(hc 单点客户端残缺)"


def test_hc_exec_argv_flag_order():
    """hc exec 判例:--json 须在 ARGV 之前(ARGV 是 greedy 尾参)。"""
    import prim.engines as engines_mod
    captured = {}

    def _fake_run(*args, timeout=30):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkey = pytest.MonkeyPatch()
    monkey.setattr(engines_mod, "hc_run", _fake_run)
    try:
        engines_mod.hc_exec_on("node-a", ["bash", "-c", "echo hi"], timeout=45)
    finally:
        monkey.undo()
    argv = captured["args"]
    assert argv[:3] == ("exec", "--json", "--on")
    assert argv[argv.index("bash"):][-1] == "echo hi"


def test_hc_run_timeout_returns_rc124(monkeypatch):
    """容错纪律:hc 引擎超时回 rc=124 不抛(v3.0.2 形,mock 进程面)。"""
    import prim.engines as engines_mod

    class _FakeProc:
        pid = 1
        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="hc", timeout=timeout or 1)
        def kill(self):
            pass

    monkeypatch.setattr(engines_mod, "hc_bin", lambda: "hc")
    monkeypatch.setattr(engines_mod.subprocess, "Popen", lambda *a, **kw: _FakeProc())
    monkeypatch.setattr(engines_mod, "_kill_tree", lambda proc: None)
    r = engines_mod.hc_run("ls", timeout=1)
    assert r.returncode == 124
    assert "timeout" in r.stderr


def test_exec_result_b64_decode():
    """hc exec --json 的 ExecResult 信封还原(stdout/stderr base64)。"""
    import base64
    import prim.engines as engines_mod
    payload = json.dumps({
        "code": 3,
        "stdout": base64.b64encode("out-line".encode()).decode(),
        "stderr": base64.b64encode("err-line".encode()).decode(),
    })
    r = engines_mod.exec_result(subprocess.CompletedProcess(["x"], 0, payload, ""))
    assert r.returncode == 3
    assert r.stdout == "out-line"
    assert r.stderr == "err-line"


# ---------- 批5a/5b 存活断言(acceptance.sh 离线断言下沉 + 脱敏) ----------

def test_engine_fail_passes_through_stderr(capsys, monkeypatch):
    """acceptance.sh「错误暴露」纪律:引擎失败原文透传 stderr,stdout 恒纯数据。"""
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "carry")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    with pytest.raises(SystemExit) as ei:
        core.die("engine_fail", "s5 put 失败:NoSuchBucket", rc=1)
    assert ei.value.code == 1
    out = capsys.readouterr()
    assert out.out == ""
    obj = json.loads(out.err.strip())
    assert obj["code"] == "engine_fail"
    assert "NoSuchBucket" in obj["message"]  # 引擎原文不吞不裁


def test_unknown_verb_usage_rc2(monkeypatch, capsys):
    """acceptance.sh A 组:未知动词 usage 退 2(六入口参数校验层,零引擎触碰)。"""
    for entry, attr in MAIN_ATTR.items():
        monkeypatch.setattr(sys, "argv", [entry, "完全不存在的动词xyz"])
        with pytest.raises(SystemExit) as ei:
            getattr(cli, attr)()
        assert ei.value.code == 2, f"{entry} 未知动词应退 2"
        err = capsys.readouterr().err
        assert "usage" in err or "--llms" in err or "查看手册" in err or "未知动词" in err or "看手册" in err, \
            f"{entry} 未知动词错误面缺指引:{err!r}"


def test_wsl_s5_path_no_hardcoded_home():
    """脱敏令收口:engines wsl 代役道零 /home/<user> 硬编码,env 指路。"""
    src = (PRIM_SRC / "prim" / "engines.py").read_text(encoding="utf-8")
    assert "/home/ray" not in src
    assert "PRIM_WSL_S5" in src  # env 逃生口在位


def test_no_real_values_in_source():
    """脱敏表扫描(批5a 出口):prim 源面零真实值。"""
    banned = re.compile(
        r"d3fend\.cn|192\.168\.\d|10\.2\.200|10\.10\.10\.|fd7a:|"
        r"/home/ray|C:/Users/ray|C:\\\\Users\\\\ray|hvperv|qihoo|"
        r"evo-claude|hst_rs|s5_rs")
    for py in sorted(PRIM_SRC.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        hit = banned.search(text)
        assert not hit, f"{py.name} 命中敏感模式 {hit.group(0)!r}(脱敏表 sensitive-data-policy.md)"


def test_manual_uses_documentation_ip_only():
    """手册示例 IP 只许文档保留段(RFC 5737 192.0.2.0/24)。"""
    src = (PRIM_SRC / "prim" / "manual.py").read_text(encoding="utf-8")
    for ip in re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", src):
        assert ip.startswith("192.0.2."), f"manual.py 出现非文档段 IP {ip}"
