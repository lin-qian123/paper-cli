# paper-cli

[English](README.md) | [简体中文](README.zh-CN.md)

> 把堆在文件夹里的 PDF，整理成 AI agent 真正读得懂、用得上、记得住的研究型文献库。

<p align="center">
  <img src="assets/icon/paper-cli-icon-legendary-v1.png" width="220" alt="paper-cli 传奇风图标：一捆被魔法点亮的研究论文" />
</p>

PDF 很适合承载论文，却并不适合让 agent 直接工作。
对 agent 来说，更自然的入口是 Markdown、图片、结构化元数据、明确的状态文件，以及可以反复读取的长期记忆。

`paper-cli` 正是为这件事而生的：它把本地论文集合转换成一个个稳定、可检查、可追踪的 paper bundle。每篇论文的原始 PDF、MinerU Markdown、图片、YAML 元数据、JSON 状态、AI 修复记录、可溯源摘要和分层记忆，都会清清楚楚地落在磁盘上。

当前项目图标是一捆带有传奇感的研究资料：文档标记对应 paper bundle，卷轴、环绕的星辉与光点则对应可被 AI agent 调用的持久知识。PNG 为透明背景，适合用于项目主页、应用启动图标和头像。

## 为什么需要 paper-cli？

大多数文献管理工具，首先是为人设计的。

这没有问题。Zotero 这类工具非常适合收集文献、阅读 PDF、整理标签、同步附件和生成引用。但当使用者变成 AI agent 时，传统 PDF 文献库就会暴露出另一面：

- PDF 是版面文档，不是 agent 原生的阅读文本。
- Agent 往往还要临时调用 Python 工具、PDF parser、OCR 脚本或专门的 skill，才能真正读到论文内容。
- GUI 优先的文献管理器通常把重要状态放在应用数据库、附件目录约定或插件内部。
- 转换结果、图片、元数据、修复记录、摘要和索引，很少以一个统一、稳定、可检查的文件系统契约同时暴露出来。

`paper-cli` 选择了另一条路：让每篇论文都变成一个自包含目录。Agent 不需要猜论文在哪里、图片在哪里、转换是否成功、摘要是否过期，也不需要反向理解某个应用的内部结构。它只需要读取文件系统里明确存在的证据。

## 它和其他工具有什么不同？

`paper-cli` 不是 Zotero 的替代品，也不是另一个通用 OCR 工具或问答系统。它更像是 AI 时代论文工作流中缺失的底座：把 PDF 文献库整理成 agent 可以稳定操作的本地知识资产。

| 工具类型 | 面向人的文献库 | Agent 可读文本 | 明确的文件系统结构 | AI 修复 / 抽取记录 | 最适合承担的角色 |
| --- | --- | --- | --- | --- | --- |
| Zotero / 文献管理器 | 很强 | 有限 | 多数由应用管理 | 无 | 收集、引用和组织参考文献 |
| Papis 类 CLI 文献库 | 较好 | 部分支持 | 文件化元数据 | 无 | 轻量的人控论文集合管理 |
| PDF parser / OCR 工具 | 否 | 部分支持 | 通常是单次运行输出 | 无 | 转换单个 PDF |
| Paper QA / RAG 工具 | 部分支持 | 主要在工具内部使用 | 通常由索引管理 | 部分支持 | 对文档提问 |
| `paper-cli` | 可用，但不是核心 | 一等目标 | 是 | 是 | 为 agent 构建持久论文 bundle |

项目的核心思想很朴素：

```text
paper bundle = PDF + Markdown + images + YAML metadata + JSON state + AI outputs
```

这个 bundle 就是 API。它让 agent 面对的不是一堆难以解析的 PDF，也不是某个 GUI 应用背后的隐式数据库，而是一套可以直接读取、检查、追踪和复用的研究文件。

## 分层 Agent 记忆

`paper-cli` 不只负责把 PDF 转成 Markdown。更重要的是，它可以把论文内容进一步提炼成 agent 能长期复用的分层记忆。

第一层是单篇论文摘要，保存在 `extracts/summary/`。它不仅有摘要文本，还保留来源映射、文本块 ID、行号范围、文本 hash、章节路径和图谱来源文本块。也就是说，摘要不是凭空生成的，它可以一路追溯回原文里的具体证据块。

