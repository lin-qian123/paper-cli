# CLI JSON 契约

所有用户可见命令都应支持 `--json`。JSON 输出面向 agent 和脚本，必须保持合法、紧凑、稳定。

## 全局规则

- JSON 输出到 stdout。
- 面向人的文本输出可以变化，但 JSON 结构应保持兼容。
- 成功命令返回退出码 `0`。
- `doctor` 发现验证问题时返回退出码 `1`。
- CLI 参数错误遵循 argparse 行为，通常为退出码 `2`。

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
      "path": "/path/to/library/inbox/Guo et al. - 2026 - Title"
    }
  ]
}
```

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
  "issues": []
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
- `duplicate-id`
- `missing-original-pdf`
- `missing-paper-md`
- `stale-index`
