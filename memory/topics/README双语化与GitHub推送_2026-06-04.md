# README双语化与GitHub推送

> 更新时间：2026-06-04 17:07:57

## 摘要

用户要求为README增加语言切换功能，默认展示英文。尝试了单文件CSS切换方案，但GitHub过滤style标签导致CSS裸露显示为乱码。最终采用双文件方案：README.md（英文，默认）+ README.zh-CN.md（中文），顶部各有语言切换链接。每次修改后提交并推送到GitHub。

## 关键词

README双语化与GitHub推送, README, CSS, GitHub, style, zh-CN, 用户要求为, 增加语言切换功能, 默认展示英文, 尝试了单文件

## 关键决策

- 尝试了单文件CSS切换方案，但GitHub过滤style标签导致CSS裸露显示为乱码
- 最终采用双文件方案：README.md（英文，默认）+ README.zh-CN.md（中文），顶部各有语言切换链接

## 待办事项

- 用户要求为README增加语言切换功能，默认展示英文

## 原始对话摘录

````text
用户要求为README增加语言切换功能，默认展示英文。尝试了单文件CSS切换方案，但GitHub过滤style标签导致CSS裸露显示为乱码。最终采用双文件方案：README.md（英文，默认）+ README.zh-CN.md（中文），顶部各有语言切换链接。每次修改后提交并推送到GitHub。
````

---

