# TODO 中文版

## 当前阶段

本地文件夹 MVP 已实现并有测试覆盖。第一阶段内置 AI repair 先告一段落：OpenAI-compatible 元数据修复、保守 Markdown 修复、备份、`repair.json`、真实 provider smoke test 和 suspicious-block 加固都已实现并验证。第二层内置 AI 功能 `paper extract summary` 已实现，用于结构化抽取文章骨架：block 总结、章节总结、轻量知识图谱，以及 `extracts/summary/` 下的原文追溯输出。

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
- [x] 写好 `paper repair` 的 AI 修复设计。

## AI 修复阶段

状态：本阶段先视为完成。下面未勾选项是后续增强，不是当前 AI repair 里程碑的阻塞点。

- [x] 实现 `paper repair`，默认等价于 `--target all`。
- [x] 增加 `--target metadata`、`--target markdown` 和 `--dry-run`。
- [x] 增加 OpenAI-compatible provider，支持环境变量和可选 `paper-cli.yaml` 配置。
- [x] 从 `paper.yaml`、bundle 名称、PDF 文件名、转换状态和 Markdown 开头构造有边界的元数据证据包。
- [x] 按置信度安全应用元数据修复，并写入 `metadata_sources=ai-repair`。
- [x] 将 `paper.md` 拆成文本块，只把可疑块发送给 AI 检查修复。
- [x] 写入 `paper.yaml` 或 `paper.md` 前创建 bundle 内备份。
- [x] 写入 `repair.json`，记录变更、warning、provider、model 和时间戳。
- [x] 增加 fake-provider 测试，覆盖 provider 错误、无效 JSON、dry-run、元数据修复、Markdown block patch 和备份创建。
- [x] 增加真实 provider 手动 smoke-test 清单到 `docs/smoke-tests/`。
- [x] 用一个已转换、非敏感 PDF 运行真实 provider AI repair smoke test。
- [ ] 在 library-wide 行为验证后，增加可选 bundle selector。
- [ ] 决定 repair 历史保持 latest-only，还是扩展为 append-only JSONL。
- [x] 修复 `paper repair --target all`：后续 Markdown provider 失败时，不能让同一个 bundle 留下 metadata 半写入状态。
- [x] 编写 suspicious block 缺陷开发记录，并实现保守的 reason/policy 分类。
- [ ] 将冗长的 `review_only` Markdown warning 按 reason/count 聚合，同时保留详细 block id。
- [ ] 为当前 `review_only` 的长段落 OCR 候选增加后续 review/apply 路径。

## AI Extract Summary 阶段

状态：第一版实现完成，并已在 `paper-libraries/full-smoke-library-optimized-v2` 上做真实 provider smoke test。

- [x] 确认命令族为 `paper extract`，第一项能力为 `paper extract summary`。
- [x] 确认采用分层抽取管线：block 级并发总结、section 级聚合、graph 级抽取。
- [x] 确认使用 CLI 内部 provider 并发，不依赖 Codex 或外部 subagent。
- [x] 确认输出位置：`extracts/summary/summary.json`、`extracts/summary/summary.md`、`extracts/summary/source-map.json`。
- [x] 确认默认跳过已有 summary 输出，使用 `--force` 重新生成。
- [x] 确认面向前端阅读器的追溯设计：稳定 `block_id`、原文行号、文本 hash、章节路径和 `source-map.json`。
- [x] 确认摘要长度按段落内容决定，不限制为一句话。
- [x] 确认第一版 block 策略：总结正文 prose/caption；跳过 references、footnotes、funding、copyright/license、页眉页脚、页码、OCR 噪声、纯公式、纯表格和纯图片。
- [x] 将设计记录到 `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`。
- [x] 实现目标选择：`--paper`、`--collection`、`--limit`、`--workers`、`--paper-workers`、`--max-requests`、`--retries`、`--force`、`--dry-run` 和 `--json`。
- [x] 实现 summary 专用 block 分类和 source-map 生成。
- [x] 实现 block batch worker 调用和 CLI 内部并发。
- [x] 实现 section 聚合和保守 graph 抽取。
- [x] 实现 missing block summary 重试，避免 provider 漏项破坏后续前端对齐。
- [x] 增加 fake-provider 测试，覆盖 block worker、section 聚合、graph 抽取、跳过策略和追溯关系。
- [x] 在已转换的非敏感论文上运行真实 provider smoke test。
- [ ] 为 `extracts/summary/summary.json` 和 `source-map.json` 增加专门契约文档。
- [ ] 如果真实 provider 在大文献库上过慢，考虑增加更便宜的 graph 模式或 `--no-graph` 选项。

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
- 2026-05-13 provenance smoke test：
  - 增加 metadata provenance 和 conversion job diagnostics 后，在 `paper-libraries/provenance-live-test` 中重新跑真实 MinerU 转换。
  - `paper status` 返回 `converted=1`、`failed=0`、`pending=0`；`paper doctor` 未报告问题。
  - `paper.yaml` 包含 `metadata_sources` 和 `metadata_confidence`：title 来自 `mineru` 且为 `high`，creators 来自 `filename-title-prefix` 且为 `medium`，year 来自 `filename` 且为 `medium`。
  - `conversion.json` 使用 schema version 1 诊断格式，包含 `converter=mineru`、`state=done`、`attempt=1`、`raw_output_dir=raw/mineru`、`markdown=paper.md`、`images=images`。
  - `indexes/jobs.jsonl` 记录了 `conversion-started` 和 `conversion-finished` 事件。