第二层是 collection 记忆，保存在每个 collection 的 `_memory/` 目录中。它会提炼这一组论文的核心主题、常见方法、关键证据和跨论文联系。

第三层是 library 记忆，保存在文献库根目录的 `_memory/` 中。它给 agent 一个全局视角：这个库里有哪些研究方向、哪些 collection 彼此相关、哪些论文构成了重要线索。

这和一次性的聊天摘要不同。Memory 文件是持久化的研究资产。Agent 之后可以重新读取这些记忆，沿着来源文本块追溯论据，并在已有研究上下文上继续工作，而不是每次都从 PDF 开始重新读一遍。

## 当前状态

`paper-cli` 当前处于 `v0.1.0` 初始预览版本。

这个版本已经可以支撑本地 PDF 文献库和 agent 工作流：

- 从本地 PDF 文件或文件夹导入论文，形成自包含 bundle。
- 通过 MinerU 单文件 API、批量 API、本地 CLI 或测试用 fixture 后端转换 PDF。
- 保留 `original.pdf`、`paper.md`、`images/`、`paper.yaml`、`conversion.json` 和索引。
- 使用 `paper doctor` 做结构检查，使用 `paper doctor --strict` 做更严格的批量审计检查。
- 使用兼容 OpenAI 接口的 AI 服务修复元数据和低风险 Markdown 抽取缺陷。
- 抽取带 block、section、graph 和 source-map 溯源的论文骨架摘要。
- 从现有摘要构建 collection 级和 library 级的 agent memory。

它还不是一个完整的文献管理器。Zotero、BibTeX/CSL JSON、全文搜索和 review queue 等能力会放在后续阶段。

## 安装

推荐使用 `pipx` 安装给普通用户使用：

```bash
brew install pipx
pipx ensurepath
pipx install "git+https://github.com/lin-qian123/paper-cli.git"
paper --help
```

`pipx` 会从 GitHub 安装 `paper-cli`，为它创建隔离的 Python 环境，并把 `paper` 命令暴露到 shell 的 `PATH` 上。如果执行 `pipx ensurepath` 后暂时找不到 `paper`，重启终端，或按照 `pipx` 输出的提示更新 shell 配置。

也可以在虚拟环境里用 `pip` 安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install "git+https://github.com/lin-qian123/paper-cli.git"
paper --help
```

安装好以后，正常使用时都直接写 `paper ...`。

要求：

- Python 3.11+
- 推荐使用 `pipx` 进行用户安装
- 使用 MinerU 云端转换时需要 `MINERU_API_KEY`
- 使用 AI 修复、摘要抽取和记忆构建时需要兼容 OpenAI 接口的 AI 服务

## 快速开始

```bash
paper init /path/to/paper-library
paper --library /path/to/paper-library import /path/to/pdfs --collection "plasma/qed" --json
paper --library /path/to/paper-library convert --pending --dry-run --json
paper --library /path/to/paper-library convert --pending --converter mineru-api-batch --json
paper --library /path/to/paper-library doctor --strict --json
paper --library /path/to/paper-library list --json
```

默认云端后端是 `mineru-api-batch`。它提供有界并行，并会自动把超过 MinerU 页数上限的 PDF 拆成每部分最多 195 页。只有明确需要旧串行 API 路径时才使用 `--converter mineru-api`。

## 配置

MinerU 云端转换读取：

```bash
export MINERU_API_KEY="..."
export MINERU_API_BASE="https://mineru.net/api/v4"  # optional
export MINERU_MAX_WAIT_SECONDS=7200                 # optional
```

AI 命令读取兼容 OpenAI Chat Completions 接口的服务配置：

```bash
export PAPER_AI_BASE_URL="https://api.openai.com/v1"
export PAPER_AI_API_KEY="..."
export PAPER_AI_MODEL="gpt-5.4-mini"
export PAPER_AI_TIMEOUT_SECONDS=60  # 每次 provider 请求的 wall-clock 硬时限
```

在启动昂贵的全库任务前，可在不发送论文正文的情况下检查凭证和连通性：

```bash
paper --library /path/to/paper-library provider doctor --json
```

`provider doctor` 使用带鉴权的 `GET /models`，且不会打印 API key。AI 命令支持 `--request-timeout-seconds`；摘要抽取额外支持 `--paper-timeout-seconds` 和 `--max-ai-seconds`。当 provider 请求停滞时，这些上限让命令能以可预期方式失败或继续处理。

本地 MinerU 设置可以写入 `paper-cli.yaml`：

```yaml
mineru:
  executable: /path/to/mineru
  local_backend: pipeline
  local_jobs: auto
