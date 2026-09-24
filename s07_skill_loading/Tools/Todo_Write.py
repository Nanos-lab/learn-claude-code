from anthropic.types import ToolParam
from pathlib import Path
import json
import ast

WORKDIR = Path.cwd()


def _normalize_todos(todos):
    """
    Normalize the todos list to ensure it's a list of dictionaries with the required keys.
    """
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return [], "Error: todos must be a list or JSON array string"
    if not isinstance(todos, list):
        return [], "Error: todos must be a list"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return [], f"Error: todos[{i}] must be an object"
        if "content" not in t or "status" not in t:
            return [], f"Error: todos[{i}] missing 'content' or 'status'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return [], f"Error: todos[{i}] has invalid status '{t['status']}'"
    return todos, None


def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for t in CURRENT_TODOS:
        icon = {
            "pending": " ",
            "in_progress": "\033[36m▸\033[0m",
            "completed": "\033[32m✓\033[0m",
        }[t["status"]]
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"


Todo_Write_Description: list[ToolParam] = [
    {
        "name": "todo_write",
        "description": "Create and manage a task list for your current coding session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                            },
                        },
                        "required": ["content", "status"],
                    },
                }
            },
            "required": ["todos"],
        },
    },
]


Todo_Write_TOOLS = {
    "todo_write": run_todo_write,
}
