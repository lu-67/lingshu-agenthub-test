﻿# 灵枢 AgentHub · 测试实操教程（总索引）

> 适用对象：第一次把这个项目的测试从头到尾做一遍的同学
> 被测系统：灵枢 AgentHub v5.0（FastAPI 单服务 + Vue3 前端）
> 后端 `http://127.0.0.1:8000`，前端 `http://127.0.0.1:5173`，接口文档 `http://127.0.0.1:8000/docs`
> 配套目录：`software test/`（Postman 集合、JMeter 脚本、压测结果）、`tests/`（自动化脚本）、`docs/`（用例表、缺陷清单、测试报告）、`.github/workflows/ci.yml`

---

## 0. 这套教程是干什么的

简历里「灵枢 AgentHub」那一段写了 7 条工作：测试方案、接口自动化、UI 自动化、自动化测试（fixture / Allure / CI）、性能压测、缺陷管理、接入 GitHub Actions。这套教程就是**一条一条带你把这几件事真做出来**。

每篇教程都按同一个套路写：先说这件事是什么 → 环境怎么装 → 一步步点/敲命令 → 自测清单 → 常见坑 → 做完应该留下什么文件 → 面试官会怎么追问、你该怎么答。末尾的问答都是大白话，不用背术语。

**建议按顺序做**，因为后面要用到前面产出的东西（比如第 2 篇要用到第 1 篇挑出来的 24 个接口，第 6 篇要用到前面所有脚本）。

---

## 1. 教程清单与简历对照表

| 编号 | 文件 | 对应简历哪一句 | 做完留下的东西 |
|---|---|---|---|
| 00 | `【教程】AgentHub-00-测试方案与136条用例.md` | 编写测试方案、136 条用例 | 测试计划书、用例编号表（API/UI 两类） |
| 01 | `【教程】AgentHub-01-接口测试Postman操作.md` | 用 Postman + Newman 批量验证 24 个接口 | 后端 24 接口 = Postman 25 请求（多了 admin 登录拿两套 token），Newman HTML 报告 |
| 02 | `【教程】AgentHub-02-接口自动化Pytest与Allure.md` | pytest+Requests 编写接口自动化脚本；88 条接口用例；fixture 复用、接口关联；Allure 报告 | 88 条脚本、`allure-results/`、Allure HTML 报告 |
| 03 | `【教程】AgentHub-03-UI自动化Playwright.md` | 使用 Playwright 编写 UI 自动化脚本；覆盖登录、主链路、权限校验 | 7 条 UI 用例、页面截图 `docs/screenshots/` |
| 04 | `【教程】AgentHub-04-性能测试JMeter.md` | send 核心压测点 + 3s 业务期望断言；P95/TPS 分 label 出报告 | 5 线程 3 循环压测报告、send P95 7.9s 瓶颈结论 |
| 05 | `【教程】AgentHub-05-缺陷管理与禅道.md` | 缺陷管理三工具（禅道 + Jira + 飞书多维表格），9 个缺陷 P0×1/P1×6/P2×2，修复后全部回归通过 | 9 条缺陷 × 3 种工具、JQL 查询、飞书零代码自动化、缺陷报告 |
| 06 | `【教程】AgentHub-06-GitHubActions持续集成.md` | 88 条接口 + 7 条 UI 接入 GitHub Actions | 绿灯的 CI 跑批、产物下载 |
| 07 | `【教程】AgentHub-07-面试官深挖20问.md` | —— | 20 个追问，每题一段能直接念出来的答案 |

每篇末尾都附「本篇对应的面试官追问」，大白话的问和答、都带项目里的真实例子，题目编号 Q01~Q20；第 07 篇把 20 题集中列一遍，每题配一段短答案，方便单独打印背。想看带例子的详细版翻各篇末尾，题号是对得上的。

---

## 2. 先把环境跑起来（所有教程的前置）

### 2.1 一键启动

双击项目根目录 `start.bat`，会开两个黑窗口：

```
AgentHub Backend  -> http://127.0.0.1:8000
AgentHub Frontend -> http://127.0.0.1:5173
```

等 10 秒，浏览器自动打开登录页。看到登录页 = 前后端都起来了。

验证后端（Git Bash 或 CMD）：

```bash
curl http://127.0.0.1:8000/health
# 返回 {"status":"ok",...} 才继续
```

### 2.2 账号

| 账号 | 密码 | 角色 | 用来测什么 |
|---|---|---|---|
| tester | tester123 | USER | 主流程、普通用户越权 |
| admin | admin123 | ADMIN | 管理后台、权限校验 |

### 2.3 Python 与工具路径（本机已装好，照抄即可）

| 东西 | 路径 / 命令 |
|---|---|
| Python | `D:\software\Python 3.10.11\python.exe` |
| JMeter | `D:\software\apache-jmeter-5.6.3\bin\jmeter.bat` |
| 前端 | `D:\nexus-agent\frontend`，`npm run dev` |
| 后端 | `D:\nexus-agent\agent-core`，`python run_server.py` |

