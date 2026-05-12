# paper-cli MVP 设计

日期：2026-05-13

## 目标

`paper-cli` 是一个本地优先、面向 agent 原生使用的文献管理 CLI。它通过构建包含 Markdown 正文、提取图片、元数据、转换状态和可重建索引的结构化 paper bundle，帮助 AI agent 管理和阅读文献。

MVP 重点是建立一个可靠的本地文献库骨架。它不试图替代 Zotero 的人类阅读和 PDF 批注体验，而是为 agent 提供稳定的文件系统结构和 CLI 契约，用于导入、转换、命名、列表、状态检查和诊断。

## 范围

第一版只支持本地 PDF 文件夹导入。

包含：

- 初始化 `paper-cli` 文献库。
- 导入单个 PDF 或一个 PDF 文件夹。
- 将每个 PDF 复制到 paper bundle。
- 创建和更新 `paper.yaml`。
- 使用 MinerU 转换 PDF。
- 将 `paper.md` 和 `images/` 与 `original.pdf` 放在同一级。
- 使用元数据优先命名。
- 允许用户配置命名模板。
- 在 MinerU 转换得到更好元数据后自动重命名 bundle。
- 维护可重建的 JSONL 索引。
- 提供状态检查和 doctor 命令。

暂缓：

- Zotero 导入。
- Attanger 专用附件映射。
- BibTeX / CSL JSON 导入。
- 其他文献管理器适配器。
- 双向同步。
- GUI。
- 全文搜索界面。
- 自动综述生成。
- 复杂知识图谱功能。

## 技术策略

MVP 应使用 Python 实现。这是务实的 MVP 选择，不是永久的产品身份。第一阶段需要快速围绕本地文件、PDF 元数据抽取、MinerU HTTP 集成、YAML/JSONL 持久化和测试进行迭代；Python 对这些任务最直接，也符合既有 MinerU 工作流经验。

长期系统应保持语言中立。持久 API 是文件系统契约：paper bundle 目录结构、`paper.yaml`、`conversion.json`、JSONL 索引、CLI 命令、结构化 `--json` 输出和退出码。这些契约应足够明确，使未来 Rust 实现可以替换或包装 Python MVP。

Rust 是后续较大范围开发的强候选，特别是在 `paper-cli` 发展为广泛分发的 CLI、需要高吞吐索引、并发任务调度、更严格可靠性和跨平台打包时。重新评估 Rust 的触发条件应该是产品契约已经稳定，而不是早期不确定性。

## 设计原则

1. 保持 paper bundle 自包含。
2. 默认将 PDF 复制到被管理的文献库中。
3. 永远不要原地修改源 PDF。
4. 使用稳定 paper ID，且 ID 不依赖文件夹名称。
5. 将文件夹名称视为展示和组织方式，而不是身份标识。
6. 将 MinerU 输出作为权威的抽取阅读层。
7. 持久化转换状态和失败信息。
8. 索引必须能从 paper bundle 重新构建。
9. 来源适配器保持薄而可选。
10. 核心系统避免用户专属假设。

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

`collections/` 保存已经分类的论文。`inbox/` 保存没有选择分类的导入论文。每个论文目录都是一个 paper bundle。

MVP 有意将 `original.pdf`、`paper.md` 和 `images/` 放在同一级。这样 agent 的常见读取路径更短、更直接。未来如果支持多个抽取器，可以迁移到 `source/original.pdf` 和 `extracted/mineru/paper.md` 之类的嵌套结构。

## 命令

### `paper init <library-dir>`

创建被管理的文献库：

- 创建文献库目录。
- 写入 `paper-cli.yaml`。
- 创建 `collections/`、`inbox/` 和 `indexes/`。
- 写入空索引文件。

### `paper import <pdf-or-folder> --collection <path>`

导入单个 PDF 或递归导入一个文件夹中的 PDF：

- 扫描 PDF。
- 计算稳定 ID。
- 从 PDF metadata 和文件名模式中抽取快速元数据。
- 根据命名模板渲染初始论文名称。
- 对名称做文件系统安全处理。
- 创建 `collections/<path>/<paper-name>/`。
- 将 PDF 复制为 `original.pdf`。
- 写入 `paper.yaml`。
- 写入或更新索引。
- 将转换状态标记为 `pending`。

### `paper import <pdf-or-folder> --inbox`

导入行为相同，但目标根目录是 `inbox/`。

### `paper convert --pending`

转换所有待处理论文：

- 找到 `status.conversion` 为 `pending` 或可重试的论文。
- 将 `original.pdf` 发送到 MinerU。
- 轮询转换状态。
- 下载并解压输出。
- 将主 Markdown 文件规范化为 `paper.md`。
- 将提取图片规范化到 `images/`。
- 写入 `conversion.json`。
- 尽可能从 MinerU Markdown 中抽取更好的元数据。
- 重新渲染配置的论文名称。
- 如果渲染名称变化且 `name_locked` 为 false，自动重命名整个 bundle。
- 在 `paper.yaml` 中记录重命名历史。
- 重建索引。

### `paper list`

列出文献库中的论文。MVP 输出应包含：

- ID 或短 ID。
- 当前 collection path。
- 当前名称。
- 转换状态。
- 元数据完整度。

### `paper status`

显示总体状态：

- 论文总数。
- 已导入论文数。
- 已转换论文数。
- 转换失败数。
- 待转换数。
- 元数据不完整论文数。
- 转换后发生过重命名的论文数。

