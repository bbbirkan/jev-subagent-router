#!/bin/bash
# Claude Code status line, two lines:
#   1) context size badge (green -> yellow -> red -> purple) + model + JEV effort (if present)
#   2) account name (before @) | 5-hour quota | weekly quota (+ reset time) | prompt-cache hit rate
# Quotas come from the `rate_limits` field Claude Code sends to status line commands;
# a window that is not reported shows "—".
# Optional: STATUSLINE_USER=name overrides the account name (e.g. for screenshots).
# Optional: JEV_EFFORT_FILE=path/to/json with {"efor": "..."} to show the JEV effort level.
IN=$(cat)
printf '%s' "$IN" | JEV_EFFORT_FILE="${JEV_EFFORT_FILE:-}" python3 -c "
import json,os,sys,time
d=json.load(sys.stdin); r=d.get('rate_limits') or {}
u=None
try:
    for l in reversed(open(d['transcript_path']).readlines()[-200:]):
        u=json.loads(l).get('message',{}).get('usage')
        if u: break
except Exception: pass
hit=(u or {}).get('cache_read_input_tokens',0)
tot=hit+(u or {}).get('cache_creation_input_tokens',0)+(u or {}).get('input_tokens',0)
k=tot//1000
D=[(0,(170,200,170)),(200,(110,170,110)),(250,(190,180,100)),(330,(190,180,100)),(331,(195,100,90)),(500,(150,90,160))]
for (a,ca),(z,cz) in zip(D,D[1:]):
    if k<=z: t=(k-a)/(z-a); c=[round(x+(y-x)*t) for x,y in zip(ca,cz)]; break
else: c=D[-1][1]
line1=f'\033[38;2;{c[0]};{c[1]};{c[2]}m● {k}k\033[0m │ '+d.get('model',{}).get('display_name','?')
try: line1+=' | '+json.load(open(os.environ['JEV_EFFORT_FILE']))['efor']
except Exception: pass
name=os.environ.get('STATUSLINE_USER')
try: name=name or json.load(open(os.path.expanduser('~/.claude.json')))['oauthAccount']['emailAddress'].split('@')[0]
except Exception: name='?'
def q(key,label):
    x=r.get(key)
    if not x: return f'{label} —'
    p=x.get('used_percentage',0); col='32' if p<60 else '33' if p<85 else '31'
    z=time.strftime('%a %H:%M' if key=='seven_day' else '%H:%M',time.localtime(x['resets_at'])) if x.get('resets_at') else ''
    return f'\033[{col}m{label} {p}%\033[0m'+(f' ({z})' if z else '')
line2=f'👤 {name} │ '+q('five_hour','5h')+' │ '+q('seven_day','week')+(f' │ cache {round(100*hit/tot)}%' if tot else '')
print(line1+'\n'+line2,end='')
" 2>/dev/null
exit 0
