# Security Policy

## Supported Versions

`paper-cli` is currently in `v0.1.x` initial preview. Security fixes should target the latest released version.

## Reporting A Vulnerability

Please report security issues privately instead of opening a public issue when the report contains sensitive details.

Use GitHub's private vulnerability reporting if it is enabled for the repository. If it is not enabled, contact the maintainer directly through the email listed in `pyproject.toml`.

Include:

- affected version or commit;
- operating system and Python version;
- command used;
- whether cloud MinerU or an AI provider was involved;
- minimal reproduction steps;
- any logs with secrets removed.

## Secrets

Do not commit secrets.

`paper-cli` expects credentials to come from environment variables or uncommitted local configuration:

- `MINERU_API_KEY`
- `MINERU_API_BASE`
- `PAPER_AI_API_KEY`
- `PAPER_AI_BASE_URL`
- `PAPER_AI_MODEL`

The repository `.gitignore` excludes `.env`, virtual environments, and local paper libraries.

## Data Privacy

`paper-cli` is local-first, but some commands send content to external services:

- MinerU cloud conversion uploads PDFs or split PDF parts to MinerU.
- AI repair, summary extraction, and memory build send bounded text or metadata evidence to the configured OpenAI-compatible provider.

Do not run cloud conversion or AI commands on private, confidential, or restricted PDFs unless you are comfortable with the configured provider receiving that content.

## Local Files

The CLI should not modify source PDFs in place. Imported PDFs are copied into paper bundles as `original.pdf`.

Generated libraries can contain copyrighted PDFs, converted Markdown, extracted images, and provider outputs. Keep generated libraries out of git unless you have verified that the contents are safe to publish.
