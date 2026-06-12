#!/usr/bin/env bash
# ============================================================================
# Claude Code Memory Skill — 一键安装脚本
#
# 用法：
#   bash install.sh
#   bash install.sh --with-jieba
#   bash install.sh --check
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "============================================"
echo " Claude Code Memory Skill — 安装"
echo "============================================"
echo ""

# ── 参数 ────────────────────────────────────────────────────
INSTALL_JIEBA=false
CHECK_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --with-jieba) INSTALL_JIEBA=true ;;
        --check) CHECK_ONLY=true ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

# ── Python 检测（验证实际可执行性）───────────────────────────
PYTHON_BIN=""
for candidate in "python3" "python"; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; print(sys.executable)" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}错误：找不到可用的 Python 解释器${NC}"
    exit 1
fi

PY_VER=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  Python: ${GREEN}$PY_VER${NC} ($PYTHON_BIN)"

# ── 检查模式 ────────────────────────────────────────────────
if [ "$CHECK_ONLY" = true ]; then
    echo ""
    echo "运行测试..."
    "$PYTHON_BIN" tests/test_memory_skill.py
    echo ""
    echo -e "${GREEN}检查完成。${NC}"
    exit 0
fi

# ── 创建记忆目录 ────────────────────────────────────────────
echo "  初始化记忆目录..."
mkdir -p memory/topics
if [ ! -f memory/index.json ]; then
    echo "{}" > memory/index.json
fi
if [ ! -f memory/topics/README.md ]; then
    echo "# topics 目录说明" > memory/topics/README.md
fi
echo -e "  ${GREEN}✓${NC} 记忆目录已就绪"

# ── 可选依赖 ────────────────────────────────────────────────
if [ "$INSTALL_JIEBA" = true ]; then
    echo "  安装 jieba（中文分词增强）..."
    "$PYTHON_BIN" -m pip install jieba --quiet 2>/dev/null || \
        echo -e "  ${YELLOW}⚠${NC} jieba 安装失败（不影响核心功能）"
else
    echo -e "  ${YELLOW}ℹ${NC} 跳过 jieba（使用 --with-jieba 安装中文分词增强）"
fi

# ── 运行测试 ────────────────────────────────────────────────
echo ""
echo "运行测试验证..."
if "$PYTHON_BIN" tests/test_memory_skill.py; then
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  安装成功！所有测试通过。${NC}"
    echo -e "${GREEN}============================================${NC}"
else
    echo ""
    echo -e "${RED}测试失败，请检查 Python 环境和依赖。${NC}"
    exit 1
fi

echo ""
echo "下一步："
echo "  1. 将 docs/settings.template.json 中的 Hook 配置"
echo "     合并到 Claude Code 的 settings.json"
echo "  2. 重新启动 Claude Code 以加载 Skill"
echo "  3. 运行 'python scripts/summarize_session.py --help' 查看保存命令"
echo ""
