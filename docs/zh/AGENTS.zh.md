# AGENTS.md 中文版

## 项目目标

将 `paper-cli` 开发为一个本地优先、面向 agent 原生使用的文献管理命令行工具。

项目目标是让 AI agent 可以直接管理和阅读研究论文：把以 PDF 为中心的文献集合转化为结构化 paper bundle，其中包含复制后的 PDF、MinerU 转换得到的 Markdown、提取图片、元数据、转换状态和持久索引。

## 核心方向

- 优先构建 agent 可以稳定调用的 CLI 工作流。
- 将转换后的 Markdown 和图片目录视为 agent 的主要阅读界面。
- 每篇论文都保持为自包含的 paper bundle。
- 原始 PDF 的复制件与转换后的 Markdown 和图片保存在同一个论文目录下。
- 使用元数据优先的命名方式，并支持用户配置命名模板。
- MVP 阶段只支持本地文件夹 PDF 导入。
- Zotero、Attanger、BibTeX、CSL JSON 和其他来源适配器放到后续阶段。
- 将 MinerU 抽取结果与后续笔记、总结、分类、评审内容分开保存。

## 技术方向

- MVP 使用 Python，因为第一阶段主要是文件系统操作、PDF 元数据抽取、MinerU API 集成、YAML/JSONL 持久化和快速测试迭代。
- 架构保持语言中立。长期稳定的产品契约是 paper bundle 目录结构、`paper.yaml`、`conversion.json`、JSONL 索引、稳定退出码和结构化 CLI 输出。
- Rust 作为后续较大范围开发的优先候选，尤其适合稳健的可分发 CLI、高吞吐索引、并发转换调度和跨平台打包。
- 不要让 Python 内部 API 成为长期产品 API。适配器、文件格式和 CLI 行为要足够明确，使未来 Rust 实现可以替换或包装 Python MVP。
- 尽早为面向用户的命令增加 `--json` 输出，让 agent 依赖结构化输出，而不是解析自然语言文本。

## MVP 范围

第一版围绕以下命令建立可用骨架：

- `paper init`
- `paper import`
- `paper convert`
- `paper list`
- `paper status`
- `paper doctor`

MVP 导入本地 PDF 文件或文件夹，将 PDF 复制进文献库，用 MinerU 转换待处理论文，写入 `paper.md` 和 `images/`，更新元数据，并在获得更好元数据后自动重命名 paper bundle。

## 当前 Post-MVP AI 范围

`paper repair` 是第一层内置 AI 功能，应保持为有边界的修复层：

- 只使用 OpenAI-compatible chat completions provider，直到后续明确设计其他 provider family。
- provider 设置从环境变量或 `paper-cli.yaml` 读取，密钥只从环境变量读取。
- 从本地 bundle 证据修复元数据和明显 Markdown 抽取缺陷；不翻译、不总结、不做风格改写。
- 应用变更前创建 bundle 内备份，并在 `repair.json` 记录应用结果。
- 第一阶段不默认接入 import/convert，也不做全文 AI pass 或外部 identifier lookup。

`paper extract summary` 是第二层内置 AI 功能，应保持为抽取层，而不是修复层：

- 只读取已转换且包含 `paper.md` 的 bundle；不修改源 PDF、`paper.md`、`paper.yaml` 或 `repair.json`。
- 在 `extracts/summary/` 下生成文章骨架输出：`summary.json`、`summary.md` 和 `source-map.json`。
- 通过稳定 block ID、行号、文本 hash、section path、章节 `block_ids` 和图谱 `source_block_ids` 保留来源追溯。
- 使用 CLI 内部 provider 并发处理 block batch，再聚合章节摘要和保守轻量知识图谱。
- 跳过 references、footnotes、funding、copyright/license、页码、明显 OCR 噪声、纯公式、纯表格、纯图片等非主体内容。

## 开发规则

- 创建新功能或改变行为前，先使用 Superpowers brainstorming 做设计，并获得用户确认。
- 项目开发过程中持续维护三个核心文件：
  - `AGENTS.md`：项目指令和协作规则。
  - `README.md`：项目概览、状态和使用方式。
  - `TODO.md`：待办事项、开发记录、阻塞点和下一步。
- 保持实现增量化、可测试。
- 不要硬编码 API key 或用户专属路径。
- 密钥从环境变量或未提交的显式配置文件读取。
- 优先使用清晰的文件系统契约，避免隐藏应用状态。
- 避免对用户原始 PDF 文献库进行破坏性操作。
- 永远不要原地修改源 PDF。
- 如果需要重命名或迁移，移动整个 paper bundle，并记录重命名历史。

## 数据原则

- 每篇论文必须有稳定 ID，且 ID 不依赖当前文件夹名称。
- 文件夹名称可以在元数据抽取后改变，但 ID 不变。
- 索引应能从 paper bundle 重新构建。
- 转换状态必须持久化，不能只打印到终端。
- 转换失败必须留下足够信息，便于诊断和重试。
- 必须尊重用户锁定的目录名。

## 文档要求

- 当项目定位、命令、安装步骤或当前状态变化时，更新 `README.md`。
- 每次有意义的开发推进后，更新 `TODO.md`。
- 较大的已确认设计写入 `docs/superpowers/specs/`。
