# paper-cli AI Extract Summary Design

## 状态

本文档记录下一阶段 AI 功能 `paper extract summary` 的设计草案。当前只完成需求澄清和方案确认，尚未进入实现。

已确认的核心方向：

- 命令族使用 `paper extract`，当前第一项能力为 `paper extract summary`。
- 采用分层抽取路线：block 级并发总结，再聚合为 section 级骨架，并生成轻量知识图谱。
- 使用 CLI 内部并发 AI worker，不依赖 Codex 外部 subagent 或本机 agent 子进程。
- 输出同时服务 agent、检索、后续前端阅读器和人类阅读。
- 结果必须可追溯：原文块能找到对应总结，总结、章节和图谱节点也能反向定位到原文块。

## 目标

`paper extract summary` 的目标不是生成一段普通全文摘要，而是从已转换的 `paper.md` 中抽取文章结构骨架：

- 按正文 block 或相邻 block 批次生成局部总结。
- 按 Markdown heading 聚合出章节级摘要、关键点和文章逻辑。
- 抽取受限类型的知识图谱节点和关系。
- 过滤引文、脚注、版权、funding、页眉页脚、孤立页码和明显 OCR 噪声等非主体内容。
- 生成前端友好的 block source map，支持后续做左右分栏阅读界面。

## 非目标

第一版不做以下事情：

- 不修改 `paper.md`、`paper.yaml`、PDF、MinerU 原始输出或 `repair.json`。
- 不把 `paper extract summary` 混入 `paper repair`。
- 不在 import 或 convert 阶段自动运行 AI 抽取。
- 不依赖 Codex subagent、外部 agent worker 或交互式桌面环境。
- 不生成开放式无限制知识图谱关系，避免模型编造复杂关系。
- 不总结 references、footnotes、funding、conflict of interest、copyright/license 等非正文材料。
- 不对纯公式、纯表格、纯图片块做第一版独立总结。

## 命令设计

推荐命令形态：

```bash
paper extract summary
paper extract summary --paper <id-or-prefix>
paper extract summary --collection <path>
paper extract summary --limit 3
paper extract summary --workers 4
paper extract summary --force
paper extract summary --dry-run
paper extract summary --json
```

默认行为：

- 遍历 library 中已完成转换且存在 `paper.md` 的 bundle。
- 默认全库处理，但可通过 `--paper`、`--collection`、`--limit` 控制成本。
- 默认跳过已有 `extracts/summary/summary.json` 的 bundle。
- 使用 `--force` 时覆盖最新 summary 输出。
- 使用 `--dry-run` 时只返回将处理、跳过、过滤和估算批次数等计划，不调用或不写入实际结果。
- 使用 `--json` 时输出结构化 CLI 结果，方便 agent 调用。

## Provider 配置

第一版复用现有 AI provider 配置：

```bash
PAPER_AI_BASE_URL=...
PAPER_AI_API_KEY=...
PAPER_AI_MODEL=...
PAPER_AI_TEMPERATURE=0
PAPER_AI_TIMEOUT_SECONDS=60
```

也可继续读取 `paper-cli.yaml` 中已有 `ai` 配置。API key 仍然只能来自环境变量，不能写入 repo 或 library 配置。

## 输出位置

每个 bundle 的输出固定放在：

```text
<paper-bundle>/
  extracts/
    summary/
      summary.json
      summary.md
      source-map.json
```

边界：

- `repair.json` 表示 AI 修复记录。
- `extracts/summary/` 表示 AI 信息抽取产物。
- `summary.json` 偏轻量，服务 agent、检索、章节骨架和知识图谱。
- `summary.md` 服务人类快速阅读。
- `source-map.json` 服务后续前端阅读器做原文和总结的精确对照。

## 总体架构

推荐采用分层抽取管线：

```text
paper.md
  -> deterministic block parser
  -> block classifier / filter
  -> paper brief builder
  -> concurrent block workers
  -> section aggregator
  -> graph extractor
  -> summary.json / summary.md / source-map.json
```

