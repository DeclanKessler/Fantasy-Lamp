# Fantasy Lamp BOM

This build is currently set up as a breadboard-first prototype. The Amazon parts
cover modules, strip, power, and cables. The DigiKey parts are the small electrical
components where exact packages matter.

## Amazon parts

| Item | Notes |
| --- | --- |
| ESP32 DevKit, ESP-WROOM-32, 38-pin, 2-pack | The hiBCTR board you picked is fine. Use a real USB data cable. |
| BTF-LIGHTING WS2812B 5 V strip, 5 mm wide, 160 LED/m, 3.2 ft | Works with the current `NUM_LEDS=160` firmware. |
| Facmogu 5 V / 4 A wall adapter, 5.5 x 2.5 mm / 5.5 x 2.1 mm tips | Use the 5.5 x 2.5 mm tip with your pigtail. |
| 5.5 x 2.5 mm female pigtail cable | This replaces a PCB barrel jack for the breadboard version. |
| Breadboard and jumper wires | A full-size breadboard is easier because 38-pin ESP32 boards are wide. |

Pigtail note: 14 AWG is too large to push directly into a breadboard. Use the
pigtail to feed a screw terminal, Wago, or solder short male jumpers to the wire
ends. Do not force 14 AWG into breadboard holes.

## DigiKey parts

| Ref | Qty | Part | Why |
| --- | ---: | --- | --- |
| U2 | 1 | `SN74AHCT125N` | 14-PDIP level shifter, breadboard friendly. |
| Q1 | 2 | `2N2222A` Diotec TO-92 | Buzzer low-side switch plus one spare. |
| BZ1 | 1 | `AI-1223-TWT-5V-5-R` | 5 V active buzzer. |
| C1 | 1 | `870135174006` | 1000 uF bulk cap for LED strip power. |
| C2 | 2 | `RDER71H104K0K1H03B` | 0.1 uF radial ceramic decoupling cap plus spare. |
| R1 | 2 | `CFR-25JB-52-330R` | 330 ohm LED data resistor plus spare. |
| R2 | 2 | `CFR-25JB-52-1K` | 1k transistor base resistor plus spare. |

The DigiKey upload file is `digikey_bom.csv`.

## KiCad footprints

| Ref | Symbol | Footprint |
| --- | --- | --- |
| U2 | `74xx:74AHCT125` | `Package_DIP:DIP-14_W7.62mm` |
| Q1 | `Device:Q_NPN_CBE` | `Package_TO_SOT_THT:TO-92_Inline` |
| R1, R2 | `Device:R` | `Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal` |
| C1 | `Device:C_Polarized` | `Capacitor_THT:CP_Radial_D8.0mm_P3.50mm` |
| C2 | `Device:C` | `Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm` |
| BZ1 | `Device:Buzzer` | `Buzzer_Beeper:Beeper_12x9.5RM7.6mm` |
| LED strip | `Connector:Conn_01x03` | `Connector_JST:JST_XH_B3B-XH-A` for PCB rev, or wire direct on breadboard. |
| 5 V input | `Connector:Conn_01x02` | `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` |

For a later PCB, use at least 1 mm traces for the LED 5 V/GND path, and consider
2 mm pours if you route the strip current through the board. For the breadboard
prototype, keep the LED power path off the ESP32 and feed the strip directly from
the 5 V supply.

## LTspice note

`ltspice_lamp_driver.asc` only models the buzzer transistor driver. ESP32 and
WS2812B timing is firmware-driven and is not meaningful in LTspice. For power
supply sizing, model the LED strip as a pulsed 5 V current load instead.
