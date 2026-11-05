# Pi owner relay and recoverable network setup

5 November 2026. Local access stays available; the owner's existing VPS provides an optional management path when direct routes are unavailable. Dorm authenticated access and reboot recovery now pass. Application deployment is separately recorded in the [runtime update QA](../../output/qa/2026-11-05-pi-runtime-upgrade/verification.md); no paid-model feature is activated by this transport.

## Three-place contract and evidence

| Place | Preserved profile and route | Evidence and remaining acceptance |
|---|---|---|
| Mainland home | FYP-Home Wi-Fi, metric50; original credentials and autoconnect retained | Home SSH/app/desktop passed31October. New recovery must retain local access without requiring an overseas VPS. |
| Classroom | FYP-Wired DHCP metric100 plus saved NETGEAR02 Wi-Fi metric600 | Earlier Wi-Fi access passed. Wired end-to-end access and unplug/replug recovery still need a classroom test. |
| Dorm | FYP-Wired DHCP; exact selected Mac /32 may be admitted on eth0; optional fixed443 owner relay |5November original-key SSH, current wired/default route, Mac HTTP/VNC and owner-confirmed restart recovery passed. Sustained power/network stability remains separate. |

Student/Halls credentials remain saved with autoconnect disabled. Region CN/HK is explicit in preparation; current physical location and read-back boot argument are HK. Moving location requires country verification as well as a connection test. The owner has rejected a hotspot workaround for this recovery.

## Optional outbound transport

`setup_owner_relay.py` installs a system service running as desk. It opens an outbound SSH connection to the explicitly selected VPS, verifies its pinned host key, and exposes only a VPS-loopback listener that forwards to Pi-loopback SSH. The original Pi user, host key and owner authentication stay in force. The Mac must verify the Pi host key through the relay before accepting the connection.

The VPS has a dedicated locked-password account, no login shell, a forced failing command and a restricted public key. Only the selected loopback remote-listen port is admitted; arbitrary forwarding destinations, extra listeners, agent/PTY/X11 access and shell execution are not granted. The key is independent of the owner's Mac/Pi management key. [OpenSSH key restrictions](https://man.openbsd.org/sshd#AUTHORIZED_KEYS_FILE_FORMAT).

The optional `--relay-bundle` is an owner-private JSON file naming the server IP/port, dedicated username, loopback relay port, pinned Ed25519 host public key and private local key-file path. Source contains no live credentials. The generated card seed is private, just like the existing Wi-Fi seed; never commit it or its backups. The service reconnects after network loss; that behavior is not proof that a particular campus or mainland path permits the connection.

## Fixed 443 transport when direct SSH is unavailable

The later durable boot reported installation completion but no direct VPS22 connectivity. An isolated Mac client forced to en0 successfully authenticated the pinned VPS through the existing port443 transport. That is the tested alternative, not a claim that Pi's direct22 path works.

`setup_relay_transport.py` optionally installs a pinned, unmodified Linux ARM64 mihomo binary. Its sole listener is loopback22422 and its sole target is the owner's VPS SSH endpoint through the already selected encrypted node. Generic proxy ports, control APIs, TUN, DNS changes and arbitrary destinations are rejected. Pi uses its normal default route, preserving home Wi-Fi and school Ethernet/Wi-Fi selection; no Mac interface name is carried over.

The runtime service runs as desk with a private writable state directory. The existing SSH service keeps strict host-key verification and its dedicated key, and connects through this loopback transport. An SSH banner is recorded only as transport evidence; authenticated Pi SSH still requires the original Pi key check.

