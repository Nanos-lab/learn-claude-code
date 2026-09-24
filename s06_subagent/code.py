#!/usr/bin/env python3
"""
s06_subagent.py - Subagents

The task tool runs a second agent loop with a fresh message list. Both
loops share the working directory, but only the final text returns to
the parent conversation.

    Parent agent                    Subagent
    +------------------+            +------------------+
    | messages=[...]   |            | messages=[prompt]|
    |                  |   task     |                  |
    | tool: task       | ---------> | own agent loop   |
    |                  |            | base tools only  |
    | tool_result      | <--------- | final text       |
    +------------------+            +------------------+

The subagent has no task tool, so it cannot delegate again.
"""

import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from anthropic.types import ToolParam

from Permission.Permission import check_permission
from Hooks.Hooks import trigger_hooks

from Tools.File import Tools_File_Description, File_Handler
from Tools.Bash import Tools_Bash_Description, Bash_Handler
from Tools.TodoWrite import Tools_TodoWrite_Description, TodoWrite_Handler
from Tools.SubTask import Tools_SubTask_Description, SubTask_Handler

load_dotenv(override=True)
WORKDIR = Path.cwd()
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]

SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Before starting any task, use todo_write to plan your steps. "
    "Update ONLY ONE todo's status per todo_write call — "
    "mark it in_progress before you start that step, "
    "and completed immediately after finishing that step, before moving to the next."
)
# ── Tool definition: just bash ────────────────────────────
TOOLS: list[ToolParam] = []
TOOLS.extend(Tools_File_Description)
TOOLS.extend(Tools_Bash_Description)
TOOLS.extend(Tools_TodoWrite_Description)
TOOLS.extend(Tools_SubTask_Description)
TOOL_HANDLERS = {}
TOOL_HANDLERS.update(File_Handler)
TOOL_HANDLERS.update(Bash_Handler)
TOOL_HANDLERS.update(TodoWrite_Handler)
TOOL_HANDLERS.update(SubTask_Handler)


# ── The core pattern: a while loop that calls tools until the model stops ──
def agent_loop(messages: list):
    rounds_since_todo = 0
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # If the model didn't call a tool, we're done
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        if not tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append({"role": "user", "content": force})
                continue
            return

        # Execute each tool call, collect results
        results = []
        used_todo = False
        for block in tool_calls:
            print(f"\033[33m> {block.name}\033[0m")
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
            try:
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
            except Exception as e:
                output = f"Error: {e}"
            trigger_hooks("PostToolUse", block, output)
            if block.name == "todo_write":
                used_todo = True
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )
        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            results.append(
                {"type": "text", "text": "<reminder>Update your todos.</reminder>"}
            )
            rounds_since_todo = 0
        # Feed tool results back, loop continues
        messages.append({"role": "user", "content": results})


# ── Entry point ──────────────────────────────────────────
if __name__ == "__main__":
    print("s06: Subagent - fresh messages, final text returns")
    print("Enter a question, press Enter to send. Type q to quit.\n")

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
        # Print the model's final text response
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if getattr(block, "type", None) == "text":
                    print(block.text)
        print()
