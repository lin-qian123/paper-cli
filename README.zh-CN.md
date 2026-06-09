# paper-cli

[English](README.md) | [简体中文](README.zh-CN.md)

> 把堆积如山的 PDF，变成 AI agent 可以直接使用的研究型文献库。

PDF 是论文存在的地方。
Markdown 才是 agent 真正能够工作的地方。

`paper-cli` 是一个 local-first、agent-native 的文献管理 CLI。它会把本地论文集合转换成稳定、可检查、可追踪的论文 bundle：原始 PDF、MinerU Markdown、图片、YAML 元数据、JSON 状态、AI 修复记录、可溯源摘要和分层文献记忆，都会以明确的文件形式保存在磁盘上。

## 为什么需要 paper-cli？

大多数文献管理工具都是为人设计的。

这对收集文献、阅读 PDF、添加标签、同步附件和生成引用来说非常合适。但对 AI agent 来说，传统 PDF 文献库往往并不好用：

- PDF 是版面文档，不是 agent 原生的阅读文本。
- Agent 通常需要临时调用 Python 工具、PDF parser、OCR 脚本或专门的 skill，才能真正读取论文内容。
- GUI 优先的文献管理器往往把重要状态藏在应用数据库、附件目录约定或插件内部。
- 转换结果、图片、元数据、修复决策、摘要和索引很少作为一个稳定的文件系统契约同时暴露出来。

`paper-cli` 选择了另一条路线：每篇论文都是一个自包含目录。Agent 可以直接读取、检查、修复、总结和记忆这些目录，而不需要反向理解某个应用的内部后端。

## 它和其他工具有什么不同？

`paper-cli` 不是要替代 Zotero、Papis、OCR 引擎或 PaperQA 类工具。它们各自解决了重要问题。`paper-cli` 关注的是一个经常缺失的层：面向 AI agent 的、本地持久化的论文工作底座。

| 工具类型 | 面向人的文献库 | Agent 可读文本 | 明确的文件系统契约 | AI 修复 / 抽取状态 | 最适合承担的角色 |
| --- | --- | --- | --- | --- | --- |
| Zotero / 文献管理器 | 很强 | 有限 | 多数由应用管理 | 无 | 收集、引用和组织参考文献 |
| Papis 类 CLI 文献库 | 较好 | 部分支持 | 文件化元数据 | 无 | 轻量的人控论文集合管理 |
| PDF parser / OCR 工具 | 否 | 部分支持 | 通常是单次运行输出 | 无 | 转换单个 PDF |
| Paper QA / RAG 工具 | 部分支持 | 内部消费 | 通常由索引管理 | 部分支持 | 对文档提问 |
| `paper-cli` | 可用，但不是核心 | 一等目标 | 是 | 是 | 为 agent 构建持久论文 bundle |

项目的核心思想很简单：

```text
paper bundle = PDF + Markdown + images + YAML metadata + JSON state + AI outputs
```

也就是说，agent 不需要猜论文在哪里、图片在哪里、转换是否失败、哪些块被修复过、摘要是否生成、collection memory 是否过期。这些证据都在磁盘上。

## 分层 Agent Memory

`paper-cli` 不只是把 PDF 转成 Markdown。它还可以把转换后的论文进一步提炼成 agent 可长期复用的持久记忆：

1. 单篇论文摘要保存在 `extracts/summary/`，包含 source map、block ID、行号范围、文本 hash、章节路径和 graph source block。
2. Collection memory 保存在每个 collection 的 `_memory/` 目录中，用来提炼该 collection 的主题、方法、证据和跨论文联系。
3. Library memory 保存在文献库根目录的 `_memory/` 中，为 agent 提供整个论文库的持久总览。

这不是一次性聊天摘要。Memory 文件是可持久化、可检查、可追溯的研究资产。Agent 可以在之后的任务中重新读取这些记忆，追溯观点来自哪些 source block，并在稳定的研究上下文上继续工作，而不是每次都从头读取 PDF。

## 当前状态

`paper-cli` 当前处于 `v0.1.0` 初始预览版本。

第一版已经可以用于本地 PDF 文献库和 agent 工作流：