### `paper doctor`

校验文献库：

- 缺失 `original.pdf`。
- 缺失 `paper.yaml`。
- 转换完成后缺失 `paper.md`。
- `images/` 损坏或缺失。
- YAML 无效。
- ID 重复。
- 索引过期。
- 转换失败。
- 当 `name_locked` 为 false 时，文件夹名称与元数据不一致。

## 论文元数据

初始 `paper.yaml` 示例：

```yaml
schema_version: 1
id: "sha256:abc123..."
name: "Vallieres et al. - 2025 - High average-flux laser-driven neutron source"
name_locked: false
previous_names: []
collection: "plasma/lwfa"

metadata:
  title: "High average-flux laser-driven neutron source"
  creators:
    - name: "Vallieres"
      role: "author"
  year: 2025
  language: "en"
  doi: null

source:
  type: "local-folder"
  imported_from: "/absolute/path/to/source.pdf"
  copied_pdf: "original.pdf"
  imported_at: "2026-05-13T00:00:00+08:00"

status:
  import: "done"
  conversion: "pending"
  metadata: "partial"
  naming: "fast"

naming:
  template: "default"
  rendered_from:
    - "creators"
    - "year"
    - "title"
  last_renamed_at: null
```

转换后：

```yaml
status:
  import: "done"
  conversion: "done"
  metadata: "complete"
  naming: "metadata"

previous_names:
  - "high-average-flux-laser-driven-neutron-source"

naming:
  template: "default"
  last_renamed_at: "2026-05-13T00:10:00+08:00"
```

## 命名

默认命名模板：

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

模板保存在 `paper-cli.yaml` 中，用户可以修改。

渲染出的名称成为文件夹名前必须做安全处理：

- 删除或替换路径分隔符。
- 删除控制字符。
- 规范化空白。
- 去掉开头和结尾的标点与空格。
- 执行可配置的最大长度限制。
- 通过追加计数器或短 ID 处理重名。

## 导入与重命名流程

MVP 使用快速导入，然后在转换后自动重命名。

导入：

1. 将 PDF 复制到目标 paper bundle。
2. 使用快速元数据和文件名解析渲染初始名称。
3. 持久化 `paper.yaml`，其中 `status.conversion = pending`。

转换：

1. 运行 MinerU。
2. 写入 `paper.md` 和 `images/`。
3. 从转换文本中抽取更好的元数据。
4. 重新渲染论文名称。
5. 如果新名称不同且 `name_locked` 为 false，移动整个 bundle。
6. 将旧名称记录到 `previous_names`。
7. 重建索引。

如果目标名称已经存在，追加 `-2` 或短 ID 等后缀。

如果 `name_locked: true`，不要自动重命名，而是标记 `status.naming = review`。

## MinerU 转换

MVP 应该在内部转换适配器后封装 MinerU。

适配器应当：

- 从环境变量或未提交的配置读取凭据。
- 上传 PDF。
- 轮询状态。
- 下载 ZIP 结果。
- 解压主 Markdown 和图片。
- 将主 Markdown 规范化为 `paper.md`。
- 将图片规范化到 `images/`。
- 写入 `conversion.json`。
- 返回结构化成功或失败结果。

不能硬编码 API key。

## 索引

`indexes/papers.jsonl` 是便利索引，不是事实来源。它可以从 `paper.yaml` 文件重新构建。

每行应包含：

- `id`
- `name`
- `collection`
- `path`
- `title`
- `creators`
- `year`
- `language`
- `status`

`indexes/jobs.jsonl` 记录转换任务摘要和失败信息。

## 错误处理

导入失败：

- 不改动源 PDF。
- 尽量不要创建半写入 bundle。
- 如果已经部分创建 bundle，需要清楚标记。

转换失败：

- 写入带错误状态的 `conversion.json`。
- 保留 `original.pdf`。
- 仅在有帮助且明确标记的情况下保留部分输出。
- 允许后续命令重试。

重命名失败：

- 不丢失 bundle。
- 如果移动失败，保留旧路径。
- 记录尝试使用的名称和错误。
- 只有移动成功后才重建索引。

## 测试策略

聚焦测试应覆盖：

- 命名模板渲染。
- 中文与非中文 creator 格式。
- 文件名安全处理。
- 重名处理。
- 稳定 ID 生成。
- 导入幂等性。
- bundle 布局创建。
- 转换后重命名行为。
- `name_locked` 行为。
- 从 bundle 元数据重建索引。
- doctor 对缺失文件和过期索引的检查。

MinerU 网络调用应封装在适配器后，这样测试可以使用假的转换输出。

## 第二阶段

Zotero 支持应作为来源适配器实现，而不是作为核心假设。

未来适配器：

- Zotero 只读 SQLite 导入。
- Zotero local API 导入。
- Zotero internal storage resolver。
- Zotero linked-file resolver。
- Attanger 风格 attachment-root resolver。
- BibTeX 导入。
- CSL JSON 导入。

核心系统只需要一个可解析的 PDF 路径和元数据，不应该关心 PDF 是如何被发现的。

## 待定问题

1. MVP 索引是否只使用 JSONL？
2. MinerU 转换前要做多少元数据抽取？
3. 是否需要一个仅用于元数据的本地 fallback extractor？
4. `paper convert --pending` 在 MVP 中应先串行处理，还是支持有限并发？
5. 在文件和 CLI 契约稳定后，何时评估 Rust 重写或 Rust CLI 包装层？
