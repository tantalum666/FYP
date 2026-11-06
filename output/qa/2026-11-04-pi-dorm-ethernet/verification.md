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

Local regression29 passed and Ruff passed. Read scope additionally covers complete network/SD scripts and network tests, and the relevant existing classroom-access helper. Original card was reverified; only user-data/meta-data changed, both exactly read back. Embedded helper matches tested source; the other three boot files retain their prior hashes. Private backups exist. FAT `fsck_msdos -n` via diskutil returned0. Card was safely ejected, owner confirmed reinsertion and power with wired cable. A temporary nonce-filtered observer was run; packets are discovery hints until pinned SSH authenticates.

[Prepared-card facts](card-preparation.json). Live IP, SSH, journal recovery, power, application and desktop remain pending at this checkpoint.

## Publication and current reachability

Published code commit7c6790da292b4d442fa13847ccc466e8e3a52633 in [draftPR87](https://github.com/tantalum666/FYP/pull/87), stacked on the unchanged PR73 branch3150f391. PR metadata confirmed the published code head. This is not a merge or application deployment. Staged contents and private-secret scan passed; staged document links resolve. Unrelated local school/merge notes remain outside this commit.

After owner-confirmed power-on, no matching fresh diagnostic packet was recorded. A single pinned SSH attempt to the saved lease candidate, bound to physical en0, failed; a bounded TCP-only check also timed out. No hostname identity was accepted or replaced. The owner was asked to report power/activity and Ethernet LEDs.

Read the referenced VPS chat through read_thread. Current VPS management authenticated using its existing pinned identity through the Mac's existing route. Direct campus-interface SSH timed out; HTTPS TCP connected but TLS timed out. These are Mac-path observations, not proof of Pi outbound capability or campus isolation. No VPS, proxy, global route or firewall change was made. Next: owner LED/boot-state confirmation, then obtain fresh boot status if the device remains unreachable.

Closeout: the temporary observer was stopped after recording no matching packet. PR87 remains open/draft; remote receipt head77477728ce895d6b3c195ae4d11ad84a1849346f was read back. Owner LED observation remains pending; no Pi session or VPS relay is running from this task.

### LED confirmation and bounded recheck

Owner reports power/activity lit and Ethernet lit/blinking. Mac remains on the same selected IPv4. An exact-host mDNS query and one physical-interface-bound, strict-host-key SSH retry to the saved lease candidate again yielded no usable address/authentication. The mDNS process was stopped. No source/configuration/device write, network setting change or new test-suite run. Asked owner to shut down normally and return the original card for the new boot’s FAT status; if red standby is not reached, do not remove the card. Current state remains pending physical input.

## Fresh boot evidence, optional relay and incomplete-install recovery

Owner returned the card after the first new boot. Identity and trial matched; network_ready, new boot ID, wired DHCP and the exact Mac /32 plus wired /22 source entries were read back. The boot country argument was HK. This verifies configuration execution and DHCP, not Mac-to-Pi reachability.

Added an optional pinned reverse SSH service and dedicated VPS key/account. A real Mac fixture verified loopback-only forwarding and denial of other listeners, arbitrary destinations and shell. The first live Pi relay attempt produced no banner in600seconds. Owner rejected a hotspot workaround and asked for a consolidated recovery. Server firewall inspection showed normal SSH allowed and no global allowlist; no firewall rule was changed.

An additional read-only card capture collected current cloud-init state/log excerpts, complete current runcmd, unit presence and permission metadata. It showed zero-byte relay script/config/key/known-hosts, no relay unit/status, current runcmd referencing the relay, and cloud-init write_files marked already run. The read-only ext4 view skipped pending journal recovery; do not call this proof of physical card failure. Empty Python returning0 was reproduced locally, demonstrating why the earlier checks could miss an incomplete installation.

Implemented a single verified bootstrap source used by bootcmd/runcmd: exact path allowlist, nonempty expected payload, paired host identity, atomic durable restoration/readback, reset only this instance's runcmd/scripts-user records while incomplete, actual installer return/result validation and completion only after success. Completed seeds do not overwrite later legitimate updates. No global cloud-init clean, OS reinstall or key regeneration. Actual Pi logs confirm bootcmd exists in its module list; deployed helper syntax was checked against Python3.13.

62 local checks and Ruff passed. Optional progress hints send only random trial ID and predefined stage to the owner's existing HTTP service; the server records only those paths. Positive and negative privacy probes passed. Existing HTTP responses/routes, subscription logging, Xray and normal SSH settings remain unchanged. The dedicated account and diagnostic-only Nginx include/server logging line are the actual VPS changes; private original configuration backup retained. Hints are unauthenticated and cannot establish Pi identity.

The new durable seed changes only backed-up user-data/meta-data, independently reads them back and preserves the other three boot files. Eight payloads and both inline execution stages are checked against tested source; the paired host fingerprint is required for this prepared card. [Verification facts](durable-recovery.json). Pi live result is still pending; home/classroom local paths are retained and classroom wired acceptance remains open.

### Consolidated package publication and physical handoff

Reviewed sourcefe9725720b24f7cfbe03fb2cc2a6b7f26b03719d was pushed and read back on PR87. The connector temporarily failed and the CLI token could not edit PR metadata; the owner's authenticated browser updated title/body, then the CLI read back the62-test description. PR remains open/draft. Browser proof is private and was shown to the owner; no private capture/credential was published.

The durable seed passed exact readback and FAT readonly0 and was safely ejected. A900-second observer finished without a stage or SSH banner while the latest reinsertion/power confirmation remained pending. One final pinned relay probe did not authenticate. This is not evidence of a failed boot of the new durable seed: the owner has not confirmed that physical step. No observer remains running. Resume by observing this prepared seed after the owner's new power-on confirmation; do not rewrite the card or ask for a hotspot by default.
