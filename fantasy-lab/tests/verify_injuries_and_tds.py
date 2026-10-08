import importlib.util
from pathlib import Path
import json
import pandas as pd

spec = importlib.util.spec_from_file_location('fantasy', 'fantasy.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
cache = Path('.tests-cache/injury_fixture')
cache.mkdir(parents=True, exist_ok=True)
season = 2018
schedule = pd.DataFrame([dict(season=season,game_type='REG',week=1,game_id='G1',home_team='A',away_team='B',home_score=10,away_score=7)])
# One actual injury absence, one rest absence, one injury reserve, one healthy
# scratch, one questionable/inactive medical absence, one questionable participant.
injuries = pd.DataFrame([
    ['I','A',1,'REG','Out','Knee'], ['R','A',1,'REG','Out','Not injury related - resting player'],
    ['Q','A',1,'REG','Questionable','Ankle'], ['P','A',1,'REG','Questionable','Ankle'],
    ['Y','A',2,'REG','Out','Knee']
],columns=['gsis_id','team','week','game_type','report_status','report_primary_injury'])
rosters = pd.DataFrame([
    ['I','A',1,'REG','INA','I01'], ['R','A',1,'REG','INA','I01'],
    ['IR','A',1,'REG','RES','R01'], ['H','A',1,'REG','INA','I01'],
    ['Q','A',1,'REG','INA','I01'], ['P','A',1,'REG','ACT','A01'],
    ['S','B',1,'REG','RES','R40'], ['B','B',1,'REG','ACT','A01']
],columns=['gsis_id','team','week','game_type','status','status_description_abbr'])
stats = pd.DataFrame([['P','G1',1,'REG']],columns=['player_id','game_id','week','season_type'])
injuries.to_csv(cache/'injuries_2018.csv',index=False)
rosters.to_csv(cache/'roster_weekly_2018.csv',index=False)
stats.to_csv(cache/'stats_2018.csv',index=False)
exclusions,_ = f.injury_season_exclusions([season],cache,schedule)
assert set(exclusions.player_id) == {'I','IR','Q'}
# Reject missing injury coverage rather than silently treating it as healthy.
injuries.loc[:,'week']=2
injuries.to_csv(cache/'injuries_2018.csv',index=False)
try:
    f.injury_season_exclusions([season],cache,schedule)
except ValueError:
    pass
else:
    raise AssertionError('Missing injury coverage must fail.')

model = json.loads(Path('confidence_model.json').read_text())
rows=[]
for pid, td_indices in [('SPIKE',{0,1,2,3,10,11,12}), ('NORMAL',{0})]:
    for i in range(20):
        rows.append(dict(receiver_player_id=pid,rusher_player_id=None,passer_player_id=None,
            pass_attempt=1,sack=0,complete_pass=1,rush_touchdown=0,
            pass_touchdown=int(i in td_indices),week=1,
            yardline_100=3 if i<5 else 12 if i<10 else 45))
pbp=pd.DataFrame(rows)
players=pd.DataFrame([dict(player_id='SPIKE',position='WR',passing_tds=0,rushing_tds=0,
    receiving_tds=7,fantasy_points_ppr=90,team_games=3),
    dict(player_id='NORMAL',position='WR',passing_tds=0,rushing_tds=0,
    receiving_tds=1,fantasy_points_ppr=60,team_games=3)])
result=f.add_td_sustainability(players,pbp,model).set_index('player_id')
spike=result.loc['SPIKE']
assert spike.red_zone_touches == 10 and spike.red_zone_tds == 4
assert abs(spike.red_zone_td_conversion-.4)<1e-9
assert abs(spike.td_free_ppr_per_game-16)<1e-9  # 30 PPR average, 14/game from TDs.
assert spike.expected_offensive_tds < 7
assert spike.td_normalized_ppr_per_game < 30
assert spike.td_sustainability in {'Unusually high TD scoring','TD-heavy; watch for regression'}
assert result.loc['NORMAL'].td_sustainability == 'No elevated TD signal'
# Incomplete targets are opportunities, but not touches.
pbp.loc[0,'complete_pass']=0
pbp.loc[0,'pass_touchdown']=0
changed=f.add_td_sustainability(players,pbp,model).set_index('player_id')
assert changed.loc['SPIKE'].red_zone_touches == 9
assert abs(changed.loc['SPIKE'].expected_offensive_tds-spike.expected_offensive_tds)<1e-9
assert abs(f.poisson_upper_tail(3,.5)-.0143876779669707)<1e-12
assert f.poisson_upper_tail(0,0)==1
print('Passed: injury vs rest/suspension/healthy scratches, injured reserve, actual participation and bye-week handling, missing coverage rejection; 30-PPR TD spike, red-zone touches vs targets, TD-free/normalized scoring and rarity calculation.')
