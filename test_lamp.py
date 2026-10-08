import unittest
from lamp_poller import detect_events, serial_msg

class LampTests(unittest.TestCase):
    def test_td_beats_big(self):
        names = {"1": ("A Player", "WR")}
        ev = detect_events({"1": 10.0}, [16.5], ["1"], names, 4.0)
        self.assertEqual(ev[0][0], "TD")
        self.assertEqual(ev[0][1], 0)
    def test_big_threshold(self):
        names = {"1": ("A Player", "RB")}
        ev = detect_events({"1": 10.0}, [14.5], ["1"], names, 4.0)
        self.assertEqual(ev[0][0], "BIG")
    def test_no_event_small(self):
        ev = detect_events({"1": 10.0}, [11.0], ["1"], {"1": ("X", "TE")}, 4.0)
        self.assertEqual(ev, [])
    def test_serial_safe(self):
        msg = serial_msg("TD", 3, "RB", 6.1)
        self.assertEqual(msg, "TRIG TD 3 RB 6.1\n")

if __name__ == "__main__":
    unittest.main()
