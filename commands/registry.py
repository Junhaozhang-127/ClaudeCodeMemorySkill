"""
commands/registry.py — CommandRegistry 命令注册中心 (v0.6.0)
"""

from __future__ import annotations

from commands.base import Command, CommandResult


class CommandRegistry:
    """命令注册器。

    管理所有命令的注册、查找和分发。
    """

    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}

    def register(self, command: Command) -> None:
        """注册命令。"""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> Command | None:
        """按名称或别名查找命令。"""
        if name in self._commands:
            return self._commands[name]
        real_name = self._aliases.get(name)
        if real_name:
            return self._commands.get(real_name)
        return None

    def list_all(self) -> list[Command]:
        """列出所有已注册命令。"""
        return list(self._commands.values())

    def dispatch(self, name: str, args: dict) -> CommandResult:
        """分发并执行命令。

        Args:
            name: 命令名或别名。
            args: 参数字典。

        Returns:
            CommandResult。
        """
        cmd = self.get(name)
        if cmd is None:
            suggestions = self._suggest(name)
            msg = f"未知命令: {name}"
            if suggestions:
                msg += f"。您是否要找: {', '.join(suggestions)}?"
            return CommandResult(ok=False, message="未找到命令", error=msg)

        valid, err = cmd.validate_args(args)
        if not valid:
            return CommandResult(ok=False, message="参数错误", error=err)

        if cmd.handler is None:
            return CommandResult(ok=False, message="命令未实现",
                                error=f"命令 {cmd.name} 没有 handler")

        try:
            return cmd.handler(args)
        except Exception as e:
            return CommandResult(ok=False, message="命令执行失败",
                                error=str(e))

    def _suggest(self, name: str) -> list[str]:
        """给出相近命令建议（编辑距离 ≤ 3）。"""
        candidates = list(self._commands.keys())
        suggestions = []
        for c in candidates:
            d = _edit_distance(name, c)
            if d <= 3:
                suggestions.append(c)
        if not suggestions:
            # 返回 name 是某个命令名子串的候选
            for c in candidates:
                if name in c or c in name:
                    suggestions.append(c)
        return suggestions[:3]


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein 编辑距离。"""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,  # delete
                curr[j] + 1,      # insert
                prev[j] + (0 if ca == cb else 1),  # substitute
            ))
        prev = curr
    return prev[-1]


# 全局注册表
_global_registry: CommandRegistry | None = None


def get_registry() -> CommandRegistry:
    """获取全局命令注册表（懒加载）。"""
    global _global_registry
    if _global_registry is None:
        _global_registry = CommandRegistry()
        _register_builtins(_global_registry)
    return _global_registry


def _register_builtins(registry: CommandRegistry) -> None:
    """注册内置命令。"""
    from commands.memory_save import SAVE_COMMAND
    from commands.memory_retrieve import RETRIEVE_COMMAND
    from commands.memory_rebuild import REBUILD_COMMAND
    from commands.memory_manage import MANAGE_COMMAND

    registry.register(SAVE_COMMAND)
    registry.register(RETRIEVE_COMMAND)
    registry.register(REBUILD_COMMAND)
    registry.register(MANAGE_COMMAND)
