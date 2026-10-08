# Carts — import, not live checkout

I can't create logged-in DigiKey / Amazon carts for you, but these import in ~2 clicks.

## DigiKey — `digikey_bom.csv`
1. Go to digikey.com -> BOM Manager -> Upload `digikey_bom.csv`
2. It matches on Manufacturer Part Number. Check package before checkout:
   - SN74AHCT125DR must say 14-SOIC
   - 2N2222A must say TO-92 Inline (Diotec) — avoid TO-18 metal can unless you want it
   - AI-1223-TWT-5V-5-R Through Hole
3. Detail pages from search:
   - https://www.digikey.com/en/products/detail/texas-instruments/SN74AHCT125DR/376412
   - https://www.digikey.com/en/products/detail/pui-audio-inc/AI-1223-TWT-5V-5-R/5011393

Add shipping: DigiKey $4.99 Economy breaks even if you bundle all ICs at once.

## Amazon — buy direct
No upload — search terms verified 2026-10-08:
- ESP32-DevKitC-32E 2-pack USB-C: https://www.amazon.com/s?k=esp32-devkit — pick 2-pack WROOM-32E, ASIN pattern B0GF1ZJCCN seen at ~$14-16
- Adafruit official board alt: https://www.adafruit.com/product/3269
- WS2812B 5V 30 LED/m 2m BTF-LIGHTING: search `amazon.com/s?k=BTF-LIGHTING+WS2812B+30`
- 5V 4A 2.1x5.5 supply ALITOVE type: search `amazon.com/s?k=5V+4A+2.1x5.5`
- ELEGOO breadboard + 120pc jumpers: search `amazon.com/s?k=ELEGOO+breadboard+jumpers`

Amazon is cheaper for modules / strip / supply. DigiKey is cheaper per exact IC.
Full notes: `BOM.md`. Machine list: `bom.csv`.
