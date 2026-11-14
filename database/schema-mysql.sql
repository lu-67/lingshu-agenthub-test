-- ============================================================
-- 灵枢 AgentHub · AI 智能体工作台 · MySQL 建库建表脚本（v5.0.0）
-- 适用：MySQL 8.x，默认 127.0.0.1:3307，账号 root / 123456，库 nexus_agent
--
-- 说明：
--   1. 服务启动时 db.init_db() 会自动建库、建表、写入种子账号与种子知识库，
--      本脚本供手工建库、数据库断言练习、答辩环境还原使用；
--   2. 密码哈希由应用以 PBKDF2 生成（12 万轮 + 随机盐），SQL 中不写任何明文密码；
--   3. v5 数据模型围绕「会话式智能体」：智能体、会话、消息、定时任务 + 任务型
--      遗留表（tasks/task_steps/artifacts/runs/eval_runs）双轨并存；
--   4. 升级时应用会自动清理 v2/v3 遗留表（conversations / feedback / workflows /
--      prompt_versions / channels / api_keys）。
-- ============================================================

CREATE DATABASE IF NOT EXISTS nexus_agent
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE nexus_agent;

-- ----------------------------------------------------------
-- 1. 账号
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(64)  NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(16)  NOT NULL DEFAULT 'USER',   -- USER / ADMIN
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 2. 任务（一句话目标 + 计划 + 状态机）
--    status: planned / running / waiting_approval / completed / failed / cancelled
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  owner_id    INT          NOT NULL,
  goal        TEXT         NOT NULL,
  skill_id    VARCHAR(32)  NOT NULL DEFAULT 'general',
  skill_name  VARCHAR(64)  NOT NULL DEFAULT '通用任务',
  status      VARCHAR(20)  NOT NULL DEFAULT 'planned',
  mode        VARCHAR(16)  NOT NULL DEFAULT 'mock',
  summary     TEXT         NOT NULL,
  progress    INT          NOT NULL DEFAULT 0,          -- 0-100
  step_total  INT          NOT NULL DEFAULT 0,
  step_done   INT          NOT NULL DEFAULT 0,
  elapsed_ms  INT          NOT NULL DEFAULT 0,
  error       TEXT         NOT NULL,
  context     TEXT         NOT NULL,                    -- 执行上下文 JSON（检索结果 / 表格 / 报告）
  day         VARCHAR(10)  NOT NULL DEFAULT '',         -- YYYY-MM-DD，看板趋势用
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME     NULL,
  KEY idx_tasks_owner (owner_id),
  KEY idx_tasks_status (status),
  KEY idx_tasks_day (day)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 5. 任务步骤（角色 / 动作 / 状态 / 授权门禁 / 耗时）
