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
  "schema_version": 1,
  "converter": "mineru",
  "ok": true,
  "state": "done",
  "attempt": 1,
  "submitted_at": "2026-05-13T00:00:00+00:00",
  "converted_at": "2026-05-13T00:01:00+00:00",
  "error": null,
  "raw_output_dir": "raw/mineru",
  "markdown": "paper.md",
  "images": "images"
}
```

## 当前失败格式

```json
{
  "schema_version": 1,
  "converter": "mineru",
  "ok": false,
  "state": "failed",
  "attempt": 1,
  "submitted_at": "2026-05-13T00:00:00+00:00",
  "converted_at": "2026-05-13T00:00:00+00:00",
  "error": "MINERU_API_KEY is not set",
  "raw_output_dir": null,
  "markdown": "paper.md",
  "images": "images"
}
```

## 字段含义

- `schema_version`：整数 schema 版本。当前为 `1`。
- `converter`：转换器名称，例如 `mineru` 或 `local-fixture`。
- `ok`：最近一次转换是否成功。
- `state`：最近一次转换状态。当前值为 `done` 或 `failed`。
- `attempt`：该 bundle 的转换尝试次数。失败 bundle 重试时会递增。
- `submitted_at`：转换器执行开始前的 UTC 时间。
- `converted_at`：写入该结果的 UTC 时间。
- `error`：成功时为 `null`，失败时为诊断文本。
- `raw_output_dir`：相对 bundle 的转换器原始输出目录，或 `null`。
- `markdown`：相对 bundle 的 Markdown 输出路径。
- `images`：相对 bundle 的图片目录路径。

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

## Job History

`indexes/jobs.jsonl` 是 append-only 的转换事件日志。每次转换尝试都会写入一个开始事件和一个结束事件。

```jsonl
{"event":"conversion-started","at":"2026-05-13T00:00:00+00:00","paper_id":"sha256:...","bundle_path":"inbox/Example","converter":"mineru","attempt":1,"state":"running"}
{"event":"conversion-finished","at":"2026-05-13T00:01:00+00:00","paper_id":"sha256:...","bundle_path":"inbox/Example","converter":"mineru","attempt":1,"state":"done","ok":true}
```

失败转换的结束事件使用 `state: "failed"`、`ok: false`，并包含 `error`。

未来读取方应忽略未知字段。
