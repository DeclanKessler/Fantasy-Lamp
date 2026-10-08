// Fantasy big-play lamp — ESP32 + WS2812B + buzzer
// Board: ESP32 DevKitC. Libs: FastLED (Library Manager).
// Wiring: GPIO16 -> 330R -> level-shifter -> LED DIN, 5V supply shared GND, 1000uF across LED power.
//         GPIO17 -> 2N2222 base via 1k -> buzzer to 5V. USB serial 115200 from lamp_poller.py
// Protocol: "TRIG TD <name> <POS> <pts>" or "TRIG BIG <name> <POS> <pts>"
#include <FastLED.h>
#define NUM_LEDS 160
#define DATA_PIN 16
#define BUZZER_PIN 17
CRGB leds[NUM_LEDS];

void beep(int freq, int ms) {
  tone(BUZZER_PIN, freq, ms);
  delay(ms + 20);
  noTone(BUZZER_PIN);
}
// Protocol v2 per-player: "TRIG TD <slot 0-9> <POS> <pts>" or "TRIG BIG <slot> <POS> <pts>"
// 60 LEDs / 10 starters = 6 LEDs per player. Slot from PC starter order.
// TD: that player's segment strobes white + pos color, rest dim. BIG: segment only.
#define SLOTS 10
void flashSegment(int slot, CRGB c, int times, int onMs = 180) {
  int per = NUM_LEDS / SLOTS;
  int start = constrain(slot, 0, SLOTS-1) * per;
  for (int i = 0; i < times; i++) {
    FastLED.clear();
    for (int j = 0; j < per; j++) leds[start+j] = c;
    FastLED.show();
    delay(onMs);
    FastLED.clear(); FastLED.show();
    delay(120);
  }
}
CRGB posColor(String pos) {
  if (pos == "RB") return CRGB::Blue;
  if (pos == "WR") return CRGB::Green;
  if (pos == "TE") return CRGB::Purple;
  if (pos == "QB") return CRGB::Red;
  return CRGB::Yellow;
}
void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
  // 160 LED/m strip can pull a lot at full white. Keep brightness modest.
  FastLED.setBrightness(100);
  // boot self-test: chase all 10 segments
  for (int s = 0; s < SLOTS; s++) { flashSegment(s, CRGB::White, 1, 80); }
  beep(660, 120);
  Serial.println("LAMP READY V2");
}
void loop() {
  if (!Serial.available()) { delay(20); return; }
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (!line.startsWith("TRIG")) return;
  // TRIG KIND SLOT POS pts
  int a = line.indexOf(' ');
  int b = line.indexOf(' ', a+1);
  int c = line.indexOf(' ', b+1);
  int d = line.indexOf(' ', c+1);
  if (b < 0 || c < 0 || d < 0) return;
  String kind = line.substring(a+1, b);
  int slot = line.substring(b+1, c).toInt();
  String pos = line.substring(c+1, d);
  if (kind == "TD") {
    flashSegment(slot, CRGB::White, 4, 150);
    flashSegment(slot, posColor(pos), 2);
    beep(880, 400); beep(1174, 400);
  } else {
    flashSegment(slot, posColor(pos), 3);
    beep(880, 150);
  }
  Serial.println("ACK " + kind);
}