- 从本地 PDF 文件或文件夹导入论文，形成自包含 bundle。
- 通过 MinerU serial API、batch API、本地 CLI 或测试 fixture 后端转换 PDF。
- 保留 `original.pdf`、`paper.md`、`images/`、`paper.yaml`、`conversion.json` 和索引。
- 使用 `paper doctor` 做结构检查，使用 `paper doctor --strict` 做更严格的批量审计检查。
- 使用 OpenAI-compatible AI provider 修复元数据和低风险 Markdown 抽取缺陷。
- 抽取带 block、section、graph 和 source-map 溯源的论文骨架摘要。
- 从现有摘要构建 collection-level 和 library-level 的 agent memory。

它还不是一个完整的文献管理器。Zotero、BibTeX/CSL JSON、全文搜索和 review queue 等能力会放在后续阶段。

## 安装

从仓库进行开发或本地使用：

```bash
git clone git@github.com:lin-qian123/paper-cli.git
cd paper-cli
uv run paper --help
```

Editable install：

```bash
python3 -m pip install -e ".[dev]"
paper --help
```

要求：

- Python 3.11+
- 推荐使用 `uv` 进行开发和运行
- 使用 MinerU cloud conversion 时需要 `MINERU_API_KEY`
- 使用 AI repair、summary extraction 和 memory build 时需要 OpenAI-compatible provider

## 快速开始

```bash
uv run paper init /path/to/paper-library
uv run paper --library /path/to/paper-library import /path/to/pdfs --collection "plasma/qed" --json
uv run paper --library /path/to/paper-library convert --pending --dry-run --json
uv run paper --library /path/to/paper-library convert --pending --converter mineru-api-batch --json
uv run paper --library /path/to/paper-library doctor --strict --json
uv run paper --library /path/to/paper-library list --json
```

默认云端后端是 serial `mineru-api`。对于更大的文献库，建议使用 `mineru-api-batch`。

## 配置

MinerU 云端转换读取：

```bash
export MINERU_API_KEY="..."
export MINERU_API_BASE="https://mineru.net/api/v4"  # optional
export MINERU_MAX_WAIT_SECONDS=7200                 # optional
```

AI 命令读取 OpenAI-compatible chat completions provider：

```bash
export PAPER_AI_BASE_URL="https://api.openai.com/v1"
export PAPER_AI_API_KEY="..."
export PAPER_AI_MODEL="gpt-5.4-mini"
```

本地 MinerU 设置可以写入 `paper-cli.yaml`：

```yaml
mineru:
  executable: /path/to/mineru
  local_backend: pipeline
  local_jobs: auto
```

Secrets 应保存在环境变量或未提交的本地配置文件中。

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
```

面向 agent 的命令在适合的地方都支持 `--json`，避免 agent 解析自然语言输出。

## PDF 转换

云端 batch conversion：

```bash
uv run paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-api-batch \
  --batch-size 20 \
  --jobs 4 \
  --json
```

`mineru-api-batch` 会：

- 将 upload-link request 控制在 50 个文件以内；
- 用有界并发上传和下载；
- 在 `conversion.json` 中记录 `batch_id`、`data_id` 和 remote state；
- 尽可能恢复已有 running batch；
- 将超过 MinerU API 页数限制的 PDF 拆分成较小 PDF 后上传。

长 PDF 拆分默认每部分 195 页，为 MinerU API 的 200 页服务上限预留冗余：

```bash
uv run paper --library /path/to/paper-library convert \
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

本地 MinerU conversion：

```bash
uv run paper --library /path/to/paper-library convert \
  --pending \
  --converter mineru-local \
  --local-backend pipeline \
  --jobs 2 \
  --json
```

测试和 dry run 使用的 fixture conversion：

```bash
uv run paper --library /tmp/lib convert \
  --pending \
  --converter local-fixture \
  --fixture-output /tmp/mineru-fixture \
  --json
```

## AI Repair

```bash
uv run paper --library /path/to/paper-library repair --target metadata --dry-run --json
uv run paper --library /path/to/paper-library repair --target markdown --paper sha256:abc --limit 1 --json
uv run paper --library /path/to/paper-library repair --json
```

`paper repair` 默认使用 `--target all`。

它可以：

