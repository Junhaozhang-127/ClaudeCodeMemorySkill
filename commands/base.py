"""
commands/base.py — Command 和 CommandResult 数据结构 (v0.6.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CommandResult:
    """命令执行结果。"""
    ok: bool = False
    data: dict = field(default_factory=dict)
    message: str = ""
    error: str = ""


@dataclass
class Command:
    """命令定义。

    Args:
        name: 命令名（主要标识符）。
        aliases: 别名列表。
        description: 简短描述。
        usage: 用法说明。
        args_schema: 参数 schema — {name: {type, required, default, description}}。
        handler: 处理函数 — (dict) -> CommandResult。
    """
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""
    args_schema: dict = field(default_factory=dict)
    handler: callable = None

    def validate_args(self, args: dict) -> tuple[bool, str]:
        """验证传入参数。返回 (is_valid, error_message)。"""
        for arg_name, schema in self.args_schema.items():
            if schema.get("required", False) and arg_name not in args:
                return False, f"缺少必需参数: {arg_name}"
            if arg_name in args:
                val = args[arg_name]
                expected = schema.get("type", "string")
                if expected == "string" and not isinstance(val, str):
                    return False, f"参数 {arg_name} 应为字符串类型"
                if expected == "int" and not isinstance(val, int):
                    return False, f"参数 {arg_name} 应为整数类型"
                if expected == "number" and not isinstance(val, (int, float)):
                    return False, f"参数 {arg_name} 应为数字类型"
                if expected == "bool" and not isinstance(val, bool):
                    return False, f"参数 {arg_name} 应为布尔类型"
        return True, ""

    def format_help(self) -> str:
        """生成帮助文本。"""
        lines = [f"命令: {self.name}"]
        if self.aliases:
            lines.append(f"别名: {', '.join(self.aliases)}")
        lines.append(f"描述: {self.description}")
        lines.append(f"用法: {self.usage}")
        if self.args_schema:
            lines.append("参数:")
            for name, schema in self.args_schema.items():
                req = " [必需]" if schema.get("required") else ""
                desc = schema.get("description", "")
                tp = schema.get("type", "string")
                default = schema.get("default")
                dflt = f" (默认: {default})" if default is not None else ""
                lines.append(f"  {name}: {tp}{req}{dflt} — {desc}")
        return "\n".join(lines)
