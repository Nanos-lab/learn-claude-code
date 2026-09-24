from pathlib import Path
from Permission.Permission import check_permission

WORKDIR = Path.cwd()

HOOKS = {
    "UserPromptSubmit": [],
    "PreToolUse": [],
    "PostToolUse": [],
    "Stop": [],
}


def register_hook(event: str, callback):
    HOOKS[event].append(callback)


def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:  # 返回值 ≠ None → hook 说"停"
            return result
    return None


# 显示工作目录
def context_inject_hook(query: str) -> str | None:
    """Inject current working directory info into every prompt."""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None  # return None = no modification, let prompt through


register_hook("UserPromptSubmit", context_inject_hook)


# 工具调用前检查权限
def permission_hook(block):
    return check_permission(block)  # 返回 True = 允许，返回 False = 拒绝


register_hook("PreToolUse", permission_hook)


# 大文件提醒
def large_output_hook(block, output):
    if len(str(output)) > 100000:
        print(f"[HOOK] ⚠ Large output from {block.name}")


register_hook("PostToolUse", large_output_hook)


# 结束总结
def summary_hook(messages: list):
    tool_count = sum(
        1
        for m in messages
        for b in (m.get("content") if isinstance(m.get("content"), list) else [])
        if isinstance(b, dict) and b.get("type") == "tool_result"
    )
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None


register_hook("Stop", summary_hook)
