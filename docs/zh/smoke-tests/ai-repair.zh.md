# 真实 AI Repair Smoke Test

用这个清单验证 `paper repair` 的真实 OpenAI-compatible provider 路径。不要提交 PDF、抽取图片、备份或真实模型输出。

## 前置条件

- `paper-libraries/` 下有一个测试文献库，至少包含一个已转换 bundle。
- bundle 内有 `paper.yaml`、`paper.md`、`original.pdf` 和 `conversion.json`。
- provider 设置来自环境变量或 `paper-cli.yaml`。
- 密钥只放在环境变量里，不写入 `paper-cli.yaml`。

检查：

```bash
test -n "$PAPER_AI_API_KEY" && echo "PAPER_AI_API_KEY=set"
test -n "$PAPER_AI_MODEL" && echo "PAPER_AI_MODEL=$PAPER_AI_MODEL"
```

可选的 `paper-cli.yaml` 配置：

```yaml
ai:
  provider: openai-compatible
  base_url: https://api.openai.com/v1
  api_key_env: PAPER_AI_API_KEY
  model: gpt-4.1-mini
  temperature: 0
  timeout_seconds: 60
```

## 运行

选择本地测试文献库：

```bash
library="paper-libraries/ai-repair-live-test"
```

先查看当前状态：

```bash
uv run python -m paper_cli --library "$library" status --json
uv run python -m paper_cli --library "$library" list --json
```

先 dry-run 元数据修复：

```bash
uv run python -m paper_cli --library "$library" repair --target metadata --dry-run --json
```

再实际应用修复：

```bash
uv run python -m paper_cli --library "$library" repair --json
```

修复后验证：

```bash
uv run python -m paper_cli --library "$library" status --json
uv run python -m paper_cli --library "$library" doctor --json
uv run python -m paper_cli --library "$library" list --json
```

## 预期结果

- dry-run 会报告建议变更，但不写 `repair.json` 或 `backups/`。
- 实际应用会在每个被修复 bundle 中写入 `repair.json`。
- 应用的元数据字段会把 `metadata_sources.<field>` 设为 `ai-repair`。
- 只有实际变更的文件才会有备份：
  - `backups/paper.yaml.<timestamp>.bak`
  - `backups/paper.md.<timestamp>.bak`
- `indexes/papers.jsonl` 反映重命名或元数据更新。
- `paper doctor --json` 返回 `{"ok": true, "issues": []}`。

## 不要提交

不要提交：

- `paper-libraries/`
- 复制后的 PDF
- 抽取图片
- 真实论文的 `repair.json`
- `backups/`
- provider API key 或用户本机绝对路径

只在 `TODO.md` 中记录简短验证摘要。
