# Claude Monitor 插件完整开发与部署 — 从零设计到安装运行

> 创建时间：2026-06-12 19:17:23
> 更新时间：2026-06-12 19:17:23

## 摘要

## 摘要 用户从零开始设计并开发了一个 Claude Code 插件 Claude Monitor，用于在独立终端窗口中可视化 Claude Code 工作状态。项目经历设计文档 v1.0→v1.2 三次迭代修正、5 个开发阶段、E2E 测试修复、最终成功安装到当前 Claude Code 环境。## 关键决策 - 技术架构：文件桥接（state.json）+ watchfiles 监听 + Python Textual TUI，零网络依赖 - 显示形态：方案 A 单行紧凑终端面板（信号灯 + 进度条 + Token/费用） - 三色信号灯映射：绿色 idle/starting/closing，黄色 waiting_user/permission_denied/recoverable_error/state_file_error，红色 working/tool_running/fatal_error - Hook 全覆盖：12/12 Hook（SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/PostToolUseFailure…

## 关键词

Claude, Monitor, 插件完整开发与部署, —, 从零设计到安装运行, Code, E2E, state, json, watchfiles

## 关键决策

- 项目经历设计文档 v1.0→v1.2 三次迭代修正、5 个开发阶段、E2E 测试修复、最终成功安装到当前 Claude Code 环境
- ## 关键决策 - 技术架构：文件桥接（state.json）+ watchfiles 监听 + Python Textual TUI，零网络依赖 - 显示形态：方案 A 单行紧凑终端面板（信号灯 + 进度条 + Token/费用） - 三…

## 待办事项

- 项目经历设计文档 v1.0→v1.2 三次迭代修正、5 个开发阶段、E2E 测试修复、最终成功安装到当前 Claude Code 环境
- ## 关键决策 - 技术架构：文件桥接（state.json）+ watchfiles 监听 + Python Textual TUI，零网络依赖 - 显示形态：方案 A 单行紧凑终端面板（信号灯 + 进度条 + Token/费用） - 三色信号灯映射：绿色 idle/starting/closin…

## 原始对话摘录

````text
## 摘要
用户从零开始设计并开发了一个 Claude Code 插件 Claude Monitor，用于在独立终端窗口中可视化 Claude Code 工作状态。项目经历设计文档 v1.0→v1.2 三次迭代修正、5 个开发阶段、E2E 测试修复、最终成功安装到当前 Claude Code 环境。

## 关键决策
- 技术架构：文件桥接（state.json）+ watchfiles 监听 + Python Textual TUI，零网络依赖
- 显示形态：方案 A 单行紧凑终端面板（信号灯 + 进度条 + Token/费用）
- 三色信号灯映射：绿色 idle/starting/closing，黄色 waiting_user/permission_denied/recoverable_error/state_file_error，红色 working/tool_running/fatal_error
- Hook 全覆盖：12/12 Hook（SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/PostToolUseFailure/PostToolBatch/PermissionRequest/PermissionDenied/Notification/Stop/StopFailure/SessionEnd）
- Token 来源：四级优先级（transcript 解析 > usage 文件 > 工具返回 > unavailable），Stop Hook 只触发刷新不直接提供数据
- SessionEnd 关闭：Hook 只写 closing 状态立即返回，延迟关闭由 TUI 事件循环执行
- 并发安全：filelock + os.replace 原子写入 + 边界值 clamp
- 目录结构：Command 优先（commands/claude-monitor.md），hooks.json 仅参考文档（被 validator 拒绝后移走）
- 安装方式：自建 marketplace.json → claude plugin marketplace add → claude plugin install
- 费用按 DeepSeek 计价，单位可切换 CNY/USD，最终账单以服务商为准

## 待办事项
- 设计文档 3 处勘误：SessionEnd/transcript_path/CLAUDE_PLUGIN_ROOT 确认状态修正
- Phase 0：离线 TUI 验证（monitor/app.py + state.json + watchfiles + 8 demo 状态）
- Phase 1：最小 Hook 接入（4 hooks：SessionStart/UserPromptSubmit/Stop/SessionEnd）
- Phase 2：权限与用户等待状态（3 hooks：PermissionRequest/PermissionDenied/Notification）
- Phase 3：工具活动统计（5 hooks：PreToolUse/PostToolUse/PostToolUseFailure/PostToolBatch/StopFailure）
- Phase 4：Token transcript 解析（monitor/transcript_parser.py + 4 路径兼容 + 费用计算）
- Phase 5：插件化整理（plugin.json + marketplace.json + commands + README）
- E2E 测试：14 事件全生命周期通过 | 并发 4 线程 x5 写入无数据丢失 | JSON 损坏恢复 | 负值 clamp
- 修复 2 个 bug：_init_state_file 不兼容 str 路径 | _ensure_state_structure 不修复已有负值
- 安装到当前环境：marketplace.json 创建 → validate 通过 → marketplace add → install 成功

## 评分
topic:5, keywords:16, decisions:12, todos:10, summary:2, content:5, recency:2
````

---

