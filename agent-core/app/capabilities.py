"""
能力工具层（Capabilities）
==========================
智能体团队执行每一步时真正调用的「工具」。全部为确定性实现：

- 不依赖外网：web_search / web_fetch 使用内置语料 + 目标哈希生成可复现结果；
- 不依赖大模型：报告由模板 + 已检索到的证据拼装，同输入同输出；
- 可选 live：report_writer 在 mode=live 且配置 DeepSeek Key 时改为大模型润色，
  失败自动回退模板，保证服务不会因为外部依赖不可用而中断。

返回值统一为 dict：{"summary": 给步骤看的结论, ...结构化字段}。
结构化字段会写入执行上下文，供后续步骤与交付物生成使用。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from . import config, llm, rag
from .skills import ACTION_LABEL, CAPABILITIES, SENSITIVE_KEYWORDS

# ------------------------------------------------------------------ 内置语料
# 每个主题 3 条来源，包含可被「数据分析」步骤消费的指标。
_TOPICS: list[dict[str, Any]] = [
    {
        "key": "宠物智能硬件", "terms": ["宠物", "猫", "狗", "饮水机", "喂食器", "宠物用品"],
        "sources": [
            {"title": "2025 中国宠物智能用品行业白皮书", "publisher": "艾瑞咨询",
             "url": "https://example.com/report/pet-tech-2025", "year": 2025,
             "snippet": "2025 年国内宠物智能用品市场规模约 186 亿元，同比增长 27.4%，"
                        "智能饮水与喂食设备占比 41%，自动清洁与可视化是核心购买动因。",
             "metric": "市场规模", "value": "186 亿元", "growth": "27.4%"},
            {"title": "宠物智能硬件出海观察", "publisher": "36氪研究院",
             "url": "https://example.com/news/pet-tech-global", "year": 2025,
             "snippet": "海外市场客单价约为国内的 2.3 倍，欧美用户最关注静音与水质监测，"
                        "亚马逊渠道占出海销售额的 58%。",
             "metric": "海外客单价", "value": "2.3 倍", "growth": "12.0%"},
            {"title": "2026 宠物消费趋势报告", "publisher": "天猫宠物",
             "url": "https://example.com/report/pet-consumer-2026", "year": 2026,
             "snippet": "90 后用户占比 63%，复购主因为「可视化 + 自动清洁」，"
                        "内容种草对首单转化的贡献达到 34%。",
             "metric": "90 后用户占比", "value": "63%", "growth": "8.5%"},
        ],
    },
    {
        "key": "AI 智能体平台", "terms": ["ai", "智能体", "大模型", "agent", "llm", "人工智能"],
        "sources": [
            {"title": "2025 中国企业级 AI 智能体应用报告", "publisher": "艾瑞咨询",
             "url": "https://example.com/report/ai-agent-2025", "year": 2025,
             "snippet": "2025 年中国企业级智能体市场规模 128 亿元，同比增长 45.2%，"
                        "平台化交付占 38%，金融与零售是落地最快的两个行业。",
             "metric": "市场规模", "value": "128 亿元", "growth": "45.2%"},
            {"title": "智能体平台能力象限", "publisher": "InfoQ",
             "url": "https://example.com/news/agent-platform-quadrant", "year": 2025,
             "snippet": "企业选型最关注任务编排、权限审计与可观测性，"
                        "具备多角色协作能力的平台中标率高出 21%。",
             "metric": "多角色平台中标率提升", "value": "21%", "growth": "9.8%"},
            {"title": "AI 应用交付模式调研", "publisher": "甲子光年",
             "url": "https://example.com/report/ai-delivery-2026", "year": 2026,
             "snippet": "按效果付费与订阅制各占 44% / 39%，平均年客单价 12 万元，"
                        "交付周期从 8 周压缩到 3 周成为主要竞争点。",
             "metric": "平均年客单价", "value": "12 万元", "growth": "15.6%"},
        ],
    },
    {
        "key": "现制咖啡", "terms": ["咖啡", "茶饮", "饮品", "门店"],
        "sources": [
            {"title": "2025 中国现制咖啡行业报告", "publisher": "欧睿国际",
             "url": "https://example.com/report/coffee-2025", "year": 2025,
             "snippet": "现制咖啡市场规模 3,800 亿元，同比增长 18.3%，"
                        "县域门店数量增速 31%，下沉市场成为主要增量。",
             "metric": "市场规模", "value": "3,800 亿元", "growth": "18.3%"},
            {"title": "咖啡价格战后的单店模型", "publisher": "窄门餐眼",
             "url": "https://example.com/news/coffee-store-model", "year": 2025,
             "snippet": "头部品牌平均客单价 15.8 元，单店日均出杯 286 杯，"
                        "9.9 元价格带贡献 47% 的订单量。",
             "metric": "平均客单价", "value": "15.8 元", "growth": "6.2%"},
            {"title": "2026 咖啡消费趋势", "publisher": "美团研究院",
             "url": "https://example.com/report/coffee-trend-2026", "year": 2026,
             "snippet": "即取即走订单占比 61%，联名款上新带来的拉新占比 23%，"
                        "健康化（低糖/燕麦奶）搜索量同比提升 58%。",
             "metric": "即取即走占比", "value": "61%", "growth": "11.4%"},
        ],
    },
    {
        "key": "新能源汽车", "terms": ["新能源", "汽车", "电动车", "充电", "车企"],
        "sources": [
            {"title": "2025 新能源汽车产销数据", "publisher": "中汽协",
             "url": "https://example.com/data/nev-2025", "year": 2025,
             "snippet": "新能源汽车销量 1,286 万辆，同比增长 32.1%，渗透率 45.8%，"
                        "插混与增程贡献主要增量。",
             "metric": "年销量", "value": "1,286 万辆", "growth": "32.1%"},
            {"title": "充电基础设施发展年报", "publisher": "中国充电联盟",
             "url": "https://example.com/report/charging-2025", "year": 2025,
             "snippet": "公共充电桩保有量 1,200 万台，车桩比 2.4:1，"
                        "高速服务区快充覆盖率 96%。",
             "metric": "公共充电桩", "value": "1,200 万台", "growth": "24.7%"},
            {"title": "2026 智能驾驶渗透观察", "publisher": "高工智能汽车",
             "url": "https://example.com/news/ad-2026", "year": 2026,
             "snippet": "城市 NOA 渗透率 18.6%，20 万元以上车型搭载率 54%，"
                        "用户对智驾的付费意愿提升至 41%。",
             "metric": "城市 NOA 渗透率", "value": "18.6%", "growth": "13.2%"},
        ],
    },
    {
        "key": "跨境电商", "terms": ["跨境", "出海", "独立站", "亚马逊", "外贸"],
        "sources": [
            {"title": "2025 跨境电商出口报告", "publisher": "海关总署",
             "url": "https://example.com/report/cross-border-2025", "year": 2025,
             "snippet": "跨境电商出口 2.4 万亿元，同比增长 19.4%，"
                        "独立站占比 26%，小包直邮向海外仓模式迁移。",
             "metric": "出口规模", "value": "2.4 万亿元", "growth": "19.4%"},
            {"title": "跨境履约时效调研", "publisher": "亿邦动力",
             "url": "https://example.com/news/logistics-2025", "year": 2025,
             "snippet": "海外仓平均履约时效 5.2 天，比直邮快 6.8 天，"
                        "退货率下降 4.1 个百分点。",
             "metric": "海外仓履约时效", "value": "5.2 天", "growth": "7.6%"},
            {"title": "2026 出海品牌趋势", "publisher": "Shopify 中国",
             "url": "https://example.com/report/global-brand-2026", "year": 2026,
             "snippet": "内容电商贡献 38% 的新客，本地化客服使复购率提升 19%，"
                        "合规（税务/隐私）成为最大门槛。",
             "metric": "内容电商新客占比", "value": "38%", "growth": "16.3%"},
        ],
    },
    {
        "key": "软件测试与质量", "terms": ["测试", "质量", "自动化", "接口测试", "性能测试", "qa", "pytest"],
        "sources": [
            {"title": "2025 中国软件测试服务市场报告", "publisher": "赛迪顾问",
             "url": "https://example.com/report/testing-2025", "year": 2025,
             "snippet": "软件测试服务市场规模 620 亿元，同比增长 21.5%，"
                        "自动化测试渗透率 54%，AI 辅助测试采用率 28%。",
             "metric": "市场规模", "value": "620 亿元", "growth": "21.5%"},
            {"title": "测试团队效能基准", "publisher": "TesterHome",
             "url": "https://example.com/news/qa-benchmark", "year": 2025,
             "snippet": "接口自动化覆盖率达到 70% 的团队，回归耗时平均下降 46%，"
                        "线上缺陷逃逸率下降 32%。",
             "metric": "回归耗时下降", "value": "46%", "growth": "9.1%"},
            {"title": "AI 测试落地实践", "publisher": "InfoQ",
             "url": "https://example.com/report/ai-testing-2026", "year": 2026,
             "snippet": "大模型主要用于用例生成、断言补全与失败归因，"
                        "人工评审后采纳率约 61%，需配合确定性评测集防止幻觉。",
             "metric": "用例采纳率", "value": "61%", "growth": "14.8%"},
        ],
    },
]

_GENERIC_TOPIC = {
    "key": "通用行业", "terms": [],
    "sources": [
        {"title": "行业公开数据汇编", "publisher": "国家统计局",
         "url": "https://example.com/data/industry",
         "snippet": "行业整体保持中速增长，头部集中度提升，数字化与降本增效是主要驱动力。",
         "metric": "行业增速", "value": "12.6%", "growth": "12.6%"},
        {"title": "细分赛道竞争格局观察", "publisher": "第一财经",
         "url": "https://example.com/news/landscape",
         "snippet": "前五名厂商合计份额 48%，中小玩家通过差异化服务获取增量。",
         "metric": "CR5 集中度", "value": "48%", "growth": "5.4%"},
        {"title": "用户需求调研摘要", "publisher": "易观分析",
         "url": "https://example.com/report/user-demand",
         "snippet": "用户最关注交付确定性、响应速度与数据安全，价格敏感度同比下降。",
         "metric": "交付确定性关注度", "value": "72%", "growth": "8.8%"},
    ],
}


def _hash_int(text: str, mod: int) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16) % mod


def detect_topic(goal: str) -> dict[str, Any]:
    low = (goal or "").lower()
    for topic in _TOPICS:
        if any(t in low for t in topic["terms"]):
            return topic
    return _GENERIC_TOPIC


def topic_sources(goal: str) -> list[dict[str, Any]]:
    """按目标返回 3 条可复现来源；通用目标会用哈希微调数值，避免每次都一样。"""
    topic = detect_topic(goal)
    sources = [dict(s) for s in topic["sources"]]
    if topic is _GENERIC_TOPIC:
        seed = _hash_int(goal, 97)
        sources[0]["snippet"] = (f"围绕「{goal}」的公开资料显示，行业仍处于增长区间，"
                                 f"近一年增速约 {8 + seed % 18}%，数字化投入是主要变量。")
        sources[0]["value"] = f"{20 + seed % 80} 亿元"
        sources[0]["growth"] = f"{8 + seed % 18}%"
        sources[1]["snippet"] = (f"竞争格局方面，头部厂商份额约 {35 + seed % 25}%，"
                                 f"细分场景仍有空白，服务差异化是关键。")
    for i, s in enumerate(sources):
        s["year"] = s.get("year") or 2025
        s["credibility"] = "高" if i == 0 else ("中" if i == 1 else "参考")
    return sources


def _md_table(columns: list[str], rows: list[list[Any]]) -> str:
    head = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join([head, sep] + body)


def to_csv(columns: list[str], rows: list[list[Any]]) -> str:
    def cell(v: Any) -> str:
        s = str(v)
        return f'"{s}"' if ("," in s or '"' in s or "\n" in s) else s
    lines = [",".join(cell(c) for c in columns)]
    lines += [",".join(cell(c) for c in row) for row in rows]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ 各动作实现
def web_search(ctx: dict) -> dict:
    sources = topic_sources(ctx["goal"])
    existing = {s["url"] for s in ctx["sources"]}
    added = [s for s in sources if s["url"] not in existing]
    ctx["sources"].extend(added)
    lines = [f"- [{i+1}] {s['title']}（{s['publisher']}，{s['year']}）：{s['snippet']}"
             for i, s in enumerate(added)]
    return {"summary": f"检索到 {len(added)} 条相关资料：\n" + "\n".join(lines),
            "sources": added}


def web_fetch(ctx: dict) -> dict:
    picked = ctx["sources"][:2]
    if not picked:
        return {"summary": "没有可抓取的来源，已跳过正文抓取。"}
    fetched = []
    for s in picked:
        body = (f"{s['snippet']} 该来源同时披露：{s['metric']}为 {s['value']}，"
                f"相关增速 {s['growth']}，统计口径为 {s['year']} 年公开数据。")
        fetched.append({"url": s["url"], "title": s["title"], "body": body})
    ctx["fetched"] = fetched
    lines = [f"- {f['title']}：{f['body']}" for f in fetched]
    return {"summary": f"抓取 {len(fetched)} 篇来源正文：\n" + "\n".join(lines),
            "fetched": fetched}


def knowledge(ctx: dict) -> dict:
    hits = rag.search(ctx["goal"], 3)
    ctx["knowledge"] = hits
    if not hits:
        return {"summary": "知识库未命中相关文档，已记录为待补充知识。"}
    lines = [f"- {h['title']}（相似度 {h['score']}）：{h['text'][:120]}"
             for h in hits]
    return {"summary": f"知识库召回 {len(hits)} 个片段：\n" + "\n".join(lines),
            "hits": hits}


def data_analyze(ctx: dict) -> dict:
    sources = ctx["sources"]
    if sources:
        columns = ["来源", "关键指标", "数值", "同比/相关增速", "可信度"]
        rows = [[s["publisher"], s["metric"], s["value"], s["growth"], s["credibility"]]
                for s in sources]
    else:
        # 没有检索结果时（如纯数据整理），按目标哈希生成可复现样本
        h = _hash_int(ctx["goal"], 1000)
        columns = ["分组", "数值", "环比%", "说明"]
        rows = [[f"样本{i+1}", 80 + (h >> i) % 120, round(((h >> i) % 90) / 10 - 2, 1),
                 "演示数据（未接入真实数据源）"] for i in range(5)]
    ctx["table"] = {"columns": columns, "rows": rows}
    growths = []
    for r in rows:
        g = str(r[3] if len(r) > 3 else "").replace("%", "").replace("倍", "")
        try:
            growths.append(float(g))
        except Exception:
            continue
    avg_growth = round(sum(growths) / len(growths), 1) if growths else 0.0
    ctx["stats"] = {"avgGrowth": avg_growth, "rows": len(rows)}
    return {"summary": f"已生成 {len(rows)} 行结构化数据，平均增速 {avg_growth}%。",
            "table": ctx["table"], "avgGrowth": avg_growth}


_RECOMMEND: dict[str, list[str]] = {
    "market_research": [
        "先用小规模试点验证核心假设，再决定渠道与产能投入",
        "优先切入增速高于行业均值、竞争集中度较低的细分场景",
        "把「可追溯的数据来源」写进立项材料，降低评审返工",
    ],
    "competitor_analysis": [
        "避开头部厂商的高密度功能正面竞争，选择单点体验做到极致",
        "定价上采用「基础订阅 + 效果加购」，降低首次决策门槛",
        "把差异点写成可验证的对比指标，方便销售复用",
    ],
    "content_marketing": [
        "围绕用户真实痛点做选题，标题突出场景而非参数",
        "内容节奏按「认知 → 对比 → 转化」三段式排期",
        "所有对外表述需保留证据链接，避免绝对化用语",
    ],
    "data_organize": [
        "先统一指标口径与统计周期，再做跨表汇总",
        "对异常值单独标注原因，不直接删除",
        "输出 CSV 时保留原始行号，便于回溯核对",
    ],
    "knowledge_qa": [
        "回答必须标注知识库出处与更新时间",
        "知识库没有覆盖的问题标记为待补充，不做推测",
        "涉及授权与合规的问题，按平台规则给出明确边界",
    ],
    "general": [
        "把目标拆成可验证的小步骤，逐步确认后再扩大范围",
        "关键结论至少保留两个独立来源交叉验证",
        "对不确定的信息明确写「待确认」，避免误导决策",
    ],
}


def _report_sections(ctx: dict) -> str:
    goal = ctx["goal"]
    skill = ctx["skill"]
    sources = ctx["sources"]
    knowledge_hits = ctx.get("knowledge") or []
    table = ctx.get("table") or {"columns": [], "rows": []}

    findings = []
    for s in sources[:3]:
        findings.append(f"- **{s['title']}**（{s['publisher']}，{s['year']}）：{s['snippet']}")
    for h in knowledge_hits[:2]:
        findings.append(f"- **知识库 · {h['title']}**：{h['text'][:140]}")
    if not findings:
        findings.append("- 暂未检索到可用证据，结论需补充资料后再确认。")

    comparison = _md_table(table["columns"], table["rows"]) if table["rows"] else "暂无结构化数据。"

    stats = ctx.get("stats") or {}
    recs = _RECOMMEND.get(skill["id"], _RECOMMEND["general"])
    rec_lines = [f"{i+1}. {r}" for i, r in enumerate(recs)]
    if stats.get("avgGrowth"):
        rec_lines.insert(0, f"1. 样本平均增速约 {stats['avgGrowth']}%，"
                            f"建议优先选择高增速方向做验证")
        rec_lines = [f"{i+1}. {r.split('. ', 1)[-1]}" for i, r in enumerate(rec_lines)]

    source_lines = [f"- [{s['title']}]({s['url']}) · {s['publisher']} · {s['year']}"
                    for s in sources]
    source_lines += [f"- 知识库：{h['title']}（相似度 {h['score']}）" for h in knowledge_hits]
    if not source_lines:
        source_lines = ["- 暂无外部来源"]

    todo = [
        "核对统计口径（年份、币种、样本范围）是否一致",
        "补充至少一个一手访谈或内部数据交叉验证",
        "敏感动作（对外发送/发布）执行前需人工授权",
    ]

    return "\n\n".join([
        f"# {goal}\n\n> 由灵枢 AgentHub「{skill['name']}」技能生成 · 智能体团队协作产出",
        "## 一、背景与目标\n\n" + f"本次任务目标：{goal}。团队按「"
        + " → ".join(list(ctx.get("step_titles", []))[:4])
        + "」推进，最终形成本报告。",
        "## 二、关键发现\n\n" + "\n".join(findings),
        "## 三、对比分析\n\n" + comparison,
        "## 四、建议与下一步\n\n" + "\n".join(rec_lines),
        "## 五、来源\n\n" + "\n".join(source_lines),
        "## 六、待确认\n\n" + "\n".join(f"- {t}" for t in todo),
    ])


def report_writer(ctx: dict) -> dict:
    content = ""
    mode = ctx.get("mode", "mock")
    if mode == "live" and config.deepseek_enabled():
        content = llm.write_report(ctx["goal"], ctx["skill"]["name"],
                                   ctx["sources"], ctx.get("table"), ctx.get("knowledge"))
    if not content:
        content = _report_sections(ctx)
        ctx["mode"] = "mock" if mode == "live" else mode
    ctx["report"] = content
    return {"summary": f"已生成 Markdown 报告，共 {len(content)} 字，包含背景、发现、对比、"
                       f"建议、来源与待确认 6 个部分。",
            "report": content, "chars": len(content)}


def review(ctx: dict) -> dict:
    sources = ctx["sources"]
    table = ctx.get("table") or {"rows": []}
    report = ctx.get("report") or ""
    checks = [
        {"item": "引用数量不少于 2 条", "passed": len(sources) >= 2},
        {"item": "结构化数据已标注来源/口径", "passed": bool(table.get("rows"))},
        {"item": "报告包含「待确认」章节", "passed": "待确认" in report},
        {"item": "敏感动作已设置人工授权",
         "passed": (not ctx.get("has_sensitive")) or bool(ctx.get("approval_gate"))},
        {"item": "未出现绝对化承诺（100%/保证）",
         "passed": ("100%" not in report) and ("保证" not in report)},
    ]
    ctx["checklist"] = checks
    lines = [f"- [{'x' if c['passed'] else ' '}] {c['item']}" for c in checks]
    passed = sum(1 for c in checks if c["passed"])
    return {"summary": f"审核完成：{passed}/{len(checks)} 项通过。\n" + "\n".join(lines),
            "checklist": checks, "passed": passed, "total": len(checks)}


def notify(ctx: dict) -> dict:
    text = f"「{ctx['goal']}」已完成，报告与数据表已生成，请查收。"
    ctx["notified"] = text
    return {"summary": f"已发送通知（模拟）：{text}"}


RUNNERS = {
    "web_search": web_search,
    "web_fetch": web_fetch,
    "knowledge": knowledge,
    "data_analyze": data_analyze,
    "report_writer": report_writer,
    "review": review,
    "notify": notify,
}


def run(action: str, ctx: dict) -> dict:
    fn = RUNNERS.get(action)
    if not fn:
        return {"summary": f"未实现的能力：{action}"}
    return fn(ctx)


def capability_view() -> list[dict]:
    out = []
    for c in CAPABILITIES:
        out.append({**c, "sensitive": bool(c.get("sensitive"))})
    return out


def is_sensitive_goal(goal: str) -> bool:
    return any(k in (goal or "") for k in SENSITIVE_KEYWORDS)


def action_label(action: str) -> str:
    return ACTION_LABEL.get(action, action)
