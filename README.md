# Learn Claude Code — Harness 工程实践（Windows 学习分支）

> 本仓库是 [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 的个人学习分支（`my-feature`），用于逐章拆解 Agent Harness 的工程实现。
>
> 原项目面向 Unix/Linux（默认 `bash`），本分支针对 **Windows (cmd.exe / PowerShell)** 做了适配；原项目 `code.py` 将所有逻辑集中在单文件中，本分支将不同关注点拆到独立模块（`Tools/`、`Permission/`、`Hooks/`），便于单独阅读和调试每一层。
>
> 当前进度：已学完 **s01 ~ s06**。

---

## 这个分支相对原项目做了什么

| 方面 | 原项目 | 本分支 |
|------|--------|--------|
| 目标平台 | Unix/Linux，命令走 `bash` | Windows，命令走 `cmd.exe`；`Bash.py` 里的危险命令名单换成 Windows 语义（`rd /s`、`del /f /s /q`、`format`、`shutdown` 等） |
| 代码组织 | 每章一个 `code.py`，所有逻辑（工具定义、权限、hooks）写在同一文件 | 按关注点拆成独立模块：`Tools/Bash.py`、`Tools/File.py`、`Tools/TodoWrite.py`、`Tools/SubTask.py`、`Permission/Permission.py`、`Hooks/Hooks.py`；`code.py` 只保留 `agent_loop` 和入口逻辑，负责组装（import + 注册） |
| 路径安全 | `safe_path` 用 POSIX 风格校验 | 沿用 `Path.resolve().is_relative_to(WORKDIR)` 的思路，但校验对象是 Windows 路径（盘符、反斜杠），避免工具跨出工作目录 |
| 权限规则 | 针对 `rm -rf`、`sudo` 等 Unix 命令 | `Permission.py` 的 `DENY_LIST` 替换为 Windows 对应命令：`rd /s`、`rmdir /s`、`del /f /s /q`、`diskpart`、`runas`、`reg delete`、`vssadmin delete`、`cipher /w` |

模块拆分之后，每一章新增的能力基本只体现为「多 import 一个模块 + 在 `TOOL_HANDLERS` 里多注册一条」，`agent_loop` 本身的改动被压缩到最小，方便对比相邻两章的 diff。

---

## 环境准备

```powershell
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY / MODEL_ID（或替换成 GLM、Kimi、DeepSeek 等兼容 Anthropic 协议的服务商）
```

每一章都是独立可运行的入口：

```powershell
python s01_agent_loop/code.py
python s06_subagent/code.py
```

---

## 章节笔记：s01 ~ s06

### s01 Agent Loop — 最小闭环

核心就是一个 `while` 循环：调用模型 → 判断是否有 `tool_use` → 没有就退出，有就执行 `run_bash` → 把 `tool_result` 塞回 `messages` → 继续循环。这一章只有一个工具（`bash`），没有权限校验、没有模块拆分，`code.py` 单文件即是全部逻辑，用来建立「Agent = LLM + 工具执行的反馈循环」这个最基础的心智模型。

### s02 Tool Use — 从一个工具到工具分发表

`bash` 之外新增 `read_file` / `write_file` / `edit_file` / `glob` 四个文件工具，拆进 `Tools/File.py`，`bash` 单独拆进 `Tools/Bash.py`。`agent_loop` 里原本硬编码的 `run_bash(...)` 调用换成 `TOOL_HANDLERS.get(block.name)` 的分发表模式，模型可以在同一轮返回多个 `tool_use`，循环体统一遍历执行。`safe_path` 在这一章引入，用 `Path.resolve().is_relative_to(WORKDIR)` 防止文件工具越权访问工作目录之外的路径。

### s03 Permission — 三道闸门

在工具执行前插入 `check_permission(block)`，`agent_loop` 只多了一个 `if` 判断。`Permission.py` 里实际是三层校验：

1. **硬拒绝列表**（`DENY_LIST`）：命中直接拒绝，不问用户，覆盖 `rd /s`、`format`、`diskpart`、`shutdown` 等 Windows 高危命令。
2. **规则匹配**（`PERMISSION_RULES`）：按工具类型分别校验，文件工具检查路径是否越出工作目录，`bash` 检查是否包含 `rm`/`del` 等破坏性命令词（用正则 `DESTRUCTIVE_COMMAND_WORD` 做词边界匹配，避免误伤 `format` 这类子串）。
3. **用户审批**（`ask_user`）：命中规则但不在硬拒绝列表时，终端交互询问是否放行。

### s04 Hooks — 把扩展点做成注册表

引入 `Hooks.py`，定义四个生命周期事件：`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`Stop`，每个事件是一个回调列表，`trigger_hooks(event, *args)` 依次执行，任何回调返回非 `None` 就短路返回（用作"拦截"信号）。s03 里直接写在 `agent_loop` 里的 `check_permission` 调用，在这一章被收编成 `PreToolUse` 的一个 hook，权限系统和主循环解耦。这一章也是本分支模块化最关键的一步：之后新增能力大多以"注册一个 hook"或"注册一个工具"的方式接入，不再需要改 `agent_loop`。

### s05 TodoWrite — 让 Agent 先规划再动手

新增 `todo_write` 工具（`Tools/TodoWrite.py`），本身不执行任何实际操作，只维护一个带状态（`pending` / `in_progress` / `completed`）的任务列表并渲染成文本。配套机制是一个"唠叨提醒"（nag reminder）：循环里用 `rounds_since_todo` 计数，连续 3 轮工具调用没有触碰 `todo_write` 就在结果里追加 `<reminder>Update your todos.</reminder>`。

实测中发现这套机制存在两个局限：

- **计数器是滞后触发的**：默认 `SYSTEM` 提示完全不提规划，模型可能在前 3 轮里都不调用 `todo_write`，得等第 4 轮才被提醒，"开局先规划"完全靠模型自觉。把 `SYSTEM` 改成显式要求"任务开始前先用 `todo_write` 规划"之后，才能观察到 Agent 首轮响应里包含 `todo_write`。
- **`TodoManager.update()` 不校验状态跳变**：一次 `todo_write` 调用可以把全部任务从 `pending` 直接改成 `completed`，没有"只能变更一个任务状态"或"必须经过 `in_progress`"之类的强制约束，模型倾向于把简单任务一次性做完再补一次全量更新，看起来像是"没有过程直接完成"。这是 prompt 层软约束和 harness 层缺少硬校验共同作用的结果。

### s06 Subagent — 给任务分配一个干净的子上下文

新增 `task` 工具（`Tools/SubTask.py`），本质是运行第二个独立的 `agent_loop`（`run_subagent`）：子 agent 有自己全新的 `messages`（只包含传入的 `prompt`），使用一份缩小的工具集（`SUB_TOOLS` = 文件工具 + `bash`，没有 `todo_write`、没有 `task` 本身，避免递归委派），跑最多 30 轮后把最终文本抽取出来（`extract_text`）作为 `tool_result` 返回给父级对话。父子 agent 共享同一个工作目录，但上下文互不污染——子 agent 看不到父级对话历史，父级也只拿到子 agent 的最终结论，不会被子 agent 执行过程中的中间工具调用淹没上下文。

---

## 目录结构约定

每一章遵循同样的骨架，方便横向对比：

```
sNN_xxx/
  code.py               # agent_loop + 入口，负责组装当前章节的工具/hook
  Tools/                 # 本章启用的工具实现 + Anthropic tool schema
  Permission/            # 权限校验逻辑（s03 起出现）
  Hooks/                 # 生命周期 hook 注册（s04 起出现）
  README.md / README.en.md / README.ja.md
```

---

## 下一步

继续从 s07（skill loading）开始，学习技能加载、上下文压缩、记忆系统等更进阶的 harness 能力。
