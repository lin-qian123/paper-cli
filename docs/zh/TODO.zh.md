# TODO 中文版

## 当前阶段

设计和计划阶段。

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

## 阻塞点 / 待定问题

- MVP 实现语言为 Python；在契约稳定后重新评估 Rust 是否适合后续大范围开发。
- 决定第一版 MinerU 集成是复用现有脚本，还是包装一个更干净的新 client。
- 决定 MinerU 转换前要做多少元数据抽取。
- 决定 MVP 索引是否只保留 JSONL，还是后续加入 SQLite。

## 实现计划

- `.agents/superpowers/specs/2026-05-13-paper-cli-mvp-implementation.md`
