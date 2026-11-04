# Dorm Pi recovery — 4 November 2026

Status: recovery seed verified and safely ejected; owner confirmed new boot. No matching diagnostic packet or pinned SSH session yet. The saved lease candidate timed out through a socket bound to the physical Mac interface. This is not wired acceptance or app deployment.

## Owner scope

Resume Pi in the dorm; wall-socket Ethernet; official Raspberry Pi27W power. No monitor. Owner selected normal shutdown then attaching the original card to the Mac. Preserve the original OS, data and pairing. No paid-model experiment was reopened.

## Actual reading

- Root `AGENTS.md`, `handoff.md`, `START_HERE_NEXT_CHAT.md`: full current files.
- `product.md`: current route/requirements, branch boundaries, evidence and hardware sections, lines1–60.
- `decision-log.md`: complete relevant sections from31October Pi recovery through2November software routing, lines398–434.
- `work-log.md`: recent Pi/device, routing, school and4November merge sections.
- `desk-companion/docs/pi-network-profiles.md`, `desk-companion/docs/pi5-usb-mac.md`: full files.
- `desk-companion/scripts/pi/prepare_network_sd.py`: full file; re-read missing range125–end after output truncation.
- `setup_network_access.py`, `connect_mac.command`, `connect_lan_mac.command`: network selection/guard/setup and current connection paths; full connector scripts observed earlier in this recovery. Guard exit path235–293 rechecked.
-31October home live-verification JSON and dedicated-device verification; relevant home QA sections.4November merge-route QA fully read.
- `rg --files --hidden -g '*.md'` scoped discovery and nestedAGENTS inventory; only rootAGENTS applies. Large/truncated search results and the device-display spec are not claimed as fully read. No test source read or test execution is claimed from truncated output.

## Initial discovery observations (before owner attached the card)

- Mac has an active campus Wi-Fi/private IPv4 network; listed Ethernet adapters were inactive. Detailed addresses remain private.
- Bounded exact `desk-companion.local` mDNS lookup yielded no address; passive ARP comparison against known Pi MACs yielded no match. No broad campus scan.
- The old classroom Pi Ethernet address is historical; normal route currently uses a VPN tunnel. It was not probed. No global route/proxy/firewall changes.
- Paired SSH host identity remains recorded locally. No authenticated SSH connection to Pi this time.
- Repeated bounded `diskutil list -plist` inspections found no `bootfs`. The SD has not been identified, read or written this time. No assumption that an internal SD reader is non-removable.
- Code inspection: `FYP-Wired` enables DHCP/autoconnect. Ordinary `--guard` only applies access rules; boot status is saved during installation, so an old status cannot prove this boot's IP or failure.
- No evidence yet for current DHCP success/failure, campus isolation, firmware current capability, undervoltage clearance, kiosk or latest app deployment.

Private checkpoint: `~/.config/desk-companion/pi5-dorm-ethernet-20261104/discovery-status.json`. Pairing/identity/credential material remains outside Git. No plaintext secrets copied into this QA.

## Documents and checks

Updated rootAGENTS/product/current entry/handoff/decision-log/work-log and Pi network/Mac-access guides. The old pause is superseded; older successful home checks remain dated history; official27W confirmation is separate from a fresh power test. Existing dirty school and merge records were retained. Documentation diff/link checks are recorded in `checks.json`; no source modification, application test suite, CI, model call or Git publication was needed for this checkpoint.

Next: after the card is attached, match its capacity/boot UUID/root PARTUUID to the private recorded identity and inspect dated nonsecret status before preparing any recovery write.

## Original-card inspection and prepared recovery

Owner attached the card, then ran the local administrator-only read helper. Capacity, boot UUID and root PARTUUID matched the private recorded identity. The FAT network status was the historical home setup. Initial debugfs attempts extracted no files; the second recorded an inode-bitmap checksum failure. A local ext4 fixture verified the listing/stat parsers. A third strictly read-only capture using debugfs `-c` recovered11 selected network files. No persistent system journal was present. All private extracts and tool diagnostics remain outside Git.

The wired profile retains DHCP/autoconnect and has a saved private lease in a different network from the Mac. Its saved timestamp predates this recovery; this is a candidate address, not live acceptance. The installed source guard cannot admit this Mac from that routed network. The read-only e2fsck returned4 with allocation summary/checksum differences and explicitly skipped journal recovery; superblock features include needs_recovery/orphan_present. This does not establish physical card failure or final post-replay integrity. No offline repair or Linux-partition write was performed on the Mac.

Implemented explicit one-owner IPv4/32 access on a live private eth0 link, preserving key-only SSH, original user/host keys, other firewall tables and loopback app/VNC. Default policy still has routed-owner access off. Guard events now persist current address and boot ID, even if diagnostic UDP delivery fails. Added explicit CN/HK country and bounded60–600-second setup discovery; HK recovery does not force the unavailable home Wi-Fi.

Local regression29 passed and Ruff passed. Read scope additionally covers complete network/SD scripts and network tests, and the relevant existing classroom-access helper. Original card was reverified; only user-data/meta-data changed, both exactly read back. Embedded helper matches tested source; the other three boot files retain their prior hashes. Private backups exist. FAT `fsck_msdos -n` via diskutil returned0. Card was safely ejected, owner confirmed reinsertion and power with wired cable. A temporary nonce-filtered observer is active; packets are discovery hints until pinned SSH authenticates.

[Prepared-card facts](card-preparation.json). Live IP, SSH, journal recovery, power, application and desktop remain pending at this checkpoint.