- 2026-05-21 AI repair 实现：
  - 增加 `paper repair`，支持 `--target metadata|markdown|all`、`--dry-run` 和 `--json`。
  - 增加 OpenAI-compatible chat completions provider，可从 `PAPER_AI_*` 或 `paper-cli.yaml` 配置；密钥只从环境变量读取。
  - 元数据修复使用来自 `paper.yaml`、bundle 名称、来源文件名、转换状态、identifier candidates 和 Markdown 开头的有界证据；安全应用的字段会标记 `metadata_sources=ai-repair`。
  - Markdown 修复会拆分 `paper.md`，只发送可疑块，应用 exact-match patch，并把 mismatch 记录为 warning。
  - 实际写入会创建 bundle-local backup、写 latest-only `repair.json`，并重建 `indexes/papers.jsonl`。
  - 增加 fake-provider 测试，覆盖配置、请求 payload、无效 JSON、缺少配置、dry-run、metadata 保护、Markdown patch、mismatch 拒绝、backup 创建和 index rebuild。
- 2026-05-21 双模照相论文全流程 smoke test：
  - 将 `/Users/yuxiangzhang/Documents/research/paper/双模照相` 下全部 12 个 PDF 复制到 ignored 测试输入 `paper-libraries/full-smoke-input/双模照相`。
  - 将复制出的目录导入 `paper-libraries/full-smoke-library-clean`，collection 为 `双模照相`；重复 PDF hash 自动合并为 7 个唯一 paper bundle。
  - 真实 MinerU 转换 7 个 bundle 全部成功：`status` 返回 `converted=7`、`failed=0`、`pending=0`；`doctor` 未报告问题。
  - 确认每个转换后 bundle 都包含 `original.pdf`、`paper.md`、`images/`、`raw/mineru/`、`conversion.json` 和 `notes/README.md`；`jobs.jsonl` 有 14 条 start/finish 事件，`papers.jsonl` 有 7 行。
  - 使用已配置的 OpenAI-compatible provider 运行 `paper repair --target metadata --dry-run --json`，返回 `ok=true`，且未写入 `repair.json`。
  - 随后运行 `paper repair --json`，7 个 bundle 全部完成且 `failed=[]`；写入 7 个 `repair.json`，只为实际变更文件创建 12 个备份，之后 `status` / `doctor` 仍然干净。
  - 第一次完整 repair 尝试中，一个 provider 响应提前结束，暴露出 metadata 已写入但 `repair.json` 未写的半完成问题；已增加回归测试，并改为先收集所有选中 target 的结果，成功后再写 bundle 文件。
