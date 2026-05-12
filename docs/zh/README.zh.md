# paper-cli

`paper-cli` 是一个计划中的本地优先、面向 agent 原生使用的文献管理命令行工具。

它的目标是让 AI agent 更容易管理和阅读研究论文。项目不再把 PDF 文件作为主要工作界面，而是构建结构化 paper bundle：其中包含复制后的 PDF、MinerU 转换得到的 Markdown、提取图片、元数据、转换状态和索引。

## 当前状态

设计阶段。当前还没有实现代码。

已经确认的 MVP 方向：

- 导入本地 PDF 文件或文件夹。
- 将每个 PDF 复制到自包含的 paper bundle 中。
- 使用 MinerU 转换 PDF。
- 将 `original.pdf`、`paper.md`、`images/`、`paper.yaml` 和转换状态保存在同一目录。
- 使用元数据优先的命名方式，并支持可配置命名模板。
- 先快速导入，再在转换得到更好元数据后自动重命名 bundle。
- Zotero 和其他来源适配器推迟到后续阶段。

## 计划中的 MVP 命令

```bash
paper init <library-dir>
paper import <pdf-or-folder> --collection <path>
paper import <pdf-or-folder> --inbox
paper convert --pending
paper list
paper status
paper doctor
```

## 计划中的文献库结构

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

当前任务列表见 [TODO.zh.md](TODO.zh.md)。MVP 设计见 [paper-cli-mvp-design.zh.md](paper-cli-mvp-design.zh.md)。

