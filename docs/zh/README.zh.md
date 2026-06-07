# paper-cli

`paper-cli` 是一个本地优先、面向 agent 原生使用的文献管理命令行工具。

它的目标是让 AI agent 更容易管理和阅读研究论文。项目不再把 PDF 文件作为主要工作界面，而是构建结构化 paper bundle：其中包含复制后的 PDF、MinerU 转换得到的 Markdown、提取图片、元数据、转换状态和索引。

## 当前状态

本地文件夹 MVP 已经实现。当前代码支持初始化文献库、导入本地 PDF、通过串行 MinerU API、MinerU precise API 批量后端、本地 MinerU CLI 后端或 fixture 输出转换待处理 bundle、重建索引、列出论文、查看状态、运行文献库检查，通过 OpenAI-compatible provider 修复已转换 bundle，从转换后的 Markdown 中抽取 AI 文章骨架摘要，并基于已有 summary 输出构建 collection 级和 library 级 agent 记忆。

最近一次真实文献库加固补上了 MinerU 网络重试/退避、单篇或单批 MinerU 等待上限、转换中断后的 job 收尾、用于批处理审计的 strict doctor 模式、防止 OCR 损坏标题导致错误重命名的质量门禁，以及可选择的 `mineru-api-batch` / `mineru-local` 转换后端。

内置 AI repair 阶段已达到阶段性可用状态。它可以修复元数据、根据修复后的元数据同步重命名 bundle，并对低风险 Markdown 抽取缺陷做自动 patch。公式密集、表格、参考文献和数学密集 block 会记录为 `review_only` warning，而不是自动改写。

内置 AI extract summary 阶段已可用。`paper extract summary` 会在 `extracts/summary/` 下生成 block 级总结、section 级骨架和轻量知识图谱，并通过 `source-map.json` 保存 block id、行号、文本 hash 和章节路径，方便后续做左右分栏阅读界面。summary 成功写入后，现在还会自动刷新对应 collection 和 library 的 memory。

内置 AI memory build 阶段现已可用。`paper memory build` 只消费已有 `extracts/summary/summary.json` 输出；缺失 summary 时跳过并报告，不会自动补跑 summary extraction。它会在 collection `_memory/` 下写入 collection 级记忆，在 library root `_memory/` 下写入顶层记忆，保留 paper id、bundle path、summary path、source-map path、section id 和 block id 的追溯关系，并把脏状态记录到 `indexes/memory-state.json`。

已经确认的 MVP 方向：

- 导入本地 PDF 文件或文件夹。
- 将每个 PDF 复制到自包含的 paper bundle 中。
- 使用 MinerU 转换 PDF。
- 将 `original.pdf`、`paper.md`、`images/`、`paper.yaml` 和转换状态保存在同一目录。
- 使用元数据优先的命名方式，并支持可配置命名模板。
- 先快速导入，再在转换得到更好元数据后自动重命名 bundle。
- Zotero 和其他来源适配器推迟到后续阶段。

## 技术方向

MVP 使用 Python 实现，因为它最适合快速完成 PDF 元数据抽取、MinerU API 集成、YAML/JSONL 持久化和测试驱动迭代。

长期架构应该保持语言中立。稳定契约是 paper bundle 格式、元数据文件、索引、CLI 命令、结构化 `--json` 输出和退出码。

Rust 是后续较大范围开发的强候选，尤其适合单二进制 CLI、更强并发、更快索引和更方便的跨平台分发。因此 MVP 不应把 Python 内部实现暴露为产品 API。

## MVP 命令

```bash
paper init <library-dir>
paper import <pdf-or-folder> --collection <path>
paper import <pdf-or-folder> --inbox
paper convert --pending
paper convert --pending --converter mineru-api-batch --batch-size 20 --jobs 4
paper convert --pending --converter mineru-local --local-backend pipeline --jobs 2
paper list
paper status
paper doctor
paper doctor --strict
paper repair
paper memory build
paper extract summary
```

## 开发安装

```bash
uv run --extra dev pytest -v
```

也可以用 editable 方式安装：

```bash
python3 -m pip install -e ".[dev]"
```

推荐的本地验证命令：

```bash
make verify
```

## 基本工作流

