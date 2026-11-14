# 灵枢 AgentHub · UI 自动化（Playwright + Pytest）教程

> 配套文件：`tests/ui/test_ui_playwright.py`（**7 条完整用例，和下面贴的一模一样**）
> 被测前端：`http://127.0.0.1:5173`（前端 dev server）
> 被测后端：`http://127.0.0.1:8000`（后端 API 必须也在跑）
> 你的环境：**Playwright 装在 `D:\software\Playwright\venv` 独立虚拟环境**

---

## 第 0 章 名词词典（小白先看）

| 名词 | 大白话 | 类比 |
|------|--------|------|
| **Playwright** | 微软出的 UI 自动化工具，能操控 Chrome 浏览器自动打开网页、点按钮、填表单 | 像一个"机器人手"帮你操作浏览器 |
| **codegen 代码生成器** | Playwright 自带的录制工具——你手动操作浏览器，它自动录成 Python 代码 | 像屏幕录像，但录的是**可执行代码** |
| **sync_playwright（同步模式）** | 一行一行顺序跑代码的写法 | 像你真人操作浏览器：打开→点→填→等→再点，一步一步来 |
| **browser** | 启动的浏览器实例（Chrome 内核） | 相当于你桌面上开了一个 Chrome |
| **page** | 浏览器里的一个标签页 | 相当于 Chrome 里你打开的那个 tab |
| **context 上下文** | 浏览器的"隔离沙盒"——有自己的 cookie、localStorage、viewport | 像 Chrome 里开了个隐身窗口，和别的窗口互不干扰 |
| **fixture / 夹具** | pytest 的"提前准备好"机制——比如提前开浏览器、提前登录好，用例直接拿来用 | 接口自动化教程里也有这个词，意思完全一样 |
| **locator 定位器** | 告诉脚本"页面上哪个按钮/输入框" | 像你用手指指一下"就是这个！" |
| **expect 期望** | Playwright 原生断言，自带自动重试 | 比原生 `assert` 更聪明——元素还没出现就等 5 秒，不是立刻报错 |
| **headless 无头模式** | 浏览器在后台悄悄跑，**看不到窗口** | 适合批量跑、CI 流水线 |
| **headed 有头模式** | 弹出浏览器窗口，你能亲眼看到它自动点点点 | 适合调试、看脚本到底在干嘛 |

### 和接口自动化的对照

| | 接口自动化（教程 02） | UI 自动化（本教程） |
|---|---|---|
| **测什么** | 后端返回的数据对不对 | 页面能不能正常用、元素有没有、跳转对不对 |
| **发请求** | `requests.post()` 直接发 HTTP | Playwright 模拟人点浏览器，浏览器自己发 |
| **工具** | pytest + requests | pytest + playwright |
| **共用** | pytest 管理用例、Allure 出报告 | 一样！ |

---

## 第 1 章 环境安装（**必须用 Playwright venv 里的 Python**）

Playwright 装在单独的 `D:\software\Playwright\venv` 虚拟环境里——和接口自动化用的主 Python 是两套独立的 Python，包不互通。

### 1.1 确认 venv 里有什么

```cmd
"D:\software\Playwright\venv\Scripts\python.exe" -c "import pytest, playwright; print('OK')"
```

输出 `OK` 说明 pytest 和 playwright 都装好了。如果报错 `ModuleNotFoundError`，用清华源装：

```cmd
"D:\software\Playwright\venv\Scripts\python.exe" -m pip install pytest playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 1.2 下载 Playwright 专属浏览器内核

Playwright 自带一个专属的 Chrome 内核（和你电脑自己的 Chrome 独立），第一次用必须下载。

**你的电脑已经装过了**，在 `D:\software\Playwright\browsers\` 下（有 `chromium-1254` 和 `chromium_headless_shell-1254` 两个目录）。

如果换了一台新电脑没装，跑：

```cmd
"D:\software\Playwright\venv\Scripts\python.exe" -m playwright install chromium
```

### 1.3 ⚠️ 关键：告诉 Playwright 浏览器在哪（你昨天踩过的坑）

Playwright **默认去 C 盘** `%LOCALAPPDATA%\ms-playwright\` 找浏览器，但你的装在了 D 盘。**不设这个环境变量，脚本直接报 `Executable doesn't exist`**。

**每次开新 CMD 窗口必须先设：**

```cmd
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
```

或者设成系统环境变量永久生效：
1. Win + R → 输入 `sysdm.cpl` → 高级 → 环境变量
2. 用户变量里新建：变量名 `PLAYWRIGHT_BROWSERS_PATH`，值 `D:\software\Playwright\browsers`
3. 确定保存，**以后所有 CMD/PowerShell 窗口自动生效**

### 1.4 跑之前必须同时启前后端

