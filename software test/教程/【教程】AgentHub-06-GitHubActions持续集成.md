# 灵枢 AgentHub · GitHub Actions 持续集成教程

> 配套文件：`.github/workflows/ci.yml`（现成配置）、`pytest.ini`、`agent-core/requirements.txt`
> 适用对象：第一次把自动化测试接到 CI 的同学
> 仓库：本地 Git 仓库（push 到 GitHub 就自动跑）

---

## 第 1 章 先搞清楚：CI 干嘛的

每次 push 代码到 GitHub，Actions **自动**帮你：
1. 拉最新代码 → 装 Python 3.10 + npm 依赖
2. **降级启动后端**（SQLite + mock，不依赖本地 MySQL/Redis/DeepSeek）
3. **起前端 Vite dev server**（5173 端口，供 Playwright UI 测试访问）
4. 跑 **pytest 接口自动化 88 条** + **Playwright UI 自动化 7 条**
5. 合并生成 **Allure HTML 报告**（接口 + UI 一份）
6. 上传报告到 GitHub Artifacts，浏览器直接下载看
7. 全绿 = 通过；有红的 = 失败，点 step 看报错日志

**你不用手动跑任何命令**，push 完去 GitHub Actions 页面看结果就行。

### 完整流水线链路图

```
push 到 main/master → GitHub Actions 自动触发
│
├─ Setup Python 3.10 + pip install pytest/allure-pytest
├─ Install Playwright + Chromium
├─ npm ci 前端依赖 + npm run dev 起前端 (5173)
│
├─ Start backend (SQLite + mock, :8000)
│   └─ nohup 后台启动 + 最多等 120 秒健康检查
│
├─ ✅ pytest tests/api → 88 条 → allure-results/
├─ ✅ pytest tests/ui  → 7 条 → allure-ui-results/
│
├─ allure generate 两份原材料 → allure-report/ (HTML 成品)
└─ 上传 Artifacts → 浏览器下载 allure-report/index.html
```

---

## 第 2 章 现成 ci.yml 逐行解读

`.github/workflows/ci.yml` 一共 **8 个 step**，和磁盘上实际文件 100% 对齐：

```yaml
name: AgentHub CI

on:
  push:
    branches: [main, master]           # push 到 main/master 自动触发
  pull_request:                        # PR 到 main/master 也触发
    branches: [main, master]
  workflow_dispatch:                   # 手动触发（GitHub Actions 页面点 Run workflow）

jobs:
  test:
    runs-on: ubuntu-latest             # GitHub 提供的 Ubuntu 虚拟机
    timeout-minutes: 30                # 超时就终止，避免卡太久
    env:
      AGENT_MODE: mock                 # 大模型走 mock，不调真实 DeepSeek
      DB_FALLBACK_SQLITE: "1"           # 数据库自动降级 SQLite（不用装 MySQL）
      API_PORT: "8000"
      BASE_URL: "http://127.0.0.1:8000"
```

### Step 1 ~ 2：Python 环境 + 依赖

```yaml
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"       # ← 和本地主 Python 版本一致（D:\software\Python 3.10.11）
          cache: pip

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r agent-core/requirements.txt
          python -m pip install pytest requests allure-pytest
```

### Step 3：Playwright + Chromium

```yaml
      - name: Install Playwright + Chromium
        run: |
          python -m pip install playwright
          python -m playwright install chromium
```

> 本地你用的是 `D:\software\Playwright\venv`，但 CI 里是全新 Ubuntu 环境，所以从头装 Playwright 包 + Chromium 浏览器。

### Step 4：起后端（降级模式）

```yaml
      - name: Start backend (SQLite + mock)
        run: |
          cd agent-core
          nohup python run_server.py > service.log 2>&1 &
          echo "PID=$!"
          for i in $(seq 1 60); do
            if curl -fsS http://127.0.0.1:8000/health > /tmp/health.json 2>/dev/null; then
              echo "✅ backend ready after ${i}x2 seconds"
              cat /tmp/health.json
              exit 0
            fi
            sleep 2
          done
          echo "❌ backend failed to start"
          cat service.log
          exit 1
```