```bash
python3 -m paper_cli init /path/to/paper-library
python3 -m paper_cli --library /path/to/paper-library import /path/to/papers --collection "plasma/lwfa" --json
python3 -m paper_cli --library /path/to/paper-library convert --pending --json
python3 -m paper_cli --library /path/to/paper-library status --json
python3 -m paper_cli --library /path/to/paper-library doctor --json
python3 -m paper_cli --library /path/to/paper-library doctor --strict --json
```

真实 MinerU 云端转换从环境变量 `MINERU_API_KEY` 读取 API key。默认 `paper convert --pending` 仍使用串行 `mineru-api` 后端。较大文献库建议使用 `--converter mineru-api-batch`；它会提交 MinerU precise API 批量任务，把单次 upload-link 请求限制在 50 个文件以内，用受限并发上传/下载，在 `conversion.json` 记录 `batch_id` / `data_id`，并在发现已有 running batch 时优先恢复轮询，避免重复提交。`--batch-size` 默认 `20`，云端上传/下载 `--jobs` 默认 `4`。网络请求会自动重试，远端长时间运行任务受 `MINERU_MAX_WAIT_SECONDS` 限制，默认每篇或每批 30 分钟。

本地 MinerU 转换使用已安装的 `mineru` 可执行文件：

```bash
python3 -m paper_cli --library /path/to/paper-library convert --pending --converter mineru-local --local-backend pipeline --jobs 2 --json
```

`--local-backend` 会作为 `-b` 传给 MinerU，例如 `pipeline`。也可以在 `paper-cli.yaml` 中保存 executable 和本地默认设置：

```yaml
mineru:
  executable: /path/to/mineru/.venv/bin/mineru
  local_backend: pipeline
  local_jobs: auto
```

`local_jobs: auto` 目前刻意保持保守，默认解析为一个本地 MinerU 进程，除非用 `--jobs` 或数字配置显式覆盖。本地后端写入与云端后端相同的 bundle 契约：`paper.md`、`images/`、`raw/mineru/` 和 `conversion.json`。

`paper doctor` 默认检查文献库结构完整性。`paper doctor --strict` 会额外报告 pending/failed 转换、悬空 conversion job、陈旧 running 转换、缺失的 MinerU batch 映射字段，以及已配置的本地 MinerU executable 问题，适合批量转换后的成功率审计。

测试或 dry run 可以用 fixture 输出，不走网络：

```bash
python3 -m paper_cli --library /tmp/lib convert --pending --converter local-fixture --fixture-output /tmp/mineru-fixture --json
```

QED 语料的重复验证可以使用本地 validation helper。它会确定性抽样 PDF，创建 symlink 输入目录和 sample list，导入样本，可选运行转换，执行 doctor 检查，统计产物，并在指定 library root 下写 Markdown 报告：

```bash
python3 -m paper_cli validate qed \
  --source /path/to/QED \
  --library-root /path/to/library-root \
  --count 30 \
  --seed 20260525 \
  --converter mineru-local \
  --local-backend pipeline \
  --jobs 1 \
  --replace \
  --json
```

使用 `--no-convert` 可以只做快速导入/list/doctor 验证，不运行 MinerU。

AI 修复使用 OpenAI-compatible chat completions provider，优先从环境变量读取：

```bash
export PAPER_AI_BASE_URL="https://api.openai.com/v1"
export PAPER_AI_API_KEY="..."
export PAPER_AI_MODEL="gpt-4.1-mini"
python3 -m paper_cli --library /path/to/paper-library repair --target metadata --dry-run --json
python3 -m paper_cli --library /path/to/paper-library repair --json
```

`paper repair` 默认等价于 `--target all`。它可以修复 `paper.yaml` 中的元数据和 `paper.md` 中低风险的可疑 Markdown 抽取缺陷；实际写入时会生成 `repair.json`，在修改前创建 bundle 内备份，并重建 `indexes/papers.jsonl`。较高风险的科学内容会保留原文，只记录为 `review_only` warning 供后续检查。

AI extract summary 使用同一套 provider 配置，并且只写抽取产物，不修改论文源文件：

```bash
python3 -m paper_cli --library /path/to/paper-library extract summary --dry-run --json
python3 -m paper_cli --library /path/to/paper-library extract summary --workers 16 --json
python3 -m paper_cli --library /path/to/paper-library extract summary --paper-workers 16 --max-requests 500 --retries 2 --json
python3 -m paper_cli --library /path/to/paper-library extract summary --paper <id-or-prefix> --force --json
```

