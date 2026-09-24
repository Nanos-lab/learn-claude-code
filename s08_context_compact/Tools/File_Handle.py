from anthropic.types import ToolParam
from pathlib import Path

WORKDIR = Path.cwd()


def safe_path(p: str) -> Path:
    # 1. 显式 resolve() 工作目录，消除 Windows 下因盘符大小写不一致（如 c:\ 与 C:\）导致的越界判定失败
    resolved_workdir = WORKDIR.resolve()

    # 2. 拼接并 resolve 目标路径
    path = (resolved_workdir / p).resolve()

    if not path.is_relative_to(resolved_workdir):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_create_file(path: str, content: str = "") -> str:
    try:
        file_path = safe_path(path)
        if file_path.exists():
            return f"Error: File already exists at {path}. Use edit_file or write_file to modify it."
        # 自动创建父级目录
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 写入初始内容（默认为空）
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully created file {path} with {len(content)} bytes."
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int | None = None) -> str:
    try:
        # 3. 显式指定 encoding="utf-8" 读取，避免 Windows 系统默认的 gbk 编码导致解码失败
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 4. 显式指定 encoding="utf-8" 写入
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_delete_file(path: str) -> str:
    try:
        file_path = safe_path(path)
        if not file_path.exists():
            return f"Error: File does not exist at {path}"
        if file_path.is_dir():
            return f"Error: {path} is a directory. This tool only deletes individual files."

        file_path.unlink()
        return f"Successfully deleted file {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        file_path = safe_path(path)
        # 5. 读写时均采用 utf-8，确保在修改文件时不会破坏原本的字符编码
        text = file_path.read_text(encoding="utf-8")
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_glob(pattern: str) -> str:
    import glob as g

    try:
        results = []
        for match in g.glob(pattern, root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


File_Handle_Tools_Description: list[ToolParam] = [
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_file",
        "description": "Create a new file in the workspace. Fails if the file already exists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                },
                "content": {
                    "type": "string",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file from the workspace. Fails if the file does not exist or is a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in a file once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
]


File_Handle_TOOLS = {
    "read_file": run_read,
    "create_file": run_create_file,
    "write_file": run_write,
    "edit_file": run_edit,
    "delete_file": run_delete_file,
    "glob": run_glob,
}
