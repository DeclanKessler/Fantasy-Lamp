# Historical projection validation

Calibration seasons: [2018, 2019, 2020, 2021, 2022, 2023]. Held-out evaluation seasons: [2024, 2025].

Confidence means the empirical historical rate of next-window average PPR being within +/-5 points per scheduled team game of the estimate. The player badge uses four calendar weeks. It does not measure exact ranking accuracy. Similar forecasts are grouped by position, cutoff stage, prediction level and recent activity; groups below 150 forecast windows fall back to broader cohorts. The displayed range uses the historical 10th and 90th percentile residuals.

Calibration windows: 86,404. Held-out windows: 26,836.

Held-out errors below are in PPR per scheduled team game. Prediction bias is predicted minus actual. The baseline repeats season-to-date PPR per team game. Low-use players can have high confidence because zero or low production is easier to predict; use the projected_5plus cohort to assess fantasy-relevant accuracy.

```csv
position,horizon,cohort,forecast_windows,mae_ppr_per_game,rmse_ppr_per_game,prediction_bias,baseline_mae,predicted_hit_pct,observed_hit_pct,interval_coverage_pct

QB,1,all_observed_players,966,3.918,6.237,-0.166,4.088,69.263,70.083,77.640

QB,1,projected_5plus,465,6.603,8.309,-0.333,6.969,49.805,44.516,76.344

QB,2,all_observed_players,1054,3.353,5.200,-0.172,3.555,73.889,74.953,78.368

QB,2,projected_5plus,503,5.517,6.900,-0.284,5.898,57.944,52.286,76.143

QB,3,all_observed_players,1054,3.097,4.755,-0.244,3.309,77.033,76.755,80.740

QB,3,projected_5plus,503,4.899,6.175,-0.221,5.275,63.856,57.853,77.734

QB,4,all_observed_players,1054,3.039,4.665,-0.274,3.248,78.203,77.704,78.178

QB,4,projected_5plus,503,4.678,5.983,-0.080,5.020,66.616,61.233,72.962

RB,1,all_observed_players,1604,3.313,5.551,-0.292,3.293,77.750,76.995,82.107

RB,1,projected_5plus,581,6.428,8.322,-0.327,6.363,52.737,48.537,75.043

RB,2,all_observed_players,1744,2.749,4.496,-0.318,2.775,81.323,81.651,81.881

RB,2,projected_5plus,627,5.101,6.638,-0.302,5.143,62.071,59.330,76.396

RB,3,all_observed_players,1744,2.429,3.857,-0.326,2.468,82.989,84.518,83.200

RB,3,projected_5plus,627,4.435,5.628,-0.283,4.467,66.286,64.753,77.193

RB,4,all_observed_players,1744,2.246,3.516,-0.337,2.317,84.030,86.353,83.200

RB,4,projected_5plus,627,4.004,5.062,-0.236,4.076,69.069,69.856,77.033

TE,1,all_observed_players,1383,2.572,4.277,-0.224,2.637,86.168,83.442,77.730

TE,1,projected_5plus,347,5.276,6.819,-0.223,5.361,68.665,53.026,62.824

TE,2,all_observed_players,1502,2.113,3.462,-0.216,2.167,88.392,88.482,81.358

TE,2,projected_5plus,377,4.262,5.516,-0.158,4.427,73.448,66.048,70.822

TE,3,all_observed_players,1502,1.896,3.025,-0.241,1.926,90.496,90.213,81.225

TE,3,projected_5plus,377,3.747,4.764,-0.164,3.862,79.785,70.557,69.496

TE,4,all_observed_players,1502,1.756,2.763,-0.244,1.795,92.718,91.678,81.158

TE,4,projected_5plus,377,3.408,4.359,-0.180,3.590,84.871,75.597,67.374

WR,1,all_observed_players,2345,3.423,5.428,-0.061,3.436,74.735,75.864,81.834

WR,1,projected_5plus,912,5.871,7.604,0.246,5.883,48.289,50.439,81.250

WR,2,all_observed_players,2546,2.832,4.343,-0.076,2.871,79.976,80.951,81.658

WR,2,projected_5plus,988,4.730,6.049,0.186,4.762,59.876,61.336,81.275

WR,3,all_observed_players,2546,2.551,3.847,-0.082,2.624,82.451,84.250,81.775

WR,3,projected_5plus,988,4.154,5.300,0.250,4.256,65.994,68.219,82.692

WR,4,all_observed_players,2546,2.421,3.607,-0.065,2.487,84.437,85.625,81.618

WR,4,projected_5plus,988,3.900,4.921,0.358,3.975,69.768,71.356,79.453


```

Frozen workload_v1; cutoffs 2-14; horizons 1-4 calendar weeks; players observed at cutoff. Entire player seasons with any documented injury/illness absence are retrospectively excluded from calibration and evaluation. This intentionally conditions on future full-season health, so confidence is not an unconditional injury-inclusive probability. Other missing future stats count as zero. Actual total points divided by scheduled games for team at cutoff. Trades may alter actual opportunities. Historical corrected data, not archived real-time snapshots. Repeated players and overlapping windows are correlated. TD benchmarks use calibration seasons only, with the same injury-season filter. No ranks or tiers are backtested.

The current production model remains unchanged; validation may show that the simpler baseline performs better. Nominal 80% intervals and historical hit percentages are estimates and can drift in new seasons. Counts are forecast windows, not independent players or trials. Injury filter: {'enabled': True, 'rule': 'Exclude the entire player season after any documented injury/illness absence in a scheduled regular-season game.', 'evidence': 'Medical injury report Out with no participation-stat row; Questionable/Doubtful plus inactive roster with no stat row; medical reserve (IR/PUP/NFI) with no stat row. Rest, personal matters and suspension alone do not qualify.', 'excluded_forecast_windows': 88749, 'excluded_forecast_player_seasons': 1900, 'coverage': [{'season': 2018, 'injury_rows': 4961, 'roster_rows': 50113, 'scheduled_team_weeks': 512, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2018.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2018.csv'}, {'season': 2019, 'injury_rows': 5202, 'roster_rows': 49561, 'scheduled_team_weeks': 512, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2019.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2019.csv'}, {'season': 2020, 'injury_rows': 5414, 'roster_rows': 41658, 'scheduled_team_weeks': 512, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2020.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2020.csv'}, {'season': 2021, 'injury_rows': 5348, 'roster_rows': 44539, 'scheduled_team_weeks': 544, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2021.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2021.csv'}, {'season': 2022, 'injury_rows': 5433, 'roster_rows': 43906, 'scheduled_team_weeks': 542, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2022.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2022.csv'}, {'season': 2023, 'injury_rows': 5451, 'roster_rows': 43545, 'scheduled_team_weeks': 544, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2023.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2023.csv'}, {'season': 2024, 'injury_rows': 5954, 'roster_rows': 44473, 'scheduled_team_weeks': 544, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2024.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2024.csv'}, {'season': 2025, 'injury_rows': 5783, 'roster_rows': 44697, 'scheduled_team_weeks': 544, 'injury_url': 'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv', 'roster_url': 'https://github.com/nflverse/nflverse-data/releases/download/weekly_rosters/roster_weekly_2025.csv'}], 'interpretation': 'Retrospective healthy-season conditioning: future full-season injury outcomes determine eligibility. Confidence excludes future injury risk and can be more optimistic than an unconditional forecast. Unrecorded injury absences may remain.'}.

Data: https://github.com/nflverse/nflverse-data/releases/tag/stats_player and https://github.com/nflverse/nfldata/blob/master/data/games.csv
