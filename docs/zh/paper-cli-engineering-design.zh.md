# paper-cli 工程化设计

日期：2026-05-13

## 目标

`paper-cli` 已经超过最初 MVP 验证阶段：它可以导入本地 PDF、复制到 bundle、通过 MinerU 转换、归一化 Markdown 和图片、更新元数据、重命名 bundle、重建索引，并通过 `doctor` 检查。

下一阶段的目标不是把它做成复杂平台，而是建立一个可以长期开发的轻量工程基础：稳定文件契约、可预测 CLI 行为、必要质量门禁和真实论文验证流程。

## 非目标

本轮工程化不做：

- GUI。
- 数据库服务。
- 插件市场。
- 后台 daemon。
- 完整搜索引擎。
- Rust 重写。
- Zotero 双向同步。
- 围绕本地文件操作的大型框架。

这些以后可能有价值，但现在加入会干扰核心契约稳定。

## 工程原则

1. 产品契约优先保持文件系统优先、语言中立。
2. 本阶段继续使用 Python。
3. 每个能力都应能通过 CLI 访问。
4. 优先使用普通文件，不依赖隐藏状态。
5. agent 面向输出必须结构化且稳定。
6. 只加入能捕获真实问题的工具。
7. 用真实 PDF 验证，但不提交用户 PDF 或 MinerU 输出。
8. Rust 是稳定契约后的替换或包装方案，不是当前紧急重写目标。

## 稳定契约

### 文献库结构

```text
paper-library/
  paper-cli.yaml
  collections/
  inbox/
  indexes/
    papers.jsonl
    jobs.jsonl
```

本地开发和手动验证库可以放在：

```text
paper-libraries/
```

`paper-libraries/` 被 git 忽略，因为其中可能包含复制后的 PDF、图片和 MinerU 原始输出。

### Paper Bundle 结构

新转换论文的 bundle 契约为：

```text
<paper-name>/
  paper.yaml
  original.pdf
  paper.md
  images/
  conversion.json
  raw/
    mineru/
      layout.json
      *_content_list.json
      *_origin.pdf
  notes/
    README.md
```

根目录保留给 agent 的常用读取路径：`paper.yaml`、`paper.md`、`images/`。转换器专属 sidecar 文件进入 `raw/<converter>/`。

### 元数据契约

`paper.yaml` 仍是 canonical paper record。下一步 schema 应增加 provenance，但不破坏当前字段：

```yaml
metadata:
  title: "..."
  creators:
    - name: "..."
      role: "author"
  year: 2026
  language: "en"
  doi: null
metadata_sources:
  title: "mineru"
  creators: "filename-title-prefix"
  year: "filename"
metadata_confidence:
  title: "high"
  creators: "medium"
  year: "medium"
```

这样既保持当前调用方可用的简单 metadata 结构，又能支持未来更稳健的覆盖和 review queue。

### CLI 契约

所有用户命令都应支持 `--json`。JSON 输出必须合法、稳定、适合 agent 使用。退出码约定：

- `0`：成功。
- `1`：`doctor` 发现验证问题。
- `2` 或 argparse 默认行为：CLI 参数错误。
- 其他非零：非预期运行错误。

下一轮工程化应先文档化已实现命令的 JSON schema，再增加更多命令。

## 最小质量工具

只加入轻量本地门禁：

- `pytest`：测试。
- `ruff`：lint 和格式化。
- `mypy` 后置，只有当类型检查不会拖慢迭代时再加入。
- 只有重复命令明显变麻烦时，再加 `Makefile` 或 `justfile`。

推荐第一批命令：

```bash
uv run --with pytest pytest -v
uv run --with ruff ruff check src tests
uv run --with ruff ruff format src tests
```

在有远程仓库和发布目标之前，不需要复杂 CI 矩阵。

## 转换工作流

当前转换流程足够支撑 MVP，但工程化版本应拆成显式阶段：

1. 发现 pending bundle。
2. 创建或更新 conversion job 记录。
3. 提交 PDF 到 converter。
4. 轮询并下载输出。
5. 归一化输出到 bundle 契约。
6. 抽取元数据。
7. 在允许时重命名 bundle。
8. 重建索引。
9. 持久化成功或失败诊断。

`conversion.json` 应从小状态文件扩展为诊断记录：

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": true,
  "state": "done",
  "submitted_at": "...",
  "converted_at": "...",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

这仍然是简单本地文件方案，不需要 daemon 或数据库。

## 索引

暂时保留 JSONL：

- `indexes/papers.jsonl`：可重建 paper summary。
- `indexes/jobs.jsonl`：当 conversion job 显式化后，作为 append-only job history。

只有出现明确性能或查询需求时，再引入 SQLite。

## 测试策略

保持测试分层：

- 单元测试：命名、元数据解析、schema helper。
- 工作流测试：导入、fixture 转换、索引重建、doctor。
- Mock 网络测试：MinerU API 形状、zip 归一化、sidecar 处理。
- 手动 smoke test：用 `paper-libraries/` 下的本地 PDF 跑真实 MinerU。

真实用户 PDF 和转换输出不提交，验证结论记录到 `TODO.md`。

## 下一阶段里程碑

### 里程碑 1：基线和工具

- 提交当前已验证 MVP 基线。
- 添加 `ruff` 配置。
- 添加一个明确的验证命令。
- 保持全量测试通过。

### 里程碑 2：契约文档

- 文档化 `paper.yaml`。
- 文档化 `conversion.json`。
- 文档化已实现命令的 CLI JSON 输出。
- 添加真实 MinerU smoke-test 清单。

### 里程碑 3：转换任务加固

- 扩展 `conversion.json`。
- 将转换事件写入 `indexes/jobs.jsonl`。
- 保留失败诊断。
- 增加失败重试行为。

### 里程碑 4：元数据 Provenance

- 增加 metadata source 和 confidence 字段。
- 根据 confidence 控制转换后覆盖。
- 保护用户锁定或人工修正元数据。

### 里程碑 5：Adapter 边界

- 定义 source adapter interface。
- 以 local-folder import 作为参考 adapter。
- 等接口明确后再做 Zotero 只读导入。

## 决策

继续增量推进。下一份实现计划只覆盖里程碑 1 和 2；里程碑 3-5 暂时保持设计状态，不直接开工。
