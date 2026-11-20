# agent-primitives — agent 原语命令(uv 工具包)

原 `prim`(herdr-ccoe 批5c 迁移形,ai-ccoe `plugins/prim` 后裔),2026-11-20 抽为独立仓 `raystyle/agent-primitives` 并更名:包 `prim`→`agent-primitives`、命令 `shares`→`files`。契约 = 仓内 `CONTRACT-v2.md`(五入口真源;v1 契约归档 `CONTRACT-v1.md`)。

## 入口(五入口,2026-11-18 收敛 + 2026-11-20 shares→files)

- `files` — 文件域(原 shares):ls/put/get/send,S3 中转(引擎 s5;内容哈希键,键形 `share/<机>/<hash>/<名>` 不变)
- `streams` — 持久流(引擎 s5):ls/room/dm/append/send(tasks 子面 2026-11-16 退役)
- `ctxs` — ClickHouse gw_logs 检索:ls/search
- `ports` — 端口映射(引擎 tailcat serve):ls/start/close/fwd/send
- `pipes` — 实时字节管道(引擎 tailcat):ls/start/close/send

agents/desks/machines/carry/mcps 域退役(归 hc/herdr-app 原生面;退役可见化:调用即 usage 退 2 带「已退役」+ 新道指路)。

## 引擎面

| 引擎 | 用于 | 说明 |
|---|---|---|
| `hc`(herdr-core) | 终端面全域 | **单点客户端** `src/agent_primitives/engines.py`(hc_run / hc_json / hc_exec_on);常驻 JSON-RPC(`hc connect`)留演进位 |
| `s5` | files / streams | PATH;win 无原生时走 WSL 代役(`PRIM_WSL_S5` env 指路,或运行时探测 WSL `$HOME/.local/bin/s5`) |
| `hst` | 历史任务面(退役道兜底) | PATH |
| `ark` | runtime 环境检查(退役道兜底) | PATH 或 `ARK_BIN` env |
| `tailcat` | pipes / ports | PATH |
| ClickHouse gwlogs | ctxs | `CTX_URL/CTX_USER/CTX_PASSWORD`(或 `~/.ctx/reader.env`);ssh 兜底道须 `CTX_SSH_HOST`(零真实缺省) |

跨机腿已换 `hc exec --on`(hc 机册节点);机册外节点保持原 ssh 道。缺二进制时 structured error(`engine_fail`,stderr 单行 JSON + CTA,退出码 1)。

## 使用

```sh
uv tool install --override-virgin-scripts git+https://github.com/raystyle/agent-primitives.git
files put report.md            # 推送上架,回 share key
streams room fleet 回执-完成    # 流域说话
ctxs search "panic"            # 跨请求检索
```

升级:`uv tool upgrade agent-primitives`(版本号不变不刷,发新版须 bump `pyproject.toml` 的 `version`)。

## 开发

```sh
uv sync --group dev
uv run pytest -q               # 74 用例:金样/parse 黄金/信封/deliver 矩阵/守卫
```

金样再生(扩面须裁定后改):跑 `tests/test_agent_primitives.py` 的 `run_llms` 形(见 `test_llms_golden`),输出写 `tests/goldens/<入口>.llms`。

## 结构沿革

- 2026-11-20 抽仓 `raystyle/agent-primitives`(herdr-ccoe subtree split,8 commits 沿革保留)+ 包更名 + `shares`→`files`
- 2026-11-18 五入口收敛(agents/desks/machines 退役;动词对齐 hc)
- 2026-11-13 批5c:ADR-0003 放开重构 + CONTRACT-v2(11→6 入口;herdr spawn 清零改 hc 单点;金样 v2 再生)
- 更早:ai-ccoe 批3R 模块化拆分;原 prim 十一入口时代见 `CONTRACT-v1.md`
