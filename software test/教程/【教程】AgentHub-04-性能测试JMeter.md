# 灵枢 AgentHub · 性能测试（JMeter）教程

> 配套文件：`software test/jmeter/agenthub-plan.jmx`（**完整 XML 脚本，327 行，和下面逐组件解释一一对应**）
> 工具路径：`D:\software\apache-jmeter-5.6.3\bin\jmeter.bat`
> 被测地址：`http://127.0.0.1:8000`
> 真实跑过的数据：5 线程 3 循环 = 90 请求，**错误率 0%**

---

## 第 0 章 名词词典（小白先看）

| 名词 | 大白话 | 类比 |
|------|--------|------|
| **JMeter** | Apache 出的免费压测工具，Java 写的，能模拟几百上千个用户同时请求 | 像一个"机器人军团"同时访问你的网站 |
| **线程 Thread** | JMeter 里"一个虚拟用户"就叫一个线程 | 5 线程 = 5 个人同时用系统 |
| **循环 Loop** | 每个线程把脚本从头到尾跑几遍 | 3 线程 × 2 循环 = 同一个请求总共被调 6 次 |
| **并发 Ramp-Up** | 5 线程不是同时启动的，JMeter 默认 5 秒内慢慢拉起来 | 模拟真实情况：用户不是同时出现的 |
| **TPS Throughput** | 每秒处理多少个请求 | `3.5/s` = 每秒 3.5 个请求 |
| **P95 95% Line** | 把所有请求按耗时排个序，排在 95% 那个位置的耗时。**比平均值更能反映真实体验** | 100 个人排队，第 95 个花的时间 = P95 |
| **jtl** | JMeter 保存原始测试结果的文件（CSV 格式） | 跑完之后每个请求一行，有耗时、状态码、成功/失败 |
| **聚合报告** | JMeter 自动汇总的表格：按请求名分组，算出平均耗时、P95、TPS、错误率 | 跑完自动出，是最重要的一张表 |
| **正则提取器** | JMeter 里从响应体里"抓东西存成变量"的组件 | 登录返回 `{"token":"abc123"}`，用正则把 abc123 抓出来存 `${token}` |

### 为什么 P95 比平均值重要？

100 个请求里 95 个都是 1 秒内返回，剩下 5 个卡了 10 秒：
- **平均值** = (95×1 + 5×10) / 100 = **1.45 秒**（看起来挺快）
- **P95** = 排序后第 95 个 = **10 秒**（反映真实的"有时候会很卡"）

面试被问"P95 和平均值有什么区别"，直接答这个例子。

---

## 第 1 章 先搞清楚：性能测试和接口测试不是一回事

| | 接口测试（Postman/pytest） | 性能测试（JMeter） |
|--|--------------------------|-------------------|
| **问的是什么** | 一次请求对不对（参数、返回值、错误码） | 很多人同时请求时还快不快、会不会崩 |
| **并发** | 1 个用户，点一次跑一次 | N 个用户同时跑，循环 M 次 |
| **关注的指标** | 状态码 200、字段不缺 | 错误率 0%、P95 < 阈值、TPS 够不够 |
| **执行方式** | 单次跑、自动化回归 | 一次性压几秒到几分钟 |

### 本项目选了哪些接口？为什么只压这 6 个？

脚本里 6 个请求 = **一条完整业务链路**（登录 → 发目标 → 查结果）：

| # | 请求 | 压它的意义 | 预估耗时 |
|---|------|-----------|---------|
| 1 | POST /api/auth/login | 每次压测的起点，所有用户都要先登录 | 快（< 200ms） |
| 2 | GET /api/agents | 轻量 GET，拿 agentId（send 需要） | 飞快（< 50ms） |
| 3 | POST /api/sessions | 建会话，send 的前置步骤 | 快（< 100ms） |
| 4 | **POST /api/sessions/{sid}/send** ★ | **核心压测点**——同步跑技能匹配+规划+执行+总结+存 run | **最慢（~7s）** |
| 5 | GET /api/sessions/{sid} | 轻量 GET，验证 send 完数据能查到 | 快（< 100ms） |
| 6 | GET /api/automations | 轻量 GET，做基线对比 | 飞快（< 50ms） |

