# Setup and operation

## 1. Prepare the Python environment

From the cloned repository on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pyserial
.\.venv\Scripts\python.exe -m unittest -v
```

The poller's data-fetching and console-only mode use the Python standard
library. `pyserial` is needed when sending events to the ESP32.

## 2. Upload the ESP32 firmware

1. Install Arduino IDE's ESP32 board support and the FastLED library.
2. Copy the root `fantasy_lamp.ino` into a folder named `fantasy_lamp` and open
   that copy in Arduino IDE. Arduino requires the sketch folder and `.ino`
   filename to match. Keep the root copy in sync when changing the firmware.
3. Select the board matching your hardware. The original build used an ESP32
   Dev Module and a CP210x USB serial connection.
4. Select the board's current COM port and upload the sketch.
5. Open Serial Monitor at **115200 baud**. After the startup sequence, the
   firmware prints `LAMP READY V2`.

The original setup successfully used ESP32 board support 3.3.12, FastLED 3.10.7,
and pyserial 3.5. These are recorded bring-up versions, not a statement that
they are the newest releases.

Follow the [README wiring notes](README.md#breadboard-wiring-notes) for the
external 5 V supply, level shifter, buzzer transistor, and shared ground.

## 3. Check your Sleeper lineup

Pass your own league ID and username when using another account:

```powershell
.\.venv\Scripts\python.exe lamp_poller.py --league YOUR_LEAGUE_ID --username YOUR_USERNAME --once
```

`--once` fetches and prints the current starter slots, then exits. It does not
prove that the LEDs or buzzer are wired correctly.

## 4. Start live polling

Close Arduino Serial Monitor before starting the poller so both programs do
not compete for the same port.

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports -v
.\.venv\Scripts\python.exe lamp_poller.py --league YOUR_LEAGUE_ID --username YOUR_USERNAME --port COM3 --poll 20
```

Replace `COM3` with the port shown for your board. The first poll establishes
a scoring baseline; later score increases generate alerts. Stop with Ctrl+C.
The default serial rate is 115200 baud. The script is not configured to launch
automatically with Windows.

## 5. Check the serial path independently

With the poller stopped, open Arduino Serial Monitor at 115200 baud and enable
a newline line ending. Send:

```text
TRIG BIG 1 RB 4.7
```

The firmware should run the big-play routine for starter slot 1 and print
`ACK BIG`. For a touchdown routine, send `TRIG TD 4 WR 6.0` and expect `ACK TD`.
These are manual test events, not actual scoring reports. Receiving an ACK
confirms the command was handled; inspect the physical outputs separately.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| COM port is missing | Use a data-capable USB cable and check the USB serial driver and selected board. |
| Port is busy | Close Serial Monitor, another poller instance, or any program using that port. |
| No alert immediately after starting | The initial poll establishes a baseline; a later scoring change is required. |
| Wrong league or no roster found | Supply the intended `--league` and `--username` values. |
| Serial ACK but no light or sound | Inspect external power, shared ground, LED data direction, level shifting, and the buzzer circuit. |
| Alerts lag the broadcast | The poller depends on Sleeper scoring updates and the polling interval. |
| A scoring bonus looks like a touchdown | The current detector classifies any increase of at least 6 points as `TD`; see the README limitations. |

## What has been verified

The October 11, 2026 setup record confirms that the four Python tests passed,
the configured Sleeper starter lineup was fetched, the firmware compiled and
uploaded, and the ESP32 returned both `LAMP READY V2` and `ACK BIG`.
That record does not establish measured brightness, audio performance,
electrical characterization, or continuous live-game reliability.