```

密钥应保存在环境变量或未提交的本地配置文件中。

## 核心命令

```bash
paper init <library-dir>
paper import <pdf-or-folder> --collection <path>
paper import <pdf-or-folder> --inbox
paper convert --pending
paper list
paper resolve <id-or-prefix-or-name-or-path>
paper get <paper-id-or-query>
paper inspect <paper-id-or-query>
paper status
paper doctor
paper doctor --strict
paper provider doctor
```

面向 agent 的命令在适合的地方都支持 `--json`，避免 agent 解析自然语言输出。

长时间运行的 `convert`、`repair`、`extract summary` 和 `memory build` 会向 stderr 输出简洁进度，并把不含秘密的 run 事件追加到 `indexes/runs.jsonl`。使用 `--json` 时 stdout 仍只保留最终 JSON 结果。

## PDF 转换

云端批量转换：

```bash
paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-api-batch \
  --batch-size 20 \
  --jobs 4 \
  --json
```

`mineru-api-batch` 会：

- 将上传链接请求控制在 50 个文件以内；
- 用有界并发上传和下载；
- 在 `conversion.json` 中记录 `batch_id`、`data_id` 和远端状态；
- 尽可能恢复已有的运行中批次；
- 将超过 MinerU API 页数限制的 PDF 拆分成较小 PDF 后上传。

长 PDF 拆分默认每部分 195 页，为 MinerU API 的 200 页服务上限预留冗余：

```bash
paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-api-batch \
  --max-pages-per-part 195 \
  --json
```

拆分输出会合并回原 bundle：

```text
paper.md
images/part-001/
images/part-002/
raw/mineru/part-001/
raw/mineru/part-002/
conversion.json
```

`conversion.json.raw.split_parts` 会记录页码范围和每个 part 的远端诊断信息。拆分转换会保留已有 `paper.yaml` 元数据，把不确定的标题/作者清理留给 AI metadata repair。

本地 MinerU 转换：

```bash
paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-local \
  --local-backend pipeline \
  --jobs 2 \
  --json
```

测试和 dry run 使用的 fixture 转换：

```bash
paper --library /tmp/lib convert \
  --pending \
  --converter local-fixture \
  --fixture-output /tmp/mineru-fixture \
  --json
