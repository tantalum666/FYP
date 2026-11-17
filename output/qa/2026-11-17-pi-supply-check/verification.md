# Group 2 · Replacement power-adapter observation

17November2026. Owner confirms replacing the adapter/charging head and pressing once to start from red standby. Original application8c67ddbe and early RTC configuration are retained. Pi still reports3000mA available current; this alone is not a stability diagnosis.

Monitoring began19:06:11HKT at uptime56.17s, boot80835efc. API and application services active; Alice kiosk present; CPU maximum2400000kHz. The monitor samples every5s for a planned600s, without deliberate shutdown, stress workload or model inference.

## Result: replacement supply has not passed

The planned600-second run ended after **485seconds /98samples** when SSH timed out (exit255). The final sample arrived19:14:16HKT; there is no finished marker. Each collected sample reported API health OK, and the configured CPU maximum stayed2400000kHz. Alice kiosk/API/application services were active at admission. No intentional shutdown/restart or load reduction occurred.

**18of98samples** had active0x50005 (current undervoltage and throttling as well as historical bits). This is a count of observed samples, not18independent fault episodes or a continuous-duration estimate. Board EXT5V ADC samples ranged **4.64712–4.93924V**; sampled temperatures **47.7–77.9°C**. No active Arm-cap bit1 or soft-temperature bit3 was sampled; that alone is not a cooling certification. The monitor is low-rate and can miss short transients.

Current-boot kernel events independently show undervoltage at uptime5.856s, normalization130.848s and renewed undervoltage132.864s. Monitoring began at uptime56.17s, so the132.864s event is new within this observation period; the initial warning belongs to the new adapter's startup. A historical0x50000alone was not treated as a current fault.

The boot ID stayed80835efc throughout collected samples. After interruption, the forwarded API and pinned SSH were unreachable at19:17HKT. This proves loss of access, not by itself a shutdown/reboot or a unique failed component. A final check is recorded separately if it returns. Repeated active undervoltage is sufficient to reject the current power-path stability criterion even without attributing the connection failure.

The device reports3000mA available current, not measured current draw. The adapter's brand/model/cable and actual external load were not independently identified. Results cannot uniquely blame the charging head rather than the cable/contact/peripherals, or establish a controlled improvement over the previous supply. Further acceptance needs a suitable stable5V supply path at the owner's unchanged operating performance.

[Official vcgencmd meanings](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/os/graphics-utilities.adoc) distinguish active/history bits. [Official Pi5supply](https://www.raspberrypi.com/products/27w-power-supply/) specifies5.1V/5A and its cable; total charger wattage alone does not identify the5V profile. No purchase was made.

Raw telemetry/private diagnostics: ~/.config/desk-companion/pi-supply-check-20261117/. This is an observation at the existing operating load, not a maximum-load or long-term certification. No files, grants, voice or performance preferences are replaced.

Final access readback: {"checked_utc": "2026-11-17T11:21:32.380383+00:00", "code": 255, "output": "", "error": "Connection timed out during banner exchange\nConnection to UNKNOWN port 65535 timed out\n"}

Documentation updated: product, power contract, decisions, work-log, handoff and entry pointers. No source behavior/dependency/firmware changes were made by this observation.