> 关键设计：`DB_FALLBACK_SQLITE=1` + `AGENT_MODE=mock` → 不依赖 MySQL/Redis/DeepSeek，CI 环境里后端照样能跑通全部业务接口。

### Step 5：起前端（Vite dev server）

```yaml
      - name: Install frontend deps + start dev server
        run: |
          cd frontend
          npm ci --registry=https://registry.npmmirror.com
          nohup npm run dev > /tmp/frontend.log 2>&1 &
          for i in $(seq 1 30); do
            if curl -fsS http://127.0.0.1:5173 > /dev/null 2>&1; then
              echo "✅ frontend ready after ${i}x2 seconds"
              exit 0
            fi
            sleep 2
          done
          echo "❌ frontend failed to start"
          cat /tmp/frontend.log
          exit 1
```

> 本地你用 `npm run dev` 起 5173，CI 里一模一样。Playwright UI 测试需要前端在 5173 端口才能访问页面。

### Step 6：跑接口自动化（88 条）

```yaml
      - name: Run API automation (88 cases)
        run: python -m pytest tests/api -v --alluredir=allure-results -p no:cacheprovider
```

> **在仓库根跑！** `pytest.ini` 的 `testpaths` 是相对路径 `tests/api`，从根跑才能正确解析 conftest.py。

### Step 7：跑 UI 自动化（7 条）

```yaml
      - name: Run UI automation (7 cases)
        env:
          PLAYWRIGHT_BROWSERS_PATH: ""
        run: python -m pytest tests/ui -v --alluredir=allure-ui-results -p no:cacheprovider
```

> 本地你要设 `PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers`，但 CI 里 Chromium 装在默认位置，所以设空字符串让 Playwright 用默认路径。

### Step 8 ~ 9：Allure 报告 + 上传产物

```yaml
      - name: Generate Allure report
        run: |
          npm install -g allure-commandline --registry=https://registry.npmmirror.com
          allure generate allure-results allure-ui-results -o allure-report --clean
          echo "Allure report generated ✓"

      - name: Upload Allure report + screenshots
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: agenthub-allure-report
          path: |
            allure-report/
            docs/screenshots/
            agent-core/service.log
            /tmp/frontend.log
          if-no-files-found: warn
```

> 两份原材料 → `allure generate` 合并成一份 HTML 成品 → 上传。点 Artifacts 就能下载整个 `allure-report/` 目录，浏览器打开 `index.html` 看报告（⚠️ 不能双击，要 HTTP 服务——看教程 03 第 6.4 节）。

---

## 第 3 章 跑起来

### 3.1 本地先提交到 Git

```cmd
cd D:\nexus-agent
git add .
git commit -m "init: add CI workflow"
```

### 3.2 配远程仓库

去 GitHub 建一个空仓库（比如 `lingshu-agenthub-test`），然后：

```cmd
git remote add origin https://github.com/你的用户名/lingshu-agenthub-test.git
git branch -M main
git push -u origin main
```

### 3.3 看结果

push 完打开 GitHub 仓库页面 → 点 **Actions** 标签 → 能看到一个正在跑的流水线，点进去能看到每一步的输出日志。

全绿 = 通过；有红的点那个 step 看报错。

### 3.4 下载 Allure 报告

流水线跑完（全绿或有红都行）→ 页面右上角找 **Artifacts** → 点 `agenthub-allure-report` 下载 zip → 解压后用 Allure CLI 或 Python HTTP 服务打开：

```cmd
# 方式 A（推荐）
allure.cmd open allure-report

# 方式 B（Allure CLI 没装时）
cd allure-report
"D:\software\Python 3.10.11\python.exe" -m http.server 8080
# 然后浏览器打开 http://127.0.0.1:8080
```

---

## 第 4 章 面试回答模板

**Q1：CI 里后端怎么启动的？没有 MySQL 怎么办？**

