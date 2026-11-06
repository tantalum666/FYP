# Fixed 443 management transport — 5 November 2026

Continues the [4November recovery](../2026-11-04-pi-dorm-ethernet/verification.md). **Current result:** real dorm Pi authentication, wired/default-route readback, transport restart recovery and owner-confirmed power-cycle recovery passed through443. Mac app/VNC access and retry/cancellation passed;92 local checks pass. Earlier diagnosis/preparation below is chronological evidence. The first durable seed reported setup_completed but direct VPS22 failure; it preceded the actual443 acceptance.

## Diagnosis and actual independent test

Mac administrative SSH reaches the VPS through its existing encrypted transport; the VPS observed its own address as that connection's peer. A plain Pi-to-VPS22 request was therefore not equivalent to the earlier Mac/VPS fixture. The server's SSH firewall allowance and dedicated-account restrictions were inspected. No firewall, original SSH or existing proxy configuration was changed. The Mac's apparent en4/en5/en6 adapters are Apple USB NCM controllers, not evidence of an available RJ45 adapter; no new cable/hotspot trial was requested.

Created a separate temporary client using the owner's existing VPS node, with TUN/DNS/general proxy/control ports disabled and only a loopback TCP forward to that VPS's SSH endpoint. Forced outbound en0 in both client and node. A real SSH connection through it verified the pinned VPS key and authenticated the dedicated key; shell execution was still denied. The temporary client was stopped, and existing Mac proxy configuration was retained. This test verifies the isolated Mac path; Linux/Pi execution remains separate.

The unmodified official mihomo v1.19.32 Linux ARM64 archive was downloaded and matched GitHub's published SHA256. The decompressed ELF is AArch64 and static, with bounded size and independent hash. [Artifact metadata](artifact.json), [official release](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.32), [fixed-target tunnel documentation](https://wiki.metacubex.one/en/config/tunnels/). Binaries and live proxy/SSH credentials remain outside Git.

## Implementation and tests

An optional transport installer validates a strict fixed-target configuration, checks archive/binary hashes and architecture, atomically publishes the binary, creates desk-owned runtime state, validates configuration as desk and installs a nonroot service. No TUN, DNS changes, generic proxy or external controller is enabled. The existing SSH relay retains its host-key pin and dedicated key; only its dial endpoint changes to the fixed loopback transport. Original Pi authentication, app data, home/classroom/dorm profiles remain unchanged.

Bootstrap order is network → fixed transport → SSH relay, with current-trial receipts for every component. Preparation stages a checksum-verified offline archive in addition to user-data/meta-data, with original-asset backup and rollback if a later seed write fails. No original Linux partition is written by the Mac. The one-time completion/recovery behavior remains.

79 focused local checks and Ruff passed, covering forbidden TUN/DNS/general listeners/destinations, bad artifacts, wrong architecture, previous binary retention, exact setup order, archive rollback, least-privilege runtime and banner-vs-authentication distinctions. A private full-package rehearsal used the actual verified artifact and protected configuration, then parsed the generated bootstrap plan; ten managed entries and three setup steps were correct. This was a local staging directory, not the real card. [Checks](checks.json).

Read scope: the existing current handoff/network/relay contracts and related actual logs are continued, not re-read wholesale; complete changed functions/modules in prepare_network_sd, setup_owner_relay, network_bootstrap and setup_relay_transport, and their focused tests. Official tunnel/interface and release references were consulted. No paid-model call, CI, app migration or unrelated UI change.

The initial publication checkpoint below preceded real-card preparation; the current result is recorded afterward. No hotspot workaround or classroom wired acceptance is claimed.

Historical publication checkpoint: source7bbeae2a was pushed to draftPR87 with the79-test/fixed443 description. At that point the real card still needed the package and authenticated Pi access was pending. Subsequent preparation and live results follow; no three-place field acceptance is claimed.

## Original-card deployment and owner-confirmed boot

The owner returned the original card on5November. Capacity, removable-media identity, boot-volume UUID and root PARTUUID matched the saved device. Its bootstrap/network/relay receipts all matched the previous durable trial: setup_completed, wired network_ready and direct VPS TimeoutError. These are card records, not a successful SSH session.

Applied the already-tested443 package to the real card with private backups. Only user-data, meta-data and the checksum-verified offline archive changed. Independent readback verified all three exact files, ten managed payloads, three commands in order, exact current bootstrap source and Python3.13 syntax. Original Pi host fingerprint and user/key preservation were checked. Home/wired profile bytes match the previous seed; the classroom profile was not targeted. Three unrelated boot files remained byte-identical. The Mac's DHCP address had changed, so its exact selected /32 was refreshed after reading the current interface, without changing Mac networking.

FAT read-only verification returned0; post-remount exact readback and whole-device ejection passed. The VPS log filter was updated to this exact trial after nginx validation/reload. Owner confirmed boot; transport banner, relay service and setup completion followed. Original-key Pi SSH then passed. [Card checks](card-deployment.json).

Continuation read scope: AGENTS/current entry/handoff; product current requirements/hardware route; decision-log31October and4–5November Pi sections; owner-relay/network-profile contracts and this QA; Pi Mac guide current sections; prepare_network_sd plus the bootstrap/transport/relay functions used for readback. At that preparation stage there was no Mac write to the Linux partition, paid-model call, CI or app deployment. A separate authenticated runtime rollout followed, recorded below.

## Real Pi and Mac acceptance

Authenticated the original host through the relay; read back active FYP-Wired/default route, enabled nonroot transport/relay, correct binary digest and current network boot ID. App health returned200 and Mac-side8891/5901 independently returned application health/RFB. Restarted the transport using a transient unit; both transport/relay PIDs changed, original-key SSH recovered and the Pi boot stayed unchanged. This is software transport recovery, not cable-unplug or long-term field acceptance.

A later interruption left a nonresponsive VPS listener. Backed up sshd_config, appended ClientAliveInterval20/CountMax3 only for the dedicated relay account, passed sshd -t and confirmed root's complete effective configuration unchanged. Stopped only the verified stale account session. Forced-en0 isolated VPS authentication/denied shell retest passed. Owner then performed normal button restart without card removal; authenticated a different Pi boot ID and verified the deployed new app/schema. The cause of the original interruption is not established.

Added a private-config owner route and reused the common Mac connector for relay access.13 new input/symlink/permission/OpenSSH-token/shell-literal checks join the existing79:92 passed. Shell syntax/Ruff passed. The actual retry loop recovered after Pi restart; SIGTERM stopped the owned launcher and released both local ports. A final launcher was started, keeping ordinary owner access available. [Live results](live-acceptance.json).

The [actual runtime update](../2026-11-05-pi-runtime-upgrade/verification.md) preserved original data and validated post-reboot HTTP owner login/core APIs, exact frontend and rendered device-panel interaction. Latest boot also has real undervoltage records; no sustained hardware/voice/GUI-load claim. Classroom wired/mainland visits remain separate. Updated root routes, network/Mac/relay docs, decision/work log and both QA routes. No CI, model test or change to global Mac proxy/DNS/TUN.