--    status: pending / running / success / failed / waiting / skipped
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_steps (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  task_id        INT          NOT NULL,
  seq            INT          NOT NULL DEFAULT 1,
  role_key       VARCHAR(32)  NOT NULL DEFAULT '',
  role_name      VARCHAR(64)  NOT NULL DEFAULT '',
  role_avatar    VARCHAR(16)  NOT NULL DEFAULT '🤖',
  action         VARCHAR(32)  NOT NULL DEFAULT '',      -- 能力工具名
  title          VARCHAR(255) NOT NULL DEFAULT '',
  input          TEXT         NOT NULL,
  output         TEXT         NOT NULL,
  status         VARCHAR(20)  NOT NULL DEFAULT 'pending',
  needs_approval TINYINT(1)   NOT NULL DEFAULT 0,
  approved       TINYINT(1)   NOT NULL DEFAULT 0,
  elapsed_ms     INT          NOT NULL DEFAULT 0,
  started_at     DATETIME     NULL,
  finished_at    DATETIME     NULL,
  KEY idx_steps_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 6. 交付物（kind: report / table / checklist；format: md / csv）
--    checksum = 内容 SHA-256 前 16 位，用于确定性断言
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  task_id    INT          NOT NULL,
  kind       VARCHAR(16)  NOT NULL DEFAULT 'report',
  title      VARCHAR(255) NOT NULL DEFAULT '',
  format     VARCHAR(16)  NOT NULL DEFAULT 'md',
  content    LONGTEXT     NOT NULL,
  size       INT          NOT NULL DEFAULT 0,
  step_seq   INT          NOT NULL DEFAULT 0,
  checksum   VARCHAR(32)  NOT NULL DEFAULT '',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_artifacts_task (task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 7. 知识库文档（向量写入 Chroma，此处只存元数据与正文）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_docs (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  owner_id   INT          NOT NULL,                     -- 0 表示系统种子文档
  title      VARCHAR(255) NOT NULL,
  doc_key    VARCHAR(32)  NOT NULL DEFAULT '',          -- Chroma 内的文档键
  content    LONGTEXT     NOT NULL,
  chunks     INT          NOT NULL DEFAULT 0,
  source     VARCHAR(32)  NOT NULL DEFAULT 'manual',    -- seed / manual
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 8. 智能体（每个用户可建多个，6 个内置不可删）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS agents (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  owner_id      INT          NOT NULL,
  name          VARCHAR(64)  NOT NULL,
  avatar        VARCHAR(16)  NOT NULL DEFAULT '🤖',
  description   VARCHAR(255) NOT NULL DEFAULT '',
  system_prompt TEXT         NOT NULL,
  model         VARCHAR(32)  NOT NULL DEFAULT 'mock',
  skill_ids     TEXT         NOT NULL DEFAULT '[]',   -- JSON 数组
  enabled       TINYINT(1)   NOT NULL DEFAULT 1,
  is_builtin    TINYINT(1)   NOT NULL DEFAULT 0,
  sort          INT          NOT NULL DEFAULT 50,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_agents_owner (owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 11. 会话（一次智能体对话）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  owner_id     INT          NOT NULL,
  agent_id     INT          NOT NULL,
  title        VARCHAR(120) NOT NULL DEFAULT '新对话',
  last_message TEXT         NOT NULL DEFAULT '',
  updated_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_sessions_owner (owner_id),
  KEY idx_sessions_agent (agent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 12. 消息（会话内逐条消息，含思考过程步骤）
--     msg_type: text / step / artifacts / plan / error
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  session_id  INT          NOT NULL,
  role        VARCHAR(16)  NOT NULL DEFAULT 'user',
  content     TEXT         NOT NULL,
  msg_type    VARCHAR(20)  NOT NULL DEFAULT 'text',
  step_no     INT          NOT NULL DEFAULT 0,
  data        TEXT         NOT NULL DEFAULT '{}',
  status      VARCHAR(16)  NOT NULL DEFAULT 'success',
  task_id     INT          NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_messages_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ----------------------------------------------------------
-- 13. 定时任务（APScheduler 注册，cron_expr 中文预设映射）
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS automations (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  owner_id    INT          NOT NULL,
  agent_id    INT          NOT NULL,
  name        VARCHAR(64)  NOT NULL,
  cron_expr   VARCHAR(40)  NOT NULL,
  goal        TEXT         NOT NULL,
  enabled     TINYINT(1)   NOT NULL DEFAULT 1,
  last_run_at DATETIME     NULL,
  next_run_at DATETIME     NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_automations_owner (owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 种子数据
-- ------------------------------------------------------------
-- 不需要手工插入：
--   * 启动时自动创建 admin/admin123、tester/tester123；
--   * 每个新账号自动复制 4 个内置角色；
--   * 启动时将 3 篇种子知识库文档幂等写入 Chroma。
-- 如需彻底重置演示环境，可执行：
--   DROP DATABASE nexus_agent; 然后重启服务。
-- ============================================================

-- ============================================================
-- 数据库断言练习（对应教程 09：数据库校验）
-- ============================================================

-- 断言 1：任务进度与步骤完成数一致
-- SELECT id, status, step_total, step_done, progress
-- FROM tasks
-- WHERE status = 'completed' AND (step_done <> step_total OR progress <> 100);

-- 断言 2：每个已完成任务至少 2 份交付物，且报告与审核清单必备
--   （市场调研 / 竞品分析 / 数据整理 / 通用任务有 CSV，共 3 份；
--     内容营销 / 知识问答无 data_analyze 步骤，只有报告 + 清单 2 份）
-- SELECT t.id, COUNT(a.id) AS art_count,
--        SUM(a.kind = 'report') AS reports, SUM(a.kind = 'checklist') AS checklists
-- FROM tasks t LEFT JOIN artifacts a ON a.task_id = t.id
-- WHERE t.status = 'completed'
-- GROUP BY t.id
-- HAVING art_count < 2 OR reports = 0 OR checklists = 0;

-- 断言 3：交付物必须挂在合法的步骤序号上（反连接，返回 0 行才通过）
-- SELECT a.id, a.step_seq FROM artifacts a
-- LEFT JOIN task_steps s ON s.task_id = a.task_id AND s.seq = a.step_seq
-- WHERE s.id IS NULL;

-- 断言 4：等待授权的任务，其最后一步必须是 notify 且未授权
-- SELECT t.id FROM tasks t
-- JOIN task_steps s ON s.task_id = t.id
-- WHERE t.status = 'waiting_approval'
--   AND s.needs_approval = 1 AND s.approved = 0
--   AND s.seq <> (SELECT MAX(seq) FROM task_steps WHERE task_id = t.id);

-- 断言 5：步骤耗时不能为负
-- SELECT id FROM task_steps WHERE elapsed_ms < 0;

-- 断言 6：同一目标同一类型的交付物只能有一种 checksum（确定性）
--   checksum 不能放进 GROUP BY，否则分组粒度被破坏、断言永远 0 行
-- SELECT t.goal, a.kind, COUNT(DISTINCT a.checksum) AS variants
-- FROM tasks t JOIN artifacts a ON a.task_id = t.id
-- WHERE t.status = 'completed'
-- GROUP BY t.goal, a.kind
-- HAVING variants > 1;

-- 断言 7：看板成功率与 runs 表一致（需要按用户、按任务终态口径对齐）
-- SELECT ROUND(SUM(status = 'success') / COUNT(*), 4) AS success_rate
-- FROM runs WHERE kind = 'task';