- 2026-05-21 suspicious-block 优化：
  - 新增 `docs/development/2026-05-21-ai-repair-suspicious-blocks.md`，记录当前缺陷、策略设计和验证结果。
  - 增加结构化 suspicious finding，包含 `reasons` 和 `policy`：`auto_repair`、`review_only`、`structural_warning`。
  - Markdown repair 现在只把 `auto_repair` block 发送给 AI；公式、表格、参考文献、数学密集 block 只记录为 `review_only` warning，不自动修。
  - 增加 HTML table、reference section、常见 OCR 词、重复片段、坏图片、长 OCR 段落的检测。
  - `make verify` 通过，测试数为 51。
  - 使用 `paper-libraries/full-smoke-library-optimized-v2` 做真实 provider 复测，结果 `failed=[]`；相比上一轮 clean 结果，patch mismatch warning 从 3 降到 1，protected-block warning 从 4 降到 0，风险较高的数学/公式发现转为明确的 `review_only` 记录。
- 2026-05-21 AI repair 元数据归一化修复：
  - 修复 full-smoke 回归：provider 将 `creators` 返回为字符串列表时会被判为非法，导致修复后 bundle 命名缺少作者前缀。
  - 增加 fake-provider 回归测试，覆盖 `creators: ["W.L. Huang", "Q.F. Li", "Y.Z. Lin"]` 归一化为 `paper.yaml` creator 对象，并触发基于元数据的 bundle 重命名。
  - 使用真实 provider 重新运行 `paper-libraries/full-smoke-library-optimized-v2`：`failed=[]`；Huang 光中子论文 bundle 已重命名为 `W.L. Huang et al. - 2005 - ...`，`paper doctor --json` 返回 `ok=true`，格式审计未发现非法 creator 形状或命名不一致。
  - Markdown 审计仍按预期标记公式/数学密集块为 review-only，另外还有少量低风险 auto-repair 候选，例如 front-matter 标签和 Richi Kumar GIANT 论文中的 OCR 拼写残留。
  - 统一 filename/PDF metadata、MinerU `Authors:` 解析、AI repair 和 doctor validation 的 creator 归一化逻辑。`make verify` 通过，测试数为 56。
- 2026-05-21 AI repair 阶段收口：
  - 内置 AI repair 功能本阶段先视为完成。
  - 当前已交付范围：OpenAI-compatible provider、元数据 evidence packet、安全元数据应用、修复后同步重命名 bundle、保守 Markdown repair、exact-match patch、bundle-local backup、latest-only `repair.json`、dry-run、fake-provider 测试和真实 provider 验证。
  - 当前安全边界：数学密集、公式、表格和参考文献 block 不自动改写，只记录为 `review_only` warning。
  - 剩余 AI repair 方向作为后续增强：warning 聚合、长段落 OCR 候选的 review/apply 工作流、可选 bundle selector、append-only repair history。
- 2026-05-21 AI extract summary 规划：
  - 确认下一项 AI 功能命名为 `paper extract summary`，并将 `paper extract` 保留为后续结构化抽取命令族。
  - 选择分层抽取路线：主流程构建简短文章背景和原文结构，内部并发 worker 总结 block batch，再聚合章节骨架和轻量知识图谱。
  - 确认输出文件位于 `extracts/summary/`：`summary.json` 面向结构化读取，`summary.md` 面向人类阅读，`source-map.json` 面向后续前端段落-总结对齐。
  - 确认严格追溯关系是核心合同：稳定 block id、行号、文本 hash、excerpt、section path、章节总结中的 `block_ids`、图谱节点/边中的 `source_block_ids`。
  - 确认第一版筛选策略：总结正文和 caption；跳过 references、footnotes、funding、author contributions、conflicts、copyright/license、页眉页脚、页码、OCR 噪声、纯公式、纯表格和纯图片。
  - 已将设计记录到 `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`；尚未开始实现。