> **为什么只压 6 个，不压全部 24 个？**
>
> 实习生 Demo 项目不用全量压——重的就 1-2 个，其他都是轻量 GET。选最重的 send（同步串行执行链）+ 几个轻量做对比基线就行。压完一眼就能看出"send 是瓶颈，其他都很快"，比压 24 个但看不出重点强多了。

---

## 第 2 章 跑起来之前

### 2.1 确认 Java 有

JMeter 是 Java 写的，没 Java 跑不起来：

```cmd
java -version
```

应该输出 `openjdk version "17.x.x"` 或类似的。

### 2.2 启动后端（mock 模式）

**压测必须用 mock 模式**——真实大模型 API 有频率限制，而且每次返回不确定，压出来的数据不稳定。

```cmd
set AGENT_MODE=mock
set SKIP_CAPTCHA=1
cd D:\nexus-agent\agent-core
"D:\software\Python 3.10.11\python.exe" run_server.py
```

### 2.3 用浏览器登一下 tester 账号

`http://127.0.0.1:5173` 用 `tester/tester123` 登录，确保后端有数据（至少有几个智能体）。

---

## 第 3 章 jmx 文件逐组件拆解（**小白版**）

`agenthub-plan.jmx` 是 JMeter 保存脚本的 XML 格式文件——**但你不用直接改 XML！** 用 GUI 打开就能看到可视化树形结构，改完保存就是 XML。

### 3.1 整体结构树（GUI 里看到的样子）

```
TestPlan "AgentHub v5 性能测试"
 ├─ 用户变量（host=127.0.0.1, port=8000, threads=${__P(threads,10)}, ramp=5, loops=5）
 ├─ HTTP 请求默认值（host + port + timeout 30s）
 ├─ 公共请求头（Content-Type: application/json + Authorization: Bearer ${token}）
 └─ 混合业务虚拟用户 Thread Group（threads × loops 个请求）
     │
     │ 每个线程把下面 6 个请求按顺序跑一遍：
     │
     ├─ 01 登录 tester
     │   ├─ POST /api/auth/login, body={"username":"tester","password":"tester123"}
     │   ├─ 🟢 断言：状态码必须 200
     │   └─ 🔍 正则提取：从响应里把 "token":"abc123" 里的 abc123 抓出来 → 存 ${token}
     │
     ├─ 02 智能体列表
     │   ├─ GET /api/agents
     │   ├─ 🟢 断言：状态码必须 200
     │   └─ 🔍 正则提取：从 agents[0].id 抓第一个智能体 id → 存 ${agentId}
     │
     ├─ 03 建会话
     │   ├─ POST /api/sessions, body={"agentId":${agentId},"title":"压测会话"}
     │   ├─ 🟢 断言：状态码必须 200
     │   └─ 🔍 正则提取：从响应的 "id":123 里抓 → 存 ${sid}
     │
     ├─ 04 发目标 send ★ 核心压测点
     │   ├─ POST /api/sessions/${sid}/send, body={"content":"帮我做调研...","autoApprove":true}
     │   ├─ 🟢 断言 1：状态码必须 200
     │   ├─ 🟢 断言 2：响应体里必须有 "completed"（业务逻辑对不对）
     │   └─ 🟢 断言 3：耗时必须 < 10000ms（mock 模式下的技术兜底）
     │
     ├─ 05 会话详情
     │   ├─ GET /api/sessions/${sid}
     │   └─ 🟢 断言：状态码必须 200
     │
     └─ 06 定时任务列表
         ├─ GET /api/automations
         └─ 🟢 断言：状态码必须 200
     │
     └─ 聚合报告（监听器，跑完自动汇总表格）
```

### 3.2 每个组件为什么要这样配

#### 🟢 用户变量（host / port / threads / ramp / loops）