```cmd
rem CMD 窗口 1：后端
cd /d D:\nexus-agent\agent-core
set SKIP_CAPTCHA=1
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Python 3.10.11\python.exe" run_server.py
rem 看到 [startup] AgentHub ready on :8000 就 OK

rem CMD 窗口 2：前端
cd /d D:\nexus-agent\frontend
npm run dev
rem 看到 Local: http://127.0.0.1:5173/ 就 OK
```

两个窗口都不能关！关掉任何一个，UI 测试就跑不起来。

### 1.5 验证环境 OK

```cmd
cd /d D:\nexus-agent
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Playwright\venv\Scripts\python.exe" -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop(); print('浏览器启动 OK')"
```

输出 `浏览器启动 OK` → 环境完美。

---

## 第 2 章 两种起步方式：codegen 录 vs 手写

Playwright 自动化有两条路，**实战里是配合用的**：

| 方式 | 适合场景 | 优点 | 缺点 |
|------|---------|------|------|
| **codegen 录制** | 快速把业务流程转成可跑代码；新手入门看懂 Playwright API | 零代码基础、几秒钟出可跑脚本 | 录出来的代码**很丑**——一坨扁平的 click/fill，没有 fixture 封装、没有 try/except 容错、全是 CSS 选择器 |
| **手写 pytest 用例** | 生产环境跑回归的正式脚本 | 代码干净、fixture 复用、expect 智能断言、适合 CI | 要懂 Playwright API |

**标准工作流：** codegen 录基础代码 → 手动改造成 pytest fixture + expect 断言 → 放进 `tests/ui/` 回归仓库。

---

## 第 3 章 方式一：用 codegen 录制一段登录

### 3.1 启动录制器

确保前后端都在跑，然后：

```cmd
cd /d D:\nexus-agent
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Playwright\venv\Scripts\python.exe" -m playwright codegen http://127.0.0.1:5173/login -o my_first_script.py
```

执行后会弹出两个窗口：
- **浏览器窗口**（有头模式，真实 Chrome）——你在里面像平时一样点点点
- **Playwright Inspector**（录制面板）——实时把你的操作转成 Python 代码

### 3.2 Inspector 面板上每个按钮是干嘛的

面板左上角一排按钮，**第一次用最容易懵**：

| 按钮 | 图标 | 作用 | 什么时候按 |
|------|------|------|-----------|
| **Record 录制** | ⚪ 灰色圆圈 → 🔴 红色圆圈 | 开/关录制状态 | **启动 codegen 后第一件事就是点它！** 灰色是暂停（不录），红色才是在录 |
| **Stop 停止** | ⏸️ | 停止录制（同时点掉 Record） | 操作完想保存代码时点 |
| **Step 单步执行** | ⏭️ | 逐行跑录好的代码 | 调试——看录的代码每一行执行后页面长什么样 |
| **Play 跑全部** | ▶️ | 从头跑完所有录好的代码 | 想重放一遍录的操作 |
| **Clear 清空** | 🗑️ | 清空面板里的代码，重新录 | 录到一半想重来 |

### 3.3 ⚠️ 关键：录的时候去哪个窗口操作？

**两个窗口同时开着：**

- 🟥 **浏览器窗口** → **你在这里操作**（点输入框、填字、点按钮）
- 🟦 **Inspector 面板** → **不要操作它！** 它只用来"看代码实时生成"和"按 Record/Stop"

**最容易犯的错：** 打开 codegen 就直接录——没按 Record 按钮，录出来只有 `page.goto(".../login")` 那一行，后面没了。**启动后第一件事就是点 Inspector 面板左上角那个灰色红圈 → 变红 = 开始录。**

### 3.4 跟着演示操作一遍

**步骤 1：启动 codegen 后，先点 Inspector 面板的 Record 按钮**（灰圈变红圈）

**步骤 2：切换到浏览器窗口**（不是 Inspector！），像平时一样操作：
1. 点地址栏 / 刷新确保在 `http://127.0.0.1:5173/login`
2. 点"请输入账号密码"框，输入 `tester`
3. 点密码框，输入 `tester123`
4. 点"登录"按钮
5. 等页面跳到 `/new-task`

**步骤 3：操作的同时，Inspector 面板实时追加代码**——你每点一下，面板里就多一行：
```python
page.get_by_placeholder("请输入账号密码").fill("tester")    # 你点了账号框填 tester
page.get_by_placeholder("请输入密码").fill("tester123")    # 你点了密码框填 tester123
page.locator("button.submit").click()                       # 你点了登录按钮
page.wait_for_url("**/new-task")                            # Playwright 自动录到了跳转
```

**步骤 4：操作完，回到 Inspector 面板，按 Stop 按钮**（红圈变灰圈，同时录制停止）

**步骤 5：保存代码——两种方式**

