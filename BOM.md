# Fantasy Lamp BOM — Amazon vs DigiKey + KiCad / LTspice

Split buy — cheapest verified pattern, not single-cart:

**Amazon (modules + power + mechanics):**
- ESP32-DevKitC-32E 2-pack USB-C — search `amazon.com/s?k=esp32-devkit` / ASIN pattern B0GF1ZJCCN. ~$14-16 for 2. DigiKey sells single Espressif boards for more + shipping.
- WS2812B 5V 30 LED/m 2m BTF-LIGHTING kit — $18-22. DigiKey only sells short Adafruit segments at 2-3x cost per LED.
- 5V 4A barrel 2.1x5.5 supply ALITOVE type — $12-15. DigiKey equivalents: Mean Well NGE30U05-P1J / SparkFun 15352, $18-25 + shipping.
- Breadboard + jumper kit ELEGOO — $9-12.

**DigiKey (exact ICs + audio):**
- U2 SN74AHCT125DR SOIC-14 — `digikey.com/en/products/detail/texas-instruments/SN74AHCT125DR/376412` — $0.55 @1. Alternative Nexperia 74AHCT125D-118 $0.35.
- Q1 2N2222A TO-92 — Diotec 2N2222A $0.18 @1 in stock 23k. Avoid $2.90 Microchip TO-18 unless you need metal can.
- BZ1 AI-1223-TWT-5V-5-R PUI — `.../5011393` — 5V 30mA 2.3kHz 85dB THT. Alt Soberton WST-1205S.
- C1 1000uF polymer radial 3.5mm pitch — Würth 870135174006 D8mm. Use 10V+.
- R1 330R / R2 1k — Yageo RC0805FR series 0805. $0.02.

Prices shift; check links above for live stock. DigiKey $4.99 shipping breaks even if you bundle ICs.

## KiCad 7/8 footprints (standard libs)

| Ref | Symbol | Footprint |
|-----|--------|-----------|
| U1 ESP32 module | MCU_ESP32:ESP32-WROOM-32 | 2x `Connector_PinHeader_2.54mm:PinHeader_1x19_P2.54mm_Vertical` spaced 1.1in, or single custom |
| U2 74AHCT125 | 74xx:74AHCT125 | `Package_SO:SOP-14_3.9x8.7mm_P1.27mm` |
| Q1 TO-92 | Device:Q_NPN_CBE | `Package_TO_SOT_THT:TO-92_Inline` flat face per silkscreen |
| R1 R2 0805 | Device:R | `Resistor_SMD:R_0805_2012Metric` |
| C1 radial | Device:C_Polarized | `Capacitor_THT:CP_Radial_D8.0mm_P3.50mm` |
| BZ1 12mm | Device:Buzzer | `PinHeader_1x02_P2.54mm_Vertical` + courtyard 12mm, or `Buzzer_Beeper:Beeper_12x9.5RM7.6mm` if present |
| J1 barrel | Connector:BarrelJack_Horizontal | `Connector_BarrelJack:BarrelJack_Horizontal` 2.1x5.5 |
| LED strip | Connector:Conn_01x03 | 3-pin JST — `Connector_JST:JST_XH_B3B-XH-A` for schematic, wire to strip in build |

Tie U2 OE pins 1OE/2OE/3OE/4OE to GND, VCC to 5V, unused inputs to GND. 1000uF within 2cm of strip power. 330R at ESP32 side.

## LTspice

`ltspice_lamp_driver.asc` simulates only the analog part:
- V1 = ESP32 GPIO17 3.3V pulse
- R2 1k base, Q1 2N2222 (built-in), Rbuz 166R = 5V/30mA buzzer
- Run `.tran 5m`, probe `BUZZ_OUT` collector current ~30mA

Do not try to simulate ESP32 / WS2812B / FastLED in LTspice — digital protocol, no models. Simulate 5V rail separately as pulsed 0-3.6A current source for 60 LEDs at full white to size supply and cap.

Full BOM machine-readable: `bom.csv`.
