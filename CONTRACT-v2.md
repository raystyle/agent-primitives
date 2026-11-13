# prim 契约 v2(重构中,ADR-0003)

状态: draft(依 `docs/product/prim-verb-fate.md` 命运表立;v1 契约见 git 历史与 ai-ccoe 原仓,消费方 evo skills 随 v2 重写)
日期: 2026-11-13

## 入口组织(方案甲:11 → 6)

| 入口 | 域 | 动词面 |
|---|---|---|
| `agents` | 消息 + 门控引擎 | view / read / to / wait / inbox / mode / start / close / reload / trust / yolo / run / shell / dev / keys |
| `desks` | 工位 | view / start / close(split/tab/zoom/wt 退役 → mod GUI) |
| `machines` | 机册 + runtime | view / add / reconnect / run / close / runtime(子面骑 ark) |
| `streams` | 流 + 任务(任务即流) | rooms / room / dm / append / view / from / resume / follow / file;tasks: view / set / to |
| `carry` | 同构搬运三合一 | shares: put / get / to;pipes: open / close / send / to;ports: open / close / fwd |
| `ctxs` | 对话历史检索 | view / probe(mcps 域退役,ADR-0001 MCP 边缘化) |

## 通用纪律(v1 存活项)

- 信封四行形、四态 status(delivered/engine_fail/deferred/stalled)、退出码 0/1/2、`--llms` 手册面、`--json` 单行信封
- 目标文法:裸名 > `机:名` > `local:`;脚本面全限定
- 动词退役在 help/CTA 可见(废弃可见化);程序化消费走命令面不走 import

## 引擎面(5c 置换)

- herdr CLI spawnSync → **hc 单点客户端**(TS 侧 `cli/src/lib/hc.ts` 收编;prim 经 seam 调用)
- 跨机 ssh 手搓三处(ws_scan/yolo/runtimes)→ `hc exec --on`
- s5/tailcat/hst/ark/CH 五引擎保留(命运表证据:hc 无对等原语)
- 保留动词的门控/拒投/审计/CTA 语义不动

## 验收

- 金样按 v2 再生(旧 79 用例归档为迁移证据);退役动词留废弃可见化断言
- grep 守卫:prim/cli 源内无 `spawnSync('herdr'` / `runJson('herdr'` 残留
- evo skills 按新六入口重写(project-evo 侧工程,挂账)