主流程职责：

- 读取 `paper.yaml`、`paper.md`、`conversion.json`。
- 按 heading 和 Markdown block 建立 `section_path`。
- 过滤非正文块和明显噪声块。
- 构建非常简短的全文背景，给 worker 作方向提示。
- 将正文块按 token/字符预算分成 batch。
- 用内部并发 worker 调用 OpenAI-compatible provider。
- 聚合 block summaries 为 section summaries。
- 从 block/section 结果中生成受限知识图谱。
- 写出 `summary.json`、`summary.md`、`source-map.json`。

worker 职责：

- 输入简短全文背景、当前 block batch、block 类型、行号和 section path。
- 只总结当前 batch 中给出的 block。
- 不重复全文背景。
- 不总结未给出的上下文。
- 对每个 block 输出摘要、关键点、角色标签、重要性和可选图谱候选。

## 并发模型

第一版使用 CLI 内部并发请求同一个 AI provider，例如 `ThreadPoolExecutor`：

- `--workers` 控制并发度。
- 默认并发度应保守，例如 2 或 4。
- 每个 worker 处理一个 block batch，而不是单个 paragraph，减少请求数量。
- 主流程在所有 block batch 完成后再进行 section 聚合和 graph 聚合。
- 如果单个 batch 失败，记录失败 batch 和 block IDs，不应写出伪完整结果。

这样保留“主 agent + subagent workers”的设计含义，但 CLI 本身仍然是普通、可测试、可复现的命令。

## Block 追溯设计

追溯性是该功能的核心合同。每个进入抽取或被跳过的 block 都必须有稳定标识和原文位置：

- `block_id`：如 `blk_000123`，按解析顺序稳定生成。
- `start_line` / `end_line`：对应 `paper.md` 行号。
- `text_hash`：原始 block 文本 hash，用于检测后续 repair 或手工编辑导致的失效。
- `excerpt`：短原文片段，便于快速显示和人工检查。
- `section_id` / `section_path`：对应章节路径。
- `summary_policy`：`summarize`、`skip` 或 `context_only`。
- `skip_reason`：说明为什么不总结。

从原文块找总结：

- 前端或 agent 读取 `source-map.json` 中的 `block_id`。
- 用同一个 `block_id` 查 `summary.json.blocks`。

从总结找回原文：

- `summary.json.blocks[].source_ref` 提供行号、hash 和 excerpt。
- 需要原文全文时再读取 `source-map.json.blocks[].text`。

章节级总结也必须保留来源 block：

```json
{
  "section_id": "sec_0004",
  "heading": "Diagnostic setup",
  "section_path": ["Introduction", "Diagnostic setup"],
  "block_ids": ["blk_000121", "blk_000122", "blk_000123"],
  "summary": "...",
  "key_points": ["..."]
}
```

知识图谱节点和边也必须保留 provenance：

```json
{
  "id": "node_0017",
  "type": "measurement",
  "label": "gamma signal",
  "source_block_ids": ["blk_000123", "blk_000140"]
}
```

```json
{
  "source": "node_0017",
  "target": "node_0021",
  "type": "supports",
  "source_block_ids": ["blk_000140"]
}
```

## 文件格式草案

### summary.json

`summary.json` 偏轻量，适合 agent、检索和后续程序读取。

