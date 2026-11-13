"""prim 手册单源(批3R 自 cli 拆出):manual dict + 版本单源 _pkg_ver

契约(CONTRACT 五节):--help 与 --llms 同源;版本头从包元数据 stamp(pyproject 唯一源,
禁手写漂移);手册动词表与分派注册表一致性由 tests/test_prim.py 断言。

批5a 迁移注记(herdr-ccoe,脱敏令 2026-11-13):只带 5a 六域手册面(agents/desks/
machines/tasks 四面随 5b 迁入);示例中活机器名/真实 IP 一律改角色代称
(node-a/node-b 形),金样同步再生(语义冻结点 = 结构与动词面,角色代称即冻结形)。
"""
from __future__ import annotations


def _pkg_ver() -> str:
    """--llms 头版本单源:包元数据(C4 票,禁手写漂移)。"""
    try:
        from importlib.metadata import version as _v
        return _v("prim")
    except Exception:
        return "v?"


def manual(cmd: str) -> str:
    m = {
        "shares": f"""shares@{_pkg_ver()} - 文件域:S3 中转(引擎 s5;内容哈希键)
动词:view;put <文件>;get <键> [-o|--output 名];to <id> <文件> [--force](=上架+模板知会)
示例:
  shares put report.md
  shares to node-a report.md --json""",
        "streams": f"""streams@{_pkg_ver()} - 流域:S2 持久流(引擎 s5;room 即房间,一等概念)
动词:rooms(列房间);room <room>(read room,-f 活跟随)/ room <room> <消息> [--file <文件> [--lines N:M]](speak room或传日志切片);
  dm <对方别名> <消息> [--file <文件> [--lines N:M]](DM lane,流名按双别名排序自动定);
  view [流名] [--from <seq>|--resume] [-n N] [-f](活跟随,Ctrl+C 退 130);append <流> <消息>(或 stdin 管道:cat x | streams append <流>,不加 host 前缀);to <id> <流> <消息> [--force]
示例:
  streams rooms
  streams room fleet
  streams room gateway-logging 四方合研-新证据入档
  streams room gateway-logging 日志请看 --file app.log --lines 50-62
  streams dm node-b-agent-1 私信验证
  cat build.log | streams append room/build
  streams to node-a fleet 回执-批X完成""",
        "pipes": f"""pipes@{_pkg_ver()} - 管道域:tailcat 实时(本机收对方发;管道常驻至 close)
动词:view [host];open;close <addr|pid>;send <addr>(recipient:连管道发数据,stdin 直通);to <id> [--force](=open+模板知会,取用行 pipes send)
示例:
  pipes view node-a
  pipes to node-a""",
        "ports": f"""ports@{_pkg_ver()} - 端口域:任意节点端口转发映射(引擎 tailcat serve;映射常驻至 close)
动词:view [host];open <spec>(spec = 8080,8443 端口表 / 5555:IP:5555 服务侧映射,serve 面被服务端口,非客户端监听 / all / exit-node);close <addr|pid>;fwd <addr> <local>:<remote-port>(recipient: local listener, 0 = free port, Ctrl+C to stop);to <id> <spec> [--force](=open+模板知会,取用行 ports fwd 全端口枚举)
示例:
  ports view node-a
  ports open 8123
  ports open 5555:192.0.2.10:5555
  ports to node-a 8123""",
        "ctxs": f"""ctxs@{_pkg_ver()} - 对话历史域:agent 请求全链检索(引擎 ClickHouse gw_logs;与 agents read 分工:read=实时屏,ctxs=历史档案)
动词:view [agent] [--limit N] [--since <ts>] [--before <ts>](最近请求头行:时间/模型/token/耗时/request_id;时间窗直裁分区,翻页找目标日用);
  show <request_id> [--around <词>] [--window N](全链;--around 只出命中块±N 邻块,命中块为命中点居中 3000 字);
  search <词> [--term <词>]... [--limit N] [--days N](跨请求全文,多词 OR;每行带命中片段 snip;--days 扫描窗缺省 1 天) [--since <ts>] [--before <ts>](精确窗覆盖 --days)
窗口:head 365 天,gwlog 正文 180 天;词至少 2 字符(UTF-8 计)
示例:
  ctxs view
  ctxs show 0192a0f0-xxxx --around "挂死" --window 1
  ctxs search "panic"
  ctxs search --term 杀树 --term ensure_ascii""",
        "mcps": f"""mcps@{_pkg_ver()} - MCP 域:通用 MCP 客户端(第八原语,出站;引擎 mcp2cli)
文法:mcps [全局旗标] <动词> [位置参数];裸调用 = view
动词:view [目标](在册表+健康)/ tools <目标>(列 tools)/
  call <目标> <tool> [--arg k=v]... [--arg-json k=<json>]...(调用;值字符串形透传)/
  add <名> --url <URL> [--note <注>]/ remove <名>
注册表:~/.config/mcps/targets.yaml(名->url;MCPS_REGISTRY env 覆盖)
超时:--timeout <s> 覆盖;view/tools 默认 10s、call 120s,上限 600
示例:
  mcps view
  mcps tools lab-node
  mcps call lab-node shell --arg cmd=whoami --arg wait=true
  mcps call lab-node spawn --arg-json 'argv=["notepad"]'
  mcps add my-mcp --url http://192.0.2.50:9881/mcp --note 试""",
    }
    return m.get(cmd, "")
