<template>
  <router-view />
</template>

<style>
/* ============================================================================
   灵枢 AgentHub · 设计系统（v3.0）
   原则：统一 token → 所有页面只引用变量；深/浅色主题一键切换（html[data-theme]）
   ========================================================================== */
:root {
  /* Accio Work style tokens */
  --bg: #F7F8FA;
  --bg-soft: #F3F4F6;
  --surface: #FFFFFF;
  --surface-2: #F9FAFB;
  --surface-3: #F3F4F6;
  --border: #E5E7EB;
  --border-strong: #D1D5DB;
  --text: #111827;
  --text-2: #374151;
  --muted: #6B7280;
  --primary: #111827;
  --primary-2: #374151;
  --primary-soft: #F3F4F6;
  --accent: #22C55E;
  --accent-soft: #DCFCE7;
  --success: #22C55E;
  --warn: #F59E0B;
  --danger: #EF4444;
  --info: #3B82F6;
  --sidebar: #FFFFFF;
  --sidebar-2: #F9FAFB;
  --sidebar-text: #6B7280;
  --shadow-sm: 0 1px 2px rgba(17, 24, 39, .04);
  --shadow: 0 4px 14px rgba(17, 24, 39, .06);
  --shadow-lg: 0 12px 40px rgba(17, 24, 39, .1);
  --radius: 12px;
  --mono: "JetBrains Mono", "Cascadia Code", Consolas, "Courier New", monospace;
  --el-color-primary: #111827;
}

html[data-theme="dark"] {
  --bg: #080C15;
  --bg-soft: #0C1220;
  --surface: #111827;
  --surface-2: #172033;
  --surface-3: #1C2740;
  --border: #233049;
  --border-strong: #2E3D5C;
  --text: #E8ECF6;
  --text-2: #B4BDD1;
  --muted: #7C87A0;
  --primary-soft: #1B2144;
  --sidebar: #05080F;
  --sidebar-2: #0B1221;
  --sidebar-text: #8D99B4;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, .5);
  --shadow: 0 8px 24px rgba(0, 0, 0, .45);
  --shadow-lg: 0 24px 60px rgba(0, 0, 0, .6);
}

* { box-sizing: border-box; }
html, body, #app { height: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--primary); text-decoration: none; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }

/* ------------------------------ 布局工具类 ------------------------------ */
.page { padding: 24px 30px 48px; max-width: 1480px; margin: 0 auto; }
.page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 22px; flex-wrap: wrap; }
.page-head h1 { font-size: 23px; margin: 0 0 5px; font-weight: 680; letter-spacing: -.02em; }
.page-head p { margin: 0; color: var(--muted); font-size: 13px; }
.head-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow-sm); }
.card-pad { padding: 18px 20px; }
.card-hover { transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
.card-hover:hover { transform: translateY(-2px); box-shadow: var(--shadow); border-color: var(--border-strong); }
.section-title { font-size: 14px; font-weight: 650; display: flex; align-items: center; gap: 8px; }
.grid { display: grid; gap: 16px; }
.row { display: flex; align-items: center; gap: 10px; }
.between { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.muted { color: var(--muted); }
.small { font-size: 12px; }
.mono { font-family: var(--mono); }
.ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nowrap { white-space: nowrap; }

.chip {
  display: inline-flex; align-items: center; gap: 5px; padding: 2px 9px; border-radius: 999px;
  font-size: 11px; line-height: 18px; background: var(--surface-2); color: var(--text-2);
  border: 1px solid var(--border); white-space: nowrap;
}
.chip.dot::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.chip.ok { color: #0EA97A; background: rgba(14, 169, 122, .1); border-color: rgba(14, 169, 122, .25); }
.chip.warn { color: #B87700; background: rgba(224, 138, 0, .12); border-color: rgba(224, 138, 0, .28); }
.chip.bad { color: #D93A3F; background: rgba(229, 72, 77, .1); border-color: rgba(229, 72, 77, .25); }
.chip.info { color: #0E9BD4; background: rgba(14, 155, 212, .1); border-color: rgba(14, 155, 212, .25); }
.chip.primary { color: var(--primary); background: var(--primary-soft); border-color: rgba(79, 70, 229, .22); }

.btn {
  height: 34px; padding: 0 14px; border-radius: 10px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text-2); font-size: 13px; font-weight: 500;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  cursor: pointer; transition: all .16s ease; white-space: nowrap;
}
.btn:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-soft); }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn.primary {
  background: var(--primary); border: none;
  color: #fff; box-shadow: 0 2px 8px rgba(17, 24, 39, .15);
}
.btn.primary:hover { background: #000; color: #fff; }
.btn.dark { background: var(--sidebar); border-color: var(--sidebar); color: #fff; }
.btn.sm { height: 28px; padding: 0 10px; font-size: 12px; border-radius: 8px; }
.btn.ghost { background: transparent; border-color: transparent; }
.btn.danger { color: var(--danger); border-color: rgba(229, 72, 77, .3); }
.btn.danger:hover { background: rgba(229, 72, 77, .1); color: var(--danger); }
.icon-btn {
  width: 32px; height: 32px; border-radius: 9px; border: 1px solid var(--border);
  background: var(--surface); color: var(--text-2); display: inline-flex;
  align-items: center; justify-content: center; cursor: pointer; transition: all .15s;
}
.icon-btn:hover { color: var(--primary); border-color: var(--primary); background: var(--primary-soft); }

.empty { padding: 46px 20px; text-align: center; color: var(--muted); font-size: 13px; }
.empty .big { font-size: 30px; margin-bottom: 8px; opacity: .55; }
.divider { height: 1px; background: var(--border); margin: 14px 0; }

.fade-up { animation: fadeUp .3s ease both; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ------------------------------ Element Plus 皮肤 ------------------------------ */
.el-button { border-radius: 8px !important; font-weight: 500; }
.el-button--primary { background: var(--primary) !important; border: none !important; box-shadow: 0 2px 8px rgba(17, 24, 39, .15) !important; }
.el-button--primary:hover { background: #000 !important; }
.el-input__wrapper, .el-textarea__inner, .el-select__wrapper {
  background: var(--surface-2) !important; border-radius: 10px !important;
  box-shadow: 0 0 0 1px var(--border) inset !important;
}
.el-input__wrapper.is-focus, .el-textarea__inner:focus, .el-select__wrapper.is-focused {
  box-shadow: 0 0 0 1px var(--primary) inset !important; background: var(--surface) !important;
}
.el-input__inner, .el-textarea__inner { color: var(--text) !important; }
.el-dialog, .el-drawer { border-radius: 18px !important; background: var(--surface) !important; }
.el-drawer { border-radius: 18px 0 0 18px !important; }
.el-dialog__title, .el-drawer__title { color: var(--text) !important; font-weight: 650; }
.el-dialog__body, .el-drawer__body { color: var(--text-2) !important; }
.el-table { --el-table-bg-color: transparent; --el-table-tr-bg-color: transparent; --el-table-header-bg-color: var(--surface-2); background: transparent !important; }
.el-table th.el-table__cell { background: var(--surface-2) !important; color: var(--muted) !important; font-weight: 600; font-size: 12px; }
.el-table td.el-table__cell { border-bottom: 1px solid var(--border) !important; color: var(--text-2); }
.el-table__inner-wrapper::before { display: none; }
.el-tag { border-radius: 7px !important; }
.el-switch.is-checked .el-switch__core { background: var(--primary) !important; border-color: var(--primary) !important; }
.el-tabs__item { color: var(--muted) !important; }
.el-tabs__item.is-active { color: var(--text) !important; }
.el-tabs__active-bar { background: var(--primary) !important; }
.el-tabs__nav-wrap::after { background: var(--border) !important; height: 1px !important; }
.el-progress-bar__outer { background: var(--surface-3) !important; }
.el-form-item__label { color: var(--text-2) !important; font-size: 12px !important; }
.el-message { border-radius: 10px !important; }
.el-popper.is-light { background: var(--surface) !important; border-color: var(--border) !important; }
.el-select-dropdown__item.is-selected { color: var(--primary) !important; }
.el-slider__runway { background: var(--surface-3) !important; }
.el-slider__bar { background: var(--primary) !important; }
.el-slider__button { border-color: var(--primary) !important; }
.el-empty__description p { color: var(--muted); }
</style>