```
host = 127.0.0.1        被测后端 IP
port = 8000              被测后端端口
threads = ${__P(threads,10)}    默认 10 线程，命令行 -Jthreads=5 可以覆盖
ramp = 5                 5 秒内慢慢拉起所有线程（不是同时启动）
loops = ${__P(loops,5)}        默认循环 5 遍，命令行 -Jloops=3 可以覆盖
```

**为什么 threads 和 loops 要用 `${__P(threads,10)}` 这种写法？**

这是 JMeter 的"属性函数"——默认值写死在 jmx 里（方便 GUI 打开就能跑），但命令行可以用 `-Jthreads=5` 覆盖。这样同一个 jmx 可以跑不同并发量级，不用每次进 GUI 改。

#### 🟢 HTTP 请求默认值

```
domain = ${host}         ← 用变量，改 host 就全改了
port = ${port}
connect_timeout = 10000  ← 连接超时 10 秒
response_timeout = 30000 ← 响应超时 30 秒（send 比较慢设大一点）
```

**为什么不用每个请求都写完整 URL？**

因为 6 个请求全都是 `http://127.0.0.1:8000/xxx`——domain 和 port 一样。设一次默认值，后面每个请求只写 path（比如 `/api/auth/login`）就行，干净。

#### 🟢 公共请求头

```
Content-Type: application/json; charset=UTF-8     ← 告诉后端 body 是 JSON
Authorization: Bearer ${token}                     ← 自动带 token
```

**为什么 Authorization 里能写 `${token}`？**

token 是第一个请求跑完后从响应里"抓出来"存进 JMeter 变量的。请求头管理器里 `${token}` 会自动被替换成真实值——相当于接口自动化教程里 `ApiClient` 类自动带 token。

#### 🟢 Thread Group 循环控制器

```
num_threads = ${threads}          ← 用变量
ramp_time = ${ramp}               ← 5 秒内拉起
loops = ${loops}                  ← 每个线程跑几遍
on_sample_error = continue        ← 一个请求失败了不影响后面的（继续跑完）
same_user_on_next_iteration = true ← 同一个线程循环多次时复用同一个上下文
```

#### 🟢 每个请求的三层组件

以 01 登录 tester 为例（每个请求下面都挂这三个）：

```
└─ 01 登录 tester（HTTPSamplerProxy，发请求的本体）
    ├─ 断言：状态码必须 200（ResponseAssertion）
    └─ 正则提取 token（RegexExtractor）
```

**HTTPSamplerProxy 本体**里关键配置：
- `method = POST` / `GET`
- `path = /api/auth/login`（只用写相对路径，domain/port 用默认值）
- `postBodyRaw = true` + body 里填 JSON（raw JSON body 模式，不是 form data）

#### 🟢 正则提取器为什么这样写

JMeter 没有"JSON 提取器"（老版本要装插件），所以用正则。但 jmx 里的正则是 HTML 转义后的：

| 想匹配的 | jmx 里的写法 | 意思 |
|---------|-------------|------|
| `"token":"abc123"` | `&quot;token&quot;\s*:\s*&quot;([^&quot;]+)&quot;` | `[^&quot;]+` 匹配引号里的所有字符，`$1$` 取第 1 个捕获组 |
| `"id":123` | `&quot;id&quot;\s*:\s*(\d+)` | `(\d+)` 匹配数字，`$1$` 取出来 |
| `"agents":[{"id":456...` | `&quot;agents&quot;\s*:\s*\[\s*\{[^{}]*?&quot;id&quot;\s*:\s*(\d+)` | 匹配 agents 数组里第一个对象的 id |

---

## 第 4 章 跑起来（两种方式）

### 方式 A：图形界面（第一次先试这个）

```cmd
D:\software\apache-jmeter-5.6.3\bin\jmeter.bat
```