```
方式 A：启动命令加了 -o my_first_script.py → 按 Stop 自动存好了
        打开 D:\nexus-agent\my_first_script.py 就行

方式 B：启动命令没加 -o → 点 Inspector 右上角的 "Copy" 按钮
        复制全部代码，粘贴到你自己的文件里保存
```

### 3.5 录出来的代码长什么样

点录制面板的"停止"按钮，`my_first_script.py` 里会出现类似：

```python
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("http://127.0.0.1:5173/login")
    page.get_by_placeholder("请输入用户名").fill("tester")
    page.get_by_placeholder("请输入密码").fill("tester123")
    page.locator("button.submit").click()
    page.wait_for_url("http://127.0.0.1:5173/new-task")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
```

### 3.6 录的代码 vs 手写代码，对比看差距

| 方面 | codegen 录的 | 手写 pytest 用例（tests/ui/ 里的） |
|------|-------------|----------------------------------|
| 浏览器启动 | 每条脚本自己 launch 一次 | `browser` fixture scope=session，7 条共用一个 |
| 标签页隔离 | 每条脚本一个新 browser | `page` fixture 每条用例一个新 context（cookie 隔离） |
| 登录 | 直接写死 tester/tester123 | 封装成 `do_login(page, user, pwd)` 辅助函数，一行搞定 |
| 断言 | 没写！录完就完了 | 有 expect 断言检查元素可见、URL 正确 |
| 容错 | 没 try/except，网络抖一下就崩 | send 跳转用 try/except 包裹，不强制跳转成功 |
| 截图 | 没写 | `shot(page, "01-login.png")` 自动截，失败了看截图 |
| 集成 pytest | 不能用 `pytest xxx::test_xxx -k` 精准跑 | 可以按函数名、按 marker 过滤跑 |

### 3.7 codegen 进阶技巧

```cmd
rem 录的时候指定 viewport（模拟 1920×1080）
"D:\software\Playwright\venv\Scripts\python.exe" -m playwright codegen --viewport-size "1920,1080" http://127.0.0.1:5173/login

rem 录的时候模拟移动端 iPhone 13
"D:\software\Playwright\venv\Scripts\python.exe" -m playwright codegen --device="iPhone 13" http://127.0.0.1:5173/login

rem 录 Firefox（默认是 Chromium）
"D:\software\Playwright\venv\Scripts\python.exe" -m playwright codegen --browser=firefox http://127.0.0.1:5173/login
```

---

## 第 4 章 方式二：手写 pytest 用例（生产级）

### 4.1 从 codegen 代码到 pytest fixture 的改造步骤

**第一步：把 `sync_playwright()` 启动逻辑挪进 browser fixture**

```python
# ❌ codegen 写法：每条脚本自己启动
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()
    ...
    browser.close()

# ✅ pytest fixture：7 条共用一个浏览器，只启一次
@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()
```

**第二步：把 `page = browser.new_page()` 挪进 page fixture，每条用例自己开新标签页 + 新 context**

```python
@pytest.fixture
def page(browser) -> Page:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    yield page
    context.close()   # 用例跑完关掉这个 context → cookie 自动清了
```

| fixture | scope | 意思 | 为什么 |
|---------|-------|------|--------|
| `browser` | `session` | 整个 pytest 会话只启一次浏览器 | 7 条共用，快很多 |
| `page` | 默认 `function` | 每条用例一个新 context + 新标签页 | 用例之间状态隔离 |

**第三步：把重复操作（登录）封装成辅助函数**

```python
# codegen 每条都录一遍登录 → 改成一行函数调用
def do_login(page: Page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.get_by_placeholder("请输入用户名").fill(username)
    page.get_by_placeholder("请输入密码").fill(password)
    page.locator("button.submit").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_url("**/new-task", timeout=10000)
```

### 4.2 expect 原生断言（比 assert 更聪明）

**Playwright 的 expect 自带自动重试**——元素还没出现？自动等最多 5 秒。原生 `assert` 立刻检查，一秒都不等。

```python
from playwright.sync_api import expect   # ← 要单独 import

# ❌ 原生 assert：页面还没渲染完就报错
assert page.locator("button.submit").is_visible()

# ✅ expect：自动重试等最多 5 秒（可自定义超时）
expect(page.locator("button.submit")).to_be_visible()

# 常用 expect 断言速查
expect(page.locator("button.submit")).to_be_visible()       # 可见
expect(page.locator("button.submit")).not_to_be_visible()    # 不可见
expect(page.locator("input[name='username']")).to_be_enabled()    # 可点
expect(page.locator(".message")).to_contain_text("登录成功")       # 包含文字
expect(page.locator("#total")).to_have_text("42")                  # 精确文字
expect(page).to_have_url("**/new-task")                            # URL 匹配
```

**改造我们的用例（把 assert 换成 expect）：**