> 不要直接敲 `python`：系统 PATH 里可能指向 WindowsApps 的占位程序。命令一律写全路径，或者在 CMD 里先 `set PATH=D:\software\Python 3.10.11;%PATH%`。

> **命令写法约定**：教程里的环境变量一律用 Git Bash 写法 `export KEY=value`；如果你开的是 CMD 黑窗口，改成 `set KEY=value`。JMeter 的 `jmeter -n ...` 两种终端都能跑，只是换行符不同（CMD 用 `^`，Git Bash 用 `\`），写成一行最省事。

### 2.4 还没装的测试依赖

**接口自动化（用主 Python）**：
```bash
"D:\software\Python 3.10.11\python.exe" -m pip install allure-pytest requests pytest
```

**UI 自动化（已装在 `D:\software\Playwright\venv`，不用再装）**：
```bash
# 验证装好没
"D:\software\Playwright\venv\Scripts\python.exe" -c "from playwright.sync_api import sync_playwright; print('OK')"
# 跑用例
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui/ -v
```

第 02、03 篇会分别讲 Allure 命令行和 Chromium 浏览器怎么装（国内下载慢，教程给了镜像地址）。

> **注意两套 Python**：接口 pytest 用主 Python（3.10.11），Playwright UI 用 `D:\software\Playwright\venv` 里的那套。别混用，混用就会出现 `ModuleNotFoundError`。

---

## 3. 简历里的数字，这套教程怎么落地（重要）

先把口径统一，做完每一步都对得上，面试官问「这个数怎么来的」你能直接答：

| 简历写法 | 实际口径 | 在哪篇做 |
|---|---|---|
| 共 24 个接口 | 后端源码里 `@router.xxx()` 装饰器数：健康检查(1)、登录注册(4)、智能体(3)、会话(5)、定时任务(4)、交付物(1)、管理后台(6) = 24。**Postman 集合里是 25 个请求**——多拆了一个 admin 登录（因为要同时拿 tester 和 admin 两套 token） | 01 |
| 88 条接口用例 | 24 个接口 × 3 层断言（状态码 + 业务码 + 字段） + 越权/注入/边界，用 pytest+Requests 写的 | 00、02 |
| 7 条 UI 用例 | 登录页渲染、登录跳转、Chat 对话流、定时任务页、个人设置、普通用户被 admin 拦截、admin 管理端 | 03 |
| 3 类场景压测 | 混合链路（登录→agents→sessions→send→sessions→automations）× 并发数循环 | 04 |
| 9 个缺陷，P0×1/P1×6/P2×2 | `docs/缺陷报告.md` 里 9 条（含 BUG-009 admin 删除用户漏了存在性校验），修复后全部回归通过；**用禅道 + Jira + 飞书多维表格三种工具管理** | 05 |
| 接入 GitHub Actions | 88 条接口 + 7 条 UI 进 CI 自动跑 | 06 |

> 面试时如果问"用例总数多少"，照实说：**136 条用例（85 接口 + 51 功能/UI），88 条接口自动化进 CI，UI 7 条也能跑，功能用例手工执行记在用例表**。

---

## 4. 全部做完的验收清单

- [ ] `curl /health` 返回 ok，登录页能进
- [ ] Postman 集合 25 个请求（后端 24 接口，多拆一个 admin 登录）按顺序跑，三层断言全绿；Newman 能跑出 `report.html`
- [ ] `pytest tests/api -v` 跑通，能数出约 88 条用例
- [ ] `allure-results/` 有数据，能打开 Allure 报告看到通过率
- [ ] `pytest tests/ui -v` 7 条通过，`docs/screenshots/` 有截图
- [ ] JMeter 三轮 `.jtl` + HTML 报告都在 `software test/jmeter/results/`
- [ ] `docs/缺陷报告.md` 里 9 条缺陷（含 BUG-009）都有编号、根因和回归记录；禅道本地版 + Jira 免费版（Project Key AHUB）+ 飞书多维表格 Base 三端都建好了缺陷管理
- [ ] push 后 GitHub Actions 是绿灯，能下载 artifact
- [ ] 第 07 篇的 20 个问题，每个都能讲 30 秒

---

## 5. 常见坑（先看一眼能省半小时）

1. **后端起不来**：MySQL 3307 没起或 Redis 卡住时，`/health` 会一直转。先按 00 篇第 1 章做降级启动（`DB_FALLBACK_SQLITE=1`），能跑业务接口就行。
2. **401 一片红**：脚本没带 Token，或者 `start.bat` 之后又手动重启过后端导致种子账号被重建。先跑登录请求拿新 token。
3. **路径带空格**：`software test` 目录有空格，命令行里一定要用引号包住路径。
4. **编辑器占着文档**：用 Word/WPS 打开 `docs/*.md` 时，脚本回写可能不生效，先关掉再跑。
5. **别一边改脚本一边跑**：每改一处就跑一次 `pytest -q`，一次改一堆出问题不好定位。

