# Source Adapter 契约

Source adapter 负责把本地或外部来源的论文导入统一 paper bundle 格式。

## 当前参考 Adapter

当前参考 adapter 是 `LocalFolderAdapter`：

```python
from paper_cli.adapters.local_folder import LocalFolderAdapter

result = LocalFolderAdapter().import_source(
    library_dir,
    input_path,
    collection=None,
    inbox=True,
)
```

它会扫描本地 PDF 文件或文件夹，将新 PDF 复制进 bundle，按 SHA-256 跳过重复 PDF，并把索引重建留给 importer facade。

## 接口

Adapter 暴露：

```python
name: str

def import_source(
    library_dir: Path,
    input_path: Path,
    *,
    collection: str | None,
    inbox: bool,
) -> ImportResult:
    ...
```

`ImportResult` 包含：

- `imported`：新创建的 bundle 路径。
- `skipped`：adapter 跳过的来源路径，当前主要用于重复 PDF。

## Facade

CLI 仍然调用 `paper_cli.importer.import_path()`。该 facade 委托给 `LocalFolderAdapter` 并重建索引。后续 adapter 应保持相同的 paper bundle、`paper.yaml` 和索引契约。

## 未来 Adapter

计划中的 adapter 包括：

- Zotero 只读导入。
- Attanger 风格 attachment root 映射。
- BibTeX 导入。
- CSL JSON 导入。

Adapter 不应修改外部来源文献库。它们应复制 PDF，或将来源元数据通过明确 provenance 字段写入 paper bundle。
