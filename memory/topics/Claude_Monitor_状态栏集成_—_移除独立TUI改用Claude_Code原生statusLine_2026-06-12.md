# Claude Monitor 状态栏集成 — 移除独立TUI改用Claude Code原生statusLine

> 创建时间：2026-06-12 19:41:29
> 更新时间：2026-06-12 19:41:29

## 摘要

用户反馈 Claude Monitor 插件仍然会新建终端窗口（wt.exe sp 分栏），要求将监控面板直接集成到 Claude Code 自身界面中。最终方案：放弃 Textual TUI 独立进程，改用 Claude Code 原生 statusLine 功能。核心改动： 1. 新建 scripts/status_line.py — 轻量级状态栏格式化脚本。读取 state.json，输出单行紧凑状态文本（ANSI 彩色信号灯 + 工具进度条 + Token/费用）。处理了 Windows GBK 编码问题（使用 sys.stdout.buffer.write 直接写 UTF-8 字节）

## 关键词

Claude, Monitor, 状态栏集成, —, 移除独立TUI改用Claude, Code原生statusLine, exe, Code, Textual, TUI

## 关键决策

- 最终方案：放弃 Textual TUI 独立进程，改用 Claude Code 原生 statusLine 功能

## 待办事项

- 5 种测试场景全部通过
- 2. 修改 scripts/launch_monitor.py — 删除全部 TUI 启动逻辑（_find_wt_exe、_launch_tui、_launch_tui_windows、_launch_tui_unix、subprocess/ctypes 导入、PID 检查），仅保留 state.j…

## 原始对话摘录

````text
用户反馈 Claude Monitor 插件仍然会新建终端窗口（wt.exe sp 分栏），要求将监控面板直接集成到 Claude Code 自身界面中。

最终方案：放弃 Textual TUI 独立进程，改用 Claude Code 原生 statusLine 功能。

核心改动：
1. 新建 scripts/status_line.py — 轻量级状态栏格式化脚本。读取 state.json，输出单行紧凑状态文本（ANSI 彩色信号灯 + 工具进度条 + Token/费用）。处理了 Windows GBK 编码问题（使用 sys.stdout.buffer.write 直接写 UTF-8 字节）。5 种测试场景全部通过。
2. 修改 scripts/launch_monitor.py — 删除全部 TUI 启动逻辑（_find_wt_exe、_launch_tui、_launch_tui_windows、_launch_tui_unix、subprocess/ctypes 导入、PID 检查），仅保留 state.json 初始化和 additionalContext 输出。
3. 创建 .claude/settings.json — 配置 statusLine type=command，每 2 秒刷新，指向 status_line.py。
4. 更新 commands/claude-monitor.md — 删除 restart/stop 子命令，新增状态栏格式说明。
5. 更新 plugin.json — description 和 keywords 反映状态栏模式。

状态栏格式：● CLAUDE工作中 | ██████░░░░  62% | 12.5K/38.0K | ¥0.28

所有 Hook 状态更新机制（update_state.py、write_closing_state.py）完全保留不变。monitor/app.py Textual TUI 保留用于手动调试但不自动启动。
````

---

