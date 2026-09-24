import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from Tools.Bash import Tools_Bash_Description, Bash_Handler
from Tools.File import Tools_File_Description, File_Handler
from anthropic.types import ToolParam
from Hooks.Hooks import trigger_hooks

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SUB_SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Complete the given task, then return a concise final answer."
)


SUB_TOOLS: list[ToolParam] = []
SUB_TOOLS.extend(Tools_File_Description)
SUB_TOOLS.extend(Tools_Bash_Description)
SUB_HANDLERS = {}
SUB_HANDLERS.update(File_Handler)
SUB_HANDLERS.update(Bash_Handler)


def execute_tool(block, handlers: dict) -> str:
    blocked = trigger_hooks("PreToolUse", block)
    if blocked:
        return str(blocked)

    handler = handlers.get(block.name)
    try:
        output = handler(**block.input) if handler else f"Unknown: {block.name}"
    except Exception as e:
        output = f"Error: {e}"

    trigger_hooks("PostToolUse", block, output)
    return str(output)


def extract_text(content) -> str:
    if not isinstance(content, list):
        return str(content)
    return "\n".join(
        getattr(block, "text", "")
        for block in content
        if getattr(block, "type", None) == "text"
    )


def run_subagent(prompt: str) -> str:
    print("\n\033[35m[Subagent started]\033[0m")
    messages = [{"role": "user", "content": prompt}]

    for _ in range(30):
        response = client.messages.create(
            model=MODEL,
            system=SUB_SYSTEM,
            messages=messages,
            tools=SUB_TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            print("\033[35m[Subagent done]\033[0m")
            return extract_text(response.content) or "(no summary)"

        results = []
        for block in tool_calls:
            output = execute_tool(block, SUB_HANDLERS)
            print(f"  \033[90m[sub] {block.name}: {output[:100]}\033[0m")
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                }
            )
        messages.append({"role": "user", "content": results})

    print("\033[35m[Subagent stopped]\033[0m")
    return "Subagent stopped after 30 turns without a final answer."


Tools_SubTask_Description = [
    {
        "name": "task",
        "description": "Run a subagent with fresh conversation context and return its final text.",
        "input_schema": {
            "type": "object",
            "properties": {"prompt": {"type": "string", "minLength": 1}},
            "required": ["prompt"],
        },
    }
]
SubTask_Handler = {
    "task": run_subagent,
}