`paper extract summary` 默认处理已转换且还没有 `extracts/summary/summary.json` 的 bundle。使用 `--force` 可重新生成已有输出，使用 `--paper`、`--collection` 或 `--limit` 可控制范围。并发有三层控制：`--paper-workers` 控制论文层并行，`--workers` 控制单篇论文内 block batch 并行，`--max-requests` 控制全局 provider 请求上限。`--paper-workers` 和 `--workers` 默认值为 `16`；`--max-requests` 默认值为 `500`。论文 worker 会按当前论文数裁剪，block worker 会按当前论文的 block batch 数裁剪。provider 请求会按 `--retries` 重试，默认重试 `2` 次；每次重试之间固定等待 10 秒。它会写入 `summary.json`、`summary.md` 和 `source-map.json`，并在成功后自动刷新受影响的 collection 和 library memory。

AI memory build 复用同一套 provider 配置，但只读取已有 summary 输出：

```bash
python3 -m paper_cli --library /path/to/paper-library memory build --dry-run --json
python3 -m paper_cli --library /path/to/paper-library memory build --collection dual-modality --json
python3 -m paper_cli --library /path/to/paper-library memory build --force --json
```

`paper memory build` 默认处理已经存在 `extracts/summary/summary.json` 的已转换 bundle。缺失 summary 时会跳过并报告，不会自动调用 `paper extract summary`。Collection 级记忆会写入 `collections/<collection>/_memory/collection-memory.json`、`collection-memory.md` 和 `paper-index.json`；顶层 library 记忆会写入 `_memory/library-memory.json`、`library-memory.md` 和 `collection-index.json`。已有 memory 输出默认跳过；当底层 summary hash 变化时会标记 stale，此时使用 `--force` 可重建。`import`、`convert`、`repair` 等会修改文献库状态的命令会在 `indexes/memory-state.json` 中标记 stale；成功的 `extract summary` 会自动清理并刷新对应 memory。

## 文献库结构

```text
paper-library/
  paper-cli.yaml
  collections/
    <collection-path>/
      _memory/
        collection-memory.json
        collection-memory.md
        paper-index.json
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

## 命名

默认命名格式采用元数据优先，并允许用户配置：

```text
{{if language == "zh"}}
{{ firstCreator suffix=" - " }}
{{elseif language == "zh-CN"}}
{{ firstCreator suffix=" - " }}
{{else}}
{{creators  max="1" suffix=" et al. - "}}
{{ endif }}
{{ year suffix=" - " }}
{{ title truncate="100" }}
```

导入器首先根据快速元数据或文件名解析创建可用目录。MinerU 转换后，`paper-cli` 会抽取更准确的元数据，并在名称未被锁定时自动重命名整个 paper bundle。

## 来源适配器

MVP：

- 本地文件夹导入。

后续阶段：

- Zotero 只读导入。
- Zotero linked-file 和 storage resolver。
- Attanger 风格 attachment root 映射。
- BibTeX / CSL JSON 导入。
- 其他文献管理器。

## 开发说明

当前任务列表见 [TODO.zh.md](TODO.zh.md)。MVP 设计见 [paper-cli-mvp-design.zh.md](paper-cli-mvp-design.zh.md)，工程化设计见 [paper-cli-engineering-design.zh.md](paper-cli-engineering-design.zh.md)。AI 修复层设计见 `docs/superpowers/specs/2026-05-21-paper-cli-ai-repair-design.md`，AI extract summary 设计见 `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`，AI memory build 设计见 `docs/superpowers/specs/2026-06-05-paper-cli-memory-build-design.md`，MinerU 转换后端计划见 `docs/superpowers/specs/2026-05-23-paper-cli-mineru-conversion-backends-plan.md`，suspicious block 优化记录见 `docs/development/2026-05-21-ai-repair-suspicious-blocks.md`。

契约和验证文档：

- [paper-yaml.zh.md](contracts/paper-yaml.zh.md)
- [conversion-json.zh.md](contracts/conversion-json.zh.md)
- [cli-json.zh.md](contracts/cli-json.zh.md)
- [source-adapters.zh.md](contracts/source-adapters.zh.md)
- [mineru.zh.md](smoke-tests/mineru.zh.md)
- [ai-repair.zh.md](smoke-tests/ai-repair.zh.md)

本地测试文献库可以放在 `paper-libraries/` 下。该目录已被 git 忽略，因为里面可能包含复制后的 PDF 和 MinerU 输出。
