# `paper.yaml` 契约

`paper.yaml` 是单篇论文 bundle 的 canonical record。目录名可以改变，索引可以重建，转换器 sidecar 可以重新生成，但论文身份和当前状态以 `paper.yaml` 为准。

## 位置

```text
<paper-bundle>/paper.yaml
```

每个有效 paper bundle 都必须包含这个文件。

## 当前 Schema

```yaml
schema_version: 1
id: sha256:<pdf-sha256>
name: Guo et al. - 2026 - Example Title
name_locked: false
previous_names: []
collection: plasma/lwfa
metadata:
  title: Example Title
  creators:
    - name: Guo
      role: author
  year: 2026
  language: en
  doi: null
source:
  type: local-folder
  imported_from: /absolute/source.pdf
  copied_pdf: original.pdf
  imported_at: "2026-05-13T00:00:00+00:00"
status:
  import: done
  conversion: pending
  metadata: partial
  naming: fast
naming:
  template: default
  rendered_from:
    - creators
    - year
    - title
  last_renamed_at: null
```

## 字段含义

- `schema_version`：整数 schema 版本。当前为 `1`。
- `id`：稳定 paper ID。MVP 使用 `sha256:<source-pdf-hash>`。
- `name`：当前 bundle 目录名。
- `name_locked`：为 `true` 时，禁止自动重命名 bundle。
- `previous_names`：自动重命名前的历史目录名。
- `collection`：相对 `collections/` 的分类路径；inbox 论文为 `null`。
- `metadata`：当前最佳文献元数据。
- `source`：导入来源信息。
- `status`：导入、转换、元数据和命名的工作流状态。
- `naming`：命名模板相关记录。

## 状态值

- `status.import`：`done`
- `status.conversion`：`pending`、`done` 或 `failed`
- `status.metadata`：`partial` 或 `complete`
- `status.naming`：`fast`、`metadata` 或 `review`

## 重命名规则

转换后，`paper-cli` 可以根据更好的元数据重命名整个 bundle。稳定 `id` 不能改变。旧目录名应加入 `previous_names`，并更新 `naming.last_renamed_at`。

如果 `name_locked` 为 `true`，不能自动重命名；当更好元数据本应触发重命名时，命名状态应进入 `review`。

## 计划中的兼容扩展

下一步 schema 应增加来源和置信度字段，但不移除当前字段：

```yaml
metadata_sources:
  title: mineru
  creators: filename-title-prefix
  year: filename
metadata_confidence:
  title: high
  creators: medium
  year: medium
```

调用方应忽略未知顶层字段，以保持后续扩展的向后兼容。
