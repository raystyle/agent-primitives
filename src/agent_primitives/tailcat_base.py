"""agent_primitives tailcat 基座(批3R:pipes/ports 双胞胎归一)

pipes(临时管道,stdio 直连)与 ports(端口映射,tailcat serve)两域共用:
进程起停、addr 档轮询、pid 活性、状态档三/四件、公开流广播、win 防火墙 CTA。
参数差 = 状态目录(~/.local/state/pipe 对 ports)、广播流(room/pipe-live 对 port-live)、
serve spec 参数与 spec 档、错误前缀(pipes:/ports:)。
"""
from __future__ import annotations
import os
import subprocess
import time

from .engines import _find_bin, s5_append
from .identity import host_label
from .runtime_ctx import die, eprint

_FW_CACHE: bool | None = None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def tailcat_bin() -> str:
    b = _find_bin("tailcat")
    if not b:
        die("engine_fail", "本机无 tailcat(v0.7.0)", rc=1)
    return b


def statedir(domain: str) -> str:
    """状态目录:pipes = ~/.local/state/pipe,ports = ~/.local/state/ports。"""
    d = os.path.expanduser(f"~/.local/state/{'ports' if domain == 'ports' else 'pipe'}")
    os.makedirs(d, exist_ok=True)
    return d


def broadcast(domain: str, pid: int, alive: int):
    """公开行(契约五a:跨机可见,不含 addr)。"""
    room = "room/port-live" if domain == "ports" else "room/pipe-live"
    s5_append(room, f"{host_label()}|pid={pid}|alive={alive}|ts={_now()}")


def pid_alive(pid: int) -> bool:
    """跨平台活性探测(win 上 os.kill(pid,0) 是 TerminateProcess,禁用)。"""
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            k32.CloseHandle(h)
            return True
        except Exception:
            return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def alive(domain: str) -> list[dict]:
    """本机活动项:清死档(pid 不活即收档),返回 [{pid,addr,(spec,)log}]。"""
    d = statedir(domain)
    suffixes = ("pid", "addr", "log", "spec") if domain == "ports" else ("pid", "addr", "log")
    out = []
    import glob as _g
    for pf in sorted(_g.glob(os.path.join(d, "pid.*.txt"))):
        pid = os.path.basename(pf)[4:-4]
        try:
            pid_i = int(pid)
        except ValueError:
            continue
        if not pid_alive(pid_i):
            for suf in suffixes:
                try:
                    os.remove(os.path.join(d, f"{suf}.{pid}.txt"))
                except OSError:
                    pass
            continue
        row = {"pid": pid_i, "log": os.path.join(d, f"log.{pid}.txt")}
        for key in ("addr", "spec"):
            if key in suffixes:
                try:
                    row[key] = open(os.path.join(d, f"{key}.{pid}.txt")).read().strip()
                except OSError:
                    row[key] = ""
        out.append(row)
    return out


def open_listener(domain: str, spec: str | None = None) -> tuple[int, str]:
    """起收听(后台,常驻至 close):pipes 无参,ports = serve <spec>;返回 (pid, addr)。
    状态档:pipes 三件(pid/addr/log),ports 四件(加 spec)。"""
    d = statedir(domain)
    tc = tailcat_bin()
    argv = [tc, "serve", spec] if domain == "ports" else [tc]
    addr_file = os.path.join(d, "_open.addr")
    log_file = os.path.join(d, "_open.log")
    env = dict(os.environ, TAILCAT_ADDR_FILE=addr_file)
    with open(log_file, "wb") as lg:
        p = subprocess.Popen(argv, stdout=lg, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, env=env,
                             start_new_session=True)
    addr = ""
    for _ in range(10):
        if os.path.isfile(addr_file) and os.path.getsize(addr_file) > 0:
            addr = open(addr_file).read().strip()
            break
        try:
            r = subprocess.run(["grep", "-oE", r"tc[A-Za-z0-9_-]{20,}", log_file],
                               capture_output=True, text=True, timeout=5)
            addr = (r.stdout or "").splitlines()[0].strip() if r.stdout.strip() else ""
        except Exception:
            addr = ""
        if addr:
            break
        time.sleep(1)
    pid = p.pid
    if addr:
        try:
            os.replace(addr_file, os.path.join(d, f"addr.{pid}.txt"))
        except OSError:
            pass
        log_dst = os.path.join(d, f"log.{pid}.txt")
        try:
            os.replace(log_file, log_dst)
        except OSError:
            # win:子进程握 log 句柄,replace 拒;快照代位(活文件仍 _open.log)
            try:
                import shutil as _sh
                _sh.copyfile(log_file, log_dst)
            except OSError:
                pass
        open(os.path.join(d, f"pid.{pid}.txt"), "w").close()
        if domain == "ports":
            open(os.path.join(d, f"spec.{pid}.txt"), "w").write(spec)
        broadcast(domain, pid, 1)
    else:
        p.kill()
        eprint(f"{domain}: 地址未取到(10s)")
    return pid, addr


def close_match(domain: str, q: str, cta_cmd: str):
    """close <addr|pid> 共用臂:命中即杀 15、收状态档、广播 alive=0。"""
    label = "端口映射" if domain == "ports" else "管道"
    hit = next((r for r in alive(domain)
                if str(r["pid"]) == q or r["addr"] == q), None)
    if not hit:
        die("not_found", f"未匹配{label}({q})", [{"command": cta_cmd, "description": f"查本机{label}"}])
    try:
        os.kill(hit["pid"], 15)
    except OSError:
        pass
    suffixes = ("pid", "addr", "log", "spec") if domain == "ports" else ("pid", "addr", "log")
    for suf in suffixes:
        try:
            os.remove(os.path.join(statedir(domain), f"{suf}.{hit['pid']}.txt"))
        except OSError:
            pass
    broadcast(domain, hit["pid"], 0)
    print(f"{domain}: 已关 pid={hit['pid']}(地址作废)")
    from .runtime_ctx import emit_ok
    emit_ok({"status": "delivered", "pid": hit["pid"]})


def fw_ok() -> bool:
    """win 面 tailcat 防火墙放行检测(缓存;规则名 tailcat-in,由 CTA 指令创建)。"""
    global _FW_CACHE
    if os.name != "nt":
        return True
    if _FW_CACHE is None:
        try:
            r = subprocess.run(["netsh", "advfirewall", "firewall", "show", "rule",
                                "name=tailcat-in"], capture_output=True, text=True,
                               timeout=8, encoding="utf-8", errors="replace")
            _FW_CACHE = (r.returncode == 0 and "tailcat" in (r.stdout or "").lower())
        except Exception:
            _FW_CACHE = True  # 检测失败不挡操作,只少一条提醒
    return _FW_CACHE


def fw_cta():
    """win 防火墙未放行时的 CTA 提醒(stderr 面,--json 亦可见)。"""
    if fw_ok():
        return
    tc = tailcat_bin()
    eprint("warn: windows 防火墙未见 tailcat 放行规则(默认入站 Block,对方直连会被拦,仅 DERP 中继可达)")
    eprint(f'CTA: 管理员运行: netsh advfirewall firewall add rule name=tailcat-in dir=in action=allow program="{tc}" enable=yes profile=any')