- 2026-05-21 AI extract summary 实现：
  - 增加 `paper extract summary`，支持 `--paper`、`--collection`、`--limit`、`--workers`、`--force`、`--dry-run` 和 `--json`。
  - 新增 `src/paper_cli/ai/extract_summary.py`：source-map 生成、summary 专用 block 过滤、block batch worker prompt、section 聚合、graph 抽取、原子写入输出，以及已有 summary 默认跳过。
  - 输出文件写入 `extracts/summary/summary.json`、`extracts/summary/summary.md` 和 `extracts/summary/source-map.json`；追溯字段包括 block id、行号、文本 hash、section path、章节 `block_ids` 和图谱 `source_block_ids`。
  - 增加 fake-provider 测试，覆盖 source-map 过滤、追溯关系、不修改源文件、默认 skip 和 `--force`、CLI dry-run 无需 provider 配置、missing block summary 重试。
  - 最终 `make verify` 通过，测试数为 61，ruff clean。
  - 在 `paper-libraries/full-smoke-library-optimized-v2` 上做真实 provider dry-run，识别 5 个已转换 bundle、249 个可总结 block 和 35 个 block batch。
  - 真实 provider 抽取已为 5 个转换后 bundle 写出 summary。最终每篇 `summary.json.blocks` 都与 `source-map.json` 中 `summary_policy=summarize` 的数量一致：Jae Yeon Park 44/44，Jorge Lerendegui-Marco 61/61，Richi Kumar 55/55，W.L. Huang 26/26，Yu Yangyi 63/63。
  - smoke test 中发现一次 provider 漏回 Jae Yeon Park 的部分 block summary；已增加回归测试和重试实现，避免漏项静默破坏后续前端对齐。
  - 抽取后，smoke library 的 `paper status --json` 返回 `total=5`、`converted=5`、`failed=0`、`pending=0`；`paper doctor --json` 返回 `ok=true`。
- 2026-05-23 AI extract summary 并发更新：
  - 将 `paper extract summary --workers` 默认值从 2 改为 16。
  - 增加按当前论文 block batch 数裁剪实际 worker 数的逻辑，因此像 `--workers 200` 这样的超大值不会产生超过当前论文 batch 数的并发 provider 调用。
  - 增加默认 worker 常量和 effective worker 计算的回归测试。
- 2026-05-23 AI extract summary 论文层并发更新：
  - 增加 `--paper-workers` 控制论文层并行，默认值为 16。
  - 增加 `--max-requests` 作为全局 provider 请求并发上限，默认值为 16，并由所有论文的 block summary、section aggregation 和 graph extraction 共享。
  - 增加 `--retries`，默认值为 2，包裹每一次 provider 请求；最终失败会在 `failed[].error` 中报告 schema、尝试次数和底层错误。
  - 增加 fake-provider 回归测试，覆盖多篇论文并发、全局请求限流、临时 provider 失败重试成功、最终失败时清晰报错且不写部分 summary 输出。
- 2026-05-23 AI extract summary 请求上限默认值更新：
  - 按用户的高并发 provider 环境，将全局 provider 请求上限 `--max-requests` 默认值从 16 提高到 500。
  - 保留 `--max-requests` 可配置，因此受限 provider 仍可手动降低上限。
- 2026-05-23 AI extract summary 重试等待更新：
  - 增加 provider 请求重试之间固定等待 10 秒的逻辑。
  - 将重试等待保留为程序内部常量，不暴露为公开 CLI 参数，避免参数过多。
  - 测试中的 retry case 通过内部函数使用 `retry_wait=0`，避免测试套件变慢，同时保留生产默认值。
- 2026-05-23 QED random-30 加固跟进：
  - 为 MinerU submit、upload、polling 和 ZIP download 网络请求增加重试/退避；upload 重试前会重置 PDF 文件流位置。
  - 增加 `MINERU_MAX_WAIT_SECONDS`，默认每篇 30 分钟，避免单个远端 MinerU 任务无限阻塞整个串行批处理。
  - 转换被中断时会写入 `state=interrupted` 的 `conversion.json`，追加匹配的 `conversion-finished` job event，将 bundle 标为 failed 以便后续重试，重建索引，然后重新抛出中断。
  - 增加 `paper doctor --strict`，用于报告 pending/failed 转换、非法 job JSON，以及没有匹配 finish 事件的悬空 `conversion-started`。
  - 增加标题质量门禁，OCR 损坏的 MinerU heading 如果包含尾部路径字符、替换字符、全大写改写或可疑连写，不会覆盖更好的既有标题，也不会触发 bundle 重命名。
  - `make verify` 通过，测试数为 72，ruff clean。

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
- `docs/superpowers/specs/2026-05-21-paper-cli-ai-repair-design.md`
- `docs/superpowers/specs/2026-05-21-paper-cli-extract-summary-design.md`