The optional protected bundle also supplies a transport configuration and pinned binary manifest. Preparation writes one checksum-verified offline archive alongside the two seed files, with backup/readback/rollback. On5November it was applied to the original card, independently read back, FAT-checked and safely ejected; actual Pi original-key authentication and a later reboot passed. The Mac does not write the Linux partition. Source/credentials/binary distribution are separate: source and hashes are publishable, live node credentials and prepared seeds remain private. [Official dependency release](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.32), [fixed-target transport contract](https://wiki.metacubex.one/en/config/tunnels/).

## Owner-side access and stale connections

[`owner_relay_client.py`](../scripts/pi/owner_relay_client.py) reads an owner-private JSON configuration with version1, public VPS host/port, existing administrator user, pinned host alias/known-hosts path and loopback remote port. It rejects nonpublic targets, malformed ports/users, symlinks, permissive files and OpenSSH token expansion in paths. Shell quoting is tested with literal command-substitution characters. The inner Pi session independently uses the original private key and strict Pi host pin.

[`connect_mac_relay.command`](../scripts/pi/connect_mac_relay.command) reuses the common Mac connector. Generic proxy/system networking remains untouched. The common connector checks actual forwarded app/VNC readiness, retries relay loss every10seconds, opens interfaces only once, and cleans up its own child on termination. LAN/USB modes retain their direct-route checks. Actual retry after the Pi restart and SIGTERM release of both local listeners passed.

A later unresponsive VPS session retained the remote listener. Its previous server liveness was300seconds/count2. Added an EOF `Match User fyp-pi-relay` block with `ClientAliveInterval 20` and `ClientAliveCountMax 3`, after backing up sshd_config, validating syntax and comparing root's full effective configuration unchanged. Only the verified stale dedicated session was terminated. An isolated forced-en0 authentication test still passed. The owner then restarted Pi normally and original-key access returned. This bounds stale-session cleanup; it does not diagnose the cause of the original interruption or prove an uninterrupted campus connection. [OpenSSH client liveness](https://man.openbsd.org/sshd_config#ClientAliveInterval).

## Interrupted setup recovery

The SD read-only view showed empty relay files while cloud-init recorded its write step as already run. The filesystem still required journal recovery, so this view alone is not a physical-card diagnosis. The missing relay receipt and empty-script zero-exit behavior exposed a real validation gap.

`network_bootstrap.py` is embedded as nonsecret code in bootcmd and runcmd. It reads credential payloads from the mounted seed, checks the paired device, validates an exact managed-file allowlist, restores missing/truncated files with atomic writes, file/directory synchronization and independent byte readback, and then executes the existing installers. Credentials never enter command arguments.

If this seed has not completed, its boot hook resets only its own command-generation and user-script completion records. It does not reset user creation, SSH keys, package installation, vendor provisioning or other instances. The run hook requires successful setup commands and current-trial result receipts before writing a durable completion record. A completed seed leaves subsequent legitimate software updates alone. [Cloud-init bootcmd/runcmd module behavior](https://docs.cloud-init.io/en/latest/reference/modules.html#bootcmd).

Setup completion, an active service, a TCP connection, a relay banner, authenticated Pi SSH and usable application/desktop are distinct results. Read the specific result; do not equate them.

## Diagnostics and rollback

The boot partition receives network, owner-relay and bootstrap JSON status. A bounded HTTP request may also leave a random trial ID and predefined stage in the owner's existing HTTP access log. This is an unauthenticated diagnostic hint, carries no credentials, device addresses or response commands, and never replaces SSH verification. The request does not follow redirects and cannot block local status recording when the endpoint fails. VPS logging is conditional on this exact diagnostic path; ordinary paths, query strings and subscription traffic remain unlogged.

Private operational evidence, card backups and keys are under the owner's `~/.config/desk-companion/pi5-dorm-ethernet-20261104/`. The VPS retains private backups of the original HTTP and pre-liveness SSH configurations. Proxy/firewall/subscription routes and other users' effective SSH settings remain unchanged; the dedicated account/key, its liveness block and scoped diagnostic logging are recorded separately.

To roll back the relay, first establish another management path, then disable desk-owner-relay.service and revoke only its dedicated VPS key/account. Restoring the original HTTP configuration and removing the diagnostic-only logging include requires nginx -t before reload. Local network profiles and the original Pi management key remain intact. Do not remove a live sole transport without an alternate path.

## Validation boundary

92 focused local checks, Ruff and shell syntax passed, including three-site rules, interrupted writes, empty-file restoration, scoped cloud-init retry, false-success receipts, symlink/credential boundaries and owner-client argument safety. A real Mac-to-VPS fixture verified allowed/rejected forwarding and commands. Conditional log privacy passed positive/ordinary/query-string probes. Actual dorm Pi original-key authentication, current routes, transport restart, owner reboot and Mac app/VNC checks are now separately recorded. Classroom/mainland field acceptance and sustained power remain open.

[Current transport QA](../../output/qa/2026-11-05-pi-443-transport/verification.md), [earlier recovery QA](../../output/qa/2026-11-04-pi-dorm-ethernet/verification.md).
