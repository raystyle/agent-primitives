# prim 契约 v2(ADR-0003 放开重构;现役真源)

状态: accepted(2026-11-13,ADR-0003 accepted 同批落地;动词面按 docs/product/prim-verb-fate.md 命运表执行)
日期: 2026-11-13
关联: docs/decisions/ADR-0003-prim-refactor.md、docs/product/prim-verb-fate.md、CONTRACT-v1.md(v1 原文归档;ai-ccoe 原仓见 git 历史)

## 入口组织(方案甲:11 → 6)

| 入口 | 域 | 动词面 |
|---|---|---|
| `agents` | 消息 + 门控引擎 | view / workbenches / read / to / wait / inbox / mode / start / close / reload / trust / yolo / run / shell / dev / keys |
| `desks` | 工位 | view / start / close(split/tab/zoom/wt 退役 → mod GUI) |
| `machines` | 机册 + runtime | view / add / reconnect / run / close / runtime(子面骑 ark) |
| `streams` | 流 + 任务(任务即流) | rooms / room / dm / append / view / to;task: view / set / to |
| `carry` | 同构搬运三合一 | shares: put / get / to;pipes: open / close / send / to;ports: open / close / fwd;裸形 put/get/open/close/send/to/fwd/view 智能分派 |
| `ctxs` | 对话历史检索 | view / show / search(mcps 域退役,ADR-0001 MCP 边缘化) |

退役可见化(命运表 17 项):agents list/machines/sync/split/tab/zoom/wt、machines status/rename/remove/enable/disable/pane、desks 别名 desk、mcps 全域(view/tools/call/add/remove);各入口 help/CTA 指 new 道,调用回 usage 退 2。

## 通用纪律(v1 存活项)

- 信封四行形、四态 status(delivered/engine_fail/deferred/stalled)、退出码 0/1/2、`--llms` 手册面、`--json` 单行信封
- 目标文法:裸名 > `机:名` > `local:`;跨机格址 = `机/格`(hc machine/t 形);脚本面全限定
- 动词退役在 help/CTA 可见(废弃可见化);程序化消费走命令面不走 import

## 引擎面(5c 置换已落地)

- herdr CLI spawnSync → **hc 单点客户端**:prim 侧 = `src/prim/engines.py`(hc_run / hc_json / hc_exec_on 单点);TS 侧 = `cli/src/lib/hc.ts`(唯一 herdr 出口);真正常驻 JSON-RPC(`hc connect`)留演进位
- 跨机腿三处(ws_scan / yolo / runtimes)→ `hc exec --on`(hc 机册节点;机册外六台保持原 ssh 道,红线)
- s5/tailcat/hst/ark/CH 五引擎保留(命运表证据:hc 无对等原语)
- 保留动词的门控/拒投/审计/CTA 语义不动(判标库 = prim 策略层核心资产)

## 验收

- 金样按 v2 再生(旧 79 用例面归档 `tests/goldens/archive-v1/` 为迁移证据);退役动词留废弃可见化断言(pytest 73 用例)
- grep 守卫:prim/cli 源内无 `spawnSync('herdr'` / `runJson('herdr'` / `herdr_run(` 残留(pytest + vitest 双栈钉死)
- evo skills 按新六入口重写(project-evo 侧工程,挂账)
