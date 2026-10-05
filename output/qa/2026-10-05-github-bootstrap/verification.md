# GitHub bootstrap verification · Group 2

Date: 2026-10-05 (Asia/Hong_Kong). Status: full workspace pushed; private repository, default main and every committed file verified against the remote Git tree. The early authorisation blocker is resolved.

## Scope

User authorised a new repository named FYP and upload of all project work for team collaboration. Current Desk Companion, retired Senplate, school documents, planning, research, design / brand assets, hardware studies, delivery packages and project-generated QA are retained. Fourteen explicitly supplied original attachments were copied byte-for-byte from Downloads; see [input manifest](../../../inputs/manifest.json).

Only private runtime / credentials, installed dependencies, build caches, OS font links and signing material are excluded. The upload keeps the trademark-reference SVG corpus; it is source research, not an installed dependency.

## Local checks

- [Reading record](reading-record.json): 119 project-owned Markdown files, 11,237 lines, all 51 chunks read to EOF, no file drift during full reading. A newly copied teammate Markdown was read in full before copying and hash-matched. Compaction continued the same reading record.
- [Initial inventory](file-inventory.json), final upload manifest and remote-tree verification record distinguish source coverage from dependencies.
- Gitleaks 8.30.1 scanned candidates and archives to depth 2. All 104 initial alerts were verified as 70 SHA256 integrity entries, 19 public Figma file identifiers and 15 Swift UserDefaults storage keys. [Classification](secret-classification.json). Narrow path + exact-format / literal exceptions are in `.gitleaks.toml`; provider-secret rules remain active. Filtered scans passed.
- Exact comparison against private local credential / configuration values additionally found two binary iOS test records containing an actual local test password. Those records were sanitised, with raw originals preserved inside Git-ignored `.runtime/`. [Sanitisation record](evidence-sanitization.json). Passwords are never written into these reports.
- Nine ZIP archives contain no `.runtime`, `.env` or `credentials.json` entries. Upload candidates have no remaining symlinks or private database files; all are below GitHub's 100 MiB per-file limit.
- All 107 protected school / identity / retired-code files are hash-checked and unchanged. All 14 input copies match their original hashes. No application behaviour or school DOCX / PDF was edited; earlier software tests and page renders are not being rerun or claimed as new results.

## Collaboration documentation

Root README, product contract, software README and [CONTRIBUTING.md](../../../CONTRIBUTING.md) provide current / historical routing, relative clone-and-run instructions, per-member credentials and branches / pull requests. No collaborator invitation, release, app deployment or school submission is part of this checkpoint. Member invitations are explained with official GitHub documentation.

## Remote verification

Created [tantalum666/FYP](https://github.com/tantalum666/FYP) through the authenticated Chrome session. The resulting repository page shows **Private**, owner `tantalum666` and the empty-repository setup page. No collaborators have been invited.

Local initial commit: `fc5c7c9`, 6,003 files; [upload checks](upload-manifest.json) include every source / output category and 13 known private runtime values checked against files and archive entries, with no remaining matches. Gitleaks staged scan also returned exit 0.

Both `gh repo create` (GraphQL) and REST `POST user/repos` returned permission errors. Browser creation succeeded. The HTTPS push then returned `Write access to repository not granted` (403); API access cannot resolve the private new repository with the current scoped token. An existing local SSH key did not authenticate, and the existing OS Git credential also failed. Those initial attempts did not prove upload completion. At that earlier checkpoint, no credential had been regenerated, no permissions broadened and no new SSH key registered. The later user-confirmed repository-scope change is recorded below.

The user explicitly confirmed adding **only FYP** and completed GitHub's email verification. The scope edit preserved the two already selected repositories, Contents and Workflows read/write, Metadata read-only, zero account permissions, the token's identity and expiry. GitHub displayed **Your personal access token has been updated**; subsequent CLI access to FYP and HTTPS push succeeded. No token was regenerated or disclosed.

[Remote checkpoint](remote-verification-checkpoint.json): local and remote HEAD `916f6df3e970a3607a082803c2a6963deace91ed`, actual Git tree `b345322464aa71f6b8f73f807d25cf9f5b91471a`, 6,005 files, 586,595,934 committed bytes, non-truncated response, no missing / extra paths or content / mode mismatches. This is a point-in-time checkpoint before adding the final QA helpers and closing records.

The closing commit adds these QA files and updates the current status. After its push, run the same [verification script](verify_remote.py) with output in private `.runtime/github-final-remote-check.json`; this verifies every final committed file, including this report, without creating self-referential commit IDs in the report. `upload-manifest.json` counts all indexed files and checks every source / output category; its per-file hashes exclude this QA directory to avoid self-referential evidence hashes.

Private-repository creation screenshot: [GitHub page](github-repository-created.jpg).

Uploaded repository screenshot: [GitHub files and Private badge](github-repository-uploaded.jpg).