```json
{
  "schema_version": 1,
  "paper_id": "...",
  "generated_at": "...",
  "provider": "openai-compatible",
  "model": "...",
  "source": {
    "markdown": "paper.md",
    "markdown_hash": "sha256:..."
  },
  "blocks": [
    {
      "block_id": "blk_000123",
      "source_ref": {
        "start_line": 128,
        "end_line": 136,
        "text_hash": "sha256:...",
        "excerpt": "..."
      },
      "display": {
        "order": 123,
        "section_id": "sec_0004",
        "section_path": ["Introduction", "Diagnostic setup"]
      },
      "summary": {
        "summary_text": "...",
        "summary_level": "short",
        "key_points": ["..."],
        "role": "method",
        "importance": "medium"
      }
    }
  ],
  "sections": [
    {
      "section_id": "sec_0004",
      "heading": "Diagnostic setup",
      "section_path": ["Introduction", "Diagnostic setup"],
      "block_ids": ["blk_000121", "blk_000122", "blk_000123"],
      "summary": "...",
      "key_points": ["..."]
    }
  ],
  "graph": {
    "nodes": [],
    "edges": []
  },
  "indexes": {
    "by_block_id": {},
    "by_section_id": {}
  }
}
```

摘要长度不强制限制为一句话：

- 短段落可为 1 句或 1 个短 bullet。
- 普通正文段可为 2-4 句。
- 信息密集段或合并 batch 可为 3-6 个 bullet。
- 仍然必须只总结对应 block 内容，不能把全文背景重复进每个 block summary。

### source-map.json

`source-map.json` 保存原文块全文和 UI 对齐所需字段。

```json
{
  "schema_version": 1,
  "markdown": "paper.md",
  "markdown_hash": "sha256:...",
  "blocks": [
    {
      "block_id": "blk_000123",
      "type": "paragraph",
      "summary_policy": "summarize",
      "skip_reason": null,
      "start_line": 128,
      "end_line": 136,
      "section_id": "sec_0004",
      "section_path": ["Introduction", "Diagnostic setup"],
      "text_hash": "sha256:...",
      "text": "full original block text..."
    }
  ]
}
```

后续前端可以直接用：

- 左侧按 `source-map.blocks[].order` 或数组顺序渲染原文。
- 右侧按同一个 `block_id` 渲染 `summary.json.blocks[]`。
- 点击章节时通过 `section.block_ids` 高亮对应原文段落。
- 点击图谱节点或关系时通过 `source_block_ids` 定位支撑段落。
- 用 `markdown_hash` 和 `text_hash` 判断 summary 是否已经过期。

### summary.md

`summary.md` 面向人类阅读，按章节组织：

```md
# AI Summary

## Diagnostic setup

- Section summary: ...
- Key points:
  - ...
- Source blocks: blk_000121, blk_000122, blk_000123

### Knowledge Graph

- gamma signal --supports--> dual-modality reconstruction
```

## Block 类型和筛选规则

新功能应复用或扩展现有 Markdown block splitter，但不能直接把 repair 的 suspicious 规则当作 summary 规则。需要新的 summary classification。

纳入总结：

- `abstract` 正文块。
- 正文 `paragraph`。
- 章节标题下的连续正文块。
- figure/table caption。
- introduction、methods、results、discussion、conclusion 等主体章节下的正文块。
- 解释公式、图或表的相邻正文块。

跳过：

- references / bibliography。
- footnotes。
- acknowledgements。
- funding。
- conflict of interest。
- author contribution。
- license / copyright / open access 说明。
- 单独页码、页眉页脚。
- 明显 OCR 噪声。
- 纯公式、纯表格、纯图片块。

谨慎处理：

- `heading` 不单独总结，但用于 section path。
- 公式块不单独提交 AI，但如果前后段落解释公式，可标记为 `context_only`。
- 表格块第一版不直接总结；caption 和正文解释优先。
- 图片块不总结图像内容；只总结 caption 或正文说明。

每个 block 在 `source-map.json` 中记录：

```json
{
  "block_id": "blk_000123",
  "type": "paragraph",
  "summary_policy": "summarize",
  "skip_reason": null
}
```

这样前端未来也能显示哪些段落没有 AI 总结，以及为什么。

## Prompt 约束

### 全文背景 prompt

主流程可以先构建很短的 paper brief，来源包括：

- `paper.yaml` 中的 title、creators、year、doi、language。
- Markdown 开头少量 heading / abstract。
- 章节 heading 列表。