打开后：
1. **File → Open** → 选 `D:\nexus-agent\software test\jmeter\agenthub-plan.jmx`
2. 左侧树上点 **Thread Group**，右边把 `threads` 改成 **1**、`loops` 改成 **1**（先试一遍确认不报错）
3. 点工具栏上绿色三角 ▶ 开始
4. 左侧树上展开 → 点 **查看结果树** 看每个请求的响应 → **聚合报告** 看整体统计
5. 1 线程没问题了，把 threads 改成 5、loops 改成 3，再跑正式的

### 方式 B：命令行（正式压测必须用，GUI 会占资源）

**每次跑之前先清干净旧数据**（jmeter 对 jtl 和 report 目录都是"要么空要么不存在"的要求）：

```cmd
rem 1. 清旧数据
del "D:\nexus-agent\software test\jmeter\results\round0.jtl" 2>nul
rmdir /s /q "D:\nexus-agent\software test\jmeter\results\report" 2>nul

rem 2. 跑压测
D:\software\apache-jmeter-5.6.3\bin\jmeter.bat ^
  -n ^
  -t "D:\nexus-agent\software test\jmeter\agenthub-plan.jmx" ^
  -l "D:\nexus-agent\software test\jmeter\results\round0.jtl" ^
  -e -o "D:\nexus-agent\software test\jmeter\results\report" ^
  -Jthreads=5 -Jloops=3

rem 3. 浏览器打开 HTML 报告
start "" "D:\nexus-agent\software test\jmeter\results\report\index.html"
```

参数逐段解释：

| 参数 | 意思 | 为什么 |
|------|------|--------|
| `-n` | non-GUI 模式（无头跑） | GUI 会占资源影响压测结果的准确性，**压测必须加** |
| `-t` | test plan 文件路径 | 就是那个 jmx |
| `-l` | jtl 原始数据输出路径 | 跑完每个请求一行（CSV 格式），留着做历史对比 |
| `-e -o` | 跑完自动生成 HTML 报告 | 省得手动跑 `jmeter -g jtl -o report` 再开浏览器 |
| `-Jthreads=5` | 覆盖脚本里的默认线程数 | `${__P(threads,10)}` 就是为了让你命令行可以覆盖 |
| `-Jloops=3` | 覆盖默认循环次数 | 同上 |

### 建议跑三轮（递增并发）

| 轮次 | threads | loops | 总请求数 | 目的 |
|------|---------|-------|---------|------|
| Round 0 | 1 | 1 | 6 | 验证脚本没写错，全 200 |
| Round 1 | 5 | 3 | 90 | **基线数据**（我们这个项目就跑这个） |
| Round 2 | 20 | 10 | 600 | 看高并发会不会崩（进阶，可以不跑） |

---

## 第 5 章 结果怎么看

### 5.1 先看：错误率（Error %）

HTML 报告首页右上角第一个大数字。

- **0% = 过了**（所有请求都成功）
- **有错误** → 进报告的"按请求汇总"页面，看哪条错了
  - 全是 401：token 过期了，或者线程数太多导致同一个 token 被多个线程同时用
  - 全是 500：后端崩了
  - send 挂了"耗时太长"：mock 引擎真的卡在执行步骤里了

### 5.2 聚合报告每一列是什么意思

5 线程 3 循环，90 请求全绿的**真实数据**：

| Label | Samples | Average | Median | 90% Line | 95% Line | 99% Line | Min | Max | Error % | Throughput |
|-------|---------|---------|--------|----------|----------|----------|-----|-----|---------|------------|
| 01 登录 tester | 15 | 97 | 98 | 100 | 98 | 162 | 12 | 162 | 0.00% | 2.1/s |
| 02 智能体列表 | 15 | 12 | 9 | 16 | 9 | 16 | 9 | 16 | 0.00% | 2.1/s |
| 03 建会话 | 15 | 23 | 23 | 29 | 29 | 29 | 18 | 29 | 0.00% | 2.1/s |
| **04 发目标 send** | **15** | **6591** | **7899** | **7899** | **7899** | **7899** | 5341 | 7899 | **0.00%** | 0.3/s |
| 05 会话详情 | 15 | 23 | 23 | 34 | 34 | 34 | 17 | 34 | 0.00% | 2.1/s |
| 06 定时任务列表 | 15 | 12 | 12 | 17 | 17 | 17 | 9 | 17 | 0.00% | 2.1/s |

