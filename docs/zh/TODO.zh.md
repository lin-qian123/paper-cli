# TODO 中文版

## 当前阶段

本地文件夹 MVP 已实现并有测试覆盖。工程化工作应先稳定契约和工具链，不增加不必要的平台复杂度。

## 工程化阶段

- [x] 提交已验证的 MVP 加固基线。
- [x] 编写轻量、非冗余的工程化设计。
- [x] 添加最小 lint/format 工具。
- [x] 文档化 `paper.yaml`、`conversion.json` 和 CLI JSON 输出契约。
- [x] 添加真实 MinerU 手动 smoke-test 清单。
- [x] 添加工程化里程碑 1 和 2 的实现计划。
- [x] 将 `conversion.json` 扩展为诊断记录。
- [x] 将转换任务事件追加到 `indexes/jobs.jsonl`。
- [x] 保留失败转换诊断，并在重试失败 bundle 时递增 attempt。
- [x] 在 `paper.yaml` 中增加元数据来源和置信度字段。
- [x] 按置信度合并转换元数据，保护高置信度字段。
- [x] 定义 source adapter 接口，并将本地文件夹导入作为参考 adapter。

## 验证记录

- 2026-05-13：使用桌面 PDF `Advanced Science - 2026 - Guo - Helical Electron Beam Micro-Bunching by High-Order Modes in a Micro-Plasma Waveguide.pdf` 在 `/tmp` 临时文献库中测试。
  - 导入成功，PDF 已复制到 inbox bundle。
  - 真实 MinerU 转换成功，使用环境变量 `MINERU_API_KEY`。
  - 已生成 `paper.md`、`images/`、`paper.yaml`、`conversion.json` 和 JSONL 索引。
  - `paper status --json` 返回 `total=1`、`converted=1`、`failed=0`、`pending=0`。
  - `paper doctor --json` 未报告问题。
  - MinerU 输出包含 266 行 Markdown 和 17 张提取图片。
  - 已知问题：快速文件名元数据把 `Advanced Science` 解析成作者，转换后的真实 MinerU Markdown 没有可靠纠正作者字段。
  - 已知问题：MinerU 原始 sidecar 文件，例如 `layout.json`、`*_content_list.json`、`*_origin.pdf`，当前会留在 bundle 根目录，还没有归入专门 raw-output 目录。
- 2026-05-13 后续修复：
  - 增加标题前缀作者推断：当文件名形如 `Journal - Year - Author - Title.pdf`，且 MinerU 给出干净标题时，可从旧标题前缀恢复作者。
  - 增加连字符归一化：PDF 文件名中的 Unicode 连字符可以匹配 MinerU Markdown 标题中的 ASCII 连字符。
  - 增加 MinerU sidecar 归一化：mock ZIP 输出中的原始文件会移动到 `raw/mineru/`。
  - 使用已有 MinerU 输出作为 fixture 重放桌面 PDF，bundle 现在会重命名为 `Guo et al. - 2026 - Helical Electron Beam Micro-Bunching by High-Order Modes in a Micro-Plasma Waveguide`。
  - 在 `paper-libraries/desktop-live-test` 中重新跑真实 MinerU 转换；`paper status` 和 `paper doctor` 均通过，bundle 使用 `Guo et al.` 命名，MinerU sidecar 已放入 `raw/mineru/`。

## 已确认 MVP

- [x] 将项目定义为面向 agent 的本地文献管理 CLI。
- [x] 将本地文件夹导入作为第一种来源适配器。
- [x] 默认将 PDF 复制到每篇论文的 paper bundle 中。
- [x] 使用元数据优先命名，并支持用户配置模板。
- [x] 先导入，再在 MinerU 转换后根据更好元数据自动重命名。
- [x] 将 Zotero 和 Attanger 支持推迟到第二阶段。
- [x] 创建中文文档目录和中文版本。
- [x] 审阅并确认已写好的 MVP spec。
- [x] spec 确认后创建实现计划。
- [x] 明确技术路线：Python 做 MVP，Rust 作为后续大范围开发候选，文件/CLI 契约保持语言中立。
- [x] 确认实现默认值：只在当前仓库开发、PDF 复制进 bundle、MinerU API 来自环境变量、主要命令支持 JSON 输出、按 hash 跳过重复导入、MVP 不做删除命令。
- [x] 执行 MVP 实现计划。

## 实现待办

- [x] 初始化 Python 项目结构。
- [x] 选择打包方式和 CLI 框架。
- [x] 实现 `paper init`。
- [x] 实现从 `paper-cli.yaml` 加载文献库配置。
- [x] 实现本地 PDF 扫描器。
- [x] 实现 PDF 复制到 paper bundle。
- [x] 实现稳定 paper ID 生成。
- [x] 实现快速元数据抽取。
- [x] 实现可配置命名模板渲染器。
- [x] 实现文件系统安全命名和重名处理。
- [x] 实现 MinerU 转换适配器。
- [x] 持久化 `conversion.json`。
- [x] 持久化 `paper.yaml`。
- [x] 实现转换后的元数据补全。
- [x] 实现带重命名历史的自动 bundle 重命名。
- [x] 实现索引重建。
- [x] 实现 `paper list`。
- [x] 实现 `paper status`。
- [x] 实现 `paper doctor`。
- [x] 为命名、bundle 布局、导入幂等性、重命名行为添加聚焦测试。

## 第二阶段想法

- [ ] 在 paper bundle 和 CLI 契约稳定后，评估 Rust CLI/core。
- [ ] Zotero 只读导入适配器。
- [ ] attachment resolver 抽象。
- [ ] Attanger 风格 attachment-root 映射。
- [ ] BibTeX / CSL JSON 导入。
- [ ] 基于转换 Markdown 的 agent 分类。
- [ ] 对模糊分类或命名建立 review queue。
- [ ] 对转换 Markdown 建立搜索和检索能力。

## 稳健性待办

- [x] 改进 `Journal - Year - Author - Title.pdf` 文件名在 MinerU 给出干净标题时的转换后作者推断。
- [ ] 在文件名无法推断、且 MinerU Markdown 没有显式 `Authors:` 行时，继续改进标题页作者直接抽取。
- [x] 为文件名解析得到的低置信度元数据打标记，让转换后元数据能更积极地覆盖它。
- [x] 将新转换 bundle 的 MinerU 原始 sidecar 文件归一到专门 raw-output 目录。
- [x] 增加一个真实 MinerU smoke test 清单，方便手动测试但不提交用户 PDF。

## 剩余决策

- MVP 实现语言为 Python；在契约稳定后重新评估 Rust 是否适合后续大范围开发。
- 当前 MinerU 集成采用项目内干净 client。先用真实论文验证，再决定是否需要复用旧脚本中的某些流程。
- 当前转换前元数据抽取保持轻量。只有真实论文验证暴露出命名或分类缺口时，再扩大范围。
- MVP 索引保留 JSONL。只有搜索、筛选或大规模文献库性能需求明确后，再评估 SQLite。

## 实现计划

- `.agents/superpowers/specs/2026-05-13-paper-cli-mvp-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-engineering-m1-m2-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-conversion-jobs-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-metadata-provenance-implementation.md`
- `.agents/superpowers/specs/2026-05-13-paper-cli-source-adapters-implementation.md`
