#!/usr/bin/env python3
"""
s07: Skill Loading — two-level on-demand knowledge injection.

  Layer 1 (cheap, always present):
    SYSTEM prompt includes skill names + one-line descriptions (~100 tokens/skill)
    "Skills available: agent-builder, code-review, mcp-builder, pdf"

  Layer 2 (expensive, on demand):
    Agent calls load_skill("code-review") → full SKILL.md content
    injected via tool_result (~2000 tokens/skill)

  skills/
    agent-builder/SKILL.md
    code-review/SKILL.md
    mcp-builder/SKILL.md
    pdf/SKILL.md

Changes from s06:
  + build_system() — scan skills/ dir at startup, inject catalog into SYSTEM
  + load_skill(name) — return full SKILL.md content via tool_result
  + SKILLS_DIR config
  Loop unchanged: load_skill auto-dispatches via TOOL_HANDLERS.

Run: python s07_skill_loading/code.py
Needs: pip install anthropic python-dotenv pyyaml + ANTHROPIC_API_KEY in .env
"""

import os
from pathlib import Path

from anthropic import Anthropic
from anthropic.types import ToolParam
from dotenv import load_dotenv

load_dotenv(override=True)
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"
client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ["MODEL_ID"]
CURRENT_TODOS: list[dict] = []


# s07: Skill catalog scan (used by build_system below)
from Tools.Skill_Loader import list_skills


# s07: SYSTEM includes skill catalog (cheap — just names + descriptions)
def build_system() -> str:
    """Build SYSTEM prompt with skill catalog injected at startup."""
    catalog = list_skills()
    return (
        f"You are a coding agent at {WORKDIR}. "
        f"Skills available:\n{catalog}\n"
        "Use load_skill to get full details when needed."
    )


SYSTEM = build_system()

# ═══════════════════════════════════════════════════════════
#  Tool Registry — all tools from s02-s07
# ═══════════════════════════════════════════════════════════
from Tools.File_Handle import File_Handle_TOOLS, File_Handle_Tools_Description
from Tools.Todo_Write import Todo_Write_Description, Todo_Write_TOOLS
from Tools.Sub_Task import Sub_Task_Description, Sub_Task_TOOLS
from Tools.Skill_Loader import Skill_Loader_Description, Skill_Loader_Tools

TOOLS: list[ToolParam] = []
TOOLS.extend(File_Handle_Tools_Description)
TOOLS.extend(Todo_Write_Description)
TOOLS.extend(Sub_Task_Description)
TOOLS.extend(Skill_Loader_Description)

TOOL_HANDLERS = {}
TOOL_HANDLERS.update(File_Handle_TOOLS)
TOOL_HANDLERS.update(Todo_Write_TOOLS)
TOOL_HANDLERS.update(Sub_Task_TOOLS)
TOOL_HANDLERS.update(Skill_Loader_Tools)

# ═══════════════════════════════════════════════════════════
#  FROM s04 (unchanged): Hook System
# ═══════════════════════════════════════════════════════════

from Hooks.hooks import trigger_hooks

# ═══════════════════════════════════════════════════════════
#  FROM s04 (unchanged): Hook System
# ═══════════════════════════════════════════════════════════

from Context_Compact.Context_Compact import (
    tool_result_budget,
    snip_compact,
    micro_compact,
    compact_history,
    reactive_compact,
    estimate_size,
    CONTEXT_LIMIT,
)

# ═══════════════════════════════════════════════════════════
#  agent_loop — same as s05-s06 + nag reminder
# ═══════════════════════════════════════════════════════════

rounds_since_todo = 0
MAX_REACTIVE_RETRIES = 1  # retry limit for reactive compact


def agent_loop(messages: list):
    reactive_retries = 0
    while True:
        # s08 change: three preprocessors (0 API calls, cheap first)
        # Order matches CC source: budget → snip → micro
        messages[:] = tool_result_budget(messages)  # L3: persist large results first
        messages[:] = snip_compact(messages)  # L1: trim middle
        messages[:] = micro_compact(messages)  # L2: old result placeholders

        # s08 change: tokens still over threshold → LLM summary (1 API call)
        if estimate_size(messages) > CONTEXT_LIMIT:
            print("[auto compact]")
            messages[:] = compact_history(messages)

        try:
            response = client.messages.create(
                model=MODEL,
                system=SYSTEM,
                messages=messages,
                tools=TOOLS,
                max_tokens=8000,
            )
            reactive_retries = 0  # reset on successful API call
        except Exception as e:
            if (
                "prompt_too_long" in str(e).lower()
                or "too many tokens" in str(e).lower()
            ) and reactive_retries < MAX_REACTIVE_RETRIES:
                print("[reactive compact]")
                messages[:] = reactive_compact(messages)
                reactive_retries += 1
                continue
            raise

        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\033[36m> {block.name}\033[0m")

            # s08: compact tool triggers compact_history, not a no-op string
            if block.name == "compact":
                messages[:] = compact_history(messages)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "[Compacted. Conversation history has been summarized.]",
                    }
                )
                messages.append({"role": "user", "content": results})
                break  # end current turn, start fresh with compacted context

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
            print(str(output)[:200])
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": str(output)}
            )
        else:
            # normal path: no compact was called
            messages.append({"role": "user", "content": results})
            continue
        # compact was called: results already appended above
        continue


if __name__ == "__main__":
    print("s08: Skill Loading — catalog in SYSTEM, content on demand")
    print("Type a question, press Enter. Type q to quit.\n")

    history = []
    while True:
        try:
            query = input("\033[36ms08 >> \033[0m")
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
