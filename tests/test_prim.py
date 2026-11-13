"""prim 守卫(herdr-ccoe 批5a 迁移形):入口集、--llms 金样冻结、parse 黄金、信封结构、msg 回归、五域 VERBS、deliver 矩阵、手册漂移守卫。

金样 = 5a 六入口 --llms 全文(4.0.0 基线;agents/desks/tasks/machines 四面随批5b 补)。
迁移脱敏裁定(2026-11-13,herdr-ccoe 批5a):金样示例活机器名/真实 IP 一律角色代称
(node-a / lab-node / 192.0.2.x 文档段),金样已再生,冻结语义 = 结构与动词面不变。
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
# 批5a:六入口(十一入口契约不变,agents/desks/desk/tasks/machines 随批5b 迁入)
ENTRIES = ("shares", "streams", "pipes", "ports", "ctxs", "mcps")
MAIN_ATTR = {"shares": "shares_main", "streams": "streams_main",
             "pipes": "pipes_main", "ports": "ports_main", "ctxs": "ctxs_main",
             "mcps": "mcps_main"}


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


# ---------- 金样冻结(契约执法线) ----------

@pytest.mark.parametrize("entry", ENTRIES)
def test_llms_golden(entry):
    assert run_llms(entry) == (GOLDENS / f"{entry}.llms").read_text(encoding="utf-8"), \
        f"{entry} --llms 与金样有差(放行点见 ADR-0008;扩容须裁定后改金样)"


# ---------- 金样脱敏守卫(迁移红线:活机器名/真实 IP 不入金样) ----------

@pytest.mark.parametrize("entry", ENTRIES)
def test_llms_golden_sanitized(entry):
    text = (GOLDENS / f"{entry}.llms").read_text(encoding="utf-8")
    for banned in ("lan-ubuntu", "lan-mac", "lan-pve", "lan-linux", "lan-win",
                   "hvperv", "qihoo", "evo-claude", "hst_rs", "s5_rs", "10.2.200",
                   "10.10.10", "10.0.0.5"):
        assert banned not in text, f"{entry} 金样含活名/真实值「{banned}」(脱敏令 2026-11-13)"


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
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "shares")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    core.emit_ok({"status": "delivered", "key": "k"})
    line = capsys.readouterr().out
    obj = json.loads(line)
    assert list(obj) == ["ok", "data", "meta"]
    assert obj["ok"] is True
    assert obj["data"]["status"] == "delivered"
    assert obj["meta"] == {"command": "shares"}


def test_die_json_single_line_with_cta(capsys, monkeypatch):
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "pipes")
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
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "pipes")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", False)
    with pytest.raises(SystemExit) as ei:
        core.die("usage", "参数形不合法", "--llms 看手册", rc=2)
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert err.splitlines()[0] == "pipes: 参数形不合法"
    assert "下一步:--llms 看手册" in err


def test_die_human_cta_list_form(capsys, monkeypatch):
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "shares")
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", False)
    with pytest.raises(SystemExit):
        core.die("gate_refused", "目标忙", [{"command": "--force", "description": "强投"},
                                           {"command": "streams", "description": "记流"}], rc=1)
    assert "下一步:--force; streams" in capsys.readouterr().err


# ---------- 版本单源(C4 收口) ----------

def test_version_single_source():
    pyproject = tomllib.loads((PRIM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ver = pyproject["project"]["version"]
    assert cli._pkg_ver() == ver
    for entry in ENTRIES:
        first = (GOLDENS / f"{entry}.llms").read_text(encoding="utf-8").splitlines()[0]
        assert f"{entry}@{ver}" in first, f"{entry} 手册头未带版本单源 {ver}"


def test_no_hardcoded_v3_manual_headers():
    assert "@v3" not in (PRIM_SRC / "prim" / "cli.py").read_text(encoding="utf-8"), \
        "手册头残留硬编码 @v3(C4)"


def test_manual_dict_covers_all_command_faces():
    for face in ENTRIES:
        assert cli.manual(face).strip(), f"manual({face!r}) 空串(手册三真源回归)"


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


# ---------- 批5a:五域 VERBS 注册表(tasks 随批5b;此处 shares/streams/pipes/ports) ----------

def test_domain_verb_registries():
    from prim import shares, streams, pipes, ports
    assert set(shares.VERBS) == {"view", "put", "get", "to"}
    assert set(streams.VERBS) == {"view", "rooms", "append", "to"}
    assert set(pipes.VERBS) == {"view", "open", "close", "send", "to"}
    assert set(ports.VERBS) == {"view", "open", "close", "fwd", "to"}


# ---------- 批5a:deliver 矩阵(run_to 六域脚手架;引擎全 mock) ----------

import prim.deliver as deliver_mod  # noqa: E402
import prim.shares as shares_mod  # noqa: E402
import prim.streams as streams_mod  # noqa: E402
import prim.pipes as pipes_mod  # noqa: E402
import prim.ports as ports_mod  # noqa: E402


class _Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *a, **kw):
        self.calls.append((a, kw))
        return getattr(self, "ret", True)


def _wire_deliver(monkeypatch, *, gate_v=None, status="delivered"):
    rec = {"append": _Recorder(), "deferred": _Recorder()}
    monkeypatch.setattr(runtime_ctx, "JSON_MODE", True)
    monkeypatch.setattr(runtime_ctx, "FORCE", False)
    monkeypatch.setattr(deliver_mod, "resolve", lambda i: ("local", "w9:p1"))
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
    assert rec["append"].calls and rec["append"].calls[0][0][0] == "room/deferred/w9:p1"


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
    """acceptance.sh D 组离线下沉(缺口分析尺 2.2):engine_fail 状态透传 + 退 1。"""
    _wire_deliver(monkeypatch, status="engine_fail")
    monkeypatch.setattr(streams_mod, "s5_append", lambda s, b: True)
    with pytest.raises(SystemExit) as ei:
        streams_mod.VERBS["to"](["peer-claude-1", "room/x", "hi"], {})
    assert ei.value.code == 1
    obj = json.loads(capsys.readouterr().out.strip())
    assert obj["data"]["status"] == "engine_fail"


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


# ---------- 批5a:全域注册表 + 手册漂移守卫(CONTRACT 五节宣称) ----------

import prim.mcps as mcps_mod  # noqa: E402
import prim.ctx as ctx_mod  # noqa: E402

REGISTRIES = {
    "shares": shares_mod.VERBS,
    "streams": streams_mod.VERBS,
    "pipes": pipes_mod.VERBS,
    "ports": ports_mod.VERBS,
    "ctxs": ctx_mod.VERBS,
    "mcps": mcps_mod.VERBS,
}

# 手册动词段里出现但不进注册表的词:streams 的 room/dm 是前置改写动词(改写后走 view/append)
_MANUAL_ONLY = {"streams": {"room", "dm"}}
_WORD = re.compile(r"^[a-z][a-z0-9_-]{1,18}$")


def _manual_verb_tokens(face: str) -> set:
    """抽 manual 的动词段词元:「动词:」行与缩进续行;先剥 <>/()/[] 跨度(子动词
    括注与示例不进词面),再按 ; | / 切段取首词。"""
    lines = cli.manual(face).splitlines()
    tokens: set = set()
    collecting = False
    for line in lines:
        if line.startswith("动词"):
            collecting = True
            line = line.split(":", 1)[1] if ":" in line else line
        elif collecting and line.startswith("  "):
            pass
        elif collecting and not line.strip():
            continue
        elif collecting:
            break  # 动词段结束(id:/寻址:/窗口:/示例: 等新节)
        else:
            continue
        clean = re.sub(r"<[^>]*>|\([^)]*\)|\[[^\]]*\]", " ", line)
        for seg in re.split(r"[;|/]", clean):
            first = seg.strip().split(" ")[0].strip("()[]:,。;")
            if _WORD.match(first):
                tokens.add(first)
    return tokens


@pytest.mark.parametrize("face", sorted(REGISTRIES))
def test_registry_keys_documented_in_manual(face):
    """方向一:注册表键必须在手册出现(隐藏别名白名单豁免)。"""
    text = cli.manual(face)
    for key in REGISTRIES[face]:
        assert re.search(rf"\b{re.escape(key)}\b", text), \
            f"{face} 注册表键 {key} 未在手册文档化(手册漂移或实现私增)"


@pytest.mark.parametrize("face", sorted(REGISTRIES))
def test_manual_verbs_present_in_registry(face):
    """方向二:手册动词段词元必须可分派(注册表键或白名单)。"""
    verbs = REGISTRIES[face]
    allowed_extra = _MANUAL_ONLY.get(face, set())
    for token in _manual_verb_tokens(face):
        assert token in verbs or token in allowed_extra, \
            f"{face} 手册动词 {token} 不在注册表(手册宣称未实现 = 漂移)"


# ---------- 批5a:acceptance.sh 离线断言下沉(缺口分析尺 2.2) ----------

def test_engine_fail_passes_through_stderr(capsys, monkeypatch):
    """acceptance.sh「错误暴露」纪律:引擎失败原文透传 stderr,stdout 恒纯数据。"""
    monkeypatch.setattr(runtime_ctx, "CMD_NAME", "shares")
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
    """acceptance.sh A 组:未知动词 usage 退 2(六域参数校验层,零引擎触碰)。"""
    for entry, attr in MAIN_ATTR.items():
        monkeypatch.setattr(sys, "argv", [entry, "完全不存在的动词xyz"])
        with pytest.raises(SystemExit) as ei:
            getattr(cli, attr)()
        assert ei.value.code == 2, f"{entry} 未知动词应退 2"
        err = capsys.readouterr().err
        # ctxs 走 _die 本地面前缀「ctx:」;六域错误面承诺 = 未知动词即 usage 退 2
        assert "usage" in err or "--llms" in err or "查看手册" in err or "未知动词" in err or "看手册" in err, \
            f"{entry} 未知动词错误面缺指引:{err!r}"


def test_herdr_run_timeout_returns_rc124(monkeypatch):
    """acceptance.sh 容错纪律:引擎超时回 rc=124 不抛(v3.0.2 容错;mock 进程面)。"""
    import prim.engines as engines_mod

    class _FakeProc:
        pid = 1
        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="herdr", timeout=timeout or 1)
        def kill(self):
            pass

    monkeypatch.setattr(engines_mod, "herdr", lambda: "herdr")
    monkeypatch.setattr(engines_mod.subprocess, "Popen", lambda *a, **kw: _FakeProc())
    monkeypatch.setattr(engines_mod, "_kill_tree", lambda proc: None)
    r = engines_mod.herdr_run(None, "agent", "list", timeout=1)
    assert r.returncode == 124
    assert "timeout" in r.stderr


def test_mcps_bin_missing_structured_error(monkeypatch, capsys):
    """脱敏令收口:MCPS_BIN 缺位 = structured error engine_fail(不再有仓内路径回退)。"""
    monkeypatch.delenv("MCPS_BIN", raising=False)
    import shutil as _sh
    monkeypatch.setattr(mcps_mod, "which" if hasattr(mcps_mod, "which") else "_which", None, raising=False)
    # _mcp2cli 内部 from shutil import which;屏蔽 PATH 命中 = 打桩 which 返 None
    monkeypatch.setattr(_sh, "which", lambda name: None)
    with pytest.raises(SystemExit) as ei:
        mcps_mod._mcp2cli()
    assert ei.value.code == 1
    err = capsys.readouterr().err
    assert "MCPS_BIN" in err  # 人读形或 json 形都带指路面
    if err.strip().startswith("{"):
        assert json.loads(err.strip())["code"] == "engine_fail"


def test_mcps_bin_env_resolved(monkeypatch):
    """MCPS_BIN env 指路命中(不落 PATH)。"""
    fake = PRIM_ROOT / "fake-mcp2cli.exe"
    fake.write_text("", encoding="utf-8")
    try:
        monkeypatch.setenv("MCPS_BIN", str(fake))
        assert mcps_mod._mcp2cli() == str(fake)
    finally:
        fake.unlink(missing_ok=True)


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
        r"lan-ubuntu|lan-mac|lan-pve|lan-linux2|evo-claude|hst_rs|s5_rs")
    for py in sorted(PRIM_SRC.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        hit = banned.search(text)
        assert not hit, f"{py.name} 命中敏感模式 {hit.group(0)!r}(脱敏表 sensitive-data-policy.md)"


def test_manual_uses_documentation_ip_only():
    """手册示例 IP 只许文档保留段(RFC 5737 192.0.2.0/24)。"""
    src = (PRIM_SRC / "prim" / "manual.py").read_text(encoding="utf-8")
    for ip in re.findall(r"\b\d+\.\d+\.\d+\.\d+\b", src):
        assert ip.startswith("192.0.2."), f"manual.py 出现非文档段 IP {ip}"