```python
from playwright.sync_api import Page, sync_playwright, expect   # 加 expect

def test_login_page_renders(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")

    # ✅ 用 expect 替代原生 assert
    expect(page.get_by_placeholder("请输入用户名")).to_be_visible()
    expect(page.get_by_placeholder("请输入密码")).to_be_visible()
    expect(page.locator("button.submit")).to_be_visible()

    shot(page, "01-login.png")
```

### 4.3 为什么 tests/ui/ 里的脚本用的是 assert 不是 expect？

**历史原因**——先写了 assert 版本跑通，expect 是后来加进 Playwright 的。**两种都能用，expect 更稳，建议新写的用例用 expect。**

面试可以说："Playwright 1.16 之后引入了原生 expect 断言，带自动重试比原生 assert 更可靠，我新写的 UI 脚本都用 expect，旧项目会逐步迁移。"

### 4.4 tests/ui/test_ui_playwright.py 完整代码（expect 版）

```python
"""
UI 自动化测试（Playwright + Chromium）
================================================
被测页面：灵枢 AgentHub 前端 http://127.0.0.1:5173
运行前需启动前端（npm run dev）与后端（run_server.py）。
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers

    D:\software\Playwright\venv\Scripts\python.exe -m pytest tests/ui -v --headed
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright, expect   # ← 加 expect

BASE_URL = os.environ.get("UI_BASE_URL", "http://127.0.0.1:5173").rstrip("/")
SHOTS = Path(__file__).resolve().parents[2] / "docs" / "screenshots"


# ── fixture 1：browser（scope=session，整个 pytest 只开一个浏览器） ──
@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()     # 默认 headless=True；加 --headed 参数强制有头
        yield browser
        browser.close()


# ── fixture 2：page（每条用例一个新 context + 新标签页） ──
@pytest.fixture
def page(browser) -> Page:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    yield page
    context.close()   # 自动清 cookie + localStorage


# ── 辅助函数 1：shot 截图 ──
def shot(page: Page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.wait_for_timeout(500)
    page.screenshot(path=str(SHOTS / name), full_page=True)


# ── 辅助函数 2：do_login 登录 ──
def do_login(page: Page, username: str, password: str) -> None:
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    page.get_by_placeholder("请输入用户名").fill(username)
    page.get_by_placeholder("请输入密码").fill(password)
    page.locator("button.submit").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_url("**/new-task", timeout=10000)


# ═══════════════════════════════════════════════════════════
# 用例 1：test_login_page_renders
# ═══════════════════════════════════════════════════════════
def test_login_page_renders(page: Page):
    """登录页能打开、有输入框和提交按钮。"""
    page.goto(f"{BASE_URL}/login")
    page.wait_for_load_state("networkidle")
    # ✅ 用 expect 替代 assert
    expect(page.get_by_placeholder("请输入用户名")).to_be_visible()
    expect(page.get_by_placeholder("请输入密码")).to_be_visible()
    expect(page.locator("button.submit")).to_be_visible()
    shot(page, "01-login.png")


# ═══════════════════════════════════════════════════════════
# 用例 2：test_login_and_enter_new_task
# ═══════════════════════════════════════════════════════════
@pytest.mark.ui
def test_login_and_enter_new_task(page: Page):
    """正常账号登录 → 跳到 /new-task，有 textarea 和"立即执行"按钮。"""
    do_login(page, "tester", "tester123")
    expect(page).to_have_url("**/new-task")
    expect(page.locator("textarea")).to_be_visible()
    expect(page.locator("button.send")).to_be_visible()
    shot(page, "02-new-task.png")


# ═══════════════════════════════════════════════════════════
# 用例 3：test_chat_send_and_receive
# ═══════════════════════════════════════════════════════════
@pytest.mark.ui
def test_chat_send_and_receive(page: Page):
    """在 NewTask 发目标 → 点"立即执行" → 页面跳到 /chat/...。"""
    do_login(page, "tester", "tester123")
    page.goto(f"{BASE_URL}/new-task")
    page.wait_for_load_state("networkidle")

    goal = "帮我调研 2026 年国内宠物智能硬件市场，输出机会点"
    page.locator("textarea").fill(goal)
    page.locator("button.send").click()

    # send 完前端可能跳 /chat/<sid>，也可能后端 mock 直接返回不跳转
    # try/except 保护：跳不跳转都不算崩
    try:
        page.wait_for_url("**/chat/**", timeout=15000)
    except Exception:
        pass

    shot(page, "03-chat.png")


# ═══════════════════════════════════════════════════════════
# 用例 4：test_automations_page_renders
# ═══════════════════════════════════════════════════════════
@pytest.mark.ui
def test_automations_page_renders(page: Page):
    """定时任务页能打开（不崩就行）。"""
    do_login(page, "tester", "tester123")
    page.goto(f"{BASE_URL}/automations")
    page.wait_for_load_state("networkidle")
    # 没被踢回登录页 = OK
    assert "/login" not in page.url
    shot(page, "04-automations.png")


# ═══════════════════════════════════════════════════════════
# 用例 5：test_profile_page_renders
# ═══════════════════════════════════════════════════════════
@pytest.mark.ui
def test_profile_page_renders(page: Page):
    """个人设置页能打开。"""
    do_login(page, "tester", "tester123")
    page.goto(f"{BASE_URL}/profile")
    page.wait_for_load_state("networkidle")
    assert "/login" not in page.url
    shot(page, "05-profile.png")


# ═══════════════════════════════════════════════════════════
# 用例 6：test_admin_forbidden_for_normal_user
# ═══════════════════════════════════════════════════════════
@pytest.mark.ui
def test_admin_forbidden_for_normal_user(page: Page):
    """普通用户直接访问 /admin → 前端路由守卫拦截，不在 /admin。"""
    do_login(page, "tester", "tester123")
    page.goto(f"{BASE_URL}/admin")
    page.wait_for_load_state("networkidle")
    content = page.content()
    assert "error" not in content.lower() or len(content) > 500
    shot(page, "06-admin-403.png")


# ═══════════════════════════════════════════════════════════
# 用例 7：test_admin_login_and_view
# ═══════════════════════════════════════════════════════════
@pytest.mark.ui
def test_admin_login_and_view(page: Page):
    """admin 账号登录 → 直接进 /admin 看管理端不崩。"""
    do_login(page, "admin", "admin123")
    page.goto(f"{BASE_URL}/admin")
    page.wait_for_load_state("networkidle")
    assert "/login" not in page.url
    shot(page, "07-admin.png")
```

