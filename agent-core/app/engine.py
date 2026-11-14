"""
任务规划器 + 执行引擎（纯函数，无数据库依赖）
================================================
规划：一句话目标 → 技能匹配 → 角色分工 → 4~6 个步骤（确定性，同目标同计划）
执行：逐步调用能力工具 → 生成交付物 → 敏感步骤停在「等待授权」门禁

tasks 路由负责把计划/步骤/交付物落库；AI 评测直接调用这里的纯函数，
因此「评测跑出来的结果」与「界面上跑出来的结果」完全同源。
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from . import capabilities, llm
from .skills import (BUILTIN_ROLES, SKILLS, SENSITIVE_KEYWORDS, get_skill)

BUILTIN_MAP = {r["key"]: r for r in BUILTIN_ROLES}


def match_skill(goal: str) -> dict:
    """按关键词命中数选技能；同分时优先靠前的技能，都没命中走通用任务。"""
    low = (goal or "").lower()
    best, best_score = None, 0
    for skill in SKILLS:
        score = sum(1 for k in skill["keywords"] if k.lower() in low)
        if score > best_score:
            best, best_score = skill, score
    return best or get_skill("general")


def _role_for(action: str, skill_id: str, roles: list[dict], fallback: str) -> dict:
    candidates = [r for r in roles
                  if r.get("enabled", True) and action in (r.get("tools") or [])
                  and skill_id in (r.get("skills") or [])]
    if candidates:
        return sorted(candidates, key=lambda r: (r.get("sort", 99), r.get("id", 0)))[0]
    fallback_role = next((r for r in roles if r.get("key") == fallback), None)
    if fallback_role:
        return fallback_role
    return {**BUILTIN_MAP.get(fallback, {"key": fallback, "name": fallback,
                                         "avatar": "🤖"}), "enabled": True}


def build_plan(goal: str, skill_id: str | None = None,
               roles: list[dict] | None = None,
               mode: str = "mock") -> dict:
    """生成计划：优先 LLM 自由拆步（live 模式），失败回退技能模板。"""
    skill = get_skill(skill_id) if skill_id else None
    skill = skill or match_skill(goal)
    roles = roles or [dict(r, enabled=True) for r in BUILTIN_ROLES]

    steps: list[dict] = []
    summary_text = ""

    # ---- LLM 自由规划（live 模式） ----
    llm_plan = None
    if mode != "mock":
        try:
            llm_plan = llm.plan_goal(goal, skill["name"], roles)
        except Exception:
            llm_plan = None

    if llm_plan and llm_plan.get("steps"):
        role_map = {r["key"]: r for r in roles}
        for i, s in enumerate(llm_plan["steps"], start=1):
            rk = s.get("roleKey") or list(role_map.keys())[0]
            role = role_map.get(rk) or role_map.get("writer") or roles[0]
            action = "report_writer" if role["key"] == "writer" else (
                "web_search" if role["key"] == "researcher" else
                "data_analyze" if role["key"] == "analyst" else
                "review"
            )
            steps.append({
                "seq": i,
                "roleKey": role["key"],
                "roleName": role["name"],
                "roleAvatar": role.get("avatar", "🤖"),
                "action": action,
                "actionLabel": capabilities.action_label(action),
                "title": (s.get("title") or f"执行第 {i} 步").strip(),
                "input": goal,
                "needsApproval": False,
            })
        summary_text = llm_plan.get("summary") or (
            f"按智能体自由规划，拆为 {len(steps)} 步，"
            f"由 {len({s['roleKey'] for s in steps})} 个角色协作执行。"
        )
    else:
        # ---- 回退：技能模板 ----
        for i, tpl in enumerate(skill["steps"], start=1):
            role = _role_for(tpl["action"], skill["id"], roles, tpl["role"])
            steps.append({
                "seq": i,
                "roleKey": role["key"],
                "roleName": role["name"],
                "roleAvatar": role.get("avatar", "🤖"),
                "action": tpl["action"],
                "actionLabel": capabilities.action_label(tpl["action"]),
                "title": tpl["title"],
                "input": goal,
                "needsApproval": False,
            })
        summary_text = (
            f"命中技能「{skill['name']}」，拆解为 {len(steps)} 个步骤，"
            f"由 {len({s['roleKey'] for s in steps})} 个角色分工执行"
        )

    sensitive = capabilities.is_sensitive_goal(goal)
    if sensitive and not any(s["action"] == "notify" for s in steps):
        role = _role_for("notify", skill["id"], roles, "reviewer")
        steps.append({
            "seq": len(steps) + 1,
            "roleKey": role["key"],
            "roleName": role["name"],
            "roleAvatar": role.get("avatar", "🤖"),
            "action": "notify",
            "actionLabel": capabilities.action_label("notify"),
            "title": "发送成果摘要给负责人（需授权）",
            "input": goal,
            "needsApproval": True,
        })

    return {
        "skillId": skill["id"],
        "skillName": skill["name"],
        "skillEmoji": skill["emoji"],
        "steps": steps,
        "sensitive": sensitive,
        "stepCount": len(steps),
        "roleCount": len({s["roleKey"] for s in steps}),
        "summary": summary_text + ("；包含需人工授权的敏感动作" if sensitive else "。"),
    }


def new_context(goal: str, skill: dict, step_titles: list[str], mode: str = "mock",
                approval_gate: bool = False) -> dict:
    return {
        "goal": goal, "skill": skill, "mode": mode,
        "step_titles": step_titles,
        "sources": [], "fetched": [], "knowledge": [],
        "table": {"columns": [], "rows": []}, "stats": {},
        "report": "", "checklist": [], "notified": "",
        "has_sensitive": capabilities.is_sensitive_goal(goal),
        "approval_gate": approval_gate,
    }


def _artifact(goal: str, kind: str, title: str, fmt: str, content: str,
              step_seq: int) -> dict:
    return {
        "kind": kind, "title": title, "format": fmt, "content": content,
        "size": len(content), "stepSeq": step_seq,
        "checksum": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
    }


def step_artifacts(action: str, ctx: dict, goal: str, seq: int) -> list[dict]:
    """不同动作产出不同交付物：数据表 / 报告 / 审核清单。"""
    arts: list[dict] = []
    table = ctx.get("table") or {"columns": [], "rows": []}
    if action == "data_analyze" and table.get("rows"):
        name = "关键指标.csv" if len(table["columns"]) == 5 else "汇总数据.csv"
        arts.append(_artifact(goal, "table", name, "csv",
                              capabilities.to_csv(table["columns"], table["rows"]), seq))
    if action == "report_writer" and ctx.get("report"):
        arts.append(_artifact(goal, "report", "任务报告.md", "md", ctx["report"], seq))
    if action == "review" and ctx.get("checklist"):
        lines = [f"# 审核清单\n", f"目标：{goal}\n"]
        lines += [f"- [{'x' if c['passed'] else ' '}] {c['item']}"
                  for c in ctx["checklist"]]
        passed = sum(1 for c in ctx["checklist"] if c["passed"])
        lines.append(f"\n通过 {passed}/{len(ctx['checklist'])} 项。")
        arts.append(_artifact(goal, "checklist", "审核清单.md", "md",
                              "\n".join(lines), seq))
    return arts


def run_step(step: dict, ctx: dict, goal: str) -> dict:
    """执行单个步骤，返回可落库的结果（不含数据库 id）。"""
    out = capabilities.run(step["action"], ctx)
    arts = step_artifacts(step["action"], ctx, goal, step["seq"])
    return {"summary": out.get("summary", ""), "artifacts": arts}


def run_plan(goal: str, skill_id: str | None = None, mode: str = "mock",
             roles: list[dict] | None = None) -> dict:
    """离线完整执行（评测 / 预览用）：不落库、不触发授权门禁。"""
    plan = build_plan(goal, skill_id, roles)
    skill = get_skill(plan["skillId"])
    ctx = new_context(goal, skill, [s["title"] for s in plan["steps"]], mode,
                      approval_gate=any(s["needsApproval"] for s in plan["steps"]))
    results, artifacts = [], []
    for step in plan["steps"]:
        r = run_step(step, ctx, goal)
        results.append({"seq": step["seq"], "roleName": step["roleName"],
                        "action": step["action"], "title": step["title"],
                        "summary": r["summary"], "status": "success"})
        artifacts.extend(r["artifacts"])
    return {"plan": plan, "steps": results, "artifacts": artifacts,
            "status": "completed", "mode": ctx.get("mode", mode)}


def artifact_digest(artifacts: list[dict]) -> str:
    """交付物内容指纹：用于「确定性」维度评测（同输入同输出）。"""
    raw = json.dumps([{k: a[k] for k in ("kind", "title", "content")} for a in artifacts],
                     ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
