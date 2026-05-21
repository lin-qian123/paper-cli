# AI Repair Suspicious Block Optimization Record

Date: 2026-05-21

## Background

The first `paper repair` implementation selects suspicious Markdown blocks with simple local rules, then sends those blocks to an OpenAI-compatible provider for patch suggestions. A full smoke test on the `双模照相` paper set showed that the basic flow works, but the selection layer is too coarse for scientific papers.

The tested corpus contained 12 copied PDFs, which imported into 7 unique bundles after hash-based duplicate skipping. Real MinerU conversion succeeded for all 7 bundles, and real AI repair completed after a partial-write bug was fixed. The repair run exposed concrete weaknesses in suspicious-block selection.

## Current Weaknesses

1. Formula blocks are too easily selected.
   - Blocks containing spaced OCR tokens like `s l o p e`, `A t t`, `m n u c l e u s`, or `N _ e` are selected.
   - The apply layer protects full `formula`, `table`, and `reference` blocks, but the provider still sees them.
   - Paragraphs containing inline formulas are still classified as ordinary paragraphs, so AI can rewrite scientific expressions inside prose.

2. OCR word errors are not detected consistently.
   - Real examples included `Te` for `The`, `Tere` for `There`, `fssion`, `diferent`, and `scientifc`.
   - These are repairable prose OCR errors, but the current rules only catch them incidentally.

3. Repeated text is not detected.
   - Some MinerU output repeated a phrase inside a paragraph, such as duplicated `The gamma-ray beam is produced...`.
   - This is a common PDF extraction defect and should be a repair candidate.

4. Front-matter and publisher boilerplate are under-classified.
   - Examples include `OPEN`, `Article`, `Open Access`, `Check for updates`, `Publisher's Note`, `Copyright`, and `RESEARCH ARTICLE`.
   - Some should be removed or normalized; some should simply be recorded as front matter. They should not be mixed with scientific-content repairs.

5. Table and reference detection are too weak.
   - Only pipe-style Markdown tables are detected.
   - MinerU can emit HTML tables or `Table 2 ... <table>`.
   - Only a block exactly equal to `references` or `bibliography` becomes `reference`; blocks after a references heading are not protected.

6. Image-caption mixed blocks are not separated.
   - Blocks like `![](images/x.jpg) Figure 1 ...` are classified as `image`.
   - The image path may be valid while the caption text contains OCR errors, so this needs a separate future treatment.

7. The system does not record why a block was considered suspicious.
   - Without reasons, a later audit cannot distinguish page noise, formula OCR, missing image, or prose OCR.
   - The provider prompt also cannot be constrained by reason.

## Optimization Direction

The next implementation should add a structured suspicious finding layer:

```json
{
  "block_id": "b00062",
  "reasons": ["spaced_letters", "math_heavy"],
  "policy": "review_only"
}
```

Policies:

- `auto_repair`: safe to send to AI for patch suggestions.
- `review_only`: record as suspicious, but do not send to AI for automatic patching.
- `structural_warning`: report as a structural issue, but do not ask AI to rewrite content.

Initial policy rules:

- Full `formula`, `table`, and `reference` blocks become `review_only` when suspicious.
- Math-heavy paragraphs become `review_only`, especially when the suspicious signal comes from spaced formula tokens.
- Broken image references become `structural_warning`.
- Short front-matter noise, repeated text, replacement characters, and common prose OCR word errors can be `auto_repair`.

## First Implementation Scope

Implement only the conservative selection layer:

- Add suspicious findings with `reasons` and `policy`.
- Keep the old `suspicious_blocks()` compatibility API.
- Use only `auto_repair` findings as AI Markdown candidates.
- Add warnings for `review_only` and `structural_warning` findings in `repair.json`.
- Improve block typing:
  - HTML tables become `table`.
  - `## References` / `## Bibliography` starts a protected reference section.
- Add prose repair signals:
  - common OCR words: `Te`, `Tere`, `fssion`, `diferent`, `scientifc`, `efciency`, `frst`;
  - repeated phrase fragments inside a paragraph.

Out of scope for this pass:

- Automatic formula rewriting.
- Human review UI.
- Persistent index-level AI repair job history.
- MinerU layout JSON integration.
- Image-caption splitting.

## Expected Effect