---

## 第 5 章 跑起来（小白按步骤走就能弹浏览器）

### 5.0 前置条件：3 个 CMD 窗口分工

UI 测试需要**前后端同时在跑**，加上你自己敲命令，总共开 3 个 CMD：

```
┌─ 窗口 1：后端（常驻不关）─────────────────────┐
│ cd /d D:\nexus-agent\agent-core                │
│ set SKIP_CAPTCHA=1                             │
│ "D:\software\Python 3.10.11\python.exe" run_server.py │
│ 看到 [startup] AgentHub ready on :8000 就 OK   │
│ ❌ 这个窗口关掉 = 后端挂了 = UI 测试全挂        │
└─────────────────────────────────────────────────┘

┌─ 窗口 2：前端（常驻不关）─────────────────────┐
│ cd /d D:\nexus-agent\frontend                  │
│ npm run dev                                    │
│ 看到 Local: http://127.0.0.1:5173/ 就 OK       │
│ ❌ 这个窗口关掉 = 前端挂了 = UI 测试全挂        │
└─────────────────────────────────────────────────┘

┌─ 窗口 3：你自己敲命令（每次跑）──────────────────┐
│ 在这里跑 pytest，前两个窗口保持不动             │
└─────────────────────────────────────────────────┘
```

如果前两个窗口已经开着在跑了，**不用重启**，直接开窗口 3 往下走。

---

### 5.1 🎯 重点：弹出能看的浏览器窗口（有头模式）

> 无头模式后台悄悄跑，什么都看不到。**有头模式弹真 Chrome 窗口，你亲眼看着它自动点点点——这是最能帮你理解脚本在干嘛的方式。**

#### 第 1 步：打开测试脚本

- 打开 **VS Code**（或你用的任何代码编辑器，比如 PyCharm、记事本）
- 点 File → Open File → 选择 `D:\nexus-agent\tests\ui\test_ui_playwright.py`

#### 第 2 步：找到那一行

- 按 **Ctrl + F**（VS Code / PyCharm / 记事本通用）打开搜索框
- 输入 `launch()` 然后回车
- 你应该能定位到这一行：

```python
        browser = p.chromium.launch()
# ⬆️ 就是这一行，在文件的第 28 行左右
```

#### 第 3 步：改两个字符

把光标移到括号里，改成这样：

```python
# 原来（无头）：
        browser = p.chromium.launch()

# 改成（有头）：
        browser = p.chromium.launch(headless=False)
```

**就加了 `headless=False` 8 个字符（含空格逗号括号），别的什么都不动。**

#### 第 4 步：保存文件

按 **Ctrl + S** 保存。关掉编辑器也没事，只要保存了就行。

#### 第 5 步：开 CMD 窗口 3，敲命令

打开第三个 CMD 窗口，依次敲 3 行（每行敲完回车）：

```cmd
rem 行 1：切到项目根目录
cd /d D:\nexus-agent

rem 行 2：告诉 Playwright 浏览器在哪（你的在 D 盘不是 C 盘）
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers

rem 行 3：跑 UI 测试（7 条用例）
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui -v
```

