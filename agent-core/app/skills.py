"""
技能目录 + 内置角色定义（v4.0 智能体工作台）
================================================
一个「技能」= 一类任务的计划模板：谁（角色）在什么阶段做什么（动作），
最终产出哪些交付物。规划器只做「目标 -> 技能 -> 步骤」的确定性映射，
执行器按步骤调用能力工具，因此同一目标永远得到同一计划与同一份交付物。

设计原则（同时也是可测试性设计）：
1. 纯数据：技能/角色都是普通 dict，新增技能不需要改代码；
2. 确定性：不做随机、不依赖网络，测试可以对计划、交付物做精确断言；
3. 可扩展：roles 表里的自定义角色只要 action 命中能力工具即可复用模板。
"""
from __future__ import annotations

# ------------------------------------------------------------------ 能力工具
# action 名称必须与 capabilities.run() 支持的动作一致
CAPABILITIES: list[dict] = [
    {"name": "web_search", "label": "网页检索", "icon": "search",
     "description": "按关键词检索公开资料，返回标题、摘要、来源与关键数据"},
    {"name": "web_fetch", "label": "网页抓取", "icon": "external",
     "description": "抓取指定来源正文，提取可引用的事实片段"},
    {"name": "knowledge", "label": "知识库检索", "icon": "book",
     "description": "检索团队知识库（RAG 向量召回），返回带相似度的片段"},
    {"name": "data_analyze", "label": "数据分析", "icon": "chart",
     "description": "把检索结果整理为对比表，计算规模、增速与机会评分"},
    {"name": "report_writer", "label": "报告撰写", "icon": "edit",
     "description": "按「背景/发现/对比/建议/来源/待确认」结构生成 Markdown 报告"},
    {"name": "review", "label": "质量审核", "icon": "shield",
     "description": "核对引用、数据口径与风险点，生成审核清单"},
    {"name": "notify", "label": "消息通知", "icon": "send", "sensitive": True,
     "description": "把结论发送到群/邮箱等外部渠道（敏感动作，需要人工授权）"},
]

ACTION_LABEL = {c["name"]: c["label"] for c in CAPABILITIES}


# ------------------------------------------------------------------ 内置角色
BUILTIN_ROLES: list[dict] = [
    {
        "key": "researcher", "name": "调研员", "avatar": "🔭", "sort": 1,
        "responsibility": "检索公开资料、抓取来源正文，保证每条结论都有出处",
        "skills": ["market_research", "competitor_analysis", "knowledge_qa", "general"],
        "tools": ["web_search", "web_fetch", "knowledge"],
        "prompt": "你是调研员，只负责找资料：优先给出可追溯的来源与原文摘录，不做主观推断。",
    },
    {
        "key": "analyst", "name": "分析师", "avatar": "📊", "sort": 2,
        "responsibility": "把资料整理成结构化数据，计算指标、做对比与机会判断",
        "skills": ["market_research", "competitor_analysis", "data_organize", "general"],
        "tools": ["data_analyze", "knowledge"],
        "prompt": "你是分析师，只基于已检索到的证据做量化分析，缺失数据必须标注「待确认」。",
    },
    {
        "key": "writer", "name": "撰写员", "avatar": "✍️", "sort": 3,
        "responsibility": "把分析结论写成可交付的报告、方案与表格",
        "skills": ["market_research", "competitor_analysis", "content_marketing",
                   "data_organize", "knowledge_qa", "general"],
        "tools": ["report_writer"],
        "prompt": "你是撰写员，输出结构化 Markdown：背景、关键发现、对比、建议、来源、待确认。",
    },
    {
        "key": "reviewer", "name": "审核员", "avatar": "🛡️", "sort": 4,
        "responsibility": "核对引用与口径、标注风险，并对敏感动作做授权确认",
        "skills": ["market_research", "competitor_analysis", "content_marketing",
                   "data_organize", "knowledge_qa", "general"],
        "tools": ["review", "notify"],
        "prompt": "你是审核员，逐条检查证据是否充分；涉及对外发送/付款等动作必须要求人工授权。",
    },
]


