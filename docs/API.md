# 灵枢 AgentHub · API 接口文档

> 后端：FastAPI，Base URL `http://127.0.0.1:8000`
> Swagger 在线文档：`http://127.0.0.1:8000/docs`
> 所有接口默认返回 JSON，下载类接口返回文件流

---

## 鉴权规则

除 `/health`、`/api/captcha`、`/api/auth/register`、`/api/auth/login` 外，全部需要在请求头里带 JWT：

```
Authorization: Bearer <token>
```

Token 由登录/注册接口返回。缺失或过期 → `401`；管理员接口普通用户访问 → `403`。

### 常见错误

| 状态码 | 什么时候返回 |
|--------|-------------|
| 400 | 参数不对、状态不允许、注入词被拦截 |
| 401 | Token 没带或过期 |
| 403 | 没权限（非 admin、不是资源所有者） |
| 404 | 资源不存在 |
| 422 | 请求体格式不对（Pydantic 校验失败） |

错误响应统一格式：

```json
{ "detail": "错误描述" }
```

---

## 1. 登录注册

### GET /api/captcha

生成图形验证码。注册页先调这个拿到验证码图片和 id，再连同账号密码一起提交。

**不需要登录。**

返回：

```json
{ "id": "a1b2c3d4...", "image": "data:image/png;base64,...", "pilAvailable": true }
```

`id` 要在注册时原样传回去。验证码 5 分钟有效，一次性使用。

### POST /api/auth/register

注册新账号。

```json
{ "username": "tester", "password": "123456", "captchaId": "a1b2c3d4...", "captchaCode": "A3F8" }
```

| 字段 | 要求 |
|------|------|
| username | 3–20 字符，只能是字母、数字、下划线、短横线，全局唯一 |
| password | 至少 6 个字符 |
| captchaId | GET /api/captcha 返回的 id |
| captchaCode | 用户看到的验证码（不区分大小写） |

成功直接返回 token，不用再登录一次：

```json
{ "token": "eyJhbGciOi...", "username": "tester", "role": "USER", "id": 2 }
```

### POST /api/auth/login

已有账号登录。

```json
{ "username": "tester", "password": "tester123" }
```

返回同注册。账号不存在或密码错误统一 `400 密码错误或用户不存在`。

### GET /api/auth/me

查当前登录用户自己的信息。

```json
{
  "id": 2, "username": "tester", "role": "USER",
  "createdAt": "2026-10-31 12:00:00",
  "stats": { "agents": 4, "sessions": 8, "tasks": 12 }
}
```

---

## 2. 智能体

### GET /api/agents

列出当前用户的所有智能体（内置的 + 自己建的）。

```json
{ "agents": [ { "id": 1, "name": "灵枢助手", "avatar": "🤖", "enabled": true, ... } ] }
```

### POST /api/agents

新建智能体。

```json
{
  "name": "市场调研官",
  "avatar": "🔭",
  "description": "专门搞市场调研的智能体",
  "skillIds": ["market_research", "competitor_analysis"],
  "model": "mock"
}
```

| 字段 | 说明 |
|------|------|
| name | 必填，1–64 字符 |
| avatar | emoji 字符，可选 |
| skillIds | 这个智能体允许用哪些技能，只能从 6 个内置技能里选 |
| model | `mock`（默认，确定性）或 `live`（接入真实大模型时用） |

### PUT /api/agents/{aid}

修改已有智能体。字段同新建，全部可选，只传要改的。

```json
{ "enabled": false }
```

---

## 3. 会话（对话）

### GET /api/sessions

列出当前用户的会话。

| 参数 | 说明 |
|------|------|
| agentId | 可选，按智能体筛选 |
| limit | 可选，默认 50，最大 200 |

```json
{ "sessions": [ { "id": 5, "title": "新对话", "lastMessage": "...", "updatedAt": "..." } ] }
```

### POST /api/sessions

新建会话。绑定一个智能体，给个标题。

```json
{ "agentId": 1, "title": "调研宠物智能硬件" }
```

