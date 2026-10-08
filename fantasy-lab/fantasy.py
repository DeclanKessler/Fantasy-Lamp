"""NFL offense and player opportunity analysis using public nflverse downloads.

Install: python -m pip install pandas
Run: python fantasy.py --season 2025 --week 6 --horizon 4
Only regular-season games completed through --week enter the model.
Projections use a workload heuristic; historical calibration is optional.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import re
import hashlib
import base64
import math
from pathlib import Path
import sys
import urllib.error
import urllib.request

import pandas as pd

BASE = "https://github.com/nflverse/nflverse-data/releases/download"
SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
METRICS = ["attempts", "passing_yards", "passing_tds", "passing_interceptions",
           "carries", "rushing_yards", "rushing_tds", "targets", "receptions",
           "receiving_yards", "receiving_tds", "receiving_air_yards",
           "fantasy_points_ppr"]


def normalize_team_columns(frame):
    """Historical statistics and schedules use different relocation abbreviations."""
    aliases = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}
    for column in ("team", "posteam", "defteam", "home_team", "away_team", "opponent_team"):
        if column in frame:
            frame[column] = frame[column].replace(aliases)
    return frame


def download(url: str, path: Path, refresh: bool = False) -> Path:
    """Reuse explicit disk cache; refresh downloads atomically with a timeout."""
    if path.exists() and not refresh:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    print(f"Downloading {url}", flush=True)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "FantasyAnalysis/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        temp.replace(path)
    except (OSError, urllib.error.URLError) as exc:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Could not download {url}: {exc}. Check the season, connection, "
                           "or use an existing cache without --refresh.") from exc
    return path


def load_data(season: int, cache: Path, refresh: bool):
    sources = {
        "stats": f"{BASE}/stats_player/stats_player_week_{season}.csv",
        "pbp": f"{BASE}/pbp/play_by_play_{season}.csv.gz",
        "schedules": SCHEDULE_URL,
    }
    paths = {key: download(url, cache / (f"pbp_{season}.csv.gz" if key == "pbp" else
                                       f"stats_{season}.csv" if key == "stats" else
                                       "schedules.csv"), refresh)
             for key, url in sources.items()}
    stats = normalize_team_columns(pd.read_csv(paths["stats"], low_memory=False))
    needed = {"game_id", "week", "season_type", "posteam", "defteam", "play_type",
              "epa", "yards_gained", "pass_attempt", "rush_attempt", "qb_kneel",
              "qb_spike", "two_point_attempt", "receiver_player_id", "rusher_player_id", "yardline_100",
              "passer_player_id", "complete_pass", "rush_touchdown", "pass_touchdown", "sack"}
    pbp = normalize_team_columns(pd.read_csv(paths["pbp"], usecols=lambda c: c in needed, low_memory=False))
    schedule = normalize_team_columns(pd.read_csv(paths["schedules"], low_memory=False))
    required = {"player_id", "player_display_name", "position", "team", "week",
                "season_type", "game_id", *METRICS}
    missing = required - set(stats.columns)
    if missing:
        raise ValueError(f"Player data schema is missing: {sorted(missing)}")
    missing = needed - set(pbp.columns)
    if missing:
        raise ValueError(f"Play-by-play schema is missing: {sorted(missing)}")
    metadata = {key: {"url": sources[key], "cache_file": str(path.resolve()),
                      "cached_at_utc": datetime.fromtimestamp(path.stat().st_mtime,
                                                              timezone.utc).isoformat()}
                for key, path in paths.items()}
    return stats, pbp, schedule, metadata


def completed_games(schedule, season, week):
    return schedule.loc[(schedule.season == season) & (schedule.game_type == "REG") &
                        (schedule.week <= week) & schedule.home_score.notna() &
                        schedule.away_score.notna()].copy()


def prepare(stats, pbp, schedule, season, week):
    games = completed_games(schedule, season, week)
    if games.empty:
        raise ValueError(f"No completed regular-season games for {season} through week {week}.")
    expected = set(games.game_id)
    stats = stats.loc[stats.game_id.isin(expected) & (stats.season_type == "REG")].copy()
    pbp = pbp.loc[pbp.game_id.isin(expected) & (pbp.season_type == "REG")].copy()
    for name, frame in [("player statistics", stats), ("play-by-play", pbp)]:
        missing = expected - set(frame.game_id)
        if missing:
            raise ValueError(f"{name} has not covered {len(missing)} completed games: "
                             f"{sorted(missing)[:5]}. Try an earlier --week or --refresh.")
    # Official offensive plays, including sacks; exclude kneels, spikes and no-plays.
    pbp = pbp.loc[pbp.play_type.isin(["pass", "run"]) & pbp.posteam.notna() &
                  pbp.qb_kneel.fillna(0).eq(0) & pbp.qb_spike.fillna(0).eq(0) &
                  pbp.two_point_attempt.fillna(0).eq(0)].copy()
    pbp["success"] = pbp.epa.gt(0).where(pbp.epa.notna())
    stats[METRICS] = stats[METRICS].apply(pd.to_numeric, errors="coerce").fillna(0)
    if stats.duplicated(["player_id", "game_id"]).any():
        raise ValueError("Duplicate player/game rows in source data.")
    return stats, pbp, games


def team_rankings(pbp, games):
    result = pbp.groupby("posteam").agg(plays=("game_id", "size"),
                  epa_per_play=("epa", "mean"), success_rate=("success", "mean"),
                  yards_per_play=("yards_gained", "mean"),
                  pass_rate=("pass_attempt", "mean"))
    appearances = pd.concat([
        games[["game_id", "home_team", "home_score"]].rename(
            columns={"home_team": "team", "home_score": "score"}),
        games[["game_id", "away_team", "away_score"]].rename(
            columns={"away_team": "team", "away_score": "score"})])
    result = result.join(appearances.groupby("team").agg(
        games=("game_id", "nunique"), scoreboard_points_per_game=("score", "mean")))
    result["plays_per_game"] = result.plays / result.games
    result["offense_score"] = 100 * (
        .60 * result.epa_per_play.rank(pct=True) +
        .25 * result.success_rate.rank(pct=True) +
        .15 * result.yards_per_play.rank(pct=True))
    result["offense_rank"] = result.offense_score.rank(method="min", ascending=False).astype(int)
    result.index.name = "team"
    return result.reset_index().sort_values(["offense_rank", "team"])


def player_usage(stats, pbp, games, recent_games):
    """Shares use all team games, including zero-stat games, never just player appearances."""
    rows = []
    team_games = pd.concat([games[["game_id", "week", "home_team"]].rename(
        columns={"home_team": "team"}), games[["game_id", "week", "away_team"]].rename(
        columns={"away_team": "team"})])
    offense = stats.loc[stats.position.isin(["QB", "RB", "WR", "TE"])].copy()
    contexts = {}
    for team, tg in team_games.groupby("team"):
        tg = tg.sort_values("week")
        ids = set(tg.tail(recent_games).game_id)
        ts = stats.loc[stats.team == team]
        rz = pbp.loc[(pbp.posteam == team) & (pbp.yardline_100 <= 20)]
        contexts[team] = (len(tg), ids, ts[METRICS].sum(),
                          ts.loc[ts.game_id.isin(ids), METRICS].sum(),
                          rz.receiver_player_id.value_counts(), rz.rusher_player_id.value_counts())
    for player_id, history in offense.groupby("player_id"):
        latest = history.sort_values("week").iloc[-1]
        team = latest.team
        # A traded player's old team usage does not enter their new-team projection.
        current = history.loc[history.team == team]
        n, ids, team_totals, team_recent, rz_targets, rz_carries = contexts[team]
        recent = current.loc[current.game_id.isin(ids)]
        totals, rec = current[METRICS].sum(), recent[METRICS].sum()
        nr = len(ids)
        row = {"player_id": player_id, "player": latest.player_display_name,
               "position": latest.position, "team": team, "team_games": n,
               "stat_games": current.game_id.nunique(), "last_stat_week": int(latest.week),
               "recent_team_games": nr, "ppr_per_team_game": totals.fantasy_points_ppr / n,
               "recent_ppr_per_team_game": rec.fantasy_points_ppr / nr}
        row.update({k: float(v) for k, v in totals.items()})
        for metric, label in [("targets", "target"), ("carries", "carry"),
                              ("attempts", "pass_attempt"), ("receiving_air_yards", "air_yards")]:
            denominator, rd = team_totals[metric], team_recent[metric]
            share = totals[metric] / denominator if denominator > 0 else 0
            rs = rec[metric] / rd if rd > 0 else 0
            row[f"{label}_share"] = share
            row[f"recent_{label}_share"] = rs
            row[f"{label}_share_change"] = rs - share
            if metric != "receiving_air_yards":
                # More recent games receive more weight; still use season information.
                projected_share = .65 * rs + .35 * share
                team_volume = .65 * rd / nr + .35 * denominator / n
                row[f"projected_{metric}"] = projected_share * team_volume
        target_total, carry_total = rz_targets.sum(), rz_carries.sum()
        row["red_zone_targets"] = int(rz_targets.get(player_id, 0))
        row["red_zone_carries"] = int(rz_carries.get(player_id, 0))
        row["red_zone_target_share"] = row["red_zone_targets"] / target_total if target_total else 0
        row["red_zone_carry_share"] = row["red_zone_carries"] / carry_total if carry_total else 0
        rows.append(row)
    return pd.DataFrame(rows)


def project_players(usage, stats):
    """Shrink per-opportunity efficiency toward observed position averages at cutoff."""
    result = usage.copy()
    specifications = [
        ("receptions", "targets", 30, 1), ("receiving_yards", "targets", 30, .1),
        ("receiving_tds", "targets", 60, 6), ("rushing_yards", "carries", 40, .1),
        ("rushing_tds", "carries", 80, 6), ("passing_yards", "attempts", 100, .04),
        ("passing_tds", "attempts", 150, 4), ("passing_interceptions", "attempts", 150, -2)]
    result["projected_ppr_per_game"] = 0.0
    for numerator, denominator, strength, points in specifications:
        pools = stats.groupby("position")[[numerator, denominator]].sum()
        priors = pools[numerator].div(pools[denominator].replace(0, float("nan"))).fillna(0)
        prior = result.position.map(priors).fillna(0)
        efficiency = (result[numerator] + strength * prior) / (result[denominator] + strength)
        result[f"estimated_{numerator}_per_{denominator}"] = efficiency
        result.projected_ppr_per_game += efficiency * result[f"projected_{denominator}"] * points
    # Availability, fumbling, two-point conversions and uncommon scoring are not modeled.
    result["sample_note"] = result.team_games.map(
        lambda n: "small sample" if n < 4 else "workload baseline")
    result["position_rank"] = result.groupby("position").projected_ppr_per_game.rank(
        method="min", ascending=False).astype(int)
    return result.sort_values("projected_ppr_per_game", ascending=False)


def future_weeks(players, schedule, season, week, horizon):
    future = schedule.loc[(schedule.season == season) & (schedule.game_type == "REG")]
    rows = []
    for r in players.itertuples():
        for w in range(week + 1, min(18, week + horizon) + 1):
            game = future.loc[(future.week == w) &
                              ((future.home_team == r.team) | (future.away_team == r.team))]
            if game.empty:
                if future.week.eq(w).any():
                    opponent, status, points = "", "bye", 0.0
                else:
                    opponent, status, points = "", "schedule unavailable", float("nan")
            else:
                g = game.iloc[0]
                opponent = g.away_team if g.home_team == r.team else g.home_team
                status, points = "scheduled; assumes same role and availability", r.projected_ppr_per_game
            rows.append({"player_id": r.player_id, "player": r.player, "position": r.position,
                         "team": r.team, "week": w, "opponent": opponent,
                         "projected_ppr": points, "status": status})
    return pd.DataFrame(rows, columns=["player_id", "player", "position", "team", "week",
                                      "opponent", "projected_ppr", "status"])


def confidence_features(position, week, prediction, last_week):
    stage = "early" if week <= 4 else "middle" if week <= 8 else "late"
    band = "under5" if prediction < 5 else "5to10" if prediction < 10 else "10to15" if prediction < 15 else "15plus"
    activity = "stale" if last_week < week - 1 else "recent"
    return position, stage, band, activity


def calibration_key(features, horizon, level):
    return "|".join([str(horizon), *features[:level]])


def calibration_group(model, features, horizon):
    # Prefer comparable position, cutoff stage, projected workload and recent activity.
    for level in (4, 3, 2, 1):
        key = calibration_key(features, horizon, level)
        group = model["groups"].get(key)
        if group and group["sample_size"] >= model["minimum_group_size"]:
            return key, group
    return None, None


def injury_season_exclusions(seasons, cache, schedule):
    """Flag whole player seasons from documented medical absences, never stat gaps alone."""
    records, coverage = [], []
    for season in seasons:
        ipath = download(f"{BASE}/injuries/injuries_{season}.csv", cache / f"injuries_{season}.csv")
        rpath = download(f"{BASE}/weekly_rosters/roster_weekly_{season}.csv", cache / f"roster_weekly_{season}.csv")
        injuries = normalize_team_columns(pd.read_csv(ipath, low_memory=False))
        rosters = normalize_team_columns(pd.read_csv(rpath, low_memory=False))
        required_i = {"gsis_id", "team", "week", "game_type", "report_status", "report_primary_injury"}
        required_r = {"gsis_id", "team", "week", "game_type", "status", "status_description_abbr"}
        if required_i - set(injuries) or required_r - set(rosters):
            raise ValueError(f"Incomplete injury/roster schema for {season}; cannot label it healthy.")
        games = completed_games(schedule, season, 18)
        team_weeks = pd.concat([games[["home_team", "week"]].rename(columns={"home_team": "team"}),
                               games[["away_team", "week"]].rename(columns={"away_team": "team"})]).drop_duplicates()
        injuries = injuries.loc[injuries.game_type.eq("REG")].merge(team_weeks, on=["team", "week"])
        rosters = rosters.loc[rosters.game_type.eq("REG")].merge(team_weeks, on=["team", "week"])
        expected = set(map(tuple, team_weeks[["team", "week"]].to_numpy()))
        available = set(map(tuple, rosters[["team", "week"]].drop_duplicates().to_numpy()))
        if expected - available or set(games.week) - set(injuries.week):
            raise ValueError(f"Injury/roster coverage missing scheduled weeks in {season}; refusing to assume no injuries.")
        stats = pd.read_csv(cache / f"stats_{season}.csv", usecols=["player_id", "game_id", "week", "season_type"])
        participated = set(map(tuple, stats.loc[stats.season_type.eq("REG"), ["player_id", "week"]].to_numpy()))
        inactive = set(map(tuple, rosters.loc[rosters.status.eq("INA"), ["gsis_id", "week"]].to_numpy()))
        def medical(value):
            if pd.isna(value):
                return False
            text = str(value or "").strip().lower()
            return bool(text and text != "nan" and not re.search(r"not injury|non.?injury|personal|resting player|suspension", text)
                        and text not in {"rest", "other", "none"})
        for r in injuries.itertuples():
            injury = str(getattr(r, "report_primary_injury", ""))
            secondary = getattr(r, "report_secondary_injury", "")
            status = str(r.report_status).lower()
            if pd.isna(r.gsis_id) or not (medical(injury) or medical(secondary)):
                continue
            absent = (r.gsis_id, r.week) not in participated
            confirmed = status == "out" or (status in {"questionable", "doubtful"} and (r.gsis_id, r.week) in inactive)
            if absent and confirmed:
                records.append({"season": season, "player_id": r.gsis_id,
                    "player": getattr(r, "full_name", r.gsis_id), "week": int(r.week),
                    "reason": "injury report " + status + (" + inactive roster" if status != "out" else ""),
                    "designation": injury, "team": r.team})
        # Reserve codes from nflverse's documented status descriptors: IR, PUP,
        # non-football injury/illness, and designated-for-return variants.
        codes = {"R01", "R04", "R05", "R27", "R47", "R48"}
        medical_reserve = rosters.loc[(rosters.status.eq("RES") & rosters.status_description_abbr.isin(codes)) |
                                     rosters.status.isin(["PUP", "RSN"])]
        for r in medical_reserve.itertuples():
            if pd.notna(r.gsis_id) and (r.gsis_id, r.week) not in participated:
                records.append({"season": season, "player_id": r.gsis_id,
                    "player": getattr(r, "full_name", r.gsis_id), "week": int(r.week),
                    "reason": "medical reserve roster", "designation": r.status_description_abbr, "team": r.team})
        coverage.append({"season": season, "injury_rows": len(injuries), "roster_rows": len(rosters),
                         "scheduled_team_weeks": len(expected), "injury_url": f"{BASE}/injuries/injuries_{season}.csv",
                         "roster_url": f"{BASE}/weekly_rosters/roster_weekly_{season}.csv"})
    exclusions = pd.DataFrame(records, columns=["season", "player_id", "player", "week", "reason", "designation", "team"])
    return exclusions.drop_duplicates(["season", "player_id", "week", "reason"]), coverage


def touchdown_events(pbp):
    """One record per rush, receiving target, or QB pass attempt; zones precede the play."""
    frames = []
    for role, id_column, td_column in [("rush", "rusher_player_id", "rush_touchdown"),
                                      ("receive", "receiver_player_id", "pass_touchdown"),
                                      ("pass", "passer_player_id", "pass_touchdown")]:
        selected = pbp.loc[pbp[id_column].notna()].copy()
        if role == "pass":
            selected = selected.loc[selected.pass_attempt.eq(1) & selected.sack.fillna(0).eq(0)]
        selected = selected.loc[selected.yardline_100.notna()]
        frames.append(pd.DataFrame({"player_id": selected[id_column], "week": selected.week,
            "role": role, "zone": selected.yardline_100.map(
                lambda y: "inside5" if y <= 5 else "6to20" if y <= 20 else "outside20"),
            "td": selected[td_column].fillna(0).astype(int),
            "touch": selected.complete_pass.fillna(0).astype(int) if role == "receive" else 1}))
    return pd.concat(frames, ignore_index=True)


def touchdown_baselines(seasons, cache, exclusions):
    """Fit scoring rates on calibration seasons only, after the requested season filter."""
    samples, source_rows = [], []
    for season in seasons:
        stats, pbp, schedule, sources = load_data(season, cache, False)
        stats, pbp, games = prepare(stats, pbp, schedule, season, 18)
        invalid = set(exclusions.loc[exclusions.season.eq(season), "player_id"])
        positions = stats.sort_values("week").drop_duplicates("player_id", keep="last")[["player_id", "position"]]
        positions = positions.loc[positions.position.isin(["QB", "RB", "WR", "TE"]) & ~positions.player_id.isin(invalid)]
        events = touchdown_events(pbp).merge(positions, on="player_id", how="inner")
        events["season"] = season
        samples.append(events)
        source_rows.append({"season": season, "eligible_players": len(positions), "opportunities": len(events), "pbp_url": sources["pbp"]["url"]})
    combined = pd.concat(samples, ignore_index=True)
    groups = {}
    for columns in (["position", "role", "zone"], ["position", "role"], ["role"]):
        for keys, group in combined.groupby(columns):
            if not isinstance(keys, tuple):
                keys = (keys,)
            groups["|".join(keys)] = {"opportunities": len(group), "tds": int(group.td.sum()),
                "td_rate": float(group.td.mean())}
    rz = combined.loc[combined.zone.ne("outside20") & combined.role.ne("pass") & combined.touch.eq(1)]
    conversion = {position: {"touches": len(group), "tds": int(group.td.sum()), "rate": float(group.td.mean())}
                  for position, group in rz.groupby("position")}
    return {"calibration_seasons": seasons, "groups": groups, "red_zone_touch_conversion": conversion,
            "sources": source_rows, "minimum_rate_opportunities": 50,
            "method": "Historical TD rates by position, opportunity type and pre-play field zone (inside5, 6to20, outside20). RZ touches are carries plus completed receptions. QB passing attempts are separate."}


def poisson_upper_tail(observed, expected):
    """Approximate rarity indicator, not a calibrated player-specific probability."""
    if observed <= 0:
        return 1.0
    if expected <= 0:
        return 0.0
    term = math.exp(-expected)
    cdf = term
    for k in range(1, int(observed)):
        term *= expected / k
        cdf += term
    return max(0.0, min(1.0, 1-cdf))


def add_td_sustainability(players, pbp, model):
    result = players.copy()
    events = touchdown_events(pbp)
    by_player = {pid: group for pid, group in events.groupby("player_id")}
    historical = model.get("touchdown_baselines") if model else None
    fields = ["offensive_tds", "td_points_share", "td_free_ppr_per_game", "red_zone_touches",
              "red_zone_tds", "red_zone_td_conversion", "historical_red_zone_td_conversion",
              "expected_offensive_tds", "excess_td_ppr_per_game", "td_normalized_ppr_per_game", "td_rarity_tail"]
    for field in fields:
        result[field] = float("nan")
    result["td_sustainability"] = "historical baseline unavailable"
    for idx, r in result.iterrows():
        td_count = r.passing_tds+r.rushing_tds+r.receiving_tds
        td_points = 4*r.passing_tds+6*(r.rushing_tds+r.receiving_tds)
        result.loc[idx, "offensive_tds"] = td_count
        result.loc[idx, "td_points_share"] = td_points/r.fantasy_points_ppr if r.fantasy_points_ppr > 0 else 0
        result.loc[idx, "td_free_ppr_per_game"] = (r.fantasy_points_ppr-td_points)/r.team_games
        pe = by_player.get(r.player_id, events.iloc[:0])
        rz_touches = pe.loc[pe.zone.ne("outside20") & pe.role.ne("pass") & pe.touch.eq(1)]
        touches, rz_tds = len(rz_touches), int(rz_touches.td.sum())
        result.loc[idx, "red_zone_touches"] = touches
        result.loc[idx, "red_zone_tds"] = rz_tds
        result.loc[idx, "red_zone_td_conversion"] = rz_tds/touches if touches else float("nan")
        if not historical:
            continue
        expected_tds, expected_points = 0.0, 0.0
        for (role, zone), count in pe.groupby(["role", "zone"]).size().items():
            for key in (f"{r.position}|{role}|{zone}", f"{r.position}|{role}", role):
                baseline = historical["groups"].get(key)
                if baseline and baseline["opportunities"] >= historical["minimum_rate_opportunities"]:
                    break
            else:
                raise ValueError(f"No supported historical TD baseline for {r.position}/{role}.")
            expected = count*baseline["td_rate"]
            expected_tds += expected
            expected_points += expected*(4 if role == "pass" else 6)
        excess = (td_points-expected_points)/r.team_games
        rarity = poisson_upper_tail(td_count, expected_tds)
        result.loc[idx, "expected_offensive_tds"] = expected_tds
        result.loc[idx, "excess_td_ppr_per_game"] = excess
        result.loc[idx, "td_normalized_ppr_per_game"] = (r.fantasy_points_ppr-td_points+expected_points)/r.team_games
        result.loc[idx, "td_rarity_tail"] = rarity
        conversion = historical["red_zone_touch_conversion"].get(r.position)
        result.loc[idx, "historical_red_zone_td_conversion"] = conversion["rate"] if conversion else float("nan")
        result.loc[idx, "td_sustainability"] = ("Unusually high TD scoring" if td_count >= 2 and rarity < .05 and excess >= 1
            else "TD-heavy; watch for regression" if td_count >= 2 and excess >= 2
            else "No elevated TD signal")
    return result


def add_confidence(players, model, season, week, recent_games, schedule):
    result = players.copy()
    metadata = {"available": False, "reason": "No historical confidence model loaded."}
    fields = ["confidence_pct", "confidence_sample_size", "ppr_lower_80", "ppr_upper_80"]
    for field in fields:
        result[field] = float("nan")
    result["confidence_group"] = ""
    if model is None:
        return result, metadata
    if model.get("model_version") != "workload_v1" or model.get("recent_games") != recent_games:
        raise ValueError("Confidence calibration does not match this model or --recent-games.")
    if max(model["calibration_seasons"]) >= season:
        raise ValueError("Confidence model contains the forecast season or later data. Use earlier calibration seasons.")
    end_week = int(schedule.loc[(schedule.season == season) & (schedule.game_type == "REG"), "week"].max())
    for idx, r in result.iterrows():
        if week < 2 or week + 4 > end_week:
            continue  # Cannot promise a complete four-calendar-week horizon at season end.
        features = confidence_features(r.position, week, r.projected_ppr_per_game, r.last_stat_week)
        key, group = calibration_group(model, features, 4)
        if not group:
            continue
        result.loc[idx, "confidence_pct"] = group["confidence_pct"]
        result.loc[idx, "confidence_sample_size"] = group["sample_size"]
        result.loc[idx, "ppr_lower_80"] = r.projected_ppr_per_game + group["residual_q10"]
        result.loc[idx, "ppr_upper_80"] = r.projected_ppr_per_game + group["residual_q90"]
        result.loc[idx, "confidence_group"] = key
    metadata = {"available": True, "horizon_calendar_weeks": 4, "tolerance_ppr_per_game": 5,
                "meaning": "Historical rate that next-four-week average PPR per scheduled team game is within +/-5 of the projection; not rank correctness.",
                "calibration_seasons": model["calibration_seasons"],
                "evaluation_seasons": model["evaluation_seasons"],
                "minimum_group_size": model["minimum_group_size"],
                "injury_filter": model.get("injury_filter", {"enabled": False}),
                "evaluation": model["evaluation_summary"],
                "range": "Empirical 10th-90th percentile residual range; 80% target coverage, not guaranteed.",
                "caveat": "Forecast windows overlap and players repeat; sample counts are not independent trials. When injury seasons are excluded, confidence is conditional on no documented injury absence over the whole season, not an unconditional live forecast probability."}
    return result, metadata


def build_forecast_history(seasons, cache, recent_games):
    schedule_path = download(SCHEDULE_URL, cache / "schedules.csv")
    schedule = normalize_team_columns(pd.read_csv(schedule_path, low_memory=False))
    all_rows = []
    empty_pbp = pd.DataFrame(columns=["posteam", "yardline_100", "receiver_player_id", "rusher_player_id"])
    for season in seasons:
        path = download(f"{BASE}/stats_player/stats_player_week_{season}.csv", cache / f"stats_{season}.csv")
        stats = normalize_team_columns(pd.read_csv(path, low_memory=False))
        required = {"team", "game_id", "player_id", "player_display_name", "position", "week", "season_type", *METRICS}
        if required - set(stats):
            raise ValueError(f"Historical schema missing fields in {season}: {sorted(required-set(stats))}")
        games = completed_games(schedule, season, 18)
        planned = schedule.loc[(schedule.season == season) & (schedule.game_type == "REG")]
        if games.empty or len(games) != len(planned):
            raise ValueError(f"Season {season} is incomplete; use completed historical seasons only.")
        if set(games.game_id) - set(stats.game_id):
            raise ValueError(f"Historical player statistics omit completed games in {season}.")
        stats = stats.loc[stats.game_id.isin(games.game_id) & stats.season_type.eq("REG")].copy()
        if stats.duplicated(["player_id", "game_id"]).any():
            raise ValueError(f"Duplicate historical player/game rows in {season}.")
        stats[METRICS] = stats[METRICS].apply(pd.to_numeric, errors="coerce").fillna(0)
        end_week = int(games.week.max())
        team_game_rows = pd.concat([games[["week", "home_team"]].rename(columns={"home_team": "team"}),
                                    games[["week", "away_team"]].rename(columns={"away_team": "team"})])
        for cutoff in range(2, 15):
            observed = stats.loc[stats.week <= cutoff]
            past_games = games.loc[games.week <= cutoff]
            predictions = project_players(player_usage(observed, empty_pbp, past_games, recent_games), observed)
            for horizon in range(1, 5):
                if cutoff + horizon > end_week:
                    continue
                future_stats = stats.loc[(stats.week > cutoff) & (stats.week <= cutoff + horizon)]
                actual = future_stats.groupby("player_id").fantasy_points_ppr.sum()
                future_games = team_game_rows.loc[(team_game_rows.week > cutoff) &
                                                 (team_game_rows.week <= cutoff + horizon)].groupby("team").size()
                for r in predictions.itertuples():
                    n = int(future_games.get(r.team, 0))
                    if n == 0:
                        continue
                    realized = float(actual.get(r.player_id, 0)) / n
                    features = confidence_features(r.position, cutoff, r.projected_ppr_per_game, r.last_stat_week)
                    all_rows.append({"season": season, "cutoff": cutoff, "horizon": horizon,
                        "player_id": r.player_id, "player": r.player, "position": r.position,
                        "stage": features[1], "prediction_band": features[2], "activity": features[3],
                        "team": r.team, "scheduled_games": n,
                        "prediction": r.projected_ppr_per_game, "actual": realized,
                        "baseline": r.ppr_per_team_game,
                        "residual": realized-r.projected_ppr_per_game})
            print(f"Backtest {season}, cutoff week {cutoff}: {len(predictions)} players", flush=True)
    return pd.DataFrame(all_rows)


def backtest(cache, out, calibration_seasons, evaluation_seasons, recent_games, history_file=None, exclude_injuries=True):
    if not calibration_seasons or not evaluation_seasons or max(calibration_seasons) >= min(evaluation_seasons):
        raise ValueError("Calibration seasons must be strictly earlier than all evaluation seasons.")
    out.mkdir(parents=True, exist_ok=True)
    records_path = out / "forecast_history.csv"
    seasons = sorted(set(calibration_seasons + evaluation_seasons))
    if history_file:
        source_model = json.loads((history_file.parent / "confidence_model.json").read_text(encoding="utf-8"))
        if source_model.get("recent_games") != recent_games or source_model.get("injury_filter", {}).get("enabled"):
            raise ValueError("--history-file must contain unfiltered forecasts with the same --recent-games.")
        records = pd.read_csv(history_file)
        if set(records.season.unique()) != set(seasons):
            raise ValueError("--history-file does not cover the requested historical seasons.")
    else:
        records = build_forecast_history(seasons, cache, recent_games)
    exclusions = pd.DataFrame(columns=["season", "player_id"])
    injury_filter = {"enabled": exclude_injuries}
    if exclude_injuries:
        schedule = normalize_team_columns(pd.read_csv(cache / "schedules.csv", low_memory=False))
        exclusions, injury_coverage = injury_season_exclusions(seasons, cache, schedule)
        flagged = exclusions[["season", "player_id"]].drop_duplicates().assign(injury_season=True)
        marked = records.merge(flagged, on=["season", "player_id"], how="left")
        excluded = marked.loc[marked.injury_season.eq(True)]
        records = marked.loc[~marked.injury_season.eq(True)].drop(columns="injury_season")
        exclusions.to_csv(out / "injury_exclusions.csv", index=False)
        injury_filter.update({"rule": "Exclude the entire player season after any documented injury/illness absence in a scheduled regular-season game.",
            "evidence": "Medical injury report Out with no participation-stat row; Questionable/Doubtful plus inactive roster with no stat row; medical reserve (IR/PUP/NFI) with no stat row. Rest, personal matters and suspension alone do not qualify.",
            "excluded_forecast_windows": len(excluded),
            "excluded_forecast_player_seasons": len(excluded[["season", "player_id"]].drop_duplicates()),
            "coverage": injury_coverage,
            "interpretation": "Retrospective healthy-season conditioning: future full-season injury outcomes determine eligibility. Confidence excludes future injury risk and can be more optimistic than an unconditional forecast. Unrecorded injury absences may remain."})
        print(f"Excluded {len(excluded):,} forecast windows from {injury_filter['excluded_forecast_player_seasons']} injury-affected player seasons.", flush=True)
    records.to_csv(records_path, index=False, float_format="%.6f")
    calibration = records.loc[records.season.isin(calibration_seasons)]
    evaluation = records.loc[records.season.isin(evaluation_seasons)].copy()
    model = {"schema_version": 1, "model_version": "workload_v1", "recent_games": recent_games,
             "calibration_seasons": calibration_seasons, "evaluation_seasons": evaluation_seasons,
             "minimum_group_size": 150, "tolerance": 5, "groups": {}, "injury_filter": injury_filter}
    model["touchdown_baselines"] = touchdown_baselines(calibration_seasons, cache, exclusions)
    grouping = ["position", "stage", "prediction_band", "activity"]
    for level in (1, 2, 3, 4):
        for keys, group in calibration.groupby(["horizon", *grouping[:level]]):
            horizon, *features = keys
            key = calibration_key(features, int(horizon), level)
            model["groups"][key] = {"sample_size": len(group),
                "confidence_pct": float(100 * group.residual.abs().le(5).mean()),
                "residual_q10": float(group.residual.quantile(.1)),
                "residual_q90": float(group.residual.quantile(.9))}
    confidences, lower, upper = [], [], []
    for r in evaluation.itertuples():
        _, group = calibration_group(model, (r.position, r.stage, r.prediction_band, r.activity), r.horizon)
        confidences.append(group["confidence_pct"] / 100 if group else float("nan"))
        lower.append(r.prediction + group["residual_q10"] if group else float("nan"))
        upper.append(r.prediction + group["residual_q90"] if group else float("nan"))
    evaluation["confidence_probability"] = confidences
    evaluation["lower_80"], evaluation["upper_80"] = lower, upper
    evaluation["hit"] = evaluation.residual.abs().le(5)
    evaluation["covered_80"] = evaluation.actual.ge(evaluation.lower_80) & evaluation.actual.le(evaluation.upper_80)
    summary_rows = []
    for (position, horizon), group in evaluation.groupby(["position", "horizon"]):
        for cohort, cohort_data in [("all_observed_players", group), ("projected_5plus", group.loc[group.prediction >= 5])]:
            if cohort_data.empty:
                continue
            summary_rows.append({"position": position, "horizon": int(horizon), "cohort": cohort,
                "forecast_windows": len(cohort_data), "mae_ppr_per_game": float(cohort_data.residual.abs().mean()),
                "rmse_ppr_per_game": float((cohort_data.residual.pow(2).mean())**.5),
                "prediction_bias": float(-cohort_data.residual.mean()),
                "baseline_mae": float((cohort_data.actual-cohort_data.baseline).abs().mean()),
                "predicted_hit_pct": float(100*cohort_data.confidence_probability.mean()),
                "observed_hit_pct": float(100*cohort_data.hit.mean()),
                "interval_coverage_pct": float(100*cohort_data.covered_80.mean())})
    summary = pd.DataFrame(summary_rows)
    model["evaluation_summary"] = json.loads(summary.to_json(orient="records"))
    model["forecast_windows"] = {"calibration": len(calibration), "evaluation": len(evaluation)}
    model["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    model["methodology"] = "Frozen workload_v1; cutoffs 2-14; horizons 1-4 calendar weeks; players observed at cutoff. " + (
        "Entire player seasons with any documented injury/illness absence are retrospectively excluded from calibration and evaluation. This intentionally conditions on future full-season health, so confidence is not an unconditional injury-inclusive probability. " if exclude_injuries else
        "Injury seasons are retained. ") + "Other missing future stats count as zero. Actual total points divided by scheduled games for team at cutoff. Trades may alter actual opportunities. Historical corrected data, not archived real-time snapshots. Repeated players and overlapping windows are correlated. TD benchmarks use calibration seasons only, with the same injury-season filter. No ranks or tiers are backtested."
    (out / "confidence_model.json").write_text(json.dumps(model, indent=2), encoding="utf-8")
    summary.to_csv(out / "validation_summary.csv", index=False, float_format="%.4f")
    evaluation.to_csv(out / "held_out_predictions.csv", index=False, float_format="%.5f")
    evaluation["confidence_band"] = pd.cut(evaluation.confidence_probability, [0,.2,.4,.6,.8,1], include_lowest=True)
    reliability = evaluation.groupby(["horizon", "confidence_band"], observed=True).agg(
        forecast_windows=("hit", "size"), predicted_probability=("confidence_probability", "mean"),
        observed_hit_rate=("hit", "mean"))
    reliability.to_csv(out / "confidence_reliability.csv", float_format="%.5f")
    text = f"""# Historical projection validation