Compared with the previous real repair run:

- Fewer formula/math-heavy blocks should be sent to AI.
- `Protected Markdown block skipped` warnings should decrease because protected blocks should not reach the provider.
- Repair should focus more on prose OCR defects and repeated text.
- Metadata repair behavior should remain unchanged.
- `paper doctor` and `make verify` must remain clean.

## Validation Plan

1. Add unit tests for:
   - suspicious finding reasons and policies;
   - formula block is `review_only`;
   - math-heavy paragraph is `review_only`;
   - common OCR word paragraph is `auto_repair`;
   - repeated phrase paragraph is `auto_repair`;
   - broken image is `structural_warning`;
   - reference section blocks are protected.
2. Run focused tests.
3. Run `make verify`.
4. Rebuild a clean test library from the `双模照相` PDFs.
5. Run real MinerU conversion.
6. Run `paper repair --target metadata --dry-run --json`.
7. Run `paper repair --json`.
8. Compare repair quality:
   - count of Markdown blocks changed;
   - count and type of warnings;
   - whether formula/protected-block warnings decreased;
   - inspect Markdown diffs against backups for scientific-content risk.

## Implementation Notes

Implemented conservative suspicious-block classification:

- Added `SuspiciousFinding` with `reasons` and `policy`.
- Preserved `suspicious_blocks()` as a compatibility wrapper.
- Added `repairable_suspicious_blocks()` so Markdown repair only sends `auto_repair` blocks to the provider.
- Added `review_only` warnings for protected or math-heavy findings.
- Added `structural_warning` policy for broken image references.
- Improved block typing for HTML tables and reference sections.
- Added common OCR word and repeated-phrase signals.
- Added a length guard so common OCR words in long scientific paragraphs are `review_only` instead of automatic repair candidates.

## Validation Result

Validation used the `双模照相` PDF set again. A fresh optimized test library was built under `paper-libraries/full-smoke-library-optimized-v2`.

Notes:

- Real MinerU conversion had one transient network failure on the Yangyi Yu paper (`mineru.oss-cn-shanghai.aliyuncs.com` read timeout). The failed bundle was completed from the previous clean test's local converted Markdown/images fixture to continue AI-repair comparison without repeatedly hitting the network.
- `make verify` passed before the real-provider retest: 51 tests passed and ruff passed.
- `paper repair --target metadata --dry-run --json` returned `ok=true` and wrote no `repair.json`.
- `paper repair --json` returned `ok=true`, `failed=[]`; `paper status` reported `converted=7`, `failed=0`, `pending=0`; `paper doctor` reported no issues.

Comparison against the previous clean repair run:

| Metric | Previous clean run | Optimized v2 run | Interpretation |
| --- | ---: | ---: | --- |
| Bundles repaired | 7 | 7 | Same coverage |
| Markdown-changed bundles | 5 | 3 | Fewer automatic content edits |
| Suspicious blocks checked | 33 | 101 | More defects classified and recorded |
| Markdown blocks changed | 9 | 10 | Similar total changes, concentrated in safer candidates |
| Patch mismatch warnings | 3 | 1 | Better provider/apply alignment |
| Protected-block warnings | 4 | 0 | Protected blocks no longer reach the old apply-time guard |
| Review-only warnings | 0 | 83 | Risky math/formula/scientific blocks are now recorded instead of auto-sent |
| Backup files | 12 | 10 | Fewer files were modified |

Qualitative result:

- Improved: formula-heavy and math-heavy content is no longer automatically sent for repair.
- Improved: `Protected Markdown block skipped` warnings disappeared because risky blocks are filtered earlier.
- Improved: Richi Kumar prose OCR fixes now target more ordinary prose, such as `Tis` -> `This`, `diferent` -> `different`, `dark feld` -> `dark field`, `frst` -> `first`, and `Ten` -> `Then`.
- Improved: scientific formula-heavy changes in Yangyi Yu and the Chinese reports were mostly converted to `review_only` instead of automatic edits.
- Remaining issue: `review_only` warnings are too verbose for large papers. The next improvement should aggregate warnings by reason and count, while preserving detailed block IDs in a machine-readable field.
- Remaining issue: long prose OCR errors are conservative `review_only` by default, so automatic repair may miss valid prose fixes unless a future review/apply workflow is added.