返回会话详情（不含消息，消息要用 GET /sessions/{id} 拿）。

### GET /api/sessions/{sid}

查会话详情，包含全部历史消息。

```json
{
  "id": 5, "agentId": 1, "agentName": "灵枢助手", "title": "...",
  "messages": [
    { "role": "user", "content": "调研宠物智能硬件市场", "createdAt": "..." },
    { "role": "assistant", "content": "根据调研结果...", "data": { "artifacts": [...], "thinking": [...] } }
  ]
}
```

assistant 消息里的 `data` 字段：
- `artifacts`：执行过程中产生的交付物列表（报告、表格、审核清单）
- `thinking`：内部思考过程（每个步骤的角色、标题、耗时、状态），前端折叠显示

### POST /api/sessions/{sid}/send （核心接口）

给会话发一个目标。后端自动匹配技能、规划步骤、逐步执行、出最终自然语言回答。

```json
{ "content": "调研 2026 年国内宠物智能硬件市场，输出机会点与进入建议", "autoApprove": false }
```

| 字段 | 说明 |
|------|------|
| content | 必填，2–500 字符。敏感词（"忽略之前"、"忽略以上"等注入词）会被拦截 |
| autoApprove | 可选，默认 false。测试时传 true 可以跳过授权门禁 |

**两种可能的返回：**

**a) 正常完成：**

```json
{
  "message": "completed",
  "sessionId": 5, "taskId": 12,
  "elapsedMs": 2340, "artifacts": 3,
  "messages": [ /* 完整消息列表，最后一条是自然语言回答 */ ]
}
```

**b) 遇到敏感步骤（目标里有"发送"、"邮件"、"通知"等），停在授权门禁：**

```json
{
  "message": "waiting_approval",
  "sessionId": 5, "taskId": 12, "stepSeq": 5,
  "messages": [ /* 同上 */ ]
}
```

这时要调下面的 approve 接口批准后才会继续。

### POST /api/sessions/{sid}/approve

批准敏感步骤继续执行。

```json
{ "note": "内容已确认" }
```

成功后继续执行剩余步骤，最终返回自然语言回答。

---

## 4. 定时任务（Automations）

给某个智能体设一个目标 + 触发规则，到点自动执行。

### GET /api/automations

列出当前用户的所有定时任务。

```json
{ "automations": [ { "id": 3, "name": "每周一调研", "goal": "调研...", "enabled": true, "lastRunAt": "...", "nextRunAt": "..." } ] }
```

### POST /api/automations

新建定时任务。

```json
{
  "agentId": 1,
  "name": "每周一市场调研",
  "cronExpr": "0 9 * * 1",
  "goal": "调研本周宠物智能硬件市场动态，输出简报",
  "enabled": true
}
```

| 字段 | 说明 |
|------|------|
| agentId | 必填，绑定哪个智能体 |
| name | 必填，起个名字 |
| cronExpr | 必填，cron 表达式 |
| goal | 必填，自动执行时发的目标 |
| enabled | 可选，默认 true |

创建后自动注册到 APScheduler，不用手动重启。

### PUT /api/automations/{aid}

修改定时任务。字段可选，只传要改的。改完自动同步调度器。

```json
{ "enabled": false }
```

### DELETE /api/automations/{aid}

删除定时任务。数据库记录 + 调度器 job 一起删。

---

## 5. 交付物下载

执行任务会产出交付物（CSV 表格、Markdown 报告、审核清单），挂在 assistant 消息的 `data.artifacts` 里。

### GET /api/artifacts/{aid}/download

下载交付物原始文件。浏览器会触发下载，文件名自动带上。

| 参数 | 说明 |
|------|------|
| aid | 交付物 id（从 messages 里拿） |

响应：文件流。CSV 用 `text/csv`，Markdown 用 `text/markdown`。

---

## 6. 管理后台（仅 admin 角色）

普通用户访问统一 `403`。

### GET /api/admin/users

全量用户列表。

