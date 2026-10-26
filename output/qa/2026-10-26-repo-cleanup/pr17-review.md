# PR #17 hardware review — 26 October 2026

Reviewed original head `8141d374e6e3d476d874310a7fed158a51fc28df`, authored by xuz204077-prog. The repository owner requested review, repairs and merging; the original upload's no-merge scope is historical. No hardware operation or deployment is performed.

## Findings repaired

- School-loan Pi 5 information did not establish RAM, and must not override the owner's separately confirmed Pi 5 8GB test board. Whether these describe the same board remains unknown; Pi connectivity work stays paused.
- Hardware-member discussion targets are labelled as such. A merged research package does not approve all procurement, establish a final BOM or prove robot performance.
- [Pololu 5113](https://www.pololu.com/product/5113) specifies a 9 mm output shaft. The JSON now uses that length; the package README carries an explicit page 3 erratum while preserving the original PDF. The motor pin table and separate encoder supply were checked; 12 CPR refers to the motor shaft, rather than the gearbox output.
- [Cytron's Singapore page](https://sg.cytron.io/p-robo-esp32) displayed S$21.29 during this review. Its URL cannot substantiate a US-dollar current quote; the JSON dates the new observation and retains US$16.40 only as historical. This is still not a complete delivered-price quotation.
- Integration requirements now bind device identity, command content/version/expiry, duplicate handling, local watchdog and stop precedence; receipt, physical completion and unknown result remain distinct. These are requirements, not implemented firmware.

## Validation

All nine PDF pages were rendered and inspected, and extracted text was read to EOF. Original PDF SHA-256 remains `4b225e9baa76c0b130891ba5f90557a0f5425ccf6185b9ff5f16f4a985d45182`. [Independent checks](pr17-validation.json) validate the 13 images / 30 links, 13 source records / 22 checklist rows, source-package hashes and US$76.89 walking subtotal, plus relative document links. [Reading record](reading-record.json) covers all repository Markdown and PR variants; full-text snapshots were used locally and are not included in this commit.

[Pololu 5543](https://www.pololu.com/product/5543) confirms the 1 mm six-pin, 28 AWG, double-ended cable and the different standard/encoder wire colours; a finished controller adapter is still missing. [Seeed's Line Finder wiki](https://wiki.seeedstudio.com/Grove-Line_Finder/) specifies 5 V, so the existing hold on unverified 3.3 V direct connection is retained. No component package is declared electrically or mechanically accepted.

Application source is unchanged, so software and hardware execution tests are not claimed for this documentation PR. GitHub reports no checks or statuses on the original head; absence of CI is not a passing CI result. The staged patch receives whitespace and Gitleaks checks before commit; actual commit and merge receipts are recorded in the repository-cleanup closeout.
