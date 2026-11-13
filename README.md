# prim — agent 原语命令(uv 工具包)

ai-ccoe `plugins/prim` 的 herdr-ccoe 迁移形,批5c 已按 **ADR-0003 放开重构 + CONTRACT-v2** 重塑(2026-11-13)。包名保持 `prim`,契约 = 仓内 `CONTRACT-v2.md`(六入口真源;v1 契约归档 `CONTRACT-v1.md`)。

## 入口(CONTRACT-v2 方案甲,11 → 6)

- `agents` — 消息域:to/wait/inbox/read/mode/start/close/reload/trust/yolo/run/shell/dev/keys/workbenches(退役可见化:list/machines/sync/split/tab/zoom/wt)
- `desks` — 工位拓扑兜底:view/start/close(退役可见化:split/tab/zoom/wt;desk 单字别名删除)
- `machines` — 机册(hc machine.* 直通)+ runtime 子面(骑 ark)(退役可见化:status/rename/remove/enable/disable/pane)
- `streams` — 持久流(引擎 s5)+ tasks 子面(任务即流:`streams task view|set|to`)
- `carry` — 同构搬运三合一:shares/pipes/ports 域面不变,裸形智能分派(`carry put|get|open|close|send|to|fwd|view`)
- `ctxs` — ClickHouse gw_logs 检索(mcps 域整域退役,ADR-0001 MCP 边缘化)

退役动词调用即 usage 退 2,错误面带「已退役(ADR-0003)」+ 新道指路(kubectl 废弃可见化)。

## 引擎面(批5c 置换)

| 引擎 | 用于 | 说明 |
|---|---|---|
| `hc`(herdr-core) | agents/machines/addressing 全域终端面 | **单点客户端** `src/prim/engines.py`(hc_run / hc_json / hc_exec_on);TS 侧单点 = `cli/src/lib/hc.ts`;常驻 JSON-RPC 留演进位 |
| `s5` | shares / streams | PATH;win 无原生时走 WSL 代役(`PRIM_WSL_S5` env 指路,或运行时探测 WSL `$HOME/.local/bin/s5`) |
| `hst` | streams task 子面 | PATH |
| `ark` | machines runtime 子面(环境检查) | PATH 或 `ARK_BIN` env |
| `tailcat` | pipes / ports | PATH |
| ClickHouse gwlogs | ctxs | `CTX_URL/CTX_USER/CTX_PASSWORD`(或 `~/.ctx/reader.env`);ssh 兜底道须 `CTX_SSH_HOST`(零真实缺省) |

跨机腿三处(workbenches / yolo / runtimes)已换 `hc exec --on`(hc 机册节点);机册外节点保持原 ssh 道。缺二进制时 structured error(`engine_fail`,stderr 单行 JSON + CTA,退出码 1)。

## 使用

```bash
cd prim
uv sync
uv run pytest          # 73 用例(金样 v2 六枚 / 退役可见化断言 / deliver 矩阵 / hc 守卫 / 脱敏扫描)

uv run carry --llms    # 手册面(六入口同式)
uv run agents view     # `uv run <入口> <动词>` 即用(未装全局工具)
```

金样再生:`uv run python scripts/capture_goldens.py`(金样 = 重构回归参照,ADR-0003 决策 5;旧十一入口金样归档 `tests/goldens/archive-v1/`)。

## 迁移脱敏裁定(2026-11-13)

示例与源面零真实值:活机器名/真实 IP 一律角色代称(node-a / lab-node / RFC 5737 192.0.2.x),扫描钉死在 pytest(`test_no_real_values_in_source` / `test_llms_golden_sanitized`)。
