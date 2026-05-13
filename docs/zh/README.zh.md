# paper-cli

`paper-cli` 是一个本地优先、面向 agent 原生使用的文献管理命令行工具。

它的目标是让 AI agent 更容易管理和阅读研究论文。项目不再把 PDF 文件作为主要工作界面，而是构建结构化 paper bundle：其中包含复制后的 PDF、MinerU 转换得到的 Markdown、提取图片、元数据、转换状态和索引。

## 当前状态

本地文件夹 MVP 已经实现。当前代码支持初始化文献库、导入本地 PDF、通过 MinerU 或 fixture 输出转换待处理 bundle、重建索引、列出论文、查看状态和运行文献库检查。

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
paper list
paper status
paper doctor
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
```

真实 MinerU 转换从环境变量 `MINERU_API_KEY` 读取 API key。

测试或 dry run 可以用 fixture 输出，不走网络：

```bash
python3 -m paper_cli --library /tmp/lib convert --pending --fixture-output /tmp/mineru-fixture --json
```

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
        notes/
          README.md
  inbox/
    <paper-name>/
      paper.yaml
      original.pdf
      paper.md
      images/
      conversion.json
      notes/
        README.md
  indexes/
    papers.jsonl
    jobs.jsonl
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

当前任务列表见 [TODO.zh.md](TODO.zh.md)。MVP 设计见 [paper-cli-mvp-design.zh.md](paper-cli-mvp-design.zh.md)，工程化设计见 [paper-cli-engineering-design.zh.md](paper-cli-engineering-design.zh.md)。

契约和验证文档：

- [paper-yaml.zh.md](contracts/paper-yaml.zh.md)
- [conversion-json.zh.md](contracts/conversion-json.zh.md)
- [cli-json.zh.md](contracts/cli-json.zh.md)
- [source-adapters.zh.md](contracts/source-adapters.zh.md)
- [mineru.zh.md](smoke-tests/mineru.zh.md)

本地测试文献库可以放在 `paper-libraries/` 下。该目录已被 git 忽略，因为里面可能包含复制后的 PDF 和 MinerU 输出。
