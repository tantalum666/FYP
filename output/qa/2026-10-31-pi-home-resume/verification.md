# Group 2 · Pi home-network resumption

31 October 2026. The owner explicitly resumed Pi work after returning home, supplied the home Wi-Fi privately, and added wired Ethernet for classroom/dorm use. [Network contract](../../../desk-companion/docs/pi-network-profiles.md).

Read the actual [referenced VPS chat](thread://019decde-5067-7000-bdea-e91f5d4d9ea4?hostId=local), recent maintenance notes and Pi handoff. Existing VPS/Clash connectivity was not treated as current Pi connectivity or permission to change unrelated Mac networking. No VPS or system-proxy setting was changed.

## Verified preparation

- Mac is on a new home private subnet; old classroom/Halls management assumptions cannot be reused. Initial bounded mDNS/known-neighbor checks did not establish Pi access.
- User returned the original card after shutdown. Capacity127999672320, removable SD identity, boot UUID/root PARTUUID and the recorded public SSH host fingerprint match the earlier paired Pi. Internal=true is the built-in SD reader, not the Mac system disk.
- New home and wired DHCP profiles; known classroom Wi-Fi preserved, Student/Halls autoconnect stopped. Owner-key SSH follows admitted connected LANs; app/VNC remain loopback.
-25local checks pass, including untrusted/down/broad/public network rejection, seed rollback on second-file failure, key/user preservation, profile privacy, classroom/dorm policy and wired/no-carrier boot flows. Ruff passes. These are local checks, not school Ethernet acceptance.
- Existing five boot files backed up privately. Only user-data/meta-data changed; exact readback, YAML parsing and credential equality were checked without printing the credential. Other boot files and the Linux partition were not written by Mac.
- diskutil verifyVolume ran fsck_msdos -n and returned0; the original card was safely ejected. This is a FAT check, not an ext4/whole-card health certificate.

[Card readback](card-verification.json), [checks](pi-checks.txt), [scope/read record](reading-record.json), [current state](progress.json). Private credential-bearing seeds/backups remain outside Git.

## Live gate

A bounded nonce-filtered UDP receiver was started on the Mac before requesting that the owner reinsert the card and power the Pi. Home Wi-Fi, pinned-key SSH, actual application/desktop access and any VPS need still require independent live verification. Writing the card is not connection/deployment success. No current-main application upgrade or paid model call has occurred.
