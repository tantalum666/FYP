# Original Pi after manual power restoration

26 November 2026, Hong Kong time. Compared the journal on the original device across its loss of access and the owner-confirmed reconnection of its existing USB-C power path. The recovered API and kiosk served application `949d76df`. A fresh read-only fare search used the existing Pi account. This is a field investigation of the deployed version.

## Power timeline

| Time | On-device evidence |
| --- | --- |
| 21:40:13 | The previous boot’s ninth recorded undervoltage warning. The kernel reported normal voltage again about two seconds later. |
| 21:41:54 | The last successful regular RTC renewal read back its target of 21:44:54. |
| 21:42:06 | The previous boot’s last retained event, from the application. The investigation found no orderly shutdown sequence, power-button shutdown, kernel panic or critical-temperature shutdown in that boot’s retained journal. |
| Around 23:04 | The owner unplugged and reconnected the original power path. Current uptime and the synchronized clock identify the new boot. Journald reported an unclean journal. Early RTC time was about thirteen seconds after the 1970 epoch. |
| 23:06:14 | Following clock synchronization, firmware, Linux and the owner record agreed on an enabled RTC alarm with 158 seconds remaining. The ordinary application was active. |

The bootloader reported 900 mA as the USB-C supply capability. All USB-PD capability words were zero and no current override was present in the EEPROM settings. The original board’s `/proc/device-tree/chosen/power/power_reset` property was present and zero. USB boot over-current was also zero. These fields describe the new start after a physical cable reconnection. They cannot reconstruct a transient on the previous boot. [Raspberry Pi boot-time power properties](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/configuration/reference.adoc) · [Pi power and RTC](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html).

A separate normal-load sample completed 13 readings five seconds apart on this boot. Firmware reported 4.888–5.000 V at the board and no active or latched throttling flag within that minute. By 23:18 under ordinary operation the SoC reached 85.35 °C and firmware reported active clock capping and throttling (0xe0006). A separate 23:20 read reached 85.9 °C and confirmed one original desktop Chromium kiosk process and a healthy API. The current boot’s kernel had logged no new undervoltage warning at that point. No fan cooling device was registered. The most informative physical comparison is a known-good Pi 5 supply and cable under the same ordinary load. The 2.4 GHz configured CPU ceiling, firmware settings and recovery timer were preserved. This session did not include a deliberate shutdown or power interruption.

## Payment readiness

The original kiosk submitted one read-only retry for the previously unavailable airport. The chat’s `live_flight_search` Function succeeded, eight offers came back and a separate accessibility read on the original screen confirmed two of their fares and a nonstop flight number. All eight lacked a verified total for the requested checked baggage. The query produced zero new live order submissions and zero new sandbox orders.

On the supplier’s public page for one of those exact nonstop offers, selecting one checked bag still displayed a possible extra charge without a weight or a price for the bag. The website and agent channel also displayed different base prices. The official flight search schema lists no structured checked-weight parameter. The booking request accepts the selected supplier offer and passenger/contact details. The application can submit an approved eligible fare and poll the associated order for a reservation reference and settled amount. An unpriced bag cannot be added to that API booking at a guessed price.

On an eligible first purchase with no stored method, the official supplier returns an account-specific card-setup link. Its documented zero-value setup uses the provider’s card or Revolut Pay flow. The original authorization remains usable. A live purchase still needs the owner’s confirmation of the exact terms with their actual traveller information. Separately, the airline-direct guest page required human verification before providing a fresh all-in comparison. No passenger fields were entered and no financial call was made. [Official agent guide](https://letsfg.co/for-agents) · [FYP checkout behavior](../../../desk-companion/docs/live-flight-agent.md).

## Verification scope

Read the project entry requirements, current product and handoff, the latest flight-account decision, the power recovery and live-flight guides, and the previous incident record. Examined the booking adapter, passenger validation, checkout and seller evidence paths. Used the two real device readbacks, independent firmware register and kernel log reads, the regular kiosk and the official supplier page. Application source and previously accepted tests stayed at the deployed version. Private route, money, account details and device identifiers are omitted from this record. Updated the handoff, focused operator guides and work log.
