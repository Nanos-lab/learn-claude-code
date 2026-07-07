#!/usr/bin/env python3
"""
s06: Subagent — spawn sub-agents with fresh messages[] for context isolation.

  Parent Agent                           Subagent
  +------------------+                  +------------------+
  | messages=[...]   |                  | messages=[task]  | <-- fresh
  |                  |   dispatch       |                  |
  | tool: task       | ---------------> | own while loop   |
  |   prompt="..."   |                  |   bash/read/...  |
  |                  |   summary only   |   (max 30 turns) |
  | result = "..."   | <--------------- | return last text |
  +------------------+                  +------------------+
        ^                                      |
        |       intermediate results DISCARDED  |
        +--------------------------------------+

  Subagent tools: bash, read, write, edit, glob (NO task — no recursion)

Changes from s05:
  + task tool + spawn_subagent() with fresh messages[]
  + Safety limit: max 30 turns per subagent
  + extract_text() helper
  Subagent cannot spawn sub-subagents (no task tool in sub_tools).
  Main loop unchanged: task auto-dispatches via TOOL_HANDLERS.

Run: python s06_subagent/code.py
Needs: pip install anthropic python-dotenv + ANTHROPIC_API_KEY in .env
"""

import ast, json, os, subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from anthropic.types import ToolParam

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
CURRENT_TODOS: list[dict] = []

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "For complex sub-problems, use the task tool to spawn a subagent."
)


# ═══════════════════════════════════════════════════════════
#  FROM s02-s05 (unchanged): Tool Implementations
# ═══════════════════════════════════════════════════════════
from Tools.File_Handle import File_Handle_TOOLS, File_Handle_Tools_Description
from Tools.Todo_Write import Todo_Write_TOOLS, Todo_Write_Description

TOOLS: list[ToolParam] = []
TOOLS.extend(File_Handle_Tools_Description)
TOOLS.extend(Todo_Write_Description)
TOOL_HANDLERS = {}
TOOL_HANDLERS.update(File_Handle_TOOLS)
TOOL_HANDLERS.update(Todo_Write_TOOLS)


# Add task tool to parent's tools
from Tools.Sub_Task import Sub_Task_Description, Sub_Task_TOOLS

TOOLS.extend(Sub_Task_Description)
TOOL_HANDLERS.update(Sub_Task_TOOLS)

# ═══════════════════════════════════════════════════════════
#  FROM s04 (unchanged): Hook System
# ═══════════════════════════════════════════════════════════

from Hooks.hooks import trigger_hooks

# ═══════════════════════════════════════════════════════════
#  agent_loop — same as s05 + nag reminder, task auto-dispatches
# ═══════════════════════════════════════════════════════════

rounds_since_todo = 0


def agent_loop(messages: list):
    global rounds_since_todo
    while True:
        # s05: nag reminder
        if rounds_since_todo >= 3 and messages:
            messages.append(
                {"role": "user", "content": "<reminder>Update your todos.</reminder>"}
            )
            rounds_since_todo = 0

        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return

        rounds_since_todo += 1
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(blocked),
                    }
                )
                continue

            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"

            trigger_hooks("PostToolUse", block, output)

            if block.name == "todo_write":
                rounds_since_todo = 0

            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )

        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    print("s06: Subagent — spawn sub-agents with fresh context, summary only")
    print("Type a question, press Enter. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("\033[36ms06 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        trigger_hooks("UserPromptSubmit", query)
        history.append({"role": "user", "content": query})
        agent_loop(history)
        for block in history[-1]["content"]:
            if getattr(block, "type", None) == "text":
                print(block.text)
        print()