Calibration seasons: {calibration_seasons}. Held-out evaluation seasons: {evaluation_seasons}.

Confidence means the empirical historical rate of next-window average PPR being within +/-5 points per scheduled team game of the estimate. The player badge uses four calendar weeks. It does not measure exact ranking accuracy. Similar forecasts are grouped by position, cutoff stage, prediction level and recent activity; groups below 150 forecast windows fall back to broader cohorts. The displayed range uses the historical 10th and 90th percentile residuals.

Calibration windows: {len(calibration):,}. Held-out windows: {len(evaluation):,}.

Held-out errors below are in PPR per scheduled team game. Prediction bias is predicted minus actual. The baseline repeats season-to-date PPR per team game. Low-use players can have high confidence because zero or low production is easier to predict; use the projected_5plus cohort to assess fantasy-relevant accuracy.

```csv
{summary.to_csv(index=False, float_format='%.3f')}
```

{model['methodology']}

The current production model remains unchanged; validation may show that the simpler baseline performs better. Nominal 80% intervals and historical hit percentages are estimates and can drift in new seasons. Counts are forecast windows, not independent players or trials. Injury filter: {injury_filter}.

Data: https://github.com/nflverse/nflverse-data/releases/tag/stats_player and https://github.com/nflverse/nfldata/blob/master/data/games.csv
"""
    (out / "validation_report.md").write_text(text, encoding="utf-8")
    report_html = ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Historical Fantasy Validation</title><style>body{font:15px system-ui;margin:32px;background:#0f172a;color:#e2e8f0}"
        "p{max-width:1000px;line-height:1.7}table{border-collapse:collapse;white-space:nowrap;font-size:12px}"
        "th,td{padding:10px;border-bottom:1px solid #334155;text-align:right}a{color:#7dd3fc}.scroll{overflow:auto}</style>"
        "<h1>Historical fantasy projection validation</h1><p>Calibrated on " + html.escape(str(calibration_seasons)) +
        "; evaluated on held-out " + html.escape(str(evaluation_seasons)) + ".</p><p>Confidence means the historical rate "
        "of average PPR over the next four calendar weeks falling within ±5 points per scheduled team game of the forecast. "
        "It does not mean exact rank correctness. Calibration groups include position, season stage, projected scoring level "
        "and recent activity, falling back to broader groups when fewer than 150 forecast windows are available.</p>"
        f"<p>{len(calibration):,} calibration windows; {len(evaluation):,} held-out windows. These overlap and repeat players.</p>"
        "<h2>Four-week results for players projected at least 5 PPR/game</h2><div class='scroll'>" +
        summary.loc[(summary.horizon == 4) & summary.cohort.eq("projected_5plus")].to_html(index=False, float_format=lambda x: f"{x:.2f}") +
        "</div><p>MAE is average absolute error in PPR per scheduled team game. Bias is predicted minus actual. "
        "The baseline repeats the player's season-to-date PPR per team game. Other missing appearances count as zero; "
        "the healthy-season cohort is selected using full-season injury outcomes. The 80% range uses empirical 10th–90th percentile residuals.</p>"
        "<h2>All horizons and cohorts</h2><div class='scroll'>" + summary.to_html(index=False, float_format=lambda x: f"{x:.2f}") +
        "</div><h2>Probability calibration</h2><div class='scroll'>" + reliability.reset_index().to_html(index=False, float_format=lambda x: f"{x:.3f}") +
        "</div><p>Confidence probabilities and hit rates in this table are fractions. High confidence for low-output players "
        "can reflect how easily near-zero production is predicted.</p><p>" + html.escape(model["methodology"]) +
        "</p><p>The model was frozen before evaluation. Historical percentages may drift in a new season and 80% coverage "
        "is a target rather than a guarantee.</p><p><a href='validation_summary.csv'>Summary CSV</a> · "
        "<a href='held_out_predictions.csv'>Held-out predictions</a> · <a href='confidence_model.json'>Confidence calibration</a> · "
        "<a href='https://github.com/nflverse/nflverse-data/releases/tag/stats_player'>nflverse player statistics</a></p></html>")
    (out / "validation_report.html").write_text(report_html, encoding="utf-8")
    print(summary.loc[(summary.horizon == 4) & summary.cohort.eq("projected_5plus")].to_string(index=False))
    return model


def write_report(out, teams, players, trend, future, metadata):
    out.mkdir(parents=True, exist_ok=True)
    for name, frame in [("team_rankings", teams), ("player_usage_projections", players),
                        ("offense_rank_by_week", trend), ("future_week_projections", future)]:
        frame.to_csv(out / f"{name}.csv", index=False, float_format="%.5f")
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    export_columns = ["player_id", "player", "position", "team", "position_rank",
                      "projected_ppr_per_game", "ppr_per_team_game", "projected_targets",
                      "projected_carries", "target_share", "recent_target_share", "carry_share",
                      "recent_carry_share", "red_zone_targets", "red_zone_carries", "last_stat_week",
                      "confidence_pct", "confidence_sample_size", "ppr_lower_80", "ppr_upper_80", "confidence_group",
                      "offensive_tds", "td_points_share", "td_free_ppr_per_game", "red_zone_touches", "red_zone_tds",
                      "red_zone_td_conversion", "historical_red_zone_td_conversion", "expected_offensive_tds",
                      "excess_td_ppr_per_game", "td_normalized_ppr_per_game", "td_sustainability"]
    payload = {"schema_version": 1, "metadata": metadata,
               "players": json.loads(players[export_columns].to_json(orient="records")),
               "teams": json.loads(teams.to_json(orient="records"))}
    (out / "fantasy_lab_estimates.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    columns = ["player", "position", "team", "projected_ppr_per_game", "position_rank",
               "confidence_pct", "confidence_sample_size", "ppr_lower_80", "ppr_upper_80",
               "offensive_tds", "red_zone_touches", "red_zone_tds", "red_zone_td_conversion",
               "historical_red_zone_td_conversion", "td_points_share", "td_free_ppr_per_game",
               "expected_offensive_tds", "td_normalized_ppr_per_game", "td_sustainability",
               "ppr_per_team_game", "target_share", "recent_target_share", "carry_share",
               "recent_carry_share", "red_zone_targets", "red_zone_carries", "last_stat_week"]
    table = players[columns].copy()
    for c in table.columns:
        if "share" in c:
            table[c] = table[c].map(lambda x: f"{x:.1%}")
    dots = []
    selected = players.loc[players.position.isin(["RB", "WR", "TE"])].head(75)
    xmax = max(1, (selected.projected_targets + selected.projected_carries).max())
    ymax = max(1, selected.projected_ppr_per_game.max())
    colors = {"RB": "#38bdf8", "WR": "#fbbf24", "TE": "#c084fc"}
    for r in selected.itertuples():
        x = 60 + 800 * (r.projected_targets + r.projected_carries) / xmax
        y = 330 - 280 * r.projected_ppr_per_game / ymax
        title = html.escape(f"{r.player} ({r.team} {r.position}): "
                            f"{r.projected_ppr_per_game:.1f} projected PPR/game")
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{colors[r.position]}">'
                    f'<title>{title}</title></circle>')
    chart = ('<svg viewBox="0 0 920 390" role="img" aria-label="Usage versus projected PPR">'
             '<path d="M60 40V330H880" stroke="#aaa" fill="none"/>' + ''.join(dots) +
             f'<text x="60" y="355">0</text><text x="835" y="355">{xmax:.1f}</text>'
             f'<text x="15" y="50">{ymax:.1f}</text>'
             '<text x="320" y="380">Projected carries + targets per game</text>'
             '<text x="60" y="25">Projected PPR per game • RB blue / WR gold / TE purple</text></svg>')
    content = f'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>NFL Fantasy Report</title>
<style>body{{font:15px system-ui;background:#0f172a;color:#e2e8f0;margin:30px}}
h1,h2{{color:#fff}}p{{max-width:1000px;line-height:1.6}}a{{color:#7dd3fc}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;white-space:nowrap;font-size:13px}}
th,td{{padding:8px 12px;border-bottom:1px solid #334155;text-align:right}}
th{{background:#1e293b}}svg{{width:100%;max-width:1000px}}text{{fill:#e2e8f0;font:14px system-ui}}</style>
<h1>NFL full PPR • {metadata['season']} through week {metadata['through_week']}</h1>
<p>Offense ranking: 60% EPA/play percentile, 25% success-rate percentile, 15% yards/play percentile.
Kneels, spikes and two-point attempts excluded. Scoreboard points include defense and special teams.
Shares use all completed team games; byes do not dilute per-game volume.</p>
<h2>Team offense rankings</h2><div class="scroll">{teams.to_html(index=False, float_format=lambda x: f'{x:.3f}')}</div>
<h2>Workload → estimated production</h2>{chart}
<p>Hover over a dot for the player. Recent usage receives 65% weight; season usage receives 35%.
Efficiency is shrunk toward position averages using only data through the cutoff.
These are workload estimates, assuming the same team, role and availability.
No opponent, injury or depth-chart adjustment. Projection scoring: 1 point/reception, 0.1/receiving
or rushing yard, 6/rushing or receiving TD, 0.04/passing yard, 4/passing TD, −2/interception.
Projected fumbles, two-point conversions and unusual scoring are omitted.
Historical PPR uses nflverse's fantasy_points_ppr.</p>
<h2>Player usage and projections</h2><div class="scroll">{table.to_html(index=False, float_format=lambda x: f'{x:.2f}')}</div>
<p>Confidence % is the historical rate of next-four-week average PPR falling within ±5 points
per scheduled team game of the forecast, not exact rank correctness. Sample size counts historical
forecast windows, which overlap and repeat players. The lower/upper columns are an empirical
80% prediction range. Missing confidence means calibration is unavailable for this forecast.
Calibration details: {html.escape(json.dumps(metadata.get('confidence', {})))}</p>
<p>With injury-season exclusion enabled, confidence is conditional on no documented injury/illness
absence anywhere in the full historical season; future injury risk is excluded. TD-normalized scoring
replaces actual offensive touchdown points with historical expected TD points for the player's
opportunities. Expectations use position, pass/target/carry type and pre-play field zone. Red-zone
touches mean carries plus completed receptions, while targets also include incomplete passes.
Passing touchdowns use four points and rushing/receiving touchdowns use six. The unusually-high
TD flag is an approximate Poisson tail below 5%, at least two TDs and at least one excess PPR point
per team game; it is not proof of an unprecedented record or a guaranteed decline.</p>
<h2>Downloads</h2><p><a href="team_rankings.csv">Teams</a> ·
<a href="player_usage_projections.csv">Player usage</a> ·
<a href="offense_rank_by_week.csv">Rank history by week</a> ·
<a href="future_week_projections.csv">Future weekly estimates</a> ·
<a href="metadata.json">Source and cutoff details</a></p>
<p>Red zone: inside opponent's 20-yard line. Air-yard share can be negative or exceed 100%.
Stat games are games with a source row; they are not proof of snap participation.
Players with no recorded opportunities are absent. Traded players use their latest observed team;
future roster changes are unknown. Missing upcoming schedule entries are labeled explicitly.
Data: <a href="https://github.com/nflverse/nflverse-data">nflverse</a>.</p></html>'''
    (out / "report.html").write_text(content, encoding="utf-8")


def update_lab(template: Path, output: Path, payload_path: Path):
    """Refresh embedded estimates in a combined Lab, including CSP script hashes."""
    source = template.read_text(encoding="utf-8")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")
    pattern = r"(/\* FANTASY_ESTIMATES_START \*/).*?(/\* FANTASY_ESTIMATES_END \*/)"
    source, count = re.subn(pattern, lambda m: m[1] + "\nlet fantasyEstimatesPayload = " +
                           encoded + ";\n" + m[2], source, flags=re.S)
    if count != 1:
        raise ValueError("--lab-template must be a combined Fantasy Lab with one estimates marker.")
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", source, re.S)
    hashes = " ".join("'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() +
                      "'" for s in scripts)
    source = re.sub(r"script-src-elem [^;]*;", "script-src-elem " + hashes + ";", source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")
    print(f"Combined Fantasy Lab: {output.resolve()}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--season", type=int)
    parser.add_argument("--week", type=int, help="Regular-season calendar week cutoff (1–18)")
    parser.add_argument("--recent-games", type=int, default=3)
    parser.add_argument("--horizon", type=int, default=4, help="Upcoming calendar weeks (byes yield zero)")
    parser.add_argument("--cache-dir", type=Path, default=Path(__file__).resolve().parent / ".fantasy_cache")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "fantasy_output")
    parser.add_argument("--refresh", action="store_true", help="Redownload cached source data")
    parser.add_argument("--lab-template", type=Path, help="Combined Lab HTML to update with these estimates")
    parser.add_argument("--lab-output", type=Path, help="Destination HTML; default: output-dir/Fantasy Lab Combined.html")
    parser.add_argument("--backtest", action="store_true", help="Calibrate on 2018–2023 and evaluate on 2024–2025")
    parser.add_argument("--calibration-seasons", type=int, nargs="+", default=list(range(2018, 2024)))
    parser.add_argument("--evaluation-seasons", type=int, nargs="+", default=[2024, 2025])
    parser.add_argument("--confidence-model", type=Path,
                        default=Path(__file__).resolve().parent / "confidence_model.json")
    parser.add_argument("--history-file", type=Path, help="Reuse previously audited, unfiltered historical forecasts")
    parser.add_argument("--include-injury-seasons", action="store_true", help="Disable the default injury-season exclusion")
    args = parser.parse_args(argv)
    if args.recent_games < 1 or not 1 <= args.horizon <= 18:
        parser.error("--recent-games must be positive; --horizon must be 1–18.")
    if args.backtest:
        calibrated = backtest(args.cache_dir, args.output_dir, args.calibration_seasons, args.evaluation_seasons, args.recent_games,
                              args.history_file, not args.include_injury_seasons)
        args.confidence_model.parent.mkdir(parents=True, exist_ok=True)
        args.confidence_model.write_text(json.dumps(calibrated, indent=2), encoding="utf-8")
        return 0
    if args.season is None or args.week is None or not 1999 <= args.season <= datetime.now().year or not 1 <= args.week <= 18:
        parser.error("Use --season from 1999 through the current year and --week 1–18.")
    stats, pbp, schedule, sources = load_data(args.season, args.cache_dir, args.refresh)
    stats, pbp, games = prepare(stats, pbp, schedule, args.season, args.week)
    teams = team_rankings(pbp, games)
    usage = player_usage(stats, pbp, games, args.recent_games)
    if usage.empty:
        raise ValueError("No QB/RB/WR/TE statistics available at this cutoff.")
    players = project_players(usage, stats)
    model = json.loads(args.confidence_model.read_text(encoding="utf-8")) if args.confidence_model.exists() else None
    players, confidence = add_confidence(players, model, args.season, args.week, args.recent_games, schedule)
    players = add_td_sustainability(players, pbp, model)
    trend = pd.concat([team_rankings(pbp.loc[pbp.week <= w], games.loc[games.week <= w]).assign(through_week=w)
                       for w in sorted(games.week.unique())], ignore_index=True)
    future = future_weeks(players, schedule, args.season, args.week, args.horizon)
    pending = schedule.loc[(schedule.season == args.season) & (schedule.game_type == "REG") &
                           (schedule.week <= args.week) &
                           (schedule.home_score.isna() | schedule.away_score.isna())]
    if len(pending):
        print(f"Note: {len(pending)} scheduled games through the cutoff are not completed in the source.")
    metadata = {"season": args.season, "through_week": args.week,
                "latest_completed_week": int(games.week.max()), "recent_games": args.recent_games,
                "horizon": args.horizon, "completed_games": len(games),
                "uncompleted_games_through_cutoff": len(pending),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(), "sources": sources,
                "projection_type": "workload heuristic; full PPR; see report limitations", "confidence": confidence}
    write_report(args.output_dir, teams, players, trend, future, metadata)
    if args.lab_template:
        update_lab(args.lab_template, args.lab_output or args.output_dir / "Fantasy Lab Combined.html",
                   args.output_dir / "fantasy_lab_estimates.json")
    print(teams[["offense_rank", "team", "epa_per_play", "plays_per_game"]].head(10).to_string(index=False))
    print(players[["player", "position", "team", "projected_ppr_per_game"]].head(15).to_string(index=False))
    print(f"Report: {(args.output_dir / 'report.html').resolve()}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
