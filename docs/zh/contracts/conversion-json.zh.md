# `conversion.json` 契约

`conversion.json` 记录单个 paper bundle 最近一次转换结果。它与 `paper.yaml` 和 `paper.md` 放在同一 bundle 中。

## 位置

```text
<paper-bundle>/conversion.json
```

文件会在转换尝试之后生成。

## 当前成功格式

```json
{
  "ok": true,
  "converted_at": "2026-05-13T00:00:00+00:00",
  "error": null
}
```

## 当前失败格式

```json
{
  "ok": false,
  "converted_at": "2026-05-13T00:00:00+00:00",
  "error": "MINERU_API_KEY is not set"
}
```

## 字段含义

- `ok`：最近一次转换是否成功。
- `converted_at`：写入该结果的 UTC 时间。
- `error`：成功时为 `null`，失败时为诊断文本。

## Bundle 输出契约

转换成功后，bundle 应包含：

```text
paper.md
images/
conversion.json
raw/
  mineru/
```

`paper.md` 和 `images/` 是 agent 的主要阅读表面。MinerU sidecar 文件，例如 `layout.json`、`*_content_list.json`、`*_origin.pdf`，应放入 `raw/mineru/`。

## 计划中的兼容扩展

工程化版本应把该文件扩展为诊断记录：

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": true,
  "state": "done",
  "submitted_at": "2026-05-13T00:00:00+00:00",
  "converted_at": "2026-05-13T00:01:00+00:00",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

未来读取方应兼容当前最小格式，并忽略未知字段。
