"""
配置文件加载器 — 从 .mini TOML 文件读取配置

查找顺序：
1. ./.mini  — 当前工作目录（项目级）
2. ~/.mini  — 用户主目录（全局）

配置文件格式 (TOML):

    [provider]
    type = "deepseek"
    api_key = "$DEEPSEEK_API_KEY"   # 支持 $ENV_VAR 引用
    model = "deepseek-v4-pro"
    base_url = "https://api.deepseek.com/v1"

    [agent]
    max_turns = 25
    max_tokens = 4096

    [permissions]
    allow = ["bash:git *", "file_read"]
    deny = ["bash:rm -rf *"]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from mini_agent.types import EngineConfig, PermissionDecision, PermissionRule

# ============================================================
# TOML 解析（兼容 Python 3.10+）
# ============================================================

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]  # Python 3.10 fallback
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


# ============================================================
# Provider 预设（与 openai_provider.py 保持同步）
# ============================================================

_PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-v4-pro",
    },
    "mimo": {
        "provider": "openai",
        "base_url": "https://api.mimo.xiaomi.com/v1",
        "default_model": "mimo-v2.5-pro",
    },
    "qwen": {
        "provider": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-max",
    },
    "glm": {
        "provider": "openai",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4",
    },
    "openrouter": {
        "provider": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "deepseek/deepseek-v4-pro",
    },
    "siliconflow": {
        "provider": "openai",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
    },
    "ollama": {
        "provider": "openai",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
    },
}


# ============================================================
# 配置文件查找
# ============================================================


def find_config_path() -> Path | None:
    """
    按优先级查找 .mini 配置文件

    查找顺序：
    1. ./.mini  — 项目级配置
    2. ~/.mini  — 用户级配置

    Returns:
        找到的配置文件路径，或 None
    """
    candidates = [
        Path.cwd() / ".mini",
        Path.home() / ".mini",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


# ============================================================
# TOML 解析
# ============================================================


def load_config_file(path: Path) -> dict[str, Any]:
    """
    解析 .mini TOML 配置文件

    Args:
        path: 配置文件路径

    Returns:
        解析后的字典

    Raises:
        SystemExit: 解析失败时退出
    """
    if tomllib is None:
        _print_error(
            "缺少 TOML 解析库。请安装 tomli：\n"
            "  pip install tomli\n"
            "（Python 3.11+ 已内置 tomllib，无需额外安装）"
        )
        sys.exit(1)

    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        _print_error(f"配置文件解析失败: {path}\n  {e}")
        sys.exit(1)


# ============================================================
# API Key 解析
# ============================================================


def resolve_api_key(raw: str | None) -> str | None:
    """
    解析 api_key 值，支持 $ENV_VAR 引用

    支持的写法：
    - "sk-ant-xxx"         → 直接使用
    - "$ANTHROPIC_API_KEY" → 读取环境变量
    - "${ANTHROPIC_API_KEY}" → 同上（花括号风格）

    Args:
        raw: 配置文件中的原始值

    Returns:
        解析后的 API Key，或 None
    """
    if not raw:
        return None

    # 去除空白
    raw = raw.strip()

    # $ENV_VAR 或 ${ENV_VAR} 风格
    if raw.startswith("$"):
        var_name = raw[1:]
        if var_name.startswith("{") and var_name.endswith("}"):
            var_name = var_name[1:-1]
        value = os.environ.get(var_name)
        if not value:
            _print_error(
                f"环境变量 {var_name} 未设置。\n"
                f"请设置后重试：export {var_name}=your-api-key"
            )
            sys.exit(1)
        return value

    return raw


# ============================================================
# 构建 EngineConfig
# ============================================================


def build_engine_config(file_config: dict[str, Any]) -> EngineConfig:
    """
    从配置文件字典构建 EngineConfig

    Args:
        file_config: 解析后的 TOML 字典

    Returns:
        EngineConfig 实例
    """
    provider_section = file_config.get("provider", {})
    agent_section = file_config.get("agent", {})
    perm_section = file_config.get("permissions", {})

    # --- Provider ---
    type_raw = provider_section.get("type", "anthropic").lower()

    # 查找预设
    if type_raw in _PROVIDER_PRESETS:
        preset = _PROVIDER_PRESETS[type_raw]
        provider = preset["provider"]
        default_base_url = preset["base_url"]
        default_model = preset["default_model"]
    elif type_raw in ("anthropic", "openai"):
        provider = type_raw
        default_base_url = None
        default_model = (
            "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o"
        )
    else:
        # 未知类型，当作 openai 兼容
        provider = "openai"
        default_base_url = None
        default_model = "gpt-4o"

    # API Key（支持 $ENV_VAR 引用）
    api_key_raw = provider_section.get("api_key")
    # 兼容旧的 api_key_env 字段
    if not api_key_raw and "api_key_env" in provider_section:
        api_key_raw = f"${provider_section['api_key_env']}"

    api_key = resolve_api_key(api_key_raw)

    if not api_key:
        _print_error(
            "配置文件中缺少 api_key。\n"
            "请在 [provider] 中设置：\n"
            '  api_key = "sk-..."\n'
            '  api_key = "$YOUR_ENV_VAR"  # 引用环境变量'
        )
        sys.exit(1)

    model = provider_section.get("model", default_model)
    base_url = provider_section.get("base_url", default_base_url)

    # --- Agent ---
    max_turns = agent_section.get("max_turns", 25)
    max_tokens = agent_section.get("max_tokens", 4096)
    project_root = agent_section.get("project_root", ".")

    # --- Permissions ---
    permission_rules = _parse_permissions(perm_section)

    return EngineConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None,
        max_turns=int(max_turns),
        max_tokens=int(max_tokens),
        project_root=project_root,
        permission_rules=permission_rules,
        auto_compact=True,
        compact_threshold=80000,
    )


def _parse_permissions(section: dict[str, Any]) -> list[PermissionRule]:
    """
    解析 [permissions] 配置

    支持格式：
    [permissions]
    allow = ["bash:git *", "file_read"]
    deny = ["bash:rm -rf *"]
    """
    rules: list[PermissionRule] = []

    for decision_key, decision in [("allow", PermissionDecision.ALLOW), ("deny", PermissionDecision.DENY)]:
        entries = section.get(decision_key, [])
        for entry in entries:
            if ":" in entry:
                tool_name, pattern = entry.split(":", 1)
            else:
                tool_name = entry
                pattern = None
            rules.append(PermissionRule(
                tool=tool_name.strip(),
                decision=decision,
                pattern=pattern.strip() if pattern else None,
            ))

    return rules


# ============================================================
# 错误输出
# ============================================================

_RED = "\033[31m"
_RESET = "\033[0m"


def _print_error(msg: str) -> None:
    print(f"{_RED}错误:{_RESET} {msg}", file=sys.stderr)
