# 真实 MinerU Smoke Test

使用这个清单验证真实 MinerU 转换路径，同时避免提交用户 PDF 或转换产物。

## 前置条件

- 环境变量中已设置 `MINERU_API_KEY`。
- 准备一个较小的本地 PDF。
- 当前目录是 `paper-cli` 仓库根目录。
- `paper-libraries/` 已被 git 忽略。

检查：

```bash
test -n "$MINERU_API_KEY" && echo "MINERU_API_KEY=set"
git status --short --ignored paper-libraries
```

## 运行

选择一个本地测试库名称：

```bash
library="paper-libraries/desktop-live-test"
pdf="/absolute/path/to/paper.pdf"
rm -rf "$library"
```

初始化并导入：

```bash
uv run python -m paper_cli init "$library" --json
uv run python -m paper_cli --library "$library" import "$pdf" --inbox --json
```

使用真实 MinerU 转换：

```bash
uv run python -m paper_cli --library "$library" convert --pending --json
```

验证：

```bash
uv run python -m paper_cli --library "$library" status --json
uv run python -m paper_cli --library "$library" doctor --json
uv run python -m paper_cli --library "$library" list --json
```

## 预期结果

- `status` 报告 `failed: 0`。
- `doctor` 报告 `{"ok": true, "issues": []}`。
- bundle 包含：
  - `original.pdf`
  - `paper.yaml`
  - `paper.md`
  - `images/`
  - `conversion.json`
  - `raw/mineru/`
  - `notes/README.md`
- MinerU sidecar 文件位于 `raw/mineru/`，不在 bundle 根目录。

## 不要提交的内容

不要提交：

- `paper-libraries/`
- 复制后的 PDF
- 提取图片
- MinerU 原始输出
- 生成 bundle 文件中的用户本机绝对路径

只把验证结论记录到 `TODO.md`。