```

## AI 修复

```bash
paper --library /path/to/paper-library repair --target metadata --dry-run --json
paper --library /path/to/paper-library repair --target markdown --paper sha256:abc --limit 1 --json
paper --library /path/to/paper-library repair --json
```

`paper repair` 默认使用 `--target all`，也就是同时检查元数据和 Markdown。

它可以：

- 修复 `paper.yaml` 中的元数据；
- 在元数据修复后重命名 bundle；
- 修补低风险的可疑 Markdown 抽取缺陷；
- 写入前创建 bundle-local backup；
- 将最近一次运行记录到 `repair.json`。

高风险科学内容、公式、表格、参考文献和长篇不确定 OCR 文本只会被记录为 warning，不会被自动改写。

## 摘要抽取

```bash
paper --library /path/to/paper-library extract summary --dry-run --json
paper --library /path/to/paper-library extract summary --paper-workers 4 --workers 4 --max-requests 16 --paper-timeout-seconds 900 --max-ai-seconds 7200 --json
paper --library /path/to/paper-library extract summary --paper <id-or-prefix> --force --json
```

`paper extract summary` 读取已转换的 bundle，并写入：

```text
extracts/summary/summary.json
extracts/summary/summary.md
extracts/summary/source-map.json
```

它不会修改原始 PDF、`paper.md`、`paper.yaml` 或 `repair.json`。来源追踪信息会通过文本块 ID、行号范围、文本 hash、章节路径、章节对应的文本块 ID 和图谱来源文本块 ID 保留下来。目标不是生成一次性 abstract，而是创建一个结构化、可溯源、可被后续 agent 复用的阅读层。

## 记忆构建

```bash
paper --library /path/to/paper-library memory build --dry-run --json
paper --library /path/to/paper-library memory build --collection plasma/qed --json
paper --library /path/to/paper-library memory build --force --json
```

`paper memory build` 只使用已经生成的摘要输出。它会把有来源依据的单篇论文摘要，进一步提炼成 collection 级和 library 级 memory，供 agent 跨会话复用。它写入：

```text
collections/<collection>/_memory/collection-memory.json
collections/<collection>/_memory/collection-memory.md
collections/<collection>/_memory/paper-index.json
_memory/library-memory.json
_memory/library-memory.md
_memory/collection-index.json
```

改变文献库的命令会把相关 memory 标记为过期；成功的摘要抽取会自动刷新受影响的 collection 和 library 记忆。这让 agent 拥有一张持久的文献库地图：不只是文件在哪里，还包括论文讲了什么、collection 之间如何关联、哪些原文证据支撑了这些判断。

## 文献库结构

```text
paper-library/
  paper-cli.yaml
  collections/
    <collection-path>/
      <paper-name>/
        paper.yaml
        original.pdf
        paper.md
        images/
        conversion.json
        repair.json
        extracts/
          summary/
            summary.json
            summary.md
            source-map.json
        backups/
        notes/
          README.md
      _memory/
        collection-memory.json
        collection-memory.md
        paper-index.json
  inbox/
    <paper-name>/
      paper.yaml
      original.pdf
      paper.md
      images/
      conversion.json
      repair.json
      extracts/
        summary/
          summary.json
          summary.md
          source-map.json
      backups/
      notes/
        README.md
  indexes/
    papers.jsonl
    jobs.jsonl
    runs.jsonl
    memory-state.json
  _memory/
    library-memory.json
    library-memory.md
    collection-index.json
```

## 数据与隐私

`paper-cli` 是 local-first 的：bundle 元数据、转换后的 Markdown、图片、修复记录、摘要和索引都会写入你选择的本地文献库目录。

只有在你选择需要外部服务的命令时，才会调用外部服务：

- MinerU 云端转换会上传 PDF 或拆分后的 PDF parts 到 MinerU。
- AI 修复、摘要抽取和记忆构建会把有界文本/证据包发送给配置好的 AI 服务。

如果你不希望外部服务接收敏感 PDF 内容，不要对这些 PDF 使用云端转换或 AI 命令。

## 验证

当前版本已经通过：

- `uv run --extra dev pytest -q`
- `uv run --extra dev ruff check src tests`
- 包含 519 篇 PDF 的 QED corpus `mineru-api-batch` 验证
- 针对 242、270、226 页 PDF 的长 PDF 拆分验证
- AI 修复、摘要抽取和记忆构建的真实服务烟测

最新发布细节见 [CHANGELOG.md](CHANGELOG.md)。

## 文档

契约文档：

- [paper-yaml.md](docs/contracts/paper-yaml.md)
- [conversion-json.md](docs/contracts/conversion-json.md)
- [cli-json.md](docs/contracts/cli-json.md)
- [extract-summary-output.md](docs/contracts/extract-summary-output.md)
- [source-adapters.md](docs/contracts/source-adapters.md)

烟测清单：

- [mineru.md](docs/smoke-tests/mineru.md)
- [ai-repair.md](docs/smoke-tests/ai-repair.md)

开发历史和未完成事项记录在 [TODO.md](TODO.md)。更多中文文档位于 `docs/zh/`。

## 开发

```bash
git clone git@github.com:lin-qian123/paper-cli.git
cd paper-cli
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
paper --help
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
make verify
```

`uv run ...` 是在源码仓库里开发时使用的便利方式。面向使用者的命令示例都使用安装后的 `paper` 命令。

本地测试文献库可以放在 `paper-libraries/` 下；这个目录已被 git 忽略，因为其中可能包含复制的 PDF 和生成的 MinerU 输出。

## 许可证

MIT。见 [LICENSE](LICENSE)。
