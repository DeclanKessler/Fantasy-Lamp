# Shopping notes

This is not a live checkout cart. It is the exact split I would buy for the
breadboard version of the lamp.

## Amazon cart

- hiBCTR ESP32 Dev Board, ESP-WROOM-32, 38-pin, 2-pack.
- BTF-LIGHTING WS2812B 5 V strip, 5 mm wide, 160 LED/m, 3.2 ft, IP30.
- Facmogu 5 V / 4 A supply with 5.5 x 2.5 mm / 5.5 x 2.1 mm barrel tips.
- 5.5 x 2.5 mm female DC pigtail cable.
- Breadboard and jumper wire kit, if you do not already have one.

The 14 AWG pigtail is electrically fine but mechanically too thick for a
breadboard. Use it into a screw terminal / Wago / soldered jumper tails.

## DigiKey cart

Upload `digikey_bom.csv` to DigiKey BOM Manager. The important package checks:

- `SN74AHCT125N` must be 14-PDIP, not SOIC.
- `2N2222A` should be TO-92.
- `RDER71H104K0K1H03B` replaces the out-of-stock KEMET `C324...` cap.
- Do not add a PCB barrel jack for the breadboard version. The pigtail does that job.

## Quantity sanity check

| Part | Qty |
| --- | ---: |
| SN74AHCT125N | 1 |
| 2N2222A | 2 |
| AI-1223-TWT-5V-5-R | 1 |
| 870135174006 1000 uF | 1 |
| RDER71H104K0K1H03B 0.1 uF | 2 |
| CFR-25JB-52-330R | 2 |
| CFR-25JB-52-1K | 2 |

If the cart has `C324C104J5G5TA`, remove it. If it has a second `870135174006`,
reduce that line to one unless you intentionally want a spare.