paper brief 只作为 worker 的方向引导，不应包含足以让 worker 复述全文的长背景。

### Block worker prompt

worker 输入应包含：

- 简短 paper brief。
- 当前 block batch。
- 每个 block 的 `block_id`、`type`、`section_path`、行号和原文。
- 输出 JSON schema。

worker 输出应包含：

- `block_id`
- `summary_text`
- `summary_level`
- `key_points`
- `role`
- `importance`
- `concepts`
- 可选 `graph_candidates`
- `warnings`

约束：

- 只总结当前 block。
- 不重复全文背景。
- 不总结 references、footnotes、funding 等被标记为跳过的内容。
- 不改变科学含义。
- 不把公式、表格或图片内容当成已读内容编造。

### Section aggregator prompt

section aggregator 输入 block summaries 和 section structure，输出：

- section summary
- section key points
- section role
- cross-section links 或逻辑关系

section 聚合必须引用 `block_ids`，不能生成无来源总结。

### Graph extractor prompt

graph extractor 输入 block summaries 和 section summaries，输出受限图谱：

节点类型第一版限制为：

```text
concept, method, dataset_or_sample, instrument, measurement, result, limitation, claim
```

关系类型第一版限制为：

```text
uses, measures, produces, supports, compares_with, limits, depends_on, explains
```

每个 node/edge 都必须包含 `source_block_ids`。没有来源 block 的节点和边应被丢弃。

## 错误处理和恢复

建议规则：

- 如果 provider 配置缺失，命令返回失败，并提示复用 `PAPER_AI_*` 配置。
- 如果某个 bundle 已有 summary 且没有 `--force`，记录为 skipped。
- 如果某个 batch 失败，当前 bundle 标记 failed，不写出完整 summary。
- 如果只写出部分临时文件，应使用临时目录或临时文件名，全部成功后再原子替换。
- 如果 `paper.md` hash 与现有 summary source hash 不一致，后续可提示 stale。
- `--dry-run` 不调用 provider 或至少不写文件，具体实现时需在计划中明确。

## 测试计划

单元测试：

- block parser 能生成稳定 `block_id`、行号、section path。
- summary classifier 能正确标记 summarize / skip / context_only。
- references、footnotes、funding、copyright、页码和 OCR 噪声被跳过。
- caption 和正文 paragraph 被纳入。
- `summary.json`、`source-map.json` schema 可序列化且互相可对齐。
- `--force` 与默认 skip 行为正确。
- fake provider 下 block worker、section aggregator、graph extractor 的 JSON 响应能被校验。
- batch 失败时不写出伪完整 summary。

集成测试：

- 用 fixture `paper.md` 跑 `paper extract summary --json`。
- 用 fake provider 验证并发 batch 的输入输出和顺序稳定性。
- 验证 `summary.md` 包含章节摘要、source blocks 和知识图谱可读条目。
- 验证 `paper.md`、`paper.yaml`、`repair.json` 不被修改。

真实验证：

- 在已有 dual-modality smoke library 或新的非敏感 PDF library 上跑真实 provider。
- 检查 block summary 是否不会大量重复全文背景。
- 检查正文段落、章节摘要和图谱节点能回溯到原文行号和 `block_id`。
- 用至少一篇文章手工抽查前端对齐所需字段是否足够。

## 后续实现步骤

建议下一步先写 implementation plan，再进入代码：

1. 增加 `paper extract summary` CLI skeleton 和目标选择逻辑。
2. 新增 summary block parser/classifier，尽量复用现有 Markdown block 类型但独立于 repair policy。
3. 设计并实现 `source-map.json` 生成。
4. 实现 fake-provider 驱动的 block worker。
5. 增加并发 batch 调度和稳定结果合并。
6. 实现 section aggregator。
7. 实现受限 graph extractor。
8. 写 `summary.json`、`summary.md`，并保证原子写入。
9. 添加单元测试和 fixture 集成测试。
10. 用真实 provider 和真实论文做 smoke test。

