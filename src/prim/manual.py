"""prim 手册单源(批3R 自 cli 拆出):manual dict + 版本单源 _pkg_ver

契约(CONTRACT 五节):--help 与 --llms 同源;版本头从包元数据 stamp(pyproject 唯一源,
禁手写漂移);手册动词表与分派注册表一致性由 tests/test_prim.py 断言。

批5a 迁移注记(herdr-ccoe,脱敏令 2026-11-13):示例中活机器名/真实 IP 一律改角色代称
(node-a/node-b 形),金样同步再生(语义冻结点 = 结构与动词面,角色代称即冻结形)。
批5b(2026-11-13):agents/desks/machines/tasks 四面迁入合拢,十一入口齐。
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
        "agents": f"""agents@{_pkg_ver()} - 消息域:全局 pane 操作器(隐式路由,任何端点可用)
文法:agents [全局旗标] <动词> [动词旗标] [位置参数];裸调用 = view
全局旗标:--help -h --llms --json --format <fmt> --full-output --filter-output <pat> --schema --force(投递)
动词:view [host];machines;list [机];ws|workbenches [机](工作台清点:home+~/repos/* 仓+origin);yolo [--audit]|yolo <id> [--yes](四家 CLI 检测/冷翻);read <id> [--lines N] [--timeout S];keys <id> <键>;run <id> <命令...>(格内跑命令,herdr pane run 原语壳);
  to <id> <文本> [--force](投递即镜像 dm 流,回信事件道:wait 收)
  wait [--from <id>] [--timeout S](阻塞等新入站消息,到件即返;引擎级轮询,agent 不再盲等)
  inbox [--from <id>](非阻塞收件单:dm 流入站消息清单)
  mode <dnd|away|online> [until](presence 走 shares 键);
  start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机];
  ws <label> [--cwd DIR] [--machine 机]|ws list [机]|ws close <台> [机];
  shell <机> <仓路径>(开台 shell 回 root 格);dev <机> <仓路径> [--kind 类](开台+起 agent);
  split <id> [--direction right|down];tab <list [机]|create <机>|close <机:tab>>;
  zoom <id>;close <id>(关格零击杀:agent /exit 优雅退后 shell exit,格自消);
  wt [机] [--title 名](win 专属:本窗开 tab 显该机窗格视图);
  trust(信任屏放行);sync(机册面);reload <id>(同格同 session 重进,重载技能与插件)
id:裸名(全局,投递回信用bare alias)|机:名或格|local:格;裸 pane id 非法;信封 from 机器段 = host_label
示例:
  agents view
  agents read node-a-claude-1 --lines 20
  agents to node-a-claude-1 "评审请求已递" --json
  agents dev node-a ~/repos/demo-rs --kind grok""",
        "desks": f"""desks@{_pkg_ver()} - 工位(pane)/窗台(workspace)操作器(拓扑面,ADR-0007 加 2026-10-25 复数对齐裁定;消息面走 agents,机册走 machines;desk 为旧名单字别名)
术语:工位/窗格 = pane(p1,p1W);工作台/窗台 = workspace(w 编号,一个终端窗)
view [host](拓扑视图:窗台->tab->工位分组,▍ 焦点工位,活动列 = 标题;含非 agent 工位;裸调用同)
动词(与 agents 同实现,软拆 alias 期):
  start <名> --kind <类> [--pane 格] [--cwd DIR] [--machine 机];close <id>(优雅退)
  split <id> [--direction right|down];tab <list|create|close>;zoom <id>;wt [机] [--title 名]
  ws <label> [--cwd DIR] [--machine 机]|ws list [机]|ws close <台>;shell <机> <仓路径>;dev <机> <仓路径> [--kind 类]
  yolo [--audit]|yolo <id> [--yes](四家 CLI 检测/冷翻);trust(信任屏放行);reload <id>(重载技能)
id:裸名|机:名或格|local:格;示例:desks start node-a-kimi-2 --kind kimi --cwd ~/repos/demo;desks split node-a-claude-1
alias 期:agents start/split/tab/... 同实现有效(1-2 大版本后收)""",
        "machines": f"""machines@{_pkg_ver()} - 机册域:herdr machine 封装(第九原语;ADR-0007 由 nodes 更名,nodes 别名已淘汰)
动词:view/list(册表+可达)/ status [名](全量或单机)/
  add <ssh-target> [--label <名>] [--remote-session <名>](注册新节点,herdr 自动装远端并起 server)/
  rename <名> --label <新名> / remove <名> / enable <名> / disable <名> / reconnect <名>/
  runtime [view|init|check|install|update|doctor|heal|config] [工具...](agent 运行时环境面,
  骑 ark;栈真源 = 仓根 runtimes.toml 仓 agent 自定;--machine <节点> 跨机经 ssh)/
  run <节点> <格> <命令...>(格内跑命令)/ close <节点> <格>(直关格)/
  pane <节点> <herdr pane 子面...>(list/get/read/split 直透)
寻址:label 或 profile-id 皆收(label 优先);机册真源在 herdr
示例:
  machines view
  machines add user@192.0.2.20 --label node-a
  machines disable node-a
  machines reconnect node-a
""",
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
        "tasks": f"""tasks@{_pkg_ver()} - 持久任务域:hst task 全局遥控(引擎 hst)
动词:view [host](实时任务面:fleet 状态总览加本机各仓 hst task show 直读;远机任务经 agents read <id> 看屏);
  set <id> <文本>;to <id> <文本> [--force](=set+知会)
示例:
  tasks view
  tasks to node-a-claude-1 "评审收束后发版\"""",
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
