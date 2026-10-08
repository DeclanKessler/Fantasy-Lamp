# Fantasy Big-Play Lamp

PC polls your Sleeper starters, ESP32 flashes + beeps on big plays.

## Run PC side (no hardware needed first)
```powershell
cd "$HOME\OneDrive\Desktop\fantasy-lamp"
python -m unittest -v
python lamp_poller.py --once
python lamp_poller.py --poll 20
```

Live loop polls `matchups/{week}` every 20s. TD = +6.0 jump, BIG = +4.0 default (`--threshold`).

## With hardware
```
pip install pyserial
python lamp_poller.py --port COM5 --poll 20
```
Find COM port in Arduino IDE -> Tools -> Port. 115200 baud.

Upload `fantasy_lamp.ino` with FastLED installed (Arduino Library Manager -> FastLED).
The sketch is configured for the 3.2ft BTF-LIGHTING 160 LED/m strip: `NUM_LEDS=160`, split into 10 starter zones of 16 LEDs each.
Boot prints `LAMP READY`, self-test flash+beep.

## Protocol
`TRIG TD <name> <POS> <pts>` white strobe + jingle. `TRIG BIG ...` position color + short beep. RB blue, WR green, TE purple, QB red.
