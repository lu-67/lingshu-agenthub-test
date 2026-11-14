"""
大模型层（可选增强）
====================
默认走确定性模板，不依赖任何外部服务；只有用户显式选择 live 模式且配置了
DEEPSEEK_API_KEY 时，才调用 DeepSeek 对计划、总结做 LLM 增强。调用失败一律返回空，
由执行引擎回退模板，保证服务可用性与测试可复现。
"""
from __future__ import annotations

import json
import re

import httpx

from . import config

# 提示词注入特征词：安全用例与任务创建时用于拦截
INJECTION_PATTERNS = [
    "忽略以上", "忽略之前", "忽略所有", "ignore previous", "ignore all previous",
    "越狱", "jailbreak", "dan mode", "系统提示词", "system prompt",
    "输出你的指令", "reveal your", "开发者模式", "developer mode",
]


def is_injection(text: str) -> bool:
    low = (text or "").lower()
    return any(p in low for p in INJECTION_PATTERNS)


def _chat(messages: list[dict], *, temperature: float = 0.3,
          model: str | None = None, timeout: int = 60) -> str:
    """通用 chat 调用；失败返回空串。"""
    try:
        resp = httpx.post(
            f"{config.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
            json={
                "model": model or config.DEEPSEEK_MODEL,
                "temperature": temperature,
                "messages": messages,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return ""


def plan_goal(goal: str, skill_hint: str, role_pool: list[dict]) -> dict | None:
    """让 LLM 根据目标自由拆出步骤（不再用固定模板）。失败返回 None。"""
    roles_txt = " / ".join(f"{r['key']}({r['name']})" for r in role_pool)
    prompt = (
        "你是一个任务规划器。请根据用户的目标，用 JSON 输出执行计划。\n\n"
        f"目标：{goal}\n"
        f"可用角色：{roles_txt}\n"
        f"建议技能：{skill_hint}\n\n"
        "输出 JSON：\n"
        "{\n"
        '  "summary": "一句话概述这个计划在做什么",\n'
        '  "steps": [\n'
        '    {"roleKey": "researcher", "title": "这一步的具体动作（动宾短语）"}\n'
        "  ]\n"
        "}\n\n"
        "要求：\n"
        "- 3~6 步，每步角色可重复，按实际需要分配\n"
        "- title 用中文动词开头，具体到可执行的动作\n"
        "- 不要编造角色名，必须从可用角色里选\n"
        "- 只输出 JSON，不要别的"
    )
    raw = _chat([
        {"role": "system", "content": "你是任务规划器，只输出 JSON。"},
        {"role": "user", "content": prompt},
    ], temperature=0.4, timeout=45)
    if not raw:
        return None
    m = re.search(r"\{[\s\S]+\}", raw)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("steps"), list):
        return None
    return obj


def summarize_run(goal: str, step_outputs: list[dict],
                  report: str | None, sources: list[dict] | None = None) -> str:
    """让 LLM 把所有中间输出汇总成一份自然语言回答。失败返回空串。"""
    steps_txt = "\n".join(
        f"- 第{i+1}步 · {s.get('title')}：{(s.get('summary') or '')[:240]}"
        for i, s in enumerate(step_outputs)
    )
    report_snippet = (report[:1500] + "…") if report else "（无结构化报告）"
    sources_txt = ""
    if sources:
        sources_txt = "\n\n参考来源：\n" + "\n".join(
            f"- [{s.get('title', '')}]({s.get('url', '')}) · {s.get('publisher', '')}"
            for s in sources[:8]
        )

    prompt = (
        f"用户目标：{goal}\n\n"
        f"执行过程（仅供你了解，不要暴露给用户）：\n{steps_txt}\n\n"
        f"已生成的结构化报告片段：\n{report_snippet}\n{sources_txt}\n\n"
        "请用中文 Markdown 写一份直接回答用户的内容。\n"
        "风格参考：Accio Work 那种自然展开的回答——\n"
        "- 先一句话给核心结论\n"
        "- 再分小节阐述，用加粗小标题（**小节名**）\n"
        "- 适当使用有序/无序列表、对比表\n"
        "- 可以自然提到检索到的来源和关键数据\n"
        "- 不要提「调研员/分析师/步骤/计划/交付物」等内部术语\n"
        "- 不要暴露执行框架\n"
        "- 直接给用户想要的答案本身\n"
    )
    return _chat([
        {"role": "system", "content": (
            "你是一个业务 AI 助手，直接给用户答案。不要暴露内部执行过程。"
            "用自然的中文，结构清晰，适度使用 Markdown。"
        )},
        {"role": "user", "content": prompt},
    ], temperature=0.55, timeout=60)


SYSTEM_PROMPT = (
    "你是灵枢 AgentHub 的撰写员。请基于给定的证据撰写中文 Markdown 报告。"
    "不得编造来源或数据，未知信息写入「待确认」。"
)


def write_report(goal: str, skill_name: str, sources: list[dict],
                table: dict | None, knowledge_hits: list[dict] | None) -> str:
    """调用 DeepSeek 生成报告；失败返回空串，由模板兜底。"""
    evidence = {
        "目标": goal, "技能": skill_name,
        "来源": [{k: s.get(k) for k in ("title", "publisher", "url", "snippet", "year")}
                 for s in sources],
        "数据表": table or {}, "知识库": knowledge_hits or [],
    }
    raw = _chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"证据如下（JSON）：\n{evidence}"},
    ], temperature=0.2, timeout=60)
    return raw