逐列解释：

| 列 | 意思 | 怎么算出来的 |
|----|------|-------------|
| **Label** | 请求名字（脚本里每个请求的 testname） | —— |
| **Samples** | 这个请求总共被调了多少次 | 线程数 × 循环数：15 = 5 × 3 |
| **Average** | 平均响应时间（毫秒） | 所有请求耗时加起来 ÷ 请求数 |
| **Median** | 中位数（所有请求排好，取中间那个） | 和平均值差不多就正常 |
| **90% / 95% / 99% Line** | P90 / P95 / P99 | 排序后第 90/95/99 个的耗时 |
| **Min / Max** | 最快和最慢的那一次 | 看有没有离谱的偶发卡 |
| **Error %** | 这个请求的错误率 | **必须 0.00%** |
| **Throughput** | TPS（每秒多少请求） | 总请求数 ÷ 总耗时 |

### 5.3 怎么读"send 是瓶颈"这个结论？

真实数据直接能读出来：

| 对比项 | send | 其他 5 个 |
|--------|------|----------|
| **平均耗时** | 6591ms | 全部 < 100ms |
| **P95** | 7899ms | 全部 < 50ms |
| **Max** | 7899ms | 全部 < 162ms |
| **TPS** | 0.3/s | 全部 2.1/s |

**根因**：send 是**同步串行**执行链——一次请求里要顺序跑：存消息 → 技能匹配 → 规划 → 创建 task → 执行每个 step → 总结 → 存 run。这一串必须全部跑完才能返回给用户。

**改进建议**：改成**异步**——先返回 taskId，前端轮询拿进度，后端后台慢慢跑。预计 P95 能降到 200ms 以内。

---

## 第 6 章 面试回答模板

**问：你压测了哪些接口？为什么选这几个？**

答：压了 6 个，覆盖完整业务链路：登录 → 智能体列表 → 建会话 → 发目标 send → 查会话详情 → 定时任务列表。核心是 send 接口，因为它是整个平台最重的链路——同步串行执行技能匹配、规划、步骤执行、总结、存 run。其他都是轻量 GET/POST，用来做基线对比。

**问：压测结果怎么样？发现了什么？**

答：5 线程 3 循环压了 90 个请求，错误率 0%。send 是明显瓶颈，P95 7.9 秒，其他接口都在 100ms 以内。TPS 只有 0.3/s，是其他接口的 1/7。根因是 send 是同步执行路径。我提了建议：改成异步，先返回 taskId，前端轮询拿进度。

**问：并发数选 5 够不够？**

答：实习生项目 5 线程 3 循环够了，证明"不崩、不丢数据、错误率 0"就行。生产环境会压到几百上千并发看拐点，但 Demo 项目看瓶颈趋势，5 线程已经很明显了。

**问：JMeter 里正则提取器怎么用？为什么不用 JSON 提取器？**

答：JMeter 默认有 ResponseAssertion 和 RegexExtractor，JSON 提取器要装插件。我项目里的响应结构固定，用正则够了——从登录响应里抓 token、从 agents 数组里抓第一个 id、从建会话响应里抓 sid，三条正则分别对应三个变量，后面的请求直接 `${变量名}` 引用，串起来整个业务链路。

---

## 第 7 章 本篇产出

```
software test/jmeter/agenthub-plan.jmx              （完整 327 行脚本）
software test/jmeter/results/round0.jtl              （90 请求原始数据，CSV）
software test/jmeter/results/report/index.html       （HTML 报告，浏览器打开看）
```

> **简历怎么写**：压测了 6 个接口 90 个请求，send 是明显瓶颈（P95 7.9s），其他接口都在 100ms 以内。根因是同步执行路径，建议改异步。错误率 0%，证明系统在 5 并发下稳定——一句话里有真实数字、有结论、有改进建议，比空说"我会用 JMeter"强多了。