```json
{ "users": [
  { "id": 1, "username": "admin", "role": "ADMIN", "createdAt": "...", "tasks": 5, "runs": 23 }
] }
```

### GET /api/admin/stats

平台整体统计数字。

```json
{
  "users": 2, "agents": 6, "sessions": 15, "messages": 38,
  "automations": 3, "tasks": 12, "artifacts": 36, "runs": 20,
  "evals": 0, "docs": 3, "roles": 4, "db": "mysql"
}
```

### GET /api/admin/users/{uid}

查单个用户的完整画像：各模块计数 + 最近 10 条智能体、会话、定时任务、任务、运行记录。

### DELETE /api/admin/users/{uid}

删除用户 + 级联清理所有关联数据（automations → artifacts → task_steps → messages → tasks → sessions → agents → users）。**不能删自己**。

### GET /api/admin/db/overview

数据库状态：总表数、总行数、总大小（MB）、每张表的行数和大小。

```json
{
  "backend": "mysql", "database": "nexus_agent",
  "tables": 12, "rows": 1423, "size_mb": 2.4,
  "per_table": [ { "table_name": "users", "table_rows": 2, "mb": 0.01, "engine": "InnoDB" }, ... ]
}
```

### GET /api/admin/scheduler/status

定时任务调度器状态：当前注册的所有 cron job + 是否在运行。

```json
{ "ok": true, "running": true, "jobs": [ { "id": 3, "cron_expr": "0 9 * * 1", "enabled": true, "next_run_time": "..." } ] }
```

---

## 7. 健康检查

### GET /health

服务探活。Swagger / JMeter / pytest 都用它判断服务是否就绪。**不需要登录**。

```json
{
  "status": "ok", "architecture": "single-service-fastapi",
  "engine": "multi-agent-planner",
  "db_backend": "mysql", "mysql": true,
  "redis": true, "deepseek": false, "chroma_docs": 51
}
```

---

## 接口清单速查（24 个）

| 模块 | 方法 | 路径 | 一句话 |
|------|------|------|--------|
| 验证码 | GET | /api/captcha | 生成图形验证码 |
| 注册 | POST | /api/auth/register | 验证码 + 账号密码注册 |
| 登录 | POST | /api/auth/login | 账号密码换 token |
| 当前用户 | GET | /api/auth/me | 查自己的信息和统计 |
| 智能体列表 | GET | /api/agents | 列出所有智能体 |
| 建智能体 | POST | /api/agents | 新建 |
| 改智能体 | PUT | /api/agents/{aid} | 修改 |
| 会话列表 | GET | /api/sessions | 列出所有会话 |
| 建会话 | POST | /api/sessions | 绑定智能体开新对话 |
| 会话详情 | GET | /api/sessions/{sid} | 含全部历史消息 |
| 发送执行 | POST | /api/sessions/{sid}/send | **核心**：目标 → 自动执行 → 回答 |
| 授权继续 | POST | /api/sessions/{sid}/approve | 批准敏感步骤后继续 |
| 定时列表 | GET | /api/automations | 列出定时任务 |
| 建定时 | POST | /api/automations | 新建 + 自动注册调度器 |
| 改定时 | PUT | /api/automations/{aid} | 修改 + 自动同步调度器 |
| 删定时 | DELETE | /api/automations/{aid} | 删除 + 自动移除调度器 |
| 下载交付物 | GET | /api/artifacts/{aid}/download | 下载 CSV / Markdown |
| admin-用户列表 | GET | /api/admin/users | 全量用户 |
| admin-总统计 | GET | /api/admin/stats | 平台各模块数字 |
| admin-删用户 | DELETE | /api/admin/users/{uid} | 连带清理所有关联数据 |
| admin-用户详情 | GET | /api/admin/users/{uid} | 单个用户完整画像 |
| admin-数据库 | GET | /api/admin/db/overview | 表数、行数、大小 |
| admin-调度器 | GET | /api/admin/scheduler/status | 当前 cron jobs |
| 健康检查 | GET | /health | 服务活没活 |
