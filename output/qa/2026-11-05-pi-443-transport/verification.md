# Fixed 443 management transport — 5 November 2026

Continues the [4November recovery](../2026-11-04-pi-dorm-ethernet/verification.md). The owner confirmed the durable seed boot. Its matching stage hints reached file restoration, network setup, relay setup and setup_completed, but relay_tcp_unreachable was reported. This confirms reported progress, not authenticated Pi access; the strict Pi session still has not been established.

## Diagnosis and actual independent test

Mac administrative SSH reaches the VPS through its existing encrypted transport; the VPS observed its own address as that connection's peer. A plain Pi-to-VPS22 request was therefore not equivalent to the earlier Mac/VPS fixture. The server's SSH firewall allowance and dedicated-account restrictions were inspected. No firewall, original SSH or existing proxy configuration was changed. The Mac's apparent en4/en5/en6 adapters are Apple USB NCM controllers, not evidence of an available RJ45 adapter; no new cable/hotspot trial was requested.

Created a separate temporary client using the owner's existing VPS node, with TUN/DNS/general proxy/control ports disabled and only a loopback TCP forward to that VPS's SSH endpoint. Forced outbound en0 in both client and node. A real SSH connection through it verified the pinned VPS key and authenticated the dedicated key; shell execution was still denied. The temporary client was stopped, and existing Mac proxy configuration was retained. This test verifies the isolated Mac path; Linux/Pi execution remains separate.

The unmodified official mihomo v1.19.32 Linux ARM64 archive was downloaded and matched GitHub's published SHA256. The decompressed ELF is AArch64 and static, with bounded size and independent hash. [Artifact metadata](artifact.json), [official release](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.32), [fixed-target tunnel documentation](https://wiki.metacubex.one/en/config/tunnels/). Binaries and live proxy/SSH credentials remain outside Git.

## Implementation and tests

An optional transport installer validates a strict fixed-target configuration, checks archive/binary hashes and architecture, atomically publishes the binary, creates desk-owned runtime state, validates configuration as desk and installs a nonroot service. No TUN, DNS changes, generic proxy or external controller is enabled. The existing SSH relay retains its host-key pin and dedicated key; only its dial endpoint changes to the fixed loopback transport. Original Pi authentication, app data, home/classroom/dorm profiles remain unchanged.

Bootstrap order is network → fixed transport → SSH relay, with current-trial receipts for every component. Preparation stages a checksum-verified offline archive in addition to user-data/meta-data, with original-asset backup and rollback if a later seed write fails. No original Linux partition is written by the Mac. The one-time completion/recovery behavior remains.

79 focused local checks and Ruff passed, covering forbidden TUN/DNS/general listeners/destinations, bad artifacts, wrong architecture, previous binary retention, exact setup order, archive rollback, least-privilege runtime and banner-vs-authentication distinctions. A private full-package rehearsal used the actual verified artifact and protected configuration, then parsed the generated bootstrap plan; ten managed entries and three setup steps were correct. This was a local staging directory, not the real card. [Checks](checks.json).

Read scope: the existing current handoff/network/relay contracts and related actual logs are continued, not re-read wholesale; complete changed functions/modules in prepare_network_sd, setup_owner_relay, network_bootstrap and setup_relay_transport, and their focused tests. Official tunnel/interface and release references were consulted. No paid-model call, CI, app migration or unrelated UI change.

Current next step: owner returns the original card for the prepared 443 package. No hotspot workaround and no claim of Pi connectivity or classroom wired acceptance.
