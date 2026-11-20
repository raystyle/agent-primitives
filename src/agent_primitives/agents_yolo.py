"""agents yolo 子面:四家 CLI 的 yolo 检测与翻台(v3.7.0;用户令 2026-10-17)。

研究定谳(grok 研究单 yolo-detect-flip.txt,share c58479c604):
- 检测 = 状态栏/屏面正则(配置文件改模式时 argv 看不见);
- 热翻有限:claude bypass 须启动入环、kimi 斜杠要补 Enter、codex /permissions;
  可靠翻台 = 冷翻(写用户级配置 + /exit 退场 + fresh 起吃新配置);
- 各家全跳过值:claude bypassPermissions / codex never+danger-full-access /
  kimi auto(Never Ask;yolo 只是 Ask When Needed,仍会问!)/
  grok always-approve。
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from .addressing import _agents_of, _machine_labels, resolve
from .core import die, emit_ok, eprint
from .engines import exec_result, hc_exec_on, hc_run

# 检测正则族(状态栏实读形;研究单判据表,按序首中即判)
MODE_PATTERNS: dict[str, list] = {
    "claude": [("bypass permissions on", True), ("auto mode on", False),
               ("accept edits on", False), ("plan mode on", False),
               ("manual mode on", False), ("don't ask on", False)],
    "codex": [("Full Access", True), ("Read Only", False), ("Workspace Write", False)],
    "kimi": [("Never Ask", True), ("Ask When Needed", False), ("Always Ask", False)],
    "grok": [("always-approve", True), ("plan", False), ("auto", False)],
}

# 用户级配置配方(研究单设置配方表;翻台只写用户级,项目级各家不生效)
CONFIG_RECIPES: dict[str, dict] = {
    "claude": {
        "path": "~/.claude/settings.json",
        "json": {"permissions": {"defaultMode": "bypassPermissions"},
                 "skipDangerousModePermissionPrompt": True},
    },
    "codex": {
        "path": "~/.codex/config.toml",
        "toml": {"approval_policy": "never", "sandbox_mode": "danger-full-access"},
    },
    "kimi": {
        "path": "~/.kimi-code/config.toml",
        "toml": {"default_permission_mode": "auto"},  # auto = Never Ask;yolo 仍会问
    },
    "grok": {
        "path": "~/.grok/config.toml",
        "toml": {"ui": {"permission_mode": "always-approve"}},
    },
}

CLI_CMD = {"claude": "claude", "codex": "codex", "kimi": "kimi", "grok": "grok"}
CFG_PATHS = {"claude": "~/.claude/settings.json", "codex": "~/.codex/config.toml",
             "kimi": "~/.kimi-code/config.toml", "grok": "~/.grok/config.toml"}


def detect(machine: str, addr: str, kind: str):
    """读屏判模式 -> (mode 显示串, yolo)。读不到 = (None, None)。"""
    r = hc_run("read", addr, "--lines", "25", timeout=30)
    visible = (r.stdout or "") + (r.stderr or "")
    for pat, is_yolo in MODE_PATTERNS.get(kind, []):
        if pat in visible:
            return pat, is_yolo
    return None, None


def _write_local_config(kind: str) -> str:
    """本机用户级配置写(幂等合并)。返回路径。"""
    path = os.path.expanduser(CFG_PATHS[kind])
    rec = CONFIG_RECIPES[kind]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if "json" in rec:
        data = {}
        if os.path.isfile(path):
            try:
                data = json.load(open(path, encoding="utf-8"))
            except Exception:
                data = {}

        def merge(dst, src):
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    merge(dst[k], v)
                else:
                    dst[k] = v
        merge(data, rec["json"])
        json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        return path
    # toml:追加/改键行(极简行形;键值单行,单层节)
    lines = open(path, encoding="utf-8").read().splitlines() if os.path.isfile(path) else []
    for key, val in rec["toml"].items():
        if isinstance(val, dict):
            sec, skey = key, list(val)[0]
            sval = val[skey]
            in_sec = False
            wrote = False
            for i, ln in enumerate(lines):
                t = ln.strip()
                if t == f"[{sec}]":
                    in_sec = True
                    continue
                if t.startswith("["):
                    if in_sec and not wrote:
                        lines.insert(i, f"{skey} = \"{sval}\"")
                        wrote = True
                    in_sec = False
                    continue
                if in_sec and t.startswith(skey):
                    lines[i] = f"{skey} = \"{sval}\""
                    wrote = True
            if not wrote:
                lines += ["", f"[{sec}]", f"{skey} = \"{sval}\""]
        else:
            hit = False
            for i, ln in enumerate(lines):
                if ln.strip().startswith(key):
                    lines[i] = f"{key} = \"{val}\""
                    hit = True
                    break
            if not hit:
                lines.append(f"{key} = \"{val}\"")
    open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return path


_REMOTE_WRITER = (
    "import json,os,sys\n"
    "k=sys.argv[1]\n"
    "paths={'claude':'~/.claude/settings.json','codex':'~/.codex/config.toml',"
    "'kimi':'~/.kimi-code/config.toml','grok':'~/.grok/config.toml'}\n"
    "p=os.path.expanduser(paths[k])\n"
    "os.makedirs(os.path.dirname(p),exist_ok=True)\n"
    "if k=='claude':\n"
    "    import json as j\n"
    "    d={}\n"
    "    try:\n"
    "        d=j.load(open(p)) if os.path.isfile(p) else {}\n"
    "    except Exception:\n"
    "        d={}\n"
    "    d.setdefault('permissions',{})['defaultMode']='bypassPermissions'\n"
    "    d['skipDangerousModePermissionPrompt']=True\n"
    "    j.dump(d,open(p,'w'),indent=2)\n"
    "elif k=='grok':\n"
    "    ls=open(p).read().splitlines() if os.path.isfile(p) else []\n"
    "    sec=False;wrote=False\n"
    "    for i,l in enumerate(ls):\n"
    "        t=l.strip()\n"
    "        if t=='[ui]':\n"
    "            sec=True;continue\n"
    "        if t.startswith('['):\n"
    "            if sec and not wrote:\n"
    "                ls.insert(i,'permission_mode = \"always-approve\"');wrote=True\n"
    "            sec=False;continue\n"
    "        if sec and t.startswith('permission_mode'):\n"
    "            ls[i]='permission_mode = \"always-approve\"';wrote=True\n"
    "    if not wrote:\n"
    "        ls+=['','[ui]','permission_mode = \"always-approve\"']\n"
    "    open(p,'w').write('\\n'.join(ls)+'\\n')\n"
    "else:\n"
    "    keys={'codex':[('approval_policy','never'),('sandbox_mode','danger-full-access')],"
    "'kimi':[('default_permission_mode','auto')]}[k]\n"
    "    ls=open(p).read().splitlines() if os.path.isfile(p) else []\n"
    "    for key,val in keys:\n"
    "        hit=False\n"
    "        for i,l in enumerate(ls):\n"
    "            if l.strip().startswith(key):\n"
    "                ls[i]=key+' = \"'+val+'\"';hit=True;break\n"
    "        if not hit:\n"
    "            ls.append(key+' = \"'+val+'\"')\n"
    "    open(p,'w').write('\\n'.join(ls)+'\\n')\n"
    "print(p)\n"
)


def _write_config(kind: str, machine):
    """写用户级 yolo 配置;机册机经 hc exec --on 家目录写,机册外走原 ssh 道。返回路径/错误说明。"""
    if machine and machine not in ("", "local"):
        import shlex
        cmd = "python3 -c " + shlex.quote(_REMOTE_WRITER) + " " + shlex.quote(kind)
        if machine in _machine_labels():
            # hc 机册节点:hc exec --on(ssh 手搓退役;exec argv 不经 shell,python3 -c 单参)
            r = exec_result(hc_exec_on(machine, ["python3", "-c", cmd], timeout=60))
        else:
            # 机册外:原 ssh 道(红线不动)
            from .runtimes import _machine_target
            target = _machine_target(machine)
            r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", target, cmd],
                               capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return f"remote-write-fail: {(r.stderr or '')[:120]}"
        return r.stdout.strip() or "(remote)"
    return _write_local_config(kind)


def yolo_main(pos: list, g: dict) -> None:
    """agents yolo [--audit] | yolo <id> [--yes]:全舰队检测 / 单格冷翻。"""
    yes = "--yes" in sys.argv
    pos = [a for a in pos if not a.startswith("-")]

    if not pos:
        # 全舰队检测面(local + 各在册机)
        rows = []
        for a in _agents_of(None) + [x for lab in _machine_labels() for x in _agents_of(lab)]:
            kind = a.get("agent") or ""
            if kind not in MODE_PATTERNS:
                continue
            mode, is_yolo = detect(a["machine"], a["hc_address"], kind)
            rows.append({"machine": a["machine"], "pane": a.get("pane_id"),
                         "kind": kind, "cwd": a.get("cwd"),
                         "mode": mode, "yolo": is_yolo})
        if g.get("json"):
            emit_ok({"status": "ok", "count": len(rows), "rows": rows})
            return
        print(f"{'HOST':<12} {'PANE':<9} {'KIND':<7} {'MODE':<24} YOLO")
        needy = []
        for r in rows:
            mark = {True: "yes", False: "NO"}.get(r["yolo"], "?")
            print(f"{r['machine']:<12} {r['pane']:<9} {r['kind']:<7} {str(r['mode']):<24} {mark}")
            if r["yolo"] is False:
                needy.append(f"{r['machine']}:{r['pane']}({r['kind']})")
        if needy:
            print(f"\n非 yolo {len(needy)} 格;治:agents yolo <id> --yes(冷翻:用户级配置+/exit+fresh 起)")
            eprint("非 yolo: " + ", ".join(needy))
        else:
            print("\n全绿(? = 屏面无模式串,不可判)")
        return

    # 单格翻台(冷翻三步:写配置 -> /exit 退场 -> fresh 起)
    m, addr = resolve(pos[0])
    me = next((a for a in _agents_of(m) if a.get("hc_address") == addr), None)
    kind = (me or {}).get("agent") or ""
    if kind not in CONFIG_RECIPES:
        die("usage", f"「{kind or '?'}」不在四家面(claude/codex/kimi/grok)", rc=2)
    before_mode, before_yolo = detect(m, addr, kind)
    if before_yolo:
        print(f"agents: 已是 yolo({before_mode}),无需翻")
        emit_ok({"status": "ok", "target": f"{m}:{pane}", "kind": kind,
                 "before": before_mode, "after": before_mode, "executed": False})
        return
    if not yes:
        print(f"plan: {kind} 冷翻 @ {m}:{addr}")
        print(f"  1) 写用户级 {CFG_PATHS[kind]}(全跳过值;研究单配方)")
        print("  2) /exit 退场(冷翻 = 新进程吃新配置;会话上下文不迁)")
        print("  3) fresh 起 CLI")
        print("  默认预览未执行;加 --yes 执行本次变更")
        emit_ok({"status": "planned", "target": f"{m}:{addr.rsplit('/', 1)[-1]}", "kind": kind, "before": before_mode})
        return
    wrote = _write_config(kind, m)
    hc_run("send", addr, "/exit", timeout=45)
    for _ in range(12):
        time.sleep(1.5)
        from .addressing import row_of
        rr = row_of(addr)
        if not rr or rr.get("state") != "live":
            break
    argv = ["run", "--bg", "--no-notify", "--outlive-parent", CLI_CMD[kind]]
    cwd = (me or {}).get("cwd") or ""
    if cwd:
        argv += ["--cwd", cwd]
    if m not in ("", "local"):
        argv += ["--on", m]
    rk, new_addr = __import__("agent_primitives.agents_lifecycle", fromlist=["run_bg"]).run_bg(argv)
    detect_addr = new_addr or addr
    after_mode, after_yolo = None, None
    for _ in range(15):
        time.sleep(2.5)
        after_mode, after_yolo = detect(m, detect_addr, kind)
        if after_yolo:
            break
    print(f"yolo 翻 {m}:{addr.rsplit('/', 1)[-1]}({kind}):{before_mode} -> {after_mode}"
          + (f" @{new_addr}" if new_addr else "")
          + ("  OK" if after_yolo else "  仍非 yolo(查托管/requirements 锁)"))
    emit_ok({"status": "ok", "target": f"{m}:{addr.rsplit('/', 1)[-1]}", "kind": kind,
             "before": before_mode, "after": after_mode, "executed": True,
             "ok": after_yolo is True, "config": wrote, "pane": new_addr})