> 用降级模式。设了两个环境变量：`DB_FALLBACK_SQLITE=1` 让数据库自动走 SQLite（文件型，不用装），`AGENT_MODE=mock` 让大模型调用走 mock 返回固定结果，不调真实 DeepSeek API。后端代码里写了降级逻辑——连不上 MySQL 就自动切 SQLite，初始化时读 `AGENT_MODE=mock` 就跳过真实 API 调用。所以 CI 环境里不需要装 MySQL、Redis，后端照样能跑通全部 24 个接口。

**Q2：Pytest 和 Playwright 在 CI 里怎么跑的？**

> 先后台起两个服务：后端用 `nohup python run_server.py &` 放后台，循环最多等 120 秒测 `/health` 端点；前端用 `npm run dev` 放后台等 5173 端口就绪。然后先后跑 pytest 接口 88 条 + pytest UI 7 条，两份结果分别生成 `allure-results/` 和 `allure-ui-results/`，最后用 `allure generate` 合并成一份 HTML 报告上传 Artifacts。

**Q3：为什么用例数量是 88？和 24 个接口什么关系？**

> 24 是后端路由注册的接口总数（3 个 router 文件的 `@router.xxx()` 装饰器数），88 是 pytest 写的测试用例数——一个接口会写多条用例：正常路径 + 参数边界 + 权限校验 + 异常场景。比如登录接口就写了 11 条：正常登录、空用户名、空密码、错误密码、不存在用户、验证码过期、token 格式不对、普通用户 vs admin 权限差异、登录后 token 续期、登录状态下重复登录、登出再登录。

**Q4：Playwright 为什么不用 pytest-playwright 插件？**

> 一开始试过，pytest-playwright 的 browser fixture 虽然省事，但和我们手写的 scope=session 共享 browser + 每条新 context 的 fixture 架构冲突了——插件默认每条用例新起浏览器，7 条用例开 7 个浏览器太慢。我们手写 fixture 控制 browser scope=session（7 条共用一个浏览器）+ page fixture 默认 function scope（每条新 context 自动清 cookie），既快又隔离。所以 CI 里直接跑 `pytest tests/ui/` 加 `alluredir` 参数就行，不用插件。

**Q5：CI 里 Allure 报告怎么生成的？为什么要合并两份？**

> pytest 接口 88 条跑 `--alluredir=allure-results` 出原材料 JSON，UI 7 条跑 `--alluredir=allure-ui-results` 出另一份 JSON。然后用 `allure generate allure-results allure-ui-results -o allure-report --clean` 把两份原材料合并成一份 HTML——Allure 会自动识别 pytest marker（接口加了 `@pytest.mark.api`、UI 加了 `@pytest.mark.ui`）在左侧菜单分组，浏览器打开一份报告就能同时看接口和 UI 的通过率、截图、耗时。

---

## 第 5 章 本篇产出清单

```
.github/workflows/ci.yml            （现成配置，push 自动跑）
allure-report/index.html            （本地跑 Allure 生成的 HTML 报告）
docs/screenshots/*.png              （Playwright 跑完自动存的截图）
```

### 本地跑完整 CI 流程（模拟 push 触发）

想在本地先试一遍完整流水线？按这个顺序敲：

```cmd
cd /d D:\nexus-agent

rem 1. 起后端（SQLite + mock 降级）
set AGENT_MODE=mock
set DB_FALLBACK_SQLITE=1
start /min cmd /c "cd /d D:\nexus-agent\agent-core && python run_server.py"

rem 2. 起前端
start /min cmd /c "cd /d D:\nexus-agent\frontend && npm run dev"

rem 3. 等两个服务起来（浏览器分别打开 http://127.0.0.1:8000/health 和 :5173 确认）

rem 4. 跑接口 88 条 + UI 7 条
"D:\software\Python 3.10.11\python.exe" -m pytest tests/api --alluredir=allure-results -v
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui --alluredir=allure-ui-results -v

rem 5. 合并 Allure 报告 + 打开
"D:\software\allure.cmd" generate allure-results allure-ui-results -o allure-report --clean
"D:\software\allure.cmd" open allure-report
```
