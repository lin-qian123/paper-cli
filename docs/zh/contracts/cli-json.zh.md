# CLI JSON 契约

所有用户可见命令都应支持 `--json`。JSON 输出面向 agent 和脚本，必须保持合法、紧凑、稳定。

## 全局规则

- JSON 输出到 stdout。
- 面向人的文本输出可以变化，但 JSON 结构应保持兼容。
- 成功命令返回退出码 `0`。
- `doctor` 发现验证问题时返回退出码 `1`。
- `resolve`、`get` 和 `inspect` 在查询不到或查询歧义时返回退出码 `1`。
- CLI 参数错误遵循 argparse 行为，通常为退出码 `2`。
- JSON 错误不得包含 API key、bearer token、cookie 或完整敏感 header。

## `init`

```bash
python3 -m paper_cli init /path/to/library --json
```

```json
{
  "ok": true,
  "library": "/path/to/library"
}
```

## `import`

```bash
python3 -m paper_cli --library /path/to/library import /path/to/papers --inbox --json
```

```json
{
  "ok": true,
  "imported": [
    "/path/to/library/inbox/Example et al. - 2026 - Title"
  ]
}
```

`imported` 只包含新导入 bundle 路径。按 SHA-256 跳过的重复 PDF 当前不会出现在该列表中。

## `convert`

```bash
python3 -m paper_cli --library /path/to/library convert --pending --json
```

```json
{
  "ok": true,
  "converted": [
    "/path/to/library/inbox/Guo et al. - 2026 - Title"
  ]
}
```

`converted` 包含转换成功后的 bundle 路径；如果发生自动重命名，返回重命名后的路径。

Dry-run 输出用于在不写文件、不调用 MinerU 的情况下预览转换计划：

```bash
paper --library /path/to/library convert --pending --converter mineru-local --dry-run --json
```

```json
{
  "ok": true,
  "dry_run": true,
  "converter": "mineru-local",
  "batch_size": 20,
  "jobs": 1,
  "local_backend": "pipeline",
  "pending_count": 1,
  "pending": [],
  "diagnostics": {},
  "planned_writes": [
    "paper.md",
    "images/",
    "raw/mineru/",
    "conversion.json",
    "indexes/papers.jsonl",
    "indexes/jobs.jsonl"
  ]
}
```

## `list`

```bash
python3 -m paper_cli --library /path/to/library list --json
```

```json
{
  "papers": [
    {
      "id": "sha256:...",
      "name": "Guo et al. - 2026 - Title",
      "collection": null,
      "status": {
        "import": "done",
        "conversion": "done",
        "metadata": "complete",
        "naming": "metadata"
      },
      "path": "/path/to/library/inbox/Guo et al. - 2026 - Title",
      "relative_path": "inbox/Guo et al. - 2026 - Title"
    }
  ]
}
```

## `resolve` / `get` / `inspect`

`resolve` 将 paper ID、ID 前缀、名称/标题片段、相对路径、bundle 绝对路径或 bundle 内文件路径解析为单个 bundle：

```bash
paper --library /path/to/library resolve "Guo" --json
```

```json
{
  "ok": true,
  "query": "Guo",
  "paper": {
    "id": "sha256:...",
    "name": "Guo et al. - 2026 - Title",
    "collection": null,
    "status": {
      "conversion": "done"
    },
    "path": "/path/to/library/inbox/Guo et al. - 2026 - Title",
    "relative_path": "inbox/Guo et al. - 2026 - Title"
  },
  "reasons": [
    "name-substring"
  ]
}
```

歧义查询返回：

```json
{
  "ok": false,
  "query": "Guo",
  "error": "ambiguous",
  "matches": []
}
```

`get` 返回一个 paper 的 `paper.yaml` 元数据表面；`inspect` 在此基础上增加产物存在性，以及可解析的 `conversion.json`、`repair.json`、`extracts/summary/summary.json` 和 `source-map.json`。两者都只读。

## `status`

```bash
python3 -m paper_cli --library /path/to/library status --json
```

```json
{
  "total": 1,
  "converted": 1,
  "failed": 0,
  "pending": 0,
  "incomplete_metadata": 0,
  "renamed": 1
}
```

## `doctor`

```bash
python3 -m paper_cli --library /path/to/library doctor --json
```

成功输出：

```json
{
  "ok": true,
  "issues": [],
  "diagnostics": {
    "library": {
      "path": "/path/to/library",
      "config_path": "/path/to/library/paper-cli.yaml",
      "config_exists": true,
      "inbox_exists": true,
      "collections_exists": true,
      "indexes_exists": true
    },
    "mineru": {
      "api_key_env": "MINERU_API_KEY",
      "api_key_available": false,
      "configured_executable": "mineru",
      "configured_local_backend": null,
      "configured_local_jobs": "auto",
      "configured_max_wait_seconds": null
    },
    "ai": {
      "provider": "openai-compatible",
      "api_key_env": "PAPER_AI_API_KEY",
      "api_key_available": false,
      "base_url_configured": false,
      "model_configured": false
    }
  }
}
```

问题输出：

```json
{
  "ok": false,
  "issues": [
    {
      "code": "missing-original-pdf",
      "path": "/path/to/bundle",
      "message": "Missing original.pdf"
    }
  ]
}
```

当前已知 issue code：

- `invalid-paper-yaml`
- `missing-library-config`
- `duplicate-id`
- `missing-original-pdf`
- `missing-paper-md`
- `stale-index`
- `invalid-creators`
- `failed-conversion`
- `pending-conversion`
- `invalid-job-json`
- `dangling-conversion-job`
- `invalid-conversion-json`
- `missing-batch-conversion-mapping`
- `stale-running-conversion`
- `invalid-conversion-timestamp`
- `missing-mineru-local-executable`
- `invalid-mineru-local-executable`

## `repair` / `extract summary` / `validate qed`

`repair` 缺少 provider 配置时返回：

```json
{
  "ok": false,
  "error": "Missing AI provider configuration: PAPER_AI_API_KEY, PAPER_AI_MODEL or ai.model",
  "repaired": [],
  "failed": []
}
```

`extract summary` 使用统一 envelope：

```json
{
  "ok": true,
  "dry_run": true,
  "planned": [],
  "extracted": [],
  "skipped": [],
  "failed": []
}
```

`validate qed` 返回验证库路径、报告路径、抽样/导入/转换计数、产物计数和 doctor issues，用于可重复的 QED 语料 smoke test。
