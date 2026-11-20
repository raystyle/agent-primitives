"""agent_primitives 手册单源(批3R 自 cli 拆出):manual dict + 版本单源 _pkg_ver

契约(CONTRACT 五节):--help 与 --llms 同源;版本头从包元数据 stamp(pyproject 唯一源,
禁手写漂移);手册动词表与分派注册表一致性由 tests/test_prim.py 断言。

批5c(2026-11-13,ADR-0003 CONTRACT-v2):入口重组 11→6(agents/desks/machines/streams/
carry/ctxs);tasks 并入 streams 子面;files(原 shares)/pipes/ports 合成 carry;mcps 整域退役
(ADR-0001 MCP 边缘化);退役动词各入口 help/CTA 可见化。
"""
from __future__ import annotations


def _pkg_ver() -> str:
    """--llms 头版本单源:包元数据(C4 票,禁手写漂移)。"""
    try:
        from importlib.metadata import version as _v
        return _v("agent-primitives")
    except Exception:
        return "v?"


def manual(cmd: str) -> str:
    m = {
        "files": f"""files@{_pkg_ver()} - 文件域:交付或取回一份已写完的文件(五入口收敛 2026-11-18;shares 更名 files 2026-11-20;动词对齐 hc)
动词:ls(本机搬运面清点);put <path>(推送上桌,回 share key)/ get <key> [到目录](取回落盘);
  send <id> <key>(留痕加知会:入流 + hc send 一发;原 to 更名,动词五域统一)
示例:
  files put report.md
  files get 3fa9 report/ 到当前目录
  files send node-a-claude-1 3fa9 交付评审
退役注记:agents/desks/machines 三域退役(2026-11-18:归 hc 与 herdr-app 原生面);carry 域退役(2026-11-16)""",
        "streams": f"""streams@{_pkg_ver()} - 流域:增量消息(S2 持久流,引擎 s5;room 即房间)
动词:ls(裸调用 = 房间清单;带流名 = 读流,-f 活跟随);room <room>(read room,-f 活跟随)/ room <room> <消息> [--file <文件> [--lines N:M]](speak room或传日志切片);
  dm <对方别名> <消息> [--file <文件> [--lines N:M]](DM lane,流名按双别名排序自动定);
  ls [流名] [--from <seq>|--resume] [-n N] [-f](活跟随,Ctrl+C 退 130);append <流> <消息>(或 stdin 管道:cat x | streams append <流>,不加 host 前缀);send <id> <流> <消息> [--force](原 to 更名,动词五域统一)
示例:
  streams ls
  streams room fleet
  streams room gateway-logging 四方合研-新证据入档
  streams room gateway-logging 日志请看 --file app.log --lines 50-62
  streams dm node-b-agent-1 私信验证
  cat build.log | streams append room/build
  streams send node-a fleet 回执-批X完成
退役注记:tasks 子面已退役(2026-11-16:streams 只做增量消息);rooms 已并入裸 view(命名与 agents view 对齐)""",
        "ctxs": f"""ctxs@{_pkg_ver()} - 对话历史域:agent 请求全链检索(引擎 ClickHouse gw_logs;与 agents read 分工:read=实时屏,ctxs=历史档案)
动词:ls [agent] [--limit N] [--since <ts>] [--before <ts>](最近请求头行:时间/模型/token/耗时/request_id;时间窗直裁分区);
  ls <request_id> [--around <词>] [--window N](全链;--around 只出命中块±N 邻块;show 已并入 2026-11-16);
  search <词> [--term <词>]... [--limit N] [--days N](跨请求全文,多词 OR;每行带命中片段 snip;--days 扫描窗缺省 1 天) [--since <ts>] [--before <ts>](精确窗覆盖 --days)
窗口:head 365 天,gwlog 正文 180 天;词至少 2 字符(UTF-8 计)
退役注记:mcps 域整域退役(ADR-0001 MCP 边缘化,用户裁定 2026-11-13;连通用 MCP 客户端腿也不留)
示例:
  ctxs ls
  ctxs ls 0192a0f0-xxxx --around "挂死" --window 1
  ctxs search "panic"
  ctxs search --term 杀树 --term ensure_ascii""",
        "ports": f"""ports@{_pkg_ver()} - 端口映射域:tailcat serve 面板端口/服务映射(五入口直入 2026-11-18;动词对齐 hc,原 carry 域显式道)
动词:ls [host](映射面清单);start <spec>(起映射:8080,8443 端口表 / 5555:IP:5555 服务侧映射 / all / exit-node;原 open 更名);
  close <地址或pid>(停映射);fwd <addr> <local>:<remote-port>(本地起听转发,0 = 空口);
  send <id> <spec>(留痕知会:入流 + hc send 一发;原 to 更名)
示例:
  ports ls
  ports start 8123
  ports close tcADDR
  ports fwd tcADDR 15555:5555
退役注记:carry 域退役(2026-11-16);ports 直入五入口(2026-11-18)""",
        "pipes": f"""pipes@{_pkg_ver()} - 实时字节域:管道收发与转发(五入口直入 2026-11-18;动词对齐 hc,原 carry 域显式道)
动词:ls [host](管道面清单);start(起收听管道,常驻至 close;原 open 更名);
  close <地址或pid>(杀进程收档广播);send <addr>(连对方管道,stdin 直通)
示例:
  pipes ls
  pipes start
  cat x.log | pipes send tcADDR
退役注记:carry 域退役(2026-11-16);pipes 直入五入口(2026-11-18)""",
    }
    return m.get(cmd, "")
