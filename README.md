# Fantasy Big-Play Lamp

A desk lamp for fantasy football Sundays. A small Python script watches your
Sleeper starters, and an ESP32 drives an addressable LED strip when one of them
has a scoring jump. Touchdowns get a white strobe and jingle; smaller big plays
light that player's starter zone in a position color.

The current build is tuned for a 160-pixel WS2812B strip split into ten starter
segments, so each starter gets a 16-LED zone.

## What is in this repo

| Path | Purpose |
| --- | --- |
| `lamp_poller.py` | Polls Sleeper matchup scoring and sends serial events to the ESP32. |
| `fantasy_lamp.ino` | Arduino / ESP32 firmware for WS2812B LEDs and a 5 V buzzer. |
| `test_lamp.py` | Small unit tests for event detection and serial protocol formatting. |
| `BOM.md`, `CARTS.md` | Human-readable shopping notes and breadboard-friendly swaps. |
| `digikey_bom.csv` | DigiKey BOM upload list for the small parts. |
| `bom.csv` | Full project BOM with footprints and simulation notes. |
| `kicad/` | Starter KiCad project for a later PCB version. |
| `ltspice_lamp_driver.asc` | LTspice sketch for the buzzer transistor driver. |

## Hardware summary

- ESP32 DevKit board, programmed over USB.
- WS2812B 5 V LED strip, 160 LEDs total.
- 74AHCT125 level shifter for reliable 3.3 V-to-5 V LED data.
- 2N2222A transistor driving a 5 V active buzzer.
- 5 V / 4 A external supply for the strip and buzzer.
- Common ground between the supply, ESP32, LED strip, level shifter, and buzzer.

Position colors in the firmware:

| Position | Color |
| --- | --- |
| QB | Red |
| RB | Blue |
| WR | Green |
| TE | Purple |
| Other / K / DEF | Yellow |

## Breadboard wiring notes

- `GPIO16 -> 330 ohm -> 74AHCT125 input -> 74AHCT125 output -> LED DIN`
- `GPIO17 -> 1k -> 2N2222 base`
- Buzzer `+` goes to 5 V. Buzzer `-` goes to the 2N2222 collector. Emitter goes to GND.
- Put the 1000 uF cap across LED 5 V and GND near the strip.
- Put the 0.1 uF cap directly across the 74AHCT125 VCC and GND pins.
- Tie the 74AHCT125 output-enable pins low. Tie unused inputs to GND.
- For the dense 160 LED/m strip, feed 5 V and GND at both ends if possible.

The sketch keeps brightness at `100` because 160 LEDs can pull a lot of current
if they all go white. The animations only light one starter segment at a time,
but the lower brightness gives the power supply more margin.

## Run the poller without hardware

This proves the Sleeper side works before the ESP32 arrives.

```powershell
cd "$HOME\OneDrive\Desktop\fantasy-lamp"
python -m unittest -v
python lamp_poller.py --once
```

`--once` prints the current starter slots and exits. The first live loop only
sets a baseline; alerts start after points change.

## Run with the lamp connected

1. Install the Arduino IDE ESP32 board package.
2. Install the FastLED library.
3. Upload `fantasy_lamp.ino` to the ESP32.
4. Find the ESP32 COM port in Arduino IDE: **Tools -> Port**.
5. Start the PC poller:

```powershell
pip install pyserial
python lamp_poller.py --port COM5 --poll 20
```

Replace `COM5` with your port. The firmware uses 115200 baud. On boot the strip
runs a ten-segment chase and prints `LAMP READY V2`.

## Serial protocol

The PC sends one line per event:

```text
TRIG TD  <slot 0-9> <POS> <points>
TRIG BIG <slot 0-9> <POS> <points>
```

Examples:

```text
TRIG TD 4 WR 6.0
TRIG BIG 1 RB 4.7
```

The slot is the player's current Sleeper starter order. With 160 LEDs and ten
slots, slot `0` owns LEDs 0-15, slot `1` owns LEDs 16-31, and so on.

## Current limitations

- Sleeper scoring is not instant; expect delay compared with TV or live play-by-play.
- A +6 point jump is treated as a touchdown. That is good enough for standard league
  scoring, but a big yardage bonus league would need more context.
- Kicker and defense are supported visually as yellow, but the project is really
  designed around offensive player big plays.
- The KiCad files are a starter layout, not a manufactured PCB release yet.

## Next improvements

- Add a small OLED with the player name and score delta.
- Add quiet mode / volume switch.
- Replace the active buzzer with a MAX98357 I2S amp and short touchdown sounds.
- Make the ESP32 Wi-Fi native so the PC script is no longer required.

## Fantasy Lab dashboard and forecasts

The [fantasy-lab](fantasy-lab/README.md) folder contains the standalone Sleeper league dashboard and Python NFL full-PPR forecasting tool. It combines rankings with usage-based estimates, historical confidence percentages, injury-season exclusions, and touchdown sustainability analysis. Open [Fantasy Lab Combined.html](fantasy-lab/Fantasy%20Lab%20Combined.html) after downloading it, or follow the folder README to refresh the estimates. The saved example is 2026 through Week 4.