- 修复 `paper.yaml` 中的元数据；
- 在元数据修复后重命名 bundle；
- 修补低风险的可疑 Markdown 抽取缺陷；
- 写入前创建 bundle-local backup；
- 将最近一次运行记录到 `repair.json`。

高风险科学内容、公式、表格、参考文献和长篇不确定 OCR prose 只会被记录为 warning，不会被自动改写。

## Summary Extraction

```bash
uv run paper --library /path/to/paper-library extract summary --dry-run --json
uv run paper --library /path/to/paper-library extract summary --paper-workers 16 --workers 16 --max-requests 500 --json
uv run paper --library /path/to/paper-library extract summary --paper <id-or-prefix> --force --json
```

`paper extract summary` 读取已转换 bundle，并写入：

```text
extracts/summary/summary.json
extracts/summary/summary.md
extracts/summary/source-map.json
```

它不会修改 source PDF、`paper.md`、`paper.yaml` 或 `repair.json`。Source traceability 通过 block ID、行号范围、文本 hash、章节路径、section block ID 和 graph source block ID 保留下来。目标不是生成一次性 abstract，而是创建一个结构化、可溯源、可被后续 agent 复用的阅读层。

## Memory Build

```bash
uv run paper --library /path/to/paper-library memory build --dry-run --json
uv run paper --library /path/to/paper-library memory build --collection plasma/qed --json
uv run paper --library /path/to/paper-library memory build --force --json
```

`paper memory build` 只消费已有 summary outputs。它会把 source-grounded per-paper summary 转换成 collection-level 和 library-level memory，供 agent 跨会话复用。它写入：

```text
collections/<collection>/_memory/collection-memory.json
collections/<collection>/_memory/collection-memory.md
collections/<collection>/_memory/paper-index.json
_memory/library-memory.json
_memory/library-memory.md
_memory/collection-index.json
```

改变文献库的命令会标记 memory stale；成功的 summary extraction 会自动刷新受影响的 collection 和 library memory。这让 agent 拥有一张持久的文献库地图：不只是文件在哪里，还包括论文讲了什么、collection 之间如何关联、哪些 source 支撑了这些判断。

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
    memory-state.json
  _memory/
    library-memory.json
    library-memory.md
    collection-index.json
```

## 数据与隐私

`paper-cli` 是 local-first 的：bundle metadata、转换后的 Markdown、图片、repair records、summaries 和 indexes 都会写入你选择的本地文献库目录。

只有在你选择需要外部服务的命令时，才会调用外部服务：

- MinerU cloud conversion 会上传 PDF 或拆分后的 PDF parts 到 MinerU。
- AI repair、summary extraction 和 memory build 会把有界文本/证据包发送给配置的 OpenAI-compatible provider。

如果你不希望 provider 接收敏感 PDF 内容，不要对这些 PDF 使用 cloud conversion 或 AI commands。

## 验证

当前版本已经通过：

- `uv run --extra dev pytest -q`
- `uv run --extra dev ruff check src tests`
- QED corpus `mineru-api-batch` validation with 519 PDFs
- 针对 242、270、226 页 PDF 的长 PDF 拆分验证
- AI repair、summary extraction 和 memory build 的 real-provider smoke tests

最新发布细节见 [CHANGELOG.md](CHANGELOG.md)。

## 文档

Contracts：

- [paper-yaml.md](docs/contracts/paper-yaml.md)
- [conversion-json.md](docs/contracts/conversion-json.md)
- [cli-json.md](docs/contracts/cli-json.md)
- [extract-summary-output.md](docs/contracts/extract-summary-output.md)
- [source-adapters.md](docs/contracts/source-adapters.md)

Smoke tests：

- [mineru.md](docs/smoke-tests/mineru.md)
- [ai-repair.md](docs/smoke-tests/ai-repair.md)

开发历史和未完成事项记录在 [TODO.md](TODO.md)。更多中文文档位于 `docs/zh/`。

## 开发

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
make verify
```

本地测试文献库可以放在 `paper-libraries/` 下；这个目录已被 git 忽略，因为其中可能包含复制的 PDF 和生成的 MinerU 输出。

## License

MIT. See [LICENSE](LICENSE).
