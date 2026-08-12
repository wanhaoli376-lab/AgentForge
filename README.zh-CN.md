<p align="center">
  <a href="README.md">English</a> · <strong>简体中文</strong>
</p>

# AgentForge

[![CI](https://github.com/wanhaoli376-lab/AgentForge/actions/workflows/ci.yml/badge.svg)](https://github.com/wanhaoli376-lab/AgentForge/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

AgentForge 是一个开源、可扩展、重视安全边界的 AI Agent 框架，提供 Skills、Plugins 和受限工具执行能力。

> **项目状态：Alpha。** AgentForge 已可作为本地 CLI 和开发框架使用，但其子进程控制属于纵深防御，并不等同于完整的操作系统或容器隔离。不要在敏感设备上运行未经审查的 Plugin 或代码。

## 为什么需要 AgentForge

不少 Agent 项目把提示词、工具、代码执行和网络访问紧密耦合在一个应用里。这不仅让能力难以复用，也让授权决策离模型输出太近。AgentForge 将这些职责拆开：

- **Agent Core** 理解任务、选择 Skills、规划有限的 Plugin 调用，并总结结构化结果。
- **Skills** 是针对某类任务的版本化 Markdown 指南，本身不能授予任何权限。
- **Plugins** 通过统一接口暴露经过校验的操作，模型不会直接获得操作系统句柄。
- **权限和策略模块** 在代码层做出最终的允许或拒绝决定。

因此，它更像是本地自动化、开源项目维护和安全研究的可复用基础设施，而不是一个功能固定的 AI 应用。

## 功能状态

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 单 Agent 核心 | 已实现 | Skill 选择 → 计划 → Plugin 执行 → 最终回答 |
| Markdown Skills | 已实现 | YAML 元数据、格式校验、关键词与 LLM 选择 |
| Plugin 接口与注册表 | 已实现 | 操作参数模型、权限声明、结构化结果 |
| Filesystem Plugin | 已实现 | 工作区限制、路径穿越与符号链接检查、敏感路径拦截 |
| Shell Plugin | 实验性 | 仅 argv、`shell=False`、允许列表、超时和环境变量过滤 |
| Python Plugin | 实验性 | AST 策略和独立的 `python -I -S` 子进程 |
| GitHub Plugin | 已实现，只读 | 仓库、Issue、PR、文件与 diff、提交、本地 Issue 草稿 |
| 密钥脱敏 | 已实现 | 常见 OpenAI、GitHub、Bearer、AWS 和运行时显式密钥 |
| 网络策略 | 已实现 | HTTPS/域名允许列表，拒绝私有、本地和元数据 IP |
| 通用 Web/Network Plugin | 未实现 | 后续计划；网络权限默认仍关闭 |
| Plugin/Skill 市场 | 规划中 | 计划在后续版本实现 |

## 架构

```text
用户
  ↓
Agent Core
  ↓
不受信任的 Skill 指引
  ↓
经过校验的执行计划
  ↓
Plugin 接口
  ↓
权限与策略层
  ↓
受限子进程 / API 适配器
  ↓
Filesystem / Shell / Python / GitHub
```

LLM 可以提出操作建议，但不能决定自己是否有权执行。每个 Plugin 操作都会先检查配置权限并校验参数，然后才会进入实现代码。详情见[架构说明](docs/architecture.md)和[安全模型](docs/security-model.md)。

## 快速开始

需要 Python 3.11 或更高版本。

```bash
python -m venv .venv
```

激活虚拟环境：

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

安装当前 Alpha 版本并检查 CLI。PyPI 发行包名是 `agentforge-secure`，命令和 Python 包名仍然是 `agentforge`。

```bash
python -m pip install --pre agentforge-secure
agentforge --help
agentforge doctor
```

在终端中设置 OpenAI API Key，不要把它写进源码或配置文件：

```bash
# macOS / Linux
export OPENAI_API_KEY="your-key"

# Windows PowerShell
$env:OPENAI_API_KEY = "your-key"
```

运行单次任务：

```bash
agentforge run "总结当前仓库的用途和主要模块"
```

也可以启动交互模式：

```text
$ agentforge
AgentForge > 运行测试并解释第一个可以修复的失败
```

Shell 和 Python 执行默认关闭。只有在明确需要这些能力时，才复制示例配置并手动开启相应权限：

```bash
# macOS / Linux
cp agentforge.example.yaml agentforge.yaml

# Windows PowerShell
Copy-Item agentforge.example.yaml agentforge.yaml

agentforge --config agentforge.yaml doctor
agentforge --config agentforge.yaml run "运行测试并解释失败原因"
```

## 配置

AgentForge 通过 `--config` 读取 YAML 或 TOML 配置。默认配置遵循最小权限原则：

```yaml
agent:
  model: gpt-5.6-luna
  api_mode: responses
  api_key_env: OPENAI_API_KEY
workspace:
  root: .
  skills_dir: skills
permissions:
  filesystem_read: true
  filesystem_write: false
  filesystem_delete: false
  shell_execute: false
  python_execute: false
  network_access: false
  github_read: true
  github_write: false
security:
  redact_secrets: true
  command_timeout: 30
  max_output_chars: 50000
```

模型服务可以自定义：OpenAI 或兼容 Responses API 的服务使用 `responses`；只兼容 Chat Completions 的服务使用 `chat_completions`。例如：

```yaml
agent:
  model: provider-model
  api_mode: chat_completions
  base_url: https://provider.example/v1
  api_key_env: MY_LLM_API_KEY
```

```bash
# macOS / Linux
export MY_LLM_API_KEY="your-provider-key"

# Windows PowerShell
$env:MY_LLM_API_KEY = "your-provider-key"

agentforge --config agentforge.yaml doctor
```

`api_key_env` 只保存环境变量名称，真实 Key 不能写进 YAML/TOML。远程 API 地址必须使用 HTTPS；只有 `localhost`、`127.0.0.1` 等回环开发服务可以使用 HTTP。完整说明见 [LLM 提供方配置](docs/llm-providers.md)。可选的 `GITHUB_TOKEN` 与模型 Key 分开管理；GitHub Plugin 无需 Token 也能读取公开仓库，但会受到 GitHub 未认证请求速率限制。

## Skills

Skill 描述某类任务应该如何处理。每个 Skill 都是一个版本化的 `SKILL.md`，包含严格校验的 YAML 头部和 Markdown 指令：

```markdown
---
name: test-runner
version: 0.1.0
description: Run project tests and explain failures.
author: AgentForge contributors
required_plugins: [filesystem, shell]
keywords: [test, pytest, failure]
---
# Test Runner

Run tests only through the Shell Plugin and explain the first actionable failure.
```

内置 Skills：

- `repository-summary`
- `test-runner`
- `code-review`
- `github-maintainer`

Skill 文本始终是不受信任的输入。它可以影响模型的建议，但不能绕过 Plugin 参数模型、路径策略、命令策略或权限检查。详情见 [Skill 开发指南](docs/skill-development.md)和可直接参考的 [project-explainer 示例](examples/skills/project-explainer/)。

## Plugins

| Plugin | 操作 | 所需权限 |
| --- | --- | --- |
| `filesystem` | list、read、create、write、delete | 对应操作的文件系统权限 |
| `shell` | run | `shell.execute` |
| `python` | run | `python.execute` |
| `github` | 仓库、Issue、PR、diff、提交、Issue 草稿 | `github.read`；草稿仅保存在本地 |

社区 Plugin 需要继承 `Plugin`，定义 Pydantic 参数模型和权限元数据，再通过 `PluginRegistry` 显式注册。动态入口发现尚未实现。详情见 [Plugin 开发指南](docs/plugin-development.md)和 [hello_plugin 示例](examples/plugins/hello_plugin/)。

## GitHub 维护工作流

`github-maintainer` Skill 支持：

- 将 Issue 分类为 `bug`、`feature`、`question`、`documentation`、`security` 或 `duplicate candidate`；
- 总结 PR 涉及的模块、风险、建议测试和安全敏感区域；
- 按 Features、Bug Fixes、Security、Documentation 和 Breaking Changes 生成 Release Notes；
- 检查文档与代码是否发生偏移。

它不会自动关闭 Issue、合并 PR 或提交 Issue 草稿。可以从[可运行的分类示例](examples/github-maintainer/README.md)开始体验。

## 安全说明

AgentForge 同时接触 LLM 输出、第三方文本、文件系统、子进程、API Token 和社区扩展，这些都是真实的攻击面。

现有安全控制包括：

- 最小权限默认值和操作级权限检查；
- 工作区路径规范化与符号链接逃逸检查；
- 仅 argv 的子进程、命令允许列表、超时、环境过滤和输出长度限制；
- 独立进程中的保守 Python AST 检查；
- HTTPS/域名允许列表，拒绝本地、私有、链路本地、保留地址和元数据 IP；
- 在日志、LLM 上下文和 Agent 工具结果摘要之前进行密钥脱敏；
- v0.1 的 GitHub API 仅允许 GET；
- 针对路径穿越、命令注入、提示词注入影响、权限绕过和密钥泄漏的测试。

需要注意的限制：

- `ProcessSandbox` **不是**内核沙箱、虚拟机、seccomp 配置或容器。
- Python AST 校验只能提高绕过难度，不能证明任意 Python 代码是安全的。
- 导入的第三方 Plugin 本质上仍是普通 Python，可以在框架介入前执行代码。
- 开启 Shell 执行后，本地测试和项目代码本身也可能是恶意的。
- DNS 校验无法独自消除所有 DNS 重绑定或代理层风险。

开启高风险权限前，请阅读 [SECURITY.md](SECURITY.md)、[安全模型](docs/security-model.md)和[威胁模型](docs/threat-model.md)。

## 开发

```bash
python -m pip install -e ".[dev]"
ruff check src tests
mypy src
pytest
pytest tests/security
```

CI 会运行代码检查、严格类型检查、完整测试、独立安全测试和 PyPI 发行包校验。工作流只有仓库只读权限，也不会向拉取请求暴露密钥。
维护者可以使用需要单独审批的[真实 API 冒烟测试](docs/live-api-testing.md)，发起一次真实的 OpenAI Responses API 请求，同时不向普通 CI 暴露 Environment Secret。
维护者可以按照[发布指南](docs/releasing.md)发布名为 `agentforge-secure` 的 PyPI 发行包。

## 参与贡献

欢迎贡献 Skills、Plugins、测试、文档和聚焦明确的框架改进。请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。涉及安全边界的改动必须包含回归测试并经过人工审查；陌生的拉取请求不能成为启用高权限 CI 凭据或特权自动化的理由。

## 路线图

- **v0.1：** CLI、Agent Core、Skills、Plugins、权限和受限本地执行
- **v0.2：** 更强的进程隔离适配器和更丰富的 GitHub 维护工作流
- **v0.3：** 签名与验证过的 Plugin 注册表设计
- **v0.4：** Skill 注册表、来源元数据和分发工具

路线图描述的是未来计划，不代表当前已经具备这些能力。详情见[项目概览](docs/project-overview.md)。

## 许可证

Copyright 2026 wanhaoli376-lab and AgentForge contributors.

本项目采用 [Apache License 2.0](LICENSE) 许可。
