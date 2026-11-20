"""agent_primitives 引擎面(批5c 置换):hc 单点客户端 / s5 / wsl 代役 / 进程树收割

契约:引擎错误原文不吞不裁(五b);hc_run 超时/离线回 rc=124 不抛(v3.0.2 容错);
win 缺 s5 走 wsl 代役(s5_cmd 探测缓存;探测禁吃 stdin,管道留给真调用)。
引擎裁定(ADR-0003 + CONTRACT-v2):herdr CLI spawnSync 退役,终端面恒 hc
(5c 务实形 = hc CLI spawn,与旧 herdr spawn 同形;常驻 JSON-RPC 留演进位);
s5/tailcat/hst/ark/CH 五引擎保留(命运表:hc 无对等原语)。
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess

from .runtime_ctx import die


def _find_bin(name: str) -> str | None:
    p = shutil.which(name)
    if p:
        return p
    for c in (os.path.join(os.path.expanduser("~/.local/bin"), name),
              f"/usr/local/bin/{name}"):
        if os.path.exists(c):
            return c
    return None


def hc_bin() -> str:
    """hc 二进制单点(herdr-core);缺位 = structured engine_fail。"""
    b = _find_bin("hc")
    if not b:
        die("engine_fail", "本机无 hc 二进制(herdr-core);装 herdr-core 或 PRIM_HC_BIN 指路", rc=1)
    return os.environ.get("PRIM_HC_BIN") or b


def s5() -> str:
    b = _find_bin("s5")
    if not b:
        die("engine_fail", "本机无 s5 二进制(share/stream 引擎)", rc=1)
    return b

# s5 调用前缀:win 无本地 s5 时走 wsl 代役(wsl -e 直 exec,stdin/stdout 管道直通)
_S5_PREFIX: list[str] | None = None


def _wsl_s5_path() -> str:
    """wsl 代役道 s5 路径(脱敏令 2026-11-13:去家目录硬编码,运行时探测):
    1. PRIM_WSL_S5 env 显式指路(绝对路径,最高优);
    2. PRIM_WSL_HOME env 给 WSL 家目录 → 拼 .local/bin/s5;
    3. 运行时探测:`wsl -e sh -c 'echo $HOME'` 取 WSL 默认用户家目录(一次,缓存于调用方)。
    探测失败回空串,由 s5_cmd 落 engine_fail。"""
    env = os.environ.get("PRIM_WSL_S5")
    if env:
        return env
    home = os.environ.get("PRIM_WSL_HOME") or ""
    if not home:
        try:
            r = subprocess.run(_wsl_exec() + ["sh", "-c", "echo $HOME"],
                               capture_output=True, text=True, timeout=15,
                               encoding="utf-8", errors="replace",
                               stdin=subprocess.DEVNULL)
            if r.returncode == 0:
                home = (r.stdout or "").strip()
        except Exception:
            home = ""
    return f"{home}/.local/bin/s5" if home else ""


def s5_cmd() -> list[str]:
    global _S5_PREFIX
    if _S5_PREFIX is None:
        b = _find_bin("s5")
        if b:
            _S5_PREFIX = [b]
        elif os.name == "nt":
            _s5p = _wsl_s5_path()
            wsl_s5 = _wsl_exec() + ([_s5p] if _s5p else [])
            if not _s5p:
                _S5_PREFIX = []
            else:
                try:
                    r = subprocess.run(wsl_s5 + ["streams"], capture_output=True, text=True,
                                       timeout=10, encoding="utf-8", errors="replace",
                                       stdin=subprocess.DEVNULL)  # 探测禁吃 stdin(stdin 管道留给真调用)
                    _S5_PREFIX = wsl_s5 if r.returncode == 0 else []
                except Exception:
                    _S5_PREFIX = []
        else:
            _S5_PREFIX = []
    if not _S5_PREFIX:
        die("engine_fail", "本机无 s5 二进制(share/stream 引擎)", rc=1)
    return _S5_PREFIX


def s5_is_wsl() -> bool:
    """s5 道是否走 wsl 代役(路径翻译门控;win 原生 s5 装机后不得译 /mnt 形,
    判例 2026-11-13:原生 s5 收 wsl 形路径即 LocalIo)。"""
    prefix = s5_cmd()
    return bool(prefix) and "wsl" in prefix[0].lower()


def _wsl_exec() -> list[str]:
    w = shutil.which("wsl.exe") or r"C:\Windows\System32\wsl.exe"
    return [w, "-e"]


def wsl_path(p: str) -> str:
    """win 路径转 wsl 形(D:\\x → /mnt/d/x);已在 wsl 形或 POSIX 形则原样。"""
    p = p.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        return f"/mnt/{p[0].lower()}{p[2:]}"
    return p


def host_path(p: str) -> str:
    """wsl /mnt/x 形转 win 形(供 get -o 输出落回本机);非该形原样。"""
    if p.startswith("/mnt/") and len(p) > 6 and p[5].isalpha() and p[6] == "/":
        return f"{p[5].upper()}:{p[6:]}"
    return p


def _kill_tree(proc: subprocess.Popen):
    """杀整棵进程树(win 孙进程握管道致 communicate 挂死的根修)。"""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=10)
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        proc.kill()  # 兜底直杀


# ---------- hc 单点客户端(批5c;TS 侧单点 = cli/src/lib/hc.ts) ----------

def hc_run(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """spawn `hc <args...>`。容错(承引擎容错纪律(v3.0.2 形)):超时/异常回 CompletedProcess
    (rc=124 超时 / 125 spawn 失败)不抛;引擎错误原文保留。"""
    cmd = [hc_bin()] + list(args)
    popen_kw: dict = {}
    if os.name != "nt":
        popen_kw["start_new_session"] = True  # 独立进程组,杀树用
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", **popen_kw)
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 125, "", f"hc spawn fail: {e}")
    try:
        out, err = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, out or "", err or "")
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            out, err = "", f"hc timeout after {timeout}s ({' '.join(args[:2])})"
        return subprocess.CompletedProcess(cmd, 124, out or "",
                                           err or f"hc timeout after {timeout}s ({' '.join(args[:2])})")
    except KeyboardInterrupt:
        _kill_tree(proc)
        raise


def hc_json(*args: str, timeout: int = 30) -> list | dict:
    """spawn `hc <args...> --json` 解析;失败回 [](fail-soft,承 json 容错(v3 形))。"""
    r = hc_run(*args, "--json", timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return []


def hc_addr(machine: str | None, t: str) -> str:
    """终端跨机地址:t 含 "/"(已全形)原样;机册机 → machine/t;本机 → t。"""
    if not t or "/" in t:
        return t
    if machine and machine not in ("", "local"):
        return f"{machine}/{t}"
    return t


def hc_exec_on(machine: str, argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """hc exec --on:远端无终端直跑(argv 不经 shell;--json 须在 ARGV 之前,
    判例 2026-11-13:ARGV 是 greedy 尾参)。"""
    return hc_run("exec", "--json", "--on", machine, "--timeout", str(min(timeout, 600)),
                  *argv, timeout=timeout + 15)


def exec_result(r: subprocess.CompletedProcess) -> subprocess.CompletedProcess:
    """hc exec --json 的 stdout(ExecResult 信封)还原成 CompletedProcess 形
    (stdout/stderr base64 解码,returncode = code;解析败原样透传)。"""
    try:
        d = json.loads(r.stdout or "{}")
        return subprocess.CompletedProcess(r.args, int(d.get("code") or 0),
                                           _b64s(d.get("stdout")), _b64s(d.get("stderr")))
    except Exception:
        return r


def _b64s(v) -> str:
    import base64
    if not isinstance(v, str):
        return ""
    try:
        return base64.b64decode(v).decode("utf-8", errors="replace")
    except Exception:
        return ""


# ---------- s5 流封装(批3R 自 domains 拆出;files/streams/tasks/pipes/ports 共用) ----------

def s5_run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(s5_cmd() + list(args), capture_output=True, text=True,
                          input=stdin, timeout=60, encoding="utf-8", errors="replace")


def s5_append(stream: str, body: str) -> bool:
    r = s5_run("append", stream, stdin=body + "\n")
    return r.returncode == 0


def s5_tail(stream: str, n: int = 20, seq: int | None = None) -> list[dict]:
    args = ["tail", stream, "-n", str(n)]
    if seq is not None:
        args += ["--seq", str(seq)]
    r = s5_run(*args)
    out = []
    for line in (r.stdout or "").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    # s5 语义:--seq 与 -n 互斥时 -n 被忽略(从 seq 续读到尾);本层自行限 N
    if seq is not None:
        return out[:n]
    return out


def s5_ls(prefix: str) -> list[dict]:
    r = s5_run("ls", prefix)
    out = []
    for line in (r.stdout or "").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def s5_tail_streams() -> list[dict]:
    r = s5_run("streams")
    out = []
    for line in (r.stdout or "").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def json_field(text: str, *keys: str) -> str:
    """嵌套 JSON 里取字段(逐层下钻,herdr result 封套感知),失败空串。"""
    try:
        d = json.loads(text)
        for k in keys:
            d = d.get("result", d) if isinstance(d, dict) and "result" in d and k not in d else d
            d = d.get(k, "")
        return str(d or "")
    except Exception:
        return ""