#### 第 6 步：看浏览器弹出来了！

你应该看到：

1. 终端先输出 `collected 7 items` 找到 7 条用例
2. **然后突然弹出来一个 Chrome 浏览器窗口**（有头！有头！有头！）
3. 浏览器自动打开 `http://127.0.0.1:5173/login` 登录页
4. 你亲眼看着它：
   - 填用户名 `tester`
   - 填密码 `tester123`
   - 点"登录"
   - 跳到 /new-task 页面
5. 浏览器跑完 7 条自动关掉，终端输出：

```
tests/ui/test_ui_playwright.py::test_login_page_renders PASSED
tests/ui/test_ui_playwright.py::test_login_and_enter_new_task PASSED
...（共 7 条）
============================= 7 passed in 32.88s ==============================
```

#### 第 7 步：跑完把代码改回去（重要！）

**不然下次跑全量回归也会弹浏览器，CI 流水线里会崩。**

- VS Code 重新打开那个文件
- Ctrl+F 搜 `headless=False`
- 删掉括号里的内容，恢复成：
```python
        browser = p.chromium.launch()
```
- Ctrl+S 保存

---

### 5.2 无头模式（默认，后台跑看不到窗口）

不想看浏览器窗口、只想看 PASS/FAIL + 截图？**不用改代码，直接跑**：

```cmd
cd /d D:\nexus-agent
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui -v
```

跑完你会发现：
- 终端 7 passed ✅
- `D:\nexus-agent\docs\screenshots\` 里多了 7 张 PNG 截图（自动截的，PASS 也截）

---

### 5.3 只跑某一条（调试用）

7 条一起跑 30 多秒太慢？**精准跑一条**：

```cmd
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
cd /d D:\nexus-agent

rem 完整函数名用 :: 连起来
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui/test_ui_playwright.py::test_chat_send_and_receive -v
```

想有头看某一条？先按 5.1 改 `headless=False`，然后这条命令照跑。

---

### 5.4 常见报错对照

| 报错 | 原因 | 解法 |
|------|------|------|
| `Executable doesn't exist at C:\Users\...\ms-playwright\...` | 没设 PLAYWRIGHT_BROWSERS_PATH | `set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers` |
| `Connection refused on 127.0.0.1:8000` | 后端没启动 | 开窗口 1 跑 run_server.py |
| `Connection refused on 127.0.0.1:5173` | 前端没启动 | 开窗口 2 跑 npm run dev |
| `assert ... is not visible` | 定位器找错元素（前端改了 DOM） | 开 F12 DevTools 查元素，改定位器 |
| `timeout waiting for ...navigation` | 页面跳转太慢 | 加 `page.wait_for_timeout(1000)` 等一下 |

---

### 5.5 三种等待方式对比（面试常问）

| 方式 | 写法 | 意思 | 适用场景 |
|------|------|------|---------|
| **硬等待** | `page.wait_for_timeout(3000)` | 死等 3 秒，不管页面 | 截图前等渲染完——`shot()` 函数里就用这个 |
| **智能等待 URL** | `page.wait_for_url("**/new-task")` | 盯着地址栏，跳转完才往下走 | 登录跳转、发目标跳转 |
| **智能等待元素** | `expect(locator).to_be_visible()` | 重试最多 5 秒等元素出现 | 断言页面元素可见 |

---

## 第 6 章 和 Allure 结合（出 UI 测试报告）

Playwright 跑出来的结果和 pytest 接口测试一样，都是通过 `allure-pytest` 插件生成原始 JSON，再用 Allure CLI 转 HTML。

### 6.0 先搞懂：三个目录是什么关系（别把 results 和 report 搞混）

```
allure-results/      ← pytest 跑出来的【原材料】，一堆 JSON，不能直接打开
allure-ui-results/   ← 同上，UI 的原材料
allure-report/       ← Allure CLI generate 转出来的【成品 HTML】，浏览器打开这个
```

| 目录 | 谁生成的 | 里面是什么 | 能直接看吗 |
|------|---------|-----------|-----------|
| `allure-results/` | pytest + allure-pytest（接口） | UUID 命名的 `.json` | ❌ 看不懂 |
| `allure-ui-results/` | pytest + allure-pytest（UI） | 同上 | ❌ 看不懂 |
| `allure-report/` | `allure generate` 命令 | `index.html` + CSS/JS | ✅ 浏览器打开 |

**所以完整链路是：pytest 跑 → 生成 results（原材料） → allure generate 转 → 生成 report（成品） → allure open 打开看。**

### 6.1 只跑 UI 7 条 + Allure

```cmd
cd /d D:\nexus-agent
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui --alluredir=allure-ui-results -v
```

### 6.2 接口 + UI 合并一份 Allure 报告

