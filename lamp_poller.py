"""Fantasy big-play lamp poller. Polls Sleeper live matchup points for your starters,
detects scoring jumps, sends serial triggers to ESP32. Standard lib only + optional pyserial."""
from __future__ import annotations
import argparse, json, sys, time, hashlib
from pathlib import Path
from urllib.request import Request, urlopen

SLEEPER = "https://api.sleeper.app/v1"
CACHE = Path(__file__).resolve().parent / ".cache"
LEAGUE = "1391859959213359104"
USERNAME = "DeclanKessler"

def get_json(path, ttl=30):
    CACHE.mkdir(exist_ok=True)
    f = CACHE / (hashlib.sha256(path.encode()).hexdigest() + ".json")
    if f.exists() and time.time() - f.stat().st_mtime < ttl:
        return json.loads(f.read_text())
    with urlopen(Request(SLEEPER + path, headers={"User-Agent": "fantasy-lamp/0.1"}), timeout=20) as r:
        data = json.loads(r.read().decode())
    f.write_text(json.dumps(data))
    return data

def resolve_week(league, state, week_arg):
    if week_arg:
        return week_arg
    # live week: state week during season, else last scored
    try:
        return int(state.get("week") or league["settings"]["last_scored_leg"])
    except Exception:
        return int(league["settings"]["last_scored_leg"])

def serial_msg(kind, slot, pos, pts, name=""):
    return f"TRIG {kind} {slot} {pos} {pts:.1f}\n"

def detect_events(prev, cur, starters, names, threshold):
    events = []
    for slot, (pid, cur_pts) in enumerate(zip(starters, cur)):
        p = prev.get(pid, cur_pts)
        delta = cur_pts - p
        if delta >= 6.0:
            kind = "TD"
        elif delta >= threshold:
            kind = "BIG"
        else:
            continue
        nm, pos = names.get(pid, (pid, "?"))
        events.append((kind, slot, nm, pos, delta, cur_pts))
    return events

def main():
    ap = argparse.ArgumentParser(description="Poll Sleeper starters, emit lamp triggers")
    ap.add_argument("--league", default=LEAGUE)
    ap.add_argument("--username", default=USERNAME)
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--poll", type=int, default=20)
    ap.add_argument("--threshold", type=float, default=4.0, help="BIG-play delta below TD level")
    ap.add_argument("--port", default=None, help="COM port, e.g. COM5. Omit for console-only.")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    league = get_json(f"/league/{args.league}", 300)
    state = get_json("/state/nfl", 60)
    week = resolve_week(league, state, args.week)
    user = get_json(f"/user/{args.username}", 86400)
    rosters = get_json(f"/league/{args.league}/rosters", 60)
    my = next((r for r in rosters if r.get("owner_id") == user["user_id"]), None)
    if not my:
        sys.exit(f"No roster for {args.username}")
    roster_id = my["roster_id"]

    players = get_json("/players/nfl", 86400)
    names = {}
    for sid, p in players.items():
        nm = p.get("full_name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip()
        names[str(sid)] = (nm or str(sid), p.get("position", "?"))

    ser = None
    if args.port:
        try:
            import serial
        except ImportError:
            sys.exit("pip install pyserial, or run without --port for console-only")
        ser = serial.Serial(args.port, args.baud, timeout=1)
        time.sleep(2)

    print(f"{args.username} roster {roster_id} week {week} threshold BIG>={args.threshold} TD>=6.0")
    prev = {}
    while True:
        try:
            matchups = get_json(f"/league/{args.league}/matchups/{week}", 15)
        except Exception as e:
            print(f"fetch error: {e}", flush=True)
            if args.once: return 1
            time.sleep(args.poll); continue
        m = next((x for x in matchups if x["roster_id"] == roster_id), None)
        if not m:
            print("roster not in matchups"); return 1
        starters = [str(s) for s in m["starters"]]
        cur_pts = [float(x) for x in m.get("starters_points", [])]
        if not prev:
            for slot, (pid, pts) in enumerate(zip(starters, cur_pts)):
                nm, pos = names.get(pid, (pid, "?"))
                print(f"  slot {slot}: {nm} ({pos}) now {pts:.1f}")
            prev = dict(zip(starters, cur_pts))
        else:
            for kind, slot, nm, pos, delta, total in detect_events(prev, cur_pts, starters, names, args.threshold):
                msg = serial_msg(kind, slot, pos, delta)
                print(f"{kind} slot {slot} {nm} +{delta:.1f} (now {total:.1f}) -> {msg.strip()}", flush=True)
                if ser:
                    ser.write(msg.encode())
            prev = dict(zip(starters, cur_pts))
        if args.once:
            break
        time.sleep(args.poll)

if __name__ == "__main__":
    raise SystemExit(main())
