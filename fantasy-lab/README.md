# NFL fantasy analysis

Open **Fantasy Lab Combined.html** for the standalone dashboard. Run the commands below from this `fantasy-lab` folder to refresh the NFL full-PPR forecasts.

Install the one dependency, then run from a terminal:

```powershell
python -m pip install pandas
python fantasy.py --season 2026 --week 4 --refresh
```

Change `--week` to the calendar week you want to analyze. The default recent window is the last three completed team games. Change it with `--recent-games 3`; use `--horizon 4` for the next four calendar weeks.

The program downloads public nflverse weekly player statistics, play-by-play, and schedules. It caches downloads beside the script. Use `--refresh` when updating the season; without it, the cached data are reused. The first download is larger because play-by-play covers the entire available season, but the analysis strictly filters to completed games through your chosen week. Missing source coverage causes a clear error.

Open `fantasy_output/report.html` beside the script for the report. It also writes four CSV files and source metadata. `--cache-dir` and `--output-dir` can override these locations.

The saved `2026_week4` folder contains the requested report with historical confidence.

## Combined Fantasy Lab

Open `Fantasy Lab Combined.html` in this folder. It includes your 2026 week 4 estimates, preserves the original league and ranking tools, and adds a production estimates panel.

To load your own Sleeper rosters, paste your numeric league ID or full Sleeper league URL into **Connect your Sleeper league** at the top and click **Load Sleeper league** (or press Enter). Select your team afterward. The page shows loading progress and any request error, then matches your roster to the rankings and estimates.

The default combined value is 65% ranking-derived value and 35% estimate-derived value. Estimate positional ranks use the same position-specific value curves as the existing rankings, so both components have matching units. The slider changes the blend; 0% retains ranking values and 100% uses estimate-derived values for matched, ranked players. Your manual overrides always win. Unmatched players keep their original ranking values. NFL offense rankings provide context and are not added a second time to projections. The blend changes lineup and trade calculations. Changing estimates or blend weight clears saved offers because those offers contain previous values.

For future weeks, run `fantasy.py` normally. It now writes `fantasy_lab_estimates.json` alongside its reports. In the combined HTML, choose **Load estimates JSON** and select that file. Imports are validated and saved in the browser when storage is available. The cutoff is shown above the usage table.

You can also generate a refreshed standalone HTML in one command:

```powershell
python fantasy.py --season 2026 --week 5 --refresh --lab-template "Fantasy Lab Combined.html" --lab-output "Fantasy Lab Combined.html"
```

Use `--lab-template` only with the combined HTML. The Python program updates embedded estimates and script integrity hashes. It preserves the rest of the dashboard. Player matching normalizes punctuation and suffixes, requires the same position, and rejects ambiguous matches. Browser preview was blocked by local-file navigation policy; direct script checks verified the integration and calculations.

Team offense score uses league percentiles: 60% EPA per play, 25% success rate (EPA greater than zero), 15% yards per play. It excludes kneels, spikes, and two-point attempts. Scoreboard points include defense and special teams and do not enter the offense score. The weekly ranking-history CSV recomputes the ranking at each earlier cutoff.

Player usage includes target share, carry share, passing-attempt share, air-yard share, recent changes, red-zone targets and carries, and projected opportunity counts. Shares are fractions in the CSV and percentages in the report. No snap-share or route-participation data are included.

Projected carries, targets and pass attempts combine 65% recent team-game usage with 35% full-season usage. The efficiency model shrinks player yardage, catch and touchdown rates toward position averages observed through the cutoff. Priors range from 30 receiving opportunities to 150 passing opportunities, depending on the metric. It then applies full PPR scoring to these projected opportunities. This is an interpretable workload heuristic, now historically backtested without tuning its production formula on evaluation seasons.

Upcoming weekly projections use the same per-game estimate for scheduled games and zero for byes. Unknown schedules have blank estimates. They do not adjust for opponent defenses, injuries, trades after the cutoff or depth-chart changes. Fumbles, two-point conversions and unusual scoring events are omitted from projected PPR; historical PPR is the source's `fantasy_points_ppr`. A missing stat row counts as zero opportunity in team-game averages. A traded player's latest observed team controls the projection; their previous-team usage is excluded.

