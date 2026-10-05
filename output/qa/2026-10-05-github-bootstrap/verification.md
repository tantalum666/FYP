# GitHub bootstrap verification · Group 2

Date: 2026-10-05 (Asia/Hong_Kong). Status: local upload checks in progress; remote creation / push still pending in this checkpoint.

## Scope

User authorised a new repository named FYP and upload of all project work for team collaboration. Current Desk Companion, retired Senplate, school documents, planning, research, design / brand assets, hardware studies, delivery packages and project-generated QA are retained. Fourteen explicitly supplied original attachments were copied byte-for-byte from Downloads; see [input manifest](../../../inputs/manifest.json).

Only private runtime / credentials, installed dependencies, build caches, OS font links and signing material are excluded. The upload keeps the trademark-reference SVG corpus; it is source research, not an installed dependency.

## Local checks

- [Reading record](reading-record.json): 119 project-owned Markdown files, 11,237 lines, all 51 chunks read to EOF, no file drift during full reading. A newly copied teammate Markdown was read in full before copying and hash-matched. Compaction continued the same reading record.
- [Initial inventory](file-inventory.json), final upload manifest and remote-tree verification record distinguish source coverage from dependencies.
- Gitleaks 8.30.1 scanned candidates and archives to depth 2. All 104 initial alerts were verified as 70 SHA256 integrity entries, 19 public Figma file identifiers and 15 Swift UserDefaults storage keys. [Classification](secret-classification.json). Narrow path + exact-format / literal exceptions are in `.gitleaks.toml`; provider-secret rules remain active. Filtered scans passed.
- Exact comparison against private local credential / configuration values additionally found two binary iOS test records containing an actual local test password. Those records were sanitised, with raw originals preserved inside Git-ignored `.runtime/`. [Sanitisation record](evidence-sanitization.json). Passwords are never written into these reports.
- Nine ZIP archives contain no `.runtime`, `.env` or `credentials.json` entries. Upload candidates have no remaining symlinks or private database files; all are below GitHub's 100 MiB per-file limit.
- The 107 protected school / identity / retired-code files are to be hash-checked before upload. No application behaviour or school DOCX / PDF was edited; earlier software tests and page renders are not being rerun or claimed as new results.

## Collaboration documentation

Root README, product contract, software README and [CONTRIBUTING.md](../../../CONTRIBUTING.md) provide current / historical routing, relative clone-and-run instructions, per-member credentials and branches / pull requests. No collaborator invitation, release, app deployment or school submission is part of this checkpoint. Member invitations are explained with official GitHub documentation.

## Remote verification

Pending: confirm repository privacy, default branch, remote HEAD and every remote file path / Git blob against the local committed tree. Final handoff / work log will be updated after that readback.
