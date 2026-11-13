# prim — agent 原语命令(uv 工具包)

ai-ccoe `plugins/prim` 的 herdr-ccoe 迁移形(PLAN-ai-ccoe-migration **批5a 零耦合域**,2026-11-13)。包名保持 `prim`,契约沿用 ADR-0008 冻结形(CONTRACT.md 随批5b 迁入)。

## 批5a 范围

- **六域**:`shares`(S3 文件中转,引擎 s5)/ `streams`(持久流,引擎 s5)/ `pipes`(tailcat 管道)/ `ports`(tailcat 端口映射)/ `ctxs`(ClickHouse gw_logs 检索)/ `mcps`(通用 MCP 客户端,引擎 mcp2cli)
- **共享叶子**:`runtime_ctx`(态与信封)/ `engines`(进程树收割 + wsl 代役)/ `identity` / `addressing` / `gating` / `flags` / `deliver` / `manual` / `msg` / `tailcat_base` / `agents_view`(pipes/ports view 臂复用,5b 归位 agents 域)
- **批5b 未迁**:agents / desks / tasks / machines 四域 + gating 判标库扩展 + CONTRACT.md(十一入口届时合拢)

## 运行前提(引擎二进制)

| 引擎 | 用于 | 本机缺省 |
|---|---|---|
| `s5` | shares / streams | PATH;win 无原生时走 WSL 代役(`PRIM_WSL_S5` env 指路,或运行时探测 WSL `$HOME/.local/bin/s5`) |
| `herdr` | agents 表 / addressing(六域的 view 与 to 都要) | PATH |
| `tailcat` | pipes / ports | PATH |
| `mcp2cli` | mcps | **`MCPS_BIN` env 或 PATH,二选一**(零硬编码路径回退,缺位即 structured error) |
| ClickHouse gwlogs | ctxs | `CTX_URL/CTX_USER/CTX_PASSWORD`(或 `~/.ctx/reader.env`);ssh 兜底道须 `CTX_SSH_HOST`(零真实缺省) |

缺二进制时命令面出 structured error(`engine_fail`,stderr 单行 JSON + CTA,退出码 1),不挂死不裸栈。

## 使用

```bash
cd prim
uv sync
uv run pytest          # 60 用例(金样冻结 / deliver 矩阵 / 漂移守卫 / 脱敏扫描)
uv run shares --llms   # 手册面(六域同式)
uv run prim 尚未安装为全局工具;仓内 `uv run <域> <动词>` 即用
```

金样再生:`uv run python scripts/capture_goldens.py`(改手册面须先过 ADR-0008 放行点裁定)。

## 迁移脱敏裁定(2026-11-13)

- `mcps.py` win 仓内 mcp2cli 路径回退退役 → `MCPS_BIN` env / PATH 必填
- `engines.py` wsl 代役 s5 路径 → 运行时探测 WSL `$HOME`(env `PRIM_WSL_S5` / `PRIM_WSL_HOME` 可覆盖)
- 金样与手册示例活机器名/真实 IP → 角色代称(node-a / lab-node / RFC 5737 文档段 192.0.2.x)
- `ctx.py` ssh 兜底道宿主 → `CTX_SSH_HOST` 必填(零真实缺省)

测试钉死:`test_no_real_values_in_source`(源面敏感模式扫描)+ `test_llms_golden_sanitized`(金样活名扫描)。
