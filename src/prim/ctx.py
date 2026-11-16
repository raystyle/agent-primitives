"""ctx 域(第六原语)- agent 对话历史检索(引擎 ClickHouse,gw_logs 库)

命令族: view(最近请求头行)/ show(单请求全链)/ search(跨请求全文)
数据面: gwlogs 实例(https 8123 直连主道,双闸 = client 证书 + basic)。双道:
  1. 直连 https 8123(basic,ctx_reader SELECT-only;8123 mTLS 不收证书,密码道是正解)
  2. ssh 道兜底(容器内 client;无凭据或直连失败时自动落)
凭据: 环境变量 CTX_URL/CTX_USER/CTX_PASSWORD;缺省读 ~/.ctx/reader.env(600)
窗口: head 365 天(索引行),gwlog 180 天(正文块);TTL 由库面定,此处只读
"""
from __future__ import annotations
import json
import os
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request

CRED_PATH = os.path.expanduser("~/.ctx/reader.env")


def _die(code: str, msg: str, cta=None, rc: int = 1):
    from . import runtime_ctx
    if runtime_ctx.JSON_MODE:
        err = {"code": code, "message": msg, "cta": [cta] if cta else []}
        print(json.dumps(err, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"ctx: {msg}", file=sys.stderr)
        if cta:
            print(f"下一步:{cta}", file=sys.stderr)
    sys.exit(rc)


def _conf() -> dict:
    """配置面:环境变量优先,次读 ~/.ctx/reader.env(600;URL/USER/PASSWORD/CERT/KEY/CA/SSH_HOST)。"""
    keys = ("CTX_URL", "CTX_USER", "CTX_PASSWORD", "CTX_CERT", "CTX_KEY", "CTX_CA", "CTX_SSH_HOST")
    conf = {k: os.environ.get(k, "") for k in keys}
    if os.path.isfile(CRED_PATH):
        for line in open(CRED_PATH, encoding="utf-8"):
            line = line.strip()
            for k in keys:
                if line.startswith(k + "=") and not conf[k]:
                    conf[k] = line.split("=", 1)[1]
    return conf


def _creds() -> tuple[str, str, str] | None:
    c = _conf()
    return (c["CTX_URL"], c["CTX_USER"], c["CTX_PASSWORD"]) if (c["CTX_URL"] and c["CTX_USER"] and c["CTX_PASSWORD"]) else None


def _http_ch(sql: str, timeout: int = 15) -> str:
    """直连 https 8123。双闸:client 证书(TLS 层,dctl CA;服务端要求)+ basic(用户层)。
    服务端证书名与地址不合,关主机名校验;有 CA 则校验链,无则裸 TLS(边界 = 网段 ACL)。"""
    conf = _conf()
    q = urllib.parse.quote(sql)
    req = urllib.request.Request(f"{conf['CTX_URL']}/?query={q}")
    import base64
    tok = base64.b64encode(f"{conf['CTX_USER']}:{conf['CTX_PASSWORD']}".encode()).decode()
    req.add_header("Authorization", f"Basic {tok}")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    if conf["CTX_CA"]:
        ctx.load_verify_locations(os.path.expanduser(conf["CTX_CA"]))
    else:
        ctx.verify_mode = ssl.CERT_NONE
    if conf["CTX_CERT"] and conf["CTX_KEY"]:
        ctx.load_cert_chain(os.path.expanduser(conf["CTX_CERT"]), os.path.expanduser(conf["CTX_KEY"]))
    r = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return r.read().decode("utf-8", errors="replace")


def _ssh_ch(sql: str, timeout: int = 15) -> str:
    """ssh 道兜底:容器内 client(免本机证书面)。道宿主 = CTX_SSH_HOST
    (脱敏令 2026-11-13,herdr-ccoe 批5a:零真实主机名缺省;未配即 structured error)。"""
    host = _conf().get("CTX_SSH_HOST") or ""
    if not host:
        _die("engine_fail", "ssh 道宿主未配(CTX_SSH_HOST env 或 ~/.ctx/reader.env SSH_HOST 行)",
             "ctx 配置面:export CTX_SSH_HOST=<宿主机>", rc=1)
    cmd = ("docker exec dctl-ch-gwlogs-26.8 clickhouse-client --secure --port 9440 "
           "--host 127.0.0.1 --config-file /etc/clickhouse-server/dctl/cli.xml "
           f"--query {json.dumps(sql, ensure_ascii=False)}")  # ensure_ascii=False:CJK 裸传
    try:
        r = subprocess.run(["ssh", host, cmd], capture_output=True, text=True,
                           timeout=timeout + 5, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        _die("engine_fail", f"查询超时(ssh 道到 {host})")
    if r.returncode != 0:
        _die("engine_fail", f"CH 查询失败:{(r.stderr or '').strip()[:150]}")
    return r.stdout or ""


def _ch(sql: str, timeout: int = 15) -> str:
    """主道直连,败落 ssh;两道皆败才报错(错误原文带出直连失败因)。"""
    if _creds():
        try:
            return _http_ch(sql, timeout)
        except Exception:
            try:
                return _ssh_ch(sql, timeout)
            except SystemExit:
                raise
            # ssh 道 die 已带自身错误;此处不达
    return _ssh_ch(sql, timeout)


def _esc(s: str) -> str:
    """单引号转义(注入护栏;参数只进字面量位)。"""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def _pval(pos: list[str], flag: str, default: str = "") -> str:
    """动词旗标取值(ctxs 本地形,批3R 抽出;行为同原内嵌 _val)。"""
    if flag in pos and pos.index(flag) + 1 < len(pos):
        return pos[pos.index(flag) + 1]
    return default


def _retired_show(pos, g):
    _die("usage", "动词「show」已退役(ADR-0003 重构+动词标准统一 2026-11-16);详情即 view <request_id> 全链", "ctxs view <id>", rc=2)


def _view(pos: list[str], g: dict):
        # 详情并法(动词标准统一 2026-11-16):首参带 --around/--window 或形如 request_id(含-) → 原 show 语义
        if pos and not pos[0].startswith("-") and ("--around" in pos or "--window" in pos or "-" in pos[0]):
            return _show_detail(pos)
        agent = pos[0] if pos and not pos[0].startswith("-") else ""
        limit = _pval(pos, "--limit", "20")
        conds = [f"agent = '{_esc(agent)}'"] if agent else []
        # 时间窗旗标(批172上报缺口:view 万行翻页翻不出目标日;--since/--before 直裁分区)
        since, before = _pval(pos, "--since", ""), _pval(pos, "--before", "")
        if since:
            conds.append(f"ts >= '{_esc(since)}'")
        if before:
            conds.append(f"ts < '{_esc(before)}'")
        where = ("WHERE " + " AND ".join(conds)) if conds else ""
        sql = (f"SELECT toString(ts) AS t, agent, alias, status, duration_ms, "
               f"input_tokens+cache_read+cache_creation AS in_tok, "
               f"output_tokens+thinking_tokens AS out_tok, request_id "
               f"FROM gw_logs.head {where} ORDER BY ts DESC LIMIT {limit} FORMAT TSVWithNames")
        print(_ch(sql))

def _show_detail(pos: list[str], g: dict):
        if not pos:
            _die("usage", "show <request_id> [--around <关键词>] [--window N]", "ctx view 找 request_id", rc=2)
        rid = _esc(pos[0])
        around = _pval(pos, "--around", "")
        window = int(_pval("--window", "1") or 1)
        sql = (f"SELECT toString(ts), agent, alias, status, duration_ms, "
               f"input_tokens, output_tokens, thinking_tokens, session_id, error_summary "
               f"FROM gw_logs.head WHERE request_id = '{rid}' FORMAT TSVWithNames")
        out = _ch(sql)
        sql2 = (f"SELECT seq, kind, substring(payload, 1, 4000) FROM gw_logs.gwlog "
                f"WHERE request_id = '{rid}' ORDER BY seq FORMAT TSV")
        body = _ch(sql2)
        # 管道时序(批150 实证):正文块先入,head 行随 request_end 后入;在途请求只有块
        if len(out.strip().splitlines()) <= 1 and not body.strip():
            _die("not_found", "request_id 无记录(可能过 365 天窗口)", "ctx view 复核 id")
        if len(out.strip().splitlines()) <= 1:
            print("-- 头行:未落(request 在途或 request_end 批未刷;正文块先行如下)")
        else:
            print(out)
        if not body.strip():
            print("-- 正文块:空(可能过 180 天窗口)")
        elif around:
            # 命中块聚焦(批172续报根修:原实现只校验未聚焦,show 恒全量转储 80KB 级)
            # 命中在 SQL 侧全文做(payload 可超 4000 截断面);命中块 = 命中点居中 3000 字窗,邻块 ±window 全块
            if len(around.encode("utf-8")) < 2:
                _die("usage", "--around 关键词至少 2 个字符", rc=2)
            a = _esc(around)
            seqs = [int(x) for x in _ch(f"SELECT seq FROM gw_logs.gwlog WHERE request_id = '{rid}' "
                                          f"AND positionUTF8(payload, '{a}') > 0 ORDER BY seq FORMAT TSV").split()]
            if not seqs:
                print(f"-- 正文块:无「{around}」命中(全量兜底):")
                print(body)
            else:
                rows = {}
                for line in body.splitlines()[1:]:
                    parts = line.split("	", 2)
                    if len(parts) == 3:
                        try: rows[int(parts[0])] = (parts[1], parts[2])
                        except ValueError: pass
                picked = set()
                for sq in seqs:
                    for d in range(-window, window + 1):
                        if sq + d in rows: picked.add(sq + d)
                head = f"seq {'/'.join(map(str, seqs[:6]))}" + ("…" if len(seqs) > 6 else "")
                print(f"-- 正文块:「{around}」命中 {len(seqs)} 块({head}),±{window} 邻窗共 {len(picked)} 块")
                for sq in sorted(picked):
                    kind, pay = rows[sq]
                    if sq in seqs:
                        seg = _ch(
                            "SELECT substring(payload, greatest(1, positionUTF8(payload, '" + a + "') - 1500), 3000) "
                            "FROM gw_logs.gwlog WHERE request_id = '" + rid + "' AND seq = " + str(sq) + " FORMAT TSV").rstrip("\n")
                        print(f"== seq {sq} {kind} [命中点居中 3000 字]")
                        print(seg)
                    else:
                        print(f"== seq {sq} {kind} [邻块]")
                        print(pay)

def _search(pos: list[str], g: dict):
        # 词集 = 位置参数 + --term 可叠(OR 语义,先例 ctx search --term 形)
        terms = []
        if pos and not pos[0].startswith("-"):
            terms.append(pos[0])
        i = 0
        while i < len(pos):
            if pos[i] == "--term" and i + 1 < len(pos):
                terms.append(pos[i + 1])
            i += 1
        if not terms:
            _die("usage", "search <关键词> [--term <词>]...", rc=2)
        # 检索面(全文索引裁定 2026-10-14):multiSearchAnyUTF8 吃 idx_text
        # (text 索引 ngrams(2),ASCII/CJK/短语同道);needle < 2 字符无索引意义,拒
        for t in terms:
            if len(t.encode("utf-8")) < 2:
                _die("usage", "关键词至少 2 个字符(UTF-8 计)", "短词换长词或 ctx view 浏览", rc=2)
        limit = _pval(pos, "--limit", "10")
        esc = [_esc(t) for t in terms]
        arr = "[" + ",".join(f"'{t}'" for t in esc) + "]"
        cond = f"multiSearchAnyUTF8(payload, {arr})"
        days = _pval(pos, "--days", "1")
        # 片段:最早命中块内,首个出现词的位置开 120 字窗口(token 高效,先例 snippet 形)
        # 时间窗默认 7 天(2026-10-15 慢查根修:无窗 = 180 天全扫,常用词聚合分钟级;
        # 分区裁剪后日增量只扫当日分区,--days 可放宽)
        # 两段式 v3(Python 侧两步,2026-10-15:CH JOIN 聚合语法坑多,拆两次最简)
        # 第一段:轻聚合(request_id/hits/t),不碰 payload 列,亚秒
        # 第二段:top-N 每条定点取 snippet
        s_since, s_before = _pval(pos, "--since", ""), _pval(pos, "--before", "")
        tcond = f"ts > now() - INTERVAL {int(days)} DAY"
        if s_since:
            tcond = f"ts >= '{_esc(s_since)}'"
        if s_before:
            tcond += f" AND ts < '{_esc(s_before)}'"
        sub = (f"SELECT request_id, count() AS hits, min(ts) AS t "
               f"FROM gw_logs.gwlog WHERE {cond} AND {tcond} "
               f"GROUP BY request_id ORDER BY t DESC LIMIT {limit}")
        tops = _ch(sub + " FORMAT TSVWithNames")
        if not tops.strip() or len(tops.strip().splitlines()) <= 1:
            print("(无命中)")
            return
        rids = [l.split("	")[0] for l in tops.strip().splitlines()[1:] if "	" in l]
        rid_arr = "[" + ",".join(f"'{r}'" for r in rids) + "]"
        # 第二段(grok 规格修):聚合只算 min(seq)(UInt32 态),再按主键点查一行 payload;
        # 不再把 payload 放进 argMinIf(大 String 聚合态 = 5s 根因)
        sql2a = (f"SELECT request_id, min(seq) AS seq FROM gw_logs.gwlog "
                 f"PREWHERE request_id IN {rid_arr} "
                 f"WHERE {cond} GROUP BY request_id FORMAT TSV")
        minseqs = _ch(sql2a)
        pairs = []
        if minseqs.strip():
            for l in minseqs.strip().splitlines():
                ps = l.split("\t")
                if len(ps) == 2:
                    pairs.append(f"('{ps[0]}',{ps[1]})")
        pair_arr = "(" + ",".join(pairs) + ")"
        pos_terms = "coalesce(" + ",".join(
            f"nullif(positionUTF8(payload, '{t}'), 0)" for t in esc) + ", 0)"
        sql2 = (f"SELECT request_id, substringUTF8(payload, "
                f"greatest({pos_terms} - 40, 1), 120) AS snip "
                f"FROM gw_logs.gwlog "
                f"WHERE (request_id, seq) IN {pair_arr} FORMAT TSV")
        snips = _ch(sql2)
        smap = {}
        if snips.strip():
            for l in snips.strip().splitlines():
                parts = l.split("\t", 1)
                if len(parts) == 2:
                    smap[parts[0]] = parts[1]
        # 合并输出:top 行 + snippet
        lines_out = ["request_id\thits\tt\tsnip"]
        for l in tops.strip().splitlines()[1:]:
            cols = l.split("\t")
            if len(cols) >= 3:
                lines_out.append("\t".join([cols[0], cols[1], cols[2], smap.get(cols[0], "")]))
        out = "\n".join(lines_out)
        print(out if len(out.strip().splitlines()) > 1 else "(无命中;块表 180 天窗口)")

VERBS: dict = {"view": _view, "show": _retired_show, "search": _search}


def ctxs_main():
    from . import flags
    from .manual import manual
    g, verb, pos = flags.bootstrap("ctxs", manual("ctxs"))
    verb = verb or "view"
    handler = VERBS.get(verb)
    if handler is None:
        _die("usage", f"未知动词「{verb}」;--llms 看手册", rc=2)
    return handler(pos, g)