## Historical confidence

The percentage next to a player rank means the historical rate at which next-four-week average PPR per scheduled team game was within **±5 points/game** of the forecast. It is not exact rank correctness, trade fairness or injury probability. Manual trade-value changes do not change this production confidence.

The model was calibrated using 2018–2023, then evaluated on completely separate 2024–2025 seasons. Each season was forecast at cutoffs 2–14 for horizons 1–4 calendar weeks, using only stats through that cutoff. At your request, entire historical player seasons are now excluded if the player missed any scheduled regular-season game due to a documented injury/illness or medical reserve designation. Other missing appearances remain zero. Historical final/corrected data are used; these are not archived real-time feed snapshots.

This filter uses full-season outcomes to define the comparison cohort. Confidence is therefore conditional on a season without documented injury absences, and does not include future injury risk. It can be higher than an unconditional live probability. Rest, personal matters, suspensions and healthy scratches alone do not trigger the filter. Sources include weekly injury reports and medical reserve roster designations. Missing source coverage is rejected; unrecorded injuries may still remain. The exclusion list is provided in `healthy_season_validation/injury_exclusions.csv`.

Similar forecast cohorts use position, season stage, predicted scoring level and recent activity. Cohorts below 150 windows fall back to broader groups. The player table shows an empirical 80% PPR range using historical 10th–90th percentile forecast residuals. Counts are overlapping forecast windows with repeated players, not independent trials. Low-output players can have high confidence because near-zero production is easier to predict.

The current dashboard uses a four-calendar-week confidence horizon even if the forecast CSV's requested horizon differs. No confidence is shown before week 2 or when fewer than four calendar weeks remain. The calibration must precede the forecast season and match the recent-game window. Missing calibration produces blank confidence, never a fabricated percentage.

Keep `confidence_model.json` beside `fantasy.py` to apply the saved calibration to future weeks. The dashboard embeds the confidence results and remains shareable as one HTML file. The current historical report is in `healthy_season_validation/validation_report.html`, with errors, baseline comparison, confidence calibration and prediction-range coverage. Summary results and injury exclusions are included; run the backtest to regenerate full forecast-window audit files.

To reproduce the historical run:

```powershell
python fantasy.py --backtest
```

This downloads completed historical statistics, writes audit records in `fantasy_output`, and saves `confidence_model.json` beside the script. The production formula remains unchanged. Use `--calibration-seasons` and `--evaluation-seasons` to choose strictly chronological splits; `--recent-games` must match the setting used for live forecasts.

## Touchdown sustainability

The dashboard now flags scoring that is unusually touchdown-driven relative to opportunities. It shows observed PPR/game, scoring with offensive TD points removed, total offensive TDs, percentage of points from TDs, red-zone touches, red-zone TD conversion, the historical position conversion rate, expected TDs and TD-normalized PPR/game.

Red-zone touches are carries plus completed receptions, not targets. The expectation model includes carries, all receiving targets and QB passing attempts. Historical touchdown probabilities use position, opportunity type and field zone: inside the opponent's 5, from 6–20 yards, or outside the red zone. This separates strong goal-line workload from unusually high conversion or long-play TDs. Rates are calibrated on 2018–2023 seasons with the same injury exclusion.

TD-normalized scoring replaces actual offensive TD points with the expectation from those opportunities. Passing TDs contribute four points; rushing and receiving TDs contribute six. This is a sustainability diagnostic alongside the workload projection; it does not automatically overwrite your projections or manual values.

**Unusually high TD scoring** requires at least two TDs, at least one excess PPR point per team game, and an approximate Poisson upper-tail below 5%. **TD-heavy; watch for regression** requires at least two TDs and two excess PPR points/game. The Poisson indicator is approximate, not a calibrated probability of regression. An early spike is not proof of an unprecedented record, and genuine skill or game context can explain it.

## Verification

From this folder:

```powershell
python tests/verify_injuries_and_tds.py
node tests/verify_combined.cjs
```

Node is needed only for the dashboard checks. Download caches and generated output are excluded from Git.
