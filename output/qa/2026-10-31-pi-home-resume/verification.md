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

## Live home acceptance

After the owner confirmed that the card was back in the Pi and power was on, mDNS found the device. Its lease changed during profile activation; a direct Mac-LAN route and the original pinned SSH host key were independently verified before using the connection. The initial bounded UDP observer received no matching packet; that did not establish a failed boot. Temporary discovery observers have ended.

| Check | Actual result |
|---|---|
| Device / host identity | Raspberry Pi 5 Model B Rev1.0; existing paired SSH identity matches |
| Home connection | `FYP-Home` connected; supplied SSID equality checked privately; activation exit0 |
| Boot network status | `network_ready`; original classroom Wi-Fi retained |
| Profiles / preference | Home50, wired100, classroom600; autoconnect on; Student/Halls off |
| Key-only SSH / firewall | Actual sshd policy and project-owned active-private-LAN rule read back |
| App / desktop | Both user services active; API health `ok`; listeners127.0.0.1:8831 and127.0.0.1:5900 |
| Mac web | Existing owner login passed; device page and Alice rendered; no browser error/warning captured |
| Mac desktop | Existing WayVNC credentials accepted through SSH; actual Pi desktop visible |
| Pi-local web | Chromium rendered device page after cancelling a new-keyring prompt; calendar stayed locked; no new credentials created |
| Time / basic HTTPS | NTP synced; example.com HTTP200 and valid TLS; raspberrypi.com HTTP403 with valid TLS |
| Ethernet | `eth0` unavailable/no cable at last observation; not tested |

The last low-load check at04:46:40+08:00 again confirmed pinned SSH, home Wi-Fi, both services and API health. It is a spot check, not continuous monitoring. Basic HTTPS evidence does not establish unrestricted Internet or AI-provider reachability. No VPS was needed for this local home connection.

Selected machine-readable evidence is in [live verification](live-verification.json). Actual GUI captures and full selected diagnostics remain in the private local `~/.config/desk-companion/pi5-home/` directory, with owner-only permissions. Published evidence includes capture hashes, not screenshots, credentials, raw profiles or private user data.

## Power and OS findings still open

Before Pi-local browser load, the temperature was47.7°C and `get_throttled=0x0`. Starting Chromium produced the visible low-voltage warning and kernel entries at04:29:57 (undervoltage) and04:29:59 (normalized). The browser window was closed through the remote desktop; this was verified visually. One Chromium-named process remained in the subsequent count, so this is not a claim that every background process exited.

The later `0x50000` value has historical undervoltage and throttling bits, with no active low-voltage/throttling flags. A subsequent one-off rail reading was5.04242V and SoC63.1°C. These do not erase the load-time failure. Boot-reported `max_current=3000`mA and `usb_max_current_enable=0` describe firmware capability/settings, not measured current draw or proof of the physical supply. The owner was asked which PSU/cable is connected; no answer yet. Further load tests and app/database upgrades wait for that check. No warning suppression, USB-current override, forced reboot or reflash was used. Bit meanings and power interpretation follow the [official utility documentation](https://www.raspberrypi.com/documentation/computers/os.html#get_throttled) and [power guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply).

`cloud-init` exited2, `degraded done`, with errors=[] and one recoverable missing-module warning for `cc_netplan_nm_patch`. The installed cloud.cfg references the module, but it is absent. The [official Trixie tracker](https://github.com/raspberrypi/trixie-feedback/issues/45) records the same symptom; it is corroborating OS evidence, not a reason to claim the warning was fixed. Vendor cloud-init configuration was not edited and provisioning was not rerun.

The country setter returned1, but global regulatory domain CN and persisted `cfg80211.ieee80211_regdom=CN` were read back. The installed setter also contains desktop-notification commands; their involvement is a hypothesis, not a proven exit-code cause. The Mac left cmdline.txt unchanged; the authorized Pi-side country command subsequently changed it. Check/set HK when physically back in Hong Kong.

## Remaining gates

1. Confirm supply/cable and correct it if needed, then a bounded repeat of the failed browser/load scenario.
2. Optional home-router cable test, followed by actual classroom/dorm wired DHCP and Mac reachability checks. No cable/reply has been observed yet.
3. After stable power, stop services and preserve a coherent backup before any latest-main app/database migration. The Pi still runs the Oct22 app plus Oct26 repairs; this is not the current-main Alice/Omni/Work deployment.

No paid model request, microphone/camera capture or arm movement occurred. No VPS/Mac proxy setting, existing user credential or app database was changed during live verification. The current web/desktop SSH tunnel is intentionally available for the owner; there is no scheduled background monitor.

## Published checkpoint

Network source remains `bdd9c6d`; the preparation checkpoint was published in [draft PR73](https://github.com/tantalum666/FYP/pull/73), still unmerged. This continuation adds actual home acceptance, power findings and corrected current docs without changing code or rerunning unchanged application suites. Final publication state is in the [receipt](publication.json). The checked helper source matches the privately rendered seed written to the card; fresh publication checks cover the changed documentation and selected evidence.

## Latest owner direction: Pi paused

The owner subsequently paused Pi and prioritized personal-agent cross-application software. [PR74](https://github.com/tantalum666/FYP/pull/74) is the active independent software continuation. This checkpoint's results and unresolved power/wired/kiosk gates are preserved; no new Pi test or deployment is authorized by this documentation update. Original checkout entrypoints now route to the software worktree.
