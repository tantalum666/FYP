# Original Pi, flight-account activation and power incident

26 November 2026, Hong Kong time. The original Pi 5 kiosk and local API served application `949d76df`. The source for this operator change starts at `f51e9684` after [PR 182](https://github.com/tantalum666/FYP/pull/182). The operator used the enrolled original-device SSH identity.

## Ordinary account and flight search

The Pi finished its own LetsFG authorization-code flow. Its loopback callback returned through a temporary owner-side SSH forward. The provider success page and the Pi's independent connection readback both identified the requested search and booking permissions. The rotating credentials are held in each desk's own vault.

The Mac's existing local ledger first debited a fixed share in a single transaction. The original Pi then activated the issued successor term. Both live diagnostics showed the allocated daily ceilings and the allocated monthly ceilings adding to their respective original maxima. The Mac kept its statement opening and existing usage. The tests cover simultaneous issuance, retry after losing the source response, retry in a later month, a changed recipient, and insufficient headroom for existing commitments. Operator backups and financial values are private.

At 21:38, the original physical Chromium composer submitted a read-only flexible-airport query. The in-device conversation recorded OpenAI activity and a successful real flight search Function call. Both supplier searches started. At 21:39:57 one airport had eight published offers. The other returned a provider error on readback. None of the eight offers established a total covering the requested checked-bag weight. Original application records showed zero new live booking submissions and zero new sandbox orders. The full trip and account readbacks remain private. The connection ended before a post-result kiosk screen inspection. [Purchase and readback rules](../../../desk-companion/docs/live-flight-agent.md).

## Power and loss of access

The early-evening [on-device sample](../2026-11-26-original-pi-update/receipt.json) showed 85.35 °C and active frequency limiting. The next known boot began around 20:28. The independent 20:59 read found the RTC timer active and the SoC at 84.8 °C. At 21:39:57 the Pi returned the real flight data. Subsequent authenticated attempts timed out. At 21:56 the separately authenticated relay was reachable but could not read an SSH greeting from the device. At 21:57:56 its registered loopback listener refused a new connection. These observations bound the loss of reachability; the LED observation comes from the owner.

The installed RTC helper and unit files had not changed in the application release. Its previously verified policy refreshes an owned hardware alarm every 30 seconds with a three-minute lead. The Pi 5 normally shows a red standby LED after an ordinary shutdown. An RTC backup battery powers the clock while the main rail is disconnected. A remote timeout and a high SoC temperature alone cannot identify why the board went dark. [Existing RTC acceptance](../2026-11-23-api-astra-team/pi-recovery/verification.md) · [Pi 5 status LEDs](https://www.raspberrypi.com/documentation/computers/configuration.html#raspberry-pi-5-and-500-leds) · [RTC and input power](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#real-time-clock-rtc).

## Reading and checks

Read the entry contract and current sections of product, handoff and decisions, the relevant operator, live flight and Pi power guides, the November 23 RTC repair and November 26 installed-device receipts. Inspected the deployed helper and both systemd units, provider polling and current calendar ledger. Used the earlier browser, simulator and unit results for unchanged functions. The new boundary checks, operator rehearsal, live per-device term verification and real kiosk query cover the changed account and budget path. The earlier test-mode booking and real-world capture remain separate. Identifying device, billing, passenger and account data are retained outside the repository.
