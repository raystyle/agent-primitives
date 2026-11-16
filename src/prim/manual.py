"""prim 手册单源(批3R 自 cli 拆出):manual dict + 版本单源 _pkg_ver

契约(CONTRACT 五节):--help 与 --llms 同源;版本头从包元数据 stamp(pyproject 唯一源,
禁手写漂移);手册动词表与分派注册表一致性由 tests/test_prim.py 断言。

批5c(2026-11-13,ADR-0003 CONTRACT-v2):入口重组 11→6(agents/desks/machines/streams/
carry/ctxs);tasks 并入 streams 子面;shares/pipes/ports 合成 carry;mcps 整域退役
(ADR-0001 MCP 边缘化);退役动词各入口 help/CTA 可见化。
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
        "agents": f"""agents@{_pkg_ver()} - 消息域:投递/门控/收件(任何格可投;CONTRACT-v2 十五动词)
文法:agents [全局旗标] <动词> [动词旗标] [位置参数];裸调用 = view
全局旗标:--help -h --llms --json --format <fmt> --full-output --filter-output <pat> --schema --force(投递)
动词:view [host](格表:名/态/类/cwd;空 pane 异常态告警)/ workbenches [机](工作台清点:home+~/repos/* 仓+origin);
  read <id> [--lines N] [--timeout S](读屏;working 时内候到闲/超时);
  to <id> <文本> [--force](自由文投递:门控 → 拒投代记 → 信封 → dm 流镜像);
  wait [--from <id>] [--timeout S](阻塞等新入站信封);inbox [--from <id>](非阻塞收件单);
  mode <dnd|away|online> [until](presence 走 shares 键);
  start <名> --kind <类> [--cwd DIR] [--machine 机](起 agent,hc run 腿);
  close <id>(优雅退场:/exit → shell exit,格自消);reload <id>(同 session 重进,重载技能);
  trust(信任屏放行,判标库);yolo [--audit] | yolo <id> [--yes](四家 CLI 检测/冷翻);
  run <id> <命令...>(格内跑命令);shell <机> <仓路径>(起 shell 格回址);dev <机> <仓路径> [--kind 类](起 agent + 启动后阻塞检测);
  keys <id> <键>...(按键,一次多发)
已退役(ADR-0003 重构;调用回 usage 指新道):list(并入 view --json)/ machines(machines view)/
  sync(hc machine add --install)/ split / tab / zoom / wt(拓扑归 herdr-app mod GUI)
id:裸名(全局唯一)| 机:名或格 | local:格;信封 from 机器段 = host_label
示例:
  agents view
  agents read node-a-claude-1 --lines 20
  agents to node-a-claude-1 "评审请求已递" --json
  agents dev node-a ~/repos/demo-rs --kind grok""",
        "desks": f"""desks@{_pkg_ver()} - 工位拓扑兜底(view/start/close 三动词;树形主力 = herdr-app mod GUI)
术语:工位/窗格 = pane;工作台/窗台 = workspace(hc where 字段线)
view [host](全量工位表:机/格/类/态/活动;裸调用同;--json 出行形)
start <名> --kind <类> [--cwd DIR] [--machine 机];close <id>(优雅退)
已退役(ADR-0003 重构;调用回 usage 指新道):split / tab / zoom / wt(拓扑归 mod GUI);
  desk 单字别名删除(消费方可断裁定);shell/dev/ws/yolo/trust/reload 走 agents 面
id:裸名 | 机:名或格 | local:格;示例:desks view;desks close local:t1r""",
        "machines": f"""machines@{_pkg_ver()} - 机册域:hc machine.* 直通 + runtime 子面(骑 ark)
动词:view | list(机册表:机/态/靶/版本;state 即可达性)/
  add <ssh-target> [--name <名>] [--install](注册节点;--install 远端缺 hc 即装)/
  reconnect <机名>(hc machine login 直通)/
  run <节点> <格> <命令...>(格内跑命令)/ close <节点> <格>(直关格)/
  runtime(s) [view|init|check|install|update|doctor|heal|config] [工具...](agent 运行时环境面,
  骑 ark;栈真源 = 仓根 runtimes.toml 仓 agent 自定;--machine <节点> 跨机经 hc exec --on)
机册裁定:三台常驻 hc(机册节点角色代称);机册外节点不进册,ssh 行为不变
已退役(ADR-0003 重构;调用回 usage 指新道):status(并入 view)/ rename / remove(hc 直令)/
  enable / disable(hc 机册无启停态,需求再现做本地标记)/ pane(对象消失,拓扑归 mod GUI)
示例:
  machines view
  machines add user@192.0.2.20 --name node-a --install
  machines reconnect node-a
""",
        "shares": f"""shares@{_pkg_ver()} - 文件域:交付或取回一份已写完的文件(六入口复活 2026-11-16;carry 合并入口退役)
动词:view(本机搬运面清点);put <path>(推送上桌,回 share key)/ get <key> [到目录](取回落盘);
  to <id> <key>(留痕加知会:入流 + agents to 一发)
示例:
  shares put report.md
  shares get 3fa9 report/ 到当前目录
  shares to node-a-claude-1 3fa9 交付评审
退役注记:carry 域退役(2026-11-16 裁定:三合一入口不要,shares 直入);pipes(实时字节)与 ports(端口映射)随 carry 退役""",
        "streams": f"""streams@{_pkg_ver()} - 流域:增量消息(S2 持久流,引擎 s5;room 即房间)
动词:view(裸调用 = 房间清单;带流名 = 读流,-f 活跟随);room <room>(read room,-f 活跟随)/ room <room> <消息> [--file <文件> [--lines N:M]](speak room或传日志切片);
  dm <对方别名> <消息> [--file <文件> [--lines N:M]](DM lane,流名按双别名排序自动定);
  view [流名] [--from <seq>|--resume] [-n N] [-f](活跟随,Ctrl+C 退 130);append <流> <消息>(或 stdin 管道:cat x | streams append <流>,不加 host 前缀);to <id> <流> <消息> [--force]
示例:
  streams view
  streams room fleet
  streams room gateway-logging 四方合研-新证据入档
  streams room gateway-logging 日志请看 --file app.log --lines 50-62
  streams dm node-b-agent-1 私信验证
  cat build.log | streams append room/build
  streams to node-a fleet 回执-批X完成
退役注记:tasks 子面已退役(2026-11-16:streams 只做增量消息);rooms 已并入裸 view(命名与 agents view 对齐)""",
        "carry": f"""carry@{_pkg_ver()} - 搬运域:同构三合一(shares 文件 + pipes 管道 + ports 端口;CONTRACT-v2 新入口)
裸形(智能分派):put <文件>;get <键> [-o 名];open [spec](无参 = 管道,带 spec = 端口映射);
  close <地址或pid>(双域联合寻址,唯一命中即关);send <addr>(连对方管道发,stdin 直通);
  fwd <addr> <local>:<remote-port>(本地起听转发,0 = 空口);to <id> ...(文件 → shares / spec → ports / 裸 id → pipes);view [--shares|--pipes|--ports] [host](三面合一总览)
显式道(消歧逃生口,域内动词面不变):
  carry shares put|get|to;carry pipes open|close|send|to;carry ports open|close|fwd|to
域面(shares):put 上架(内容哈希键 share/<机>/<h>/<名>);get 按键取回;to 先上架再门控
域面(pipes):open 起收听(常驻至 close);close 杀进程收档广播;send 连管道 stdin 直通
域面(ports):open <spec>(8080,8443 端口表 / 5555:IP:5555 服务侧映射 / all / exit-node);fwd 本地起听转发;close 停映射
示例:
  carry put report.md
  carry open 8123
  carry close tcADDR
  carry to node-a report.md --json
  carry ports to node-a 8123
退役注记:shares/pipes/ports 独立入口并入本面(域内动词面不变)""",
        "ctxs": f"""ctxs@{_pkg_ver()} - 对话历史域:agent 请求全链检索(引擎 ClickHouse gw_logs;与 agents read 分工:read=实时屏,ctxs=历史档案)
动词:view [agent] [--limit N] [--since <ts>] [--before <ts>](最近请求头行:时间/模型/token/耗时/request_id;时间窗直裁分区);
  view <request_id> [--around <词>] [--window N](全链;--around 只出命中块±N 邻块;show 已并入 2026-11-16);
  search <词> [--term <词>]... [--limit N] [--days N](跨请求全文,多词 OR;每行带命中片段 snip;--days 扫描窗缺省 1 天) [--since <ts>] [--before <ts>](精确窗覆盖 --days)
窗口:head 365 天,gwlog 正文 180 天;词至少 2 字符(UTF-8 计)
退役注记:mcps 域整域退役(ADR-0001 MCP 边缘化,用户裁定 2026-11-13;连通用 MCP 客户端腿也不留)
示例:
  ctxs view
  ctxs show 0192a0f0-xxxx --around "挂死" --window 1
  ctxs search "panic"
  ctxs search --term 杀树 --term ensure_ascii""",
    }
    return m.get(cmd, "")