# ------------------------------------------------------------------ 技能目录
SKILLS: list[dict] = [
    {
        "id": "market_research", "name": "市场调研", "icon": "search", "emoji": "🔭",
        "category": "研究分析",
        "description": "检索市场规模、增长趋势与机会点，产出一份带引用来源的调研报告。",
        "keywords": ["调研", "市场", "行业", "赛道", "趋势", "机会", "规模", "进入",
                     "用户需求", "增长", "分析报告"],
        "example": "调研 2026 年国内宠物智能硬件市场，输出机会点与进入建议",
        "deliverables": ["调研报告（Markdown）", "关键指标（CSV）", "审核清单"],
        "steps": [
            {"role": "researcher", "action": "web_search", "title": "检索市场规模与增长趋势"},
            {"role": "researcher", "action": "web_fetch", "title": "抓取关键来源正文"},
            {"role": "analyst", "action": "data_analyze", "title": "提炼指标并生成对比表"},
            {"role": "writer", "action": "report_writer", "title": "撰写调研报告"},
            {"role": "reviewer", "action": "review", "title": "核对引用与结论"},
        ],
    },
    {
        "id": "competitor_analysis", "name": "竞品分析", "icon": "layers", "emoji": "🥊",
        "category": "研究分析",
        "description": "收集竞品资料，从定位、定价、功能、口碑四个维度对比并给出差异化建议。",
        "keywords": ["竞品", "对比", "对标", "友商", "差异化", "优势", "劣势", "定价", "功能对比"],
        "example": "对比三款 AI 智能体平台的定价与能力差异，给出我们的差异化方向",
        "deliverables": ["竞品分析报告（Markdown）", "对比矩阵（CSV）", "审核清单"],
        "steps": [
            {"role": "researcher", "action": "web_search", "title": "检索竞品公开资料"},
            {"role": "researcher", "action": "web_fetch", "title": "抓取竞品定价与功能页"},
            {"role": "analyst", "action": "data_analyze", "title": "生成四维对比矩阵"},
            {"role": "writer", "action": "report_writer", "title": "撰写竞品分析报告"},
            {"role": "reviewer", "action": "review", "title": "核对事实与口径"},
        ],
    },
    {
        "id": "content_marketing", "name": "内容营销", "icon": "wand", "emoji": "📣",
        "category": "增长运营",
        "description": "结合受众热点与品牌知识库，产出选题、标题、正文结构与发布节奏。",
        "keywords": ["文案", "营销", "推广", "小红书", "公众号", "种草", "活动", "标题",
                     "内容", "选题", "投放"],
        "example": "给宠物智能饮水机写一套小红书内容方案，包含 5 个选题和发布节奏",
        "deliverables": ["内容方案（Markdown）", "审核清单"],
        "steps": [
            {"role": "researcher", "action": "web_search", "title": "检索受众关注点与热点"},
            {"role": "researcher", "action": "knowledge", "title": "检索品牌知识库口径"},
            {"role": "writer", "action": "report_writer", "title": "生成内容方案与选题"},
            {"role": "reviewer", "action": "review", "title": "检查合规与事实表述"},
        ],
    },
    {
        "id": "data_organize", "name": "数据整理", "icon": "chart", "emoji": "🧮",
        "category": "效率工具",
        "description": "把零散数据整理成结构化表格，给出汇总指标与异常说明。",
        "keywords": ["数据", "表格", "csv", "清洗", "汇总", "统计", "整理", "台账", "口径"],
        "example": "把本周门店销售数据整理成表格，汇总环比并说明异常",
        "deliverables": ["数据说明（Markdown）", "汇总表（CSV）", "审核清单"],
        "steps": [
            {"role": "analyst", "action": "knowledge", "title": "读取指标口径与字段说明"},
            {"role": "analyst", "action": "data_analyze", "title": "清洗汇总并生成 CSV"},
            {"role": "writer", "action": "report_writer", "title": "输出数据说明"},
            {"role": "reviewer", "action": "review", "title": "校验口径与异常值"},
        ],
    },
    {
        "id": "knowledge_qa", "name": "知识问答", "icon": "book", "emoji": "📚",
        "category": "效率工具",
        "description": "先从团队知识库找依据，再补充公开资料，输出带引用的问答结论。",
        "keywords": ["知识库", "文档", "问答", "制度", "流程", "是什么", "怎么", "规定", "检索"],
        "example": "根据团队知识库说明任务授权规则，并给出出处",
        "deliverables": ["问答结论（Markdown）", "审核清单"],
        "steps": [
            {"role": "researcher", "action": "knowledge", "title": "定位知识库相关文档"},
            {"role": "analyst", "action": "web_search", "title": "补充公开资料佐证"},
            {"role": "writer", "action": "report_writer", "title": "整理问答结论"},
            {"role": "reviewer", "action": "review", "title": "核对引用与时效"},
        ],
    },
    {
        "id": "general", "name": "通用任务", "icon": "spark", "emoji": "✨",
        "category": "效率工具",
        "description": "没有命中具体技能时的兜底模板：检索 → 分析 → 撰写 → 审核。",
        "keywords": [],
        "example": "帮我研究一下 AI 测试岗位需要哪些能力，给一份学习路线",
        "deliverables": ["任务报告（Markdown）", "关键指标（CSV）", "审核清单"],
        "steps": [
            {"role": "researcher", "action": "web_search", "title": "检索任务相关资料"},
            {"role": "analyst", "action": "data_analyze", "title": "整理要点与关键指标"},
            {"role": "writer", "action": "report_writer", "title": "撰写任务报告"},
            {"role": "reviewer", "action": "review", "title": "核对结论与引用"},
        ],
    },
]

SKILL_MAP = {s["id"]: s for s in SKILLS}
SKILL_IDS = set(SKILL_MAP)

# 目标里出现这些词时追加「对外通知」步骤，并且该步骤必须人工授权
SENSITIVE_KEYWORDS = ["发送", "邮件", "通知", "发布到", "推送给", "下单", "付款", "群发"]


def get_skill(skill_id: str) -> dict | None:
    return SKILL_MAP.get((skill_id or "").strip())


def skill_view(s: dict, enabled: bool = True) -> dict:
    return {
        "id": s["id"], "name": s["name"], "icon": s["icon"], "emoji": s["emoji"],
        "category": s["category"], "description": s["description"],
        "keywords": s["keywords"], "example": s["example"],
        "deliverables": s["deliverables"], "stepCount": len(s["steps"]),
        "roles": sorted({st["role"] for st in s["steps"]}),
        "actions": [st["action"] for st in s["steps"]],
        "enabled": enabled,
    }
