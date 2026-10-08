const fs=require('fs'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
// HTML parsing normalizes CRLF before checking inline script CSP hashes.
const html=fs.readFileSync('Fantasy Lab Combined.html','utf8').replace(/\r\n?/g,'\n');
const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
for(const s of scripts){new vm.Script(s);assert(html.includes('sha256-'+crypto.createHash('sha256').update(s).digest('base64')));}
const elements=new Map();
function el(id){if(!elements.has(id))elements.set(id,{value:id==='estimateScope'?'mine':'',innerHTML:'',textContent:'',focus(){},classList:{add(){},remove(){},contains(){return false}},addEventListener(){}});return elements.get(id);}
const context=vm.createContext({console,location:{protocol:'file:',hostname:''},
  document:{getElementById:el,querySelectorAll:()=>[],querySelector:()=>null,addEventListener(){}},
  localStorage:{getItem:()=>null,setItem(){}},setTimeout:()=>0,clearTimeout(){},Set,Map,WeakMap,URL});
vm.runInContext(scripts[0],context);
vm.runInContext(scripts[1],context);
const cutoff=scripts[2].indexOf('restoreValueState();');assert(cutoff>0);
vm.runInContext(scripts[2].slice(0,cutoff),context);
vm.runInContext("function safeHTML(value){return String(value??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));}",context);
const run=code=>vm.runInContext(code,context);
run('applyLeagueFormat();buildRankings();buildRosters();renderFantasyEstimates();');
assert(elements.get('estimatesContent').innerHTML.includes('Est. PPR/game'));
assert(elements.get('estimatesContent').innerHTML.includes('2026 through week 4'));
assert(elements.get('estimatesContent').innerHTML.includes('Confidence'));
assert(elements.get('estimatesContent').innerHTML.includes('Injury seasons excluded'));
assert(elements.get('estimatesContent').innerHTML.includes('Touchdown sustainability'));
assert(elements.get('estimatesContent').innerHTML.includes('RZ TD/touch'));
assert(elements.get('estimatesContent').innerHTML.includes('not exact rank accuracy'));
assert(run('const withConfidence=Object.values(rosters).flat().find(p=>p.estimate&&p.ranked);rankLabel(withConfidence).includes("% conf.")'));
assert(run('confidenceLabel({name:"Nonexistent Player",position:"WR",team:"SF"})')==='');
assert.throws(()=>run('validateEstimates({...fantasyEstimatesPayload,players:[{...fantasyEstimatesPayload.players[0],confidence_pct:101}]})'));
assert(run('findEstimate("Kenneth Walker", "RB", "KC").player')==='Kenneth Walker III');
assert(run('findEstimate("DeVonta Smith", "WR", "PHI").player')==='DeVonta Smith');
assert(run('estimateTeam("LA")')==='LAR');
const matchCount=run('Object.values(rosters).flat().filter(p=>p.estimate).length');assert(matchCount>100);
run('estimateWeight=0;buildRosters();');
assert(run('Object.values(rosters).flat().every(p=>p.value===p.ranking_value)'));
run('estimateWeight=1;buildRosters();');
assert(run('Object.values(rosters).flat().filter(p=>p.estimate&&p.ranked).every(p=>p.value===playerValue(p.estimate.position_rank,p.position,p.estimate.position_rank))'));
run('const sample=Object.values(rosters).flat().find(p=>p.estimate&&p.ranked);overrides.set(sample.ranked_name,123.4);estimateWeight=.35;buildRosters();');
assert(run('Object.values(rosters).flat().find(p=>p.ranked_name===sample.ranked_name).value')===123.4);
assert(run('Object.values(rosters).flat().filter(p=>!p.estimate).every(p=>p.value===p.ranking_value||p.manual_override)'));
assert(run('Object.values(rosters).flat().every(p=>Number.isFinite(p.value))'));
assert(run('const tradeTeams=Object.keys(rosters); const tradeTest=evaluateTrade(rosters[tradeTeams[0]],rosters[tradeTeams[1]],[0],[0]); Number.isFinite(tradeTest.your_utility)&&Number.isFinite(tradeTest.their_utility)&&Number.isFinite(tradeTest.ratio)'));
assert.throws(()=>run('validateEstimates({schema_version:2})'));
assert.throws(()=>run('validateEstimates({...fantasyEstimatesPayload,players:[fantasyEstimatesPayload.players[0],fantasyEstimatesPayload.players[0]]})'));
run('const testCandidates=estimateIndex.get(estimateName(sample.estimate.player)+"|"+sample.position);testCandidates.push({...testCandidates[0],player_id:"duplicate",team:testCandidates[0].team});');
assert(run('findEstimate(sample.estimate.player,sample.position,sample.estimate.team)')===null);
console.log(`Passed: all 3 scripts compile and CSP hashes match; ${matchCount} roster players match; normalization, missing estimates, 0/100% blending, manual overrides, schema validation, and ambiguous-name rejection.`);
assert(run('parseSleeperLeagueId(" 1391859959213359104 ")')==='1391859959213359104');
assert(run('parseSleeperLeagueId("https://sleeper.com/leagues/1391859959213359104/team")')==='1391859959213359104');
assert(run('parseSleeperLeagueId("https://sleeper.app/leagues/1391859959213359104")')==='1391859959213359104');
assert(run('parseSleeperLeagueId("https://example.com/leagues/1391859959213359104")')==='');
assert(run('parseSleeperLeagueId("not a league")')==='');
(async()=>{
  run('globalThis.requestedId=null;globalThis.loadSleeperLeague=async options=>{requestedId=options.leagueId;return true;};');
  el('sleeperImportId').value='https://sleeper.app/leagues/1391859959213359104/team';
  assert(await run('importSleeperFromPanel()'));
  assert(run('requestedId')==='1391859959213359104');
  assert(el('sleeperImportStatus').textContent.startsWith('Loaded'));
  assert(el('sleeperImportButton').disabled===false);
  run('globalThis.loadSleeperLeague=async()=>false;');
  assert(!(await run('importSleeperFromPanel()')));
  assert(el('sleeperImportStatus').textContent.includes('Could not load'));
  run('globalThis.loadSleeperLeague=async()=>{throw new Error("offline");};');
  assert(!(await run('importSleeperFromPanel()')));
  assert(el('sleeperImportStatus').textContent==='Failed: offline');
  el('sleeperImportId').value='invalid';
  assert(!(await run('importSleeperFromPanel()')));
  assert(el('sleeperImportStatus').textContent.includes('numeric league ID'));
  console.log('Passed Sleeper import: large IDs preserved as strings, league URLs, input rejection, load success, failed requests, error display, and button reset.');
})().catch(error=>{console.error(error);process.exitCode=1;});
