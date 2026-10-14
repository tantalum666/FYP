# REA setup for Group 2

Date: 14 October 2026. This is a teammate and coding-agent setup note for the public fork [tantalum666/rea](https://github.com/tantalum666/rea) (REA v4.0.0, MIT). The binary is not vendored into FYP. Do not commit API keys, `.env` files, REA reports, or sample binaries.

Verified clone: commit `44310d8478e3e4a819636e2b262a0175d29c62f4` (`44310d8`, tag message “Release v4.0.0”). Built and run on Linux x86_64 in a scratch directory outside this repository. The verification commands and results are in the last section.

## What REA is, and what it is not

REA is a local static-analysis tool. `rea <file>` writes a Markdown report, a PDF, and a JSON summary beside the target. `rea serve` exposes the same engine as a stdio MCP server (18 tools). With no `OPENROUTER_API_KEY`, it stays offline and does not call a model.

Use it on binaries this team compiles or otherwise has the right to inspect: a small helper the team wrote, or firmware the team built from its own source for a desk device. Do not point it at third-party commercial applications. Client apps for Muse, ChatGPT, WhatsApp, or similar products are out of scope. A client binary would not reveal those products’ server-side models, prompts, or memory anyway; that limit is explained in [companion-architecture.md](companion-architecture.md).

## Build on Linux

The README’s Linux x64 commands are:

```bash
git clone https://github.com/tantalum666/rea.git
cd rea
rustup target add x86_64-unknown-linux-gnu
cargo build --release -p rea --target x86_64-unknown-linux-gnu
```

The binary is then:

```text
target/x86_64-unknown-linux-gnu/release/rea
```

Optional install onto `PATH`:

```bash
cargo install --path crates/rea
```

This machine’s default toolchain was Rust 1.83.0. Release dependencies require Cargo’s `edition2024` feature, so 1.83 failed while parsing `block-buffer`. The successful build used rustup stable **1.99.0** (`rustc 1.99.0 (b940084d7 2026-09-28)`):

```bash
rustup toolchain install stable --profile minimal
rustup run stable cargo build --release -p rea --target x86_64-unknown-linux-gnu
```

Host and target were both `x86_64-unknown-linux-gnu`. The README’s `--target` flag was kept. Fat LTO makes the release build slow; that is normal. Do not copy `target/` into FYP.

Upstream’s README clone URL is `mytechnotalent/rea`. This note follows the owner’s fork, which is the v4.0.0 tree above. Re-clone that fork if the commit moves, and re-run `--help` before trusting flags.

## One-shot and offline mode

```bash
rea --help
rea -V
rea /absolute/path/to/your-own-binary
```

Reports are written next to the target as `re-<name>.md`, `re-<name>.pdf`, and `re-<name>.json`. Keep them out of git. They can contain strings from the binary.

An OpenRouter key turns on an optional analyst loop. The project does not need that for a deterministic report. If someone uses a key, put it only in an untracked shell environment or a gitignored `.env`. Do not commit it, and do not send FYP credentials, calendar data, or voice audio to that service.

## MCP for teammates and coding agents

The server speaks JSON-RPC over stdin/stdout. It is not a network port.

```bash
rea serve
rea mcp --config
rea mcp --setup
```

`rea mcp --config` prints snippets for Claude Code, Claude Desktop, OpenCode, Cursor, and Windsurf. `rea mcp --setup` writes `./mcp_config.json` and `./opencode.jsonc` in the current directory and prints `claude mcp add rea rea serve`. Do not commit those generated files into FYP.

The Cursor snippet the binary prints is:

```json
{
  "mcpServers": {
    "rea": {
      "command": "rea",
      "args": ["serve"]
    }
  }
}
```

Put that in the user MCP config (`~/.cursor/mcp.json` in the printed hint), with `command` set to the absolute path of the built `rea` if it is not on `PATH`.

Codex is not in the printed list. Use the same stdio server. In `~/.codex/config.toml`:

```toml
[mcp_servers.rea]
command = "/absolute/path/to/rea"
args = ["serve"]
```

If a Codex build rejects that heading, use that installation’s MCP docs and keep the command as `rea serve`. Do not expose the server on the network, and do not add a key to this file.

After the agent connects, a legitimate request looks like: open a binary the team just compiled, list functions, decompile one function, and explain the report. Refuse requests that name a commercial desktop or phone application.

The 18 tool names, from the v4.0.0 server, are: `open_binary`, `binary_session`, `list_functions`, `decompile_function`, `find_xrefs`, `search_strings`, `analyze_firmware`, `analyze_javascript`, `generate_dossier`, `inspect_go`, `inspect_dotnet`, `inspect_android`, `run_rules`, `audit`, `inspect_crypto`, `decrypt_strings`, `emulate`, `unpack`.

## Legitimate use on this project

Desk Companion’s assistant does not need REA to call a model. The hosted-API design is in [companion-architecture.md](companion-architecture.md). REA is for the team’s own machine code:

- A native helper or test fixture the team compiles, to learn the report format.
- Firmware the team builds for its own controller (for example a later RIG or cleaner image built from source the team is allowed to read). Confirm the image is the team’s build before opening it. A vendor blob the team did not build is not automatically in scope.
- Checking that a small team-built ELF has the expected architecture, imports, and strings before it is flashed.

The current app talks to hardware through named presets and a simulator or PCA9685 driver. There is no team-built RIG firmware in this repository, and upstream RIG sources are intentionally not vendored. REA does not change that.

## Linux verification on 14 October 2026

Scratch clone: `/tmp/scratch/rea` at `44310d8`. This record is the result of that build; re-run the commands on a new machine instead of copying the binary here.

Toolchain: rustup stable 1.99.0. Command:

```bash
rustup run stable cargo build --release -p rea --target x86_64-unknown-linux-gnu
```

Binary: `target/x86_64-unknown-linux-gnu/release/rea`.

`rea --help` and `rea -V` exited 0. `--version` printed `rea 4.0.0`. `--help` lists `rea <file>`, `rea serve`, `rea mcp --config`, and `rea mcp --setup`.

`rea mcp --config` exited 0 and printed the Claude Code, Claude Desktop, OpenCode, Cursor, and Windsurf snippets. It did not print a Codex block.

One-shot target: a C program compiled in the scratch directory, not a third-party application.

```c
#include <stdio.h>
int main(void) {
    puts("desk-companion-own-sample");
    return 0;
}
```

`gcc -O2 -o own-sample own-sample.c`, then `rea` on that ELF. It wrote `re-own-sample.md`, `re-own-sample.pdf`, and `re-own-sample.json` beside the binary and exited 0. The JSON `format` is `Executable and Linkable Format (ELF)`, `architecture` is `X86_64`, and `imports` includes `puts`. The Markdown report, not the JSON summary, quotes the string `desk-companion-own-sample`. No OpenRouter key was set. Those outputs stayed in the scratch directory.