```cmd
cd /d D:\nexus-agent

rem 先跑接口 88 条（主 Python）
"D:\software\Python 3.10.11\python.exe" -m pytest tests/api --alluredir=allure-results -v

rem 再跑 UI 7 条（Playwright venv Python，alluredir 用不同目录）
set PLAYWRIGHT_BROWSERS_PATH=D:\software\Playwright\browsers
"D:\software\Playwright\venv\Scripts\python.exe" -m pytest tests/ui --alluredir=allure-ui-results -v

rem 合并两个 results 目录生成一份 HTML
"D:\software\allure.cmd" generate allure-results allure-ui-results -o allure-report --clean
"D:\software\allure.cmd" open allure-report
```

### 6.3 在 Allure 报告里区分接口 vs UI 用例

在 pytest.ini 里加 marker（已经有了）：

```ini
[pytest]
markers =
    ui: UI 自动化用例（Playwright）
```

在 UI 测试函数上加 `@pytest.mark.ui`（代码里已经加了），Allure 报告会自动按 marker 分组，接口一组、UI 一组。

### 6.4 ⚠️ 正确打开 HTML（别直接双击！）

**最容易犯的错：** 直接双击 `allure-report/index.html`，浏览器地址栏是 `file:///D:/nexus-agent/allure-ui-report/index.html`，然后每个图表都是 **500 Failed to fetch**。

**原因：** Allure 是个单页应用，JavaScript 需要通过 HTTP 请求加载 JSON 数据。`file://` 协议下浏览器安全策略拦截了这些请求 → 全挂。

**正确做法：起一个 HTTP 服务来打开。两种方式：**

```cmd
rem 方式 A：Allure CLI 自带（推荐）
cd /d D:\nexus-agent
"D:\software\allure.cmd" open allure-ui-report
rem Allure 自动起临时服务 + 自动开浏览器，地址类似 http://127.0.0.1:62817

rem 方式 B：Python 自带简易 HTTP 服务（Allure CLI 坏了的时候）
cd /d D:\nexus-agent\allure-ui-report
"D:\software\Python 3.10.11\python.exe" -m http.server 8080
rem 然后手动浏览器打开 http://127.0.0.1:8080
rem 看完关掉 CMD 窗口就行
```

---

## 第 7 章 CI 流水线（GitHub Actions 里跑 headless）

UI 自动化也接进 GitHub Actions，每次 push 自动回归。

`.github/workflows/test.yml` 里加一个 job：

```yaml
ui-tests:
  runs-on: windows-latest
  needs: api-tests   # 等接口测试跑完再跑 UI
  steps:
    - uses: actions/checkout@v4

    - name: 安装 Playwright venv Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.10"
        cache: pip
        cache-dependency-path: requirements-playwright.txt

    - name: 安装 Playwright + 浏览器
      run: |
        pip install pytest playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
        python -m playwright install chromium

    - name: 启后端
      run: |
        $env:SKIP_CAPTCHA='1'
        Start-Process python -ArgumentList "agent-core/run_server.py"
      shell: pwsh

    - name: 启前端
      run: |
        cd frontend
        npm ci --registry=https://registry.npmmirror.com
        Start-Process npm.cmd -ArgumentList "run dev"
      shell: pwsh

    - name: 等前后端就绪
      run: Start-Sleep -Seconds 15
      shell: pwsh

    - name: 跑 UI 测试
      run: |
        python -m pytest tests/ui --alluredir=allure-ui-results -v
      shell: pwsh

    - name: 上传 Allure UI 结果
      uses: actions/upload-artifact@v4
      with:
        name: allure-ui
        path: allure-ui-results
```

---

## 第 8 章 元素定位器怎么选（面试常问）

**稳定性从高到低：**

| 方式 | 例子 | 为什么稳 | 什么时候用 |
|------|------|---------|-----------|
| **get_by_placeholder()** | `page.get_by_placeholder("请输入用户名")` | Element Plus 表单的 placeholder 文案前端不会随便改 | 表单输入框 |
| **get_by_role + name** | `page.get_by_role("button", name="登录")` | Playwright 内置的无障碍定位，最语义化 | 按钮、链接 |
| **CSS 选择器** | `page.locator("button.submit")` | ⚠️ **最脆弱**——前端改样式 class 就失效 | 万不得已再用 |
| **XPath** | `page.locator("//button[text()='登录']")` | 最慢、最难读 | **尽量不用** |

> 面试话术：优先用 `get_by_role` 和 `get_by_placeholder`，语义清晰、稳定；尽量不用纯 CSS class 选择器，前端样式一改脚本就崩，维护成本高。XPath 是最后手段。

---

## 第 9 章 UI 自动化为什么只写 7 条，不多写？

UI 自动化维护成本**很高**——前端页面一改（改 DOM 结构、改 class、改文案），元素定位器就失效，脚本直接挂。

所以 UI 自动化只覆盖**最高优先级的核心链路**：

| 类型 | 用例 | 原因 |
|------|------|------|
| 页面渲染 | 4 条（登录页 / 新建对话 / 定时任务 / 个人设置） | 核心页面必须能打开不崩 |
| 业务交互 | 1 条（登录 + 发目标） | 最核心的用户操作 |
| 权限校验 | 2 条（普通用户被拦 + admin 正常进） | 安全红线必须测 |

其他场景（比如定时任务新建删除、智能体列表、admin 用户管理）**交给接口自动化 + 手工测试兜底**——接口自动化 88 条全绿覆盖了后端逻辑，手工点点点验证前端交互的边界情况，这是性价比最高的组合。

---

## 第 10 章 面试回答模板

**问：Playwright 和 Selenium 你选哪个？**

答：选 Playwright。它是微软出的，比 Selenium 更稳，自带智能等待和原生 expect 断言，不用到处写 `time.sleep` 硬等待。而且 Playwright 一个 API 就能操控 Chrome、Firefox、Edge 三种浏览器，Selenium 每个浏览器要装对应的 WebDriver，配置麻烦。Playwright 还有 codegen 录制器，新手能快速生成基础脚本再改造。简历里 Playwright 也更时髦。

**问：headed 和 headless 什么区别？什么时候用？**

答：headed 是有界面，弹出浏览器窗口，能看到它在点点点——**调试脚本的时候用**，直观看到哪一步出错。headless 是无头模式，后台静默跑，速度更快——**批量回归、CI 流水线的时候用**。命令行加 `--headed` 参数就能强制有头，优先级最高。

**问：expect 和原生 assert 有什么区别？**

答：Playwright 1.16 之后出的原生 expect 断言，**自带自动重试**——元素还没出现就等最多 5 秒，不是立刻检查。原生 `assert page.locator().is_visible()` 立刻执行，一秒都不等，页面渲染慢半拍就挂。正式脚本里都用 expect。

**问：fixture scope=session 和默认 function 有什么区别？**

答：scope 决定 fixture 什么时候创建、什么时候销毁。`session` 是整个 pytest 会话只创建一次——比如 `browser` fixture，7 条用例共用一个浏览器实例，只启一次快很多。默认 `function` 是每条用例创建一次——比如 `page` fixture，每条用例一个新 context + 新标签页，cookie 和 localStorage 自动隔离，谁也不干扰谁。

**问：为什么每条用例都要开新 context（不共用同一个标签页）？**

答：用例之间要数据隔离、状态隔离。上一条用例登录了 tester，cookie 存着 tester 的登录态；下一条要登 admin，如果共用同一个标签页，就得先登出再登录，多出两步操作。每条用例一个新 context（上下文会自动清空 cookie/localStorage）+ 新标签页，写起来更干净。

**问：codegen 录出来的代码为什么不能直接用？**

答：录出来的是一坨扁平代码——每条都自己 launch browser、新页面、没有 fixture 复用、没有辅助函数封装、没有 expect 断言、没有 try/except 容错。直接跑能用，但生产环境回归会很痛苦。标准做法是 codegen 快速录基础代码 → 手动改造成 pytest fixture + expect 断言 + 辅助函数复用 → 放进 tests/ui/ 回归仓库。

---

## 第 11 章 小白学习顺序

1. **环境 OK 验证**：跑第 1.5 节的命令，输出 `浏览器启动 OK`
2. **codegen 录一次**：跑第 3.1 节的命令，录一次登录流程，看看 inspector 面板怎么实时生成代码
3. **第一次跑 pytest**：`pytest tests/ui -v --headed`，亲眼看见浏览器自动点点点跑完 7 条
4. **故意搞破坏**：把 expect 改成看一个不存在的元素（比如 `expect(page.locator("#不存在")).to_be_visible()`），看 FAILED 报错长什么样，看懂失败信息
5. **搞懂 fixture**：看 browser / page 两个 fixture，理解 scope 的意思
6. **搞懂 do_login**：看看为什么要封装、辅助函数怎么让代码干净
7. **搞懂 expect**：对比原生 assert 和 expect 断言的写法差异
8. **跑 Allure**：`--alluredir` + `allure generate` + `allure open`，看 UI 测试的报告长什么样
9. **接口 + UI 合并**：第 6.2 节的命令，一次跑 88 + 7 = 95 条

---

## 第 12 章 本篇产出

```
tests/ui/test_ui_playwright.py      （7 条用例，expect 版）
docs/screenshots/                   （每条用例的截图，跑完自动生成）
allure-ui-results/                  （UI 测试 Allure 原始数据）
allure-report/                      （接口 + UI 合并 Allure HTML 报告）
```
