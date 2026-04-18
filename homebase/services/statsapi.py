import hashlib
from datetime import date

import plotly.graph_objects as go
import requests
from django.core.cache import cache

from homebase.services.assets import headshot_url, team_logo_url
from homebase.services.stat_calcs import bb_pct, so_pct

BASE_URL = 'https://statsapi.mlb.com'
DEFAULT_TTL = 600
LONG_TTL = 24 * 60 * 60

TEAM_ABBR = {
    108: 'LAA', 109: 'ARI', 110: 'BAL', 111: 'BOS', 112: 'CHC', 113: 'CIN',
    114: 'CLE', 115: 'COL', 116: 'DET', 117: 'HOU', 118: 'KC',  119: 'LAD',
    120: 'WSH', 121: 'NYM', 133: 'OAK', 134: 'PIT', 135: 'SD',  136: 'SEA',
    137: 'SF',  138: 'STL', 139: 'TB',  140: 'TEX', 141: 'TOR', 142: 'MIN',
    143: 'PHI', 144: 'ATL', 145: 'CWS', 146: 'MIA', 147: 'NYY', 158: 'MIL',
}

TEAM_SLUGS = {
    108: 'angels', 109: 'dbacks', 110: 'orioles', 111: 'redsox',
    112: 'cubs', 113: 'reds', 114: 'guardians', 115: 'rockies',
    116: 'tigers', 117: 'astros', 118: 'royals', 119: 'dodgers',
    120: 'nationals', 121: 'mets', 133: 'athletics', 134: 'pirates',
    135: 'padres', 136: 'mariners', 137: 'giants', 138: 'cardinals',
    139: 'rays', 140: 'rangers', 141: 'bluejays', 142: 'twins',
    143: 'phillies', 144: 'braves', 145: 'whitesox', 146: 'marlins',
    147: 'yankees', 158: 'brewers',
}

DIVISION_NAMES = {
    201: 'AL East', 202: 'AL Central', 200: 'AL West',
    204: 'NL East', 205: 'NL Central', 203: 'NL West',
}

DIVISION_ORDER = [201, 204, 202, 205, 200, 203]

TEAMS_NAV_ORDER = [
    141, 145, 108, 158, 144, 115,
    110, 116, 133, 134, 143, 137,
    111, 118, 117, 138, 146, 109,
    147, 114, 136, 112, 121, 135,
    139, 142, 140, 113, 120, 119,
]


def _cache_key(path, params):
    canonical = path + '?' + '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
    return 'statsapi:' + hashlib.md5(canonical.encode()).hexdigest()


def _get(path, ttl=DEFAULT_TTL, **params):
    key = _cache_key(path, params)
    cached = cache.get(key)
    if cached is not None:
        return cached
    resp = requests.get(f'{BASE_URL}{path}', params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    cache.set(key, data, ttl)
    return data


def get_teams():
    return _get('/api/v1/teams', ttl=LONG_TTL, sportId=1)


def get_team(team_id):
    return _get(f'/api/v1/teams/{team_id}', ttl=LONG_TTL)


def get_roster_with_stats(team_id):
    return _get(
        f'/api/v1/teams/{team_id}/roster/Active',
        hydrate='person(stats(type=season))',
    )


def get_standings():
    return _get('/api/v1/standings', ttl=300, leagueId='103,104')


def get_player(player_id):
    return _get(f'/api/v1/people/{player_id}', ttl=LONG_TTL)


def get_player_stats(player_id):
    return _get(
        f'/api/v1/people/{player_id}',
        hydrate='stats(type=[yearByYear,yearByYearAdvanced,projected,career]),team,currentTeam',
    )


def get_player_gamelog(player_id, group):
    return _get(
        f'/api/v1/people/{player_id}',
        hydrate=f'stats(type=[gameLog],group=[{group}])',
    )


def get_leaders(category, limit=10, team_id=None, stat_group=None):
    params = {
        'leaderCategories': category,
        'sportId': 1,
        'season': date.today().year,
        'limit': limit,
    }
    if team_id is not None:
        params['teamId'] = team_id
    if stat_group is not None:
        params['statGroup'] = stat_group
    return _get('/api/v1/stats/leaders', ttl=300, **params)


def _split_pct(split):
    if not split:
        return '-'
    wins = split.get('wins', 0)
    losses = split.get('losses', 0)
    if wins + losses == 0:
        return '-'
    pct = wins / (wins + losses)
    return f'{pct:.3f}'.lstrip('0')


def _split_record(split):
    if not split:
        return '-'
    return f"{split.get('wins', 0)}-{split.get('losses', 0)}"


def _shape_team_record(tr):
    splits = {s.get('type'): s for s in tr.get('records', {}).get('splitRecords', [])}

    pct = tr.get('winningPercentage', '')
    if pct.startswith('0.'):
        pct = pct[1:]

    diff = tr.get('runDifferential', 0)
    diff_str = f'+{diff}' if diff > 0 else str(diff)

    team_id = tr['team']['id']
    return {
        'team_id': team_id,
        'abbr': TEAM_ABBR.get(team_id, ''),
        'logo_url': team_logo_url(team_id),
        'wins': tr['wins'],
        'losses': tr['losses'],
        'pct': pct,
        'gb': tr.get('gamesBack', '-'),
        'l10': _split_record(splits.get('lastTen')),
        'diff': diff_str,
        'home_pct': _split_pct(splits.get('home')),
        'away_pct': _split_pct(splits.get('away')),
        'one_run_pct': _split_pct(splits.get('oneRun')),
        'extra_inning_pct': _split_pct(splits.get('extraInning')),
    }


def standings_grid():
    records = get_standings()['records']
    by_id = {r['division']['id']: r for r in records}
    return [
        {
            'name': DIVISION_NAMES[did],
            'teams': [_shape_team_record(tr) for tr in by_id[did]['teamRecords']],
        }
        for did in DIVISION_ORDER if did in by_id
    ]


def leader_card(category, label, team_id=None):
    data = get_leaders(category, limit=1, team_id=team_id)
    categories = data.get('leagueLeaders', [])
    if not categories or not categories[0].get('leaders'):
        return {'label': label, 'leader': None}
    top = categories[0]['leaders'][0]
    player_id = top['person']['id']
    return {
        'label': label,
        'leader': {
            'player_id': player_id,
            'name': top['person']['fullName'],
            'headshot_url': headshot_url(player_id),
            'team_abbr': TEAM_ABBR.get(top.get('team', {}).get('id'), ''),
            'value': top['value'],
        },
    }


def _ordinal(n):
    if n is None or n == '':
        return ''
    n = int(n)
    if 10 <= n % 100 <= 20:
        return f'{n}th'
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def team_header(team_id):
    teams = get_team(team_id).get('teams', [])
    full_name = teams[0].get('name', '') if teams else ''

    records = get_standings()['records']
    for record in records:
        for tr in record.get('teamRecords', []):
            if tr.get('team', {}).get('id') == team_id:
                division_id = record.get('division', {}).get('id')
                pct = tr.get('winningPercentage', '')
                if pct.startswith('0.'):
                    pct = pct[1:]
                return {
                    'team_id': team_id,
                    'name': full_name or tr['team'].get('name', ''),
                    'abbr': TEAM_ABBR.get(team_id, ''),
                    'logo_url': team_logo_url(team_id),
                    'rank_label': _ordinal(tr.get('divisionRank')),
                    'division': DIVISION_NAMES.get(division_id, ''),
                    'wins': tr.get('wins', 0),
                    'losses': tr.get('losses', 0),
                    'pct': pct,
                    'gb': tr.get('gamesBack', '-'),
                }
    return None


def _season_stats(person, group):
    for s in person.get('stats', []):
        if s.get('group', {}).get('displayName') != group:
            continue
        splits = s.get('splits', [])
        if splits:
            return splits[0].get('stat', {})
    return {}


def _fmt_pct(rate):
    if rate is None:
        return '-'
    return f'{rate * 100:.1f}%'


def _shape_hitter(entry):
    person = entry.get('person', {})
    stat = _season_stats(person, 'hitting')
    pa = stat.get('plateAppearances', 0)
    so = stat.get('strikeOuts', 0)
    bb = stat.get('baseOnBalls', 0)
    player_id = person.get('id')
    return {
        'player_id': player_id,
        'name': person.get('lastFirstName') or person.get('fullName', ''),
        'headshot_url': headshot_url(player_id),
        'pos': entry.get('position', {}).get('abbreviation', ''),
        'number': entry.get('jerseyNumber', ''),
        'age': person.get('currentAge', ''),
        'bats': person.get('batSide', {}).get('code', ''),
        'throws': person.get('pitchHand', {}).get('code', ''),
        'pa': pa,
        'h': stat.get('hits', 0),
        'double': stat.get('doubles', 0),
        'triple': stat.get('triples', 0),
        'hr': stat.get('homeRuns', 0),
        'sb': stat.get('stolenBases', 0),
        'so_pct': _fmt_pct(so_pct(so, pa)),
        'bb_pct': _fmt_pct(bb_pct(bb, pa)),
        'avg': stat.get('avg', '.000'),
        'obp': stat.get('obp', '.000'),
        'ops': stat.get('ops', '.000'),
    }


def _shape_pitcher(entry):
    person = entry.get('person', {})
    stat = _season_stats(person, 'pitching')
    bf = stat.get('battersFaced', 0)
    so = stat.get('strikeOuts', 0)
    bb = stat.get('baseOnBalls', 0)
    gs = stat.get('gamesStarted', 0) or 0
    player_id = person.get('id')
    if stat:
        pos = 'SP' if gs > 0 else 'RP'
    else:
        pos = entry.get('position', {}).get('abbreviation', 'P')
    return {
        'player_id': player_id,
        'name': person.get('lastFirstName') or person.get('fullName', ''),
        'headshot_url': headshot_url(player_id),
        'pos': pos,
        'number': entry.get('jerseyNumber', ''),
        'age': person.get('currentAge', ''),
        'g': stat.get('gamesPlayed', 0),
        'ip': stat.get('inningsPitched', '0.0'),
        'bf': bf,
        'era': stat.get('era', '0.00'),
        'so': so,
        'bb': bb,
        'so_pct': _fmt_pct(so_pct(so, bf)),
        'bb_pct': _fmt_pct(bb_pct(bb, bf)),
        'ops': stat.get('ops', '.000'),
    }


def roster_split(team_id):
    data = get_roster_with_stats(team_id)
    roster = data.get('roster', [])
    hitters = []
    pitchers = []
    for entry in roster:
        if entry.get('position', {}).get('type') == 'Pitcher':
            pitchers.append(_shape_pitcher(entry))
        else:
            hitters.append(_shape_hitter(entry))
    return hitters, pitchers


def player_header(person):
    team = person.get('currentTeam', {})
    team_id = team.get('id')
    return {
        'player_id': person.get('id'),
        'name': person.get('fullName', ''),
        'number': person.get('primaryNumber', ''),
        'headshot_url': headshot_url(person.get('id')),
        'team_id': team_id,
        'team_name': team.get('name', ''),
        'team_logo_url': team_logo_url(team_id) if team_id else '',
        'position': person.get('primaryPosition', {}).get('abbreviation', ''),
        'bats': person.get('batSide', {}).get('code', ''),
        'throws': person.get('pitchHand', {}).get('code', ''),
        'age': person.get('currentAge', ''),
        'height': person.get('height', ''),
        'weight': person.get('weight', ''),
        'draft_year': person.get('draftYear') or '—',
    }


def _team_display(split):
    team = split.get('team', {})
    team_id = team.get('id')
    if team_id:
        return team.get('name', ''), team_logo_url(team_id)
    num_teams = split.get('numTeams')
    if num_teams and num_teams > 1:
        return f'{num_teams} Teams', ''
    return '', ''


def _shape_year_hitter(split, season_label, kind):
    team_name, team_logo = _team_display(split)
    stat = split.get('stat', {})
    pa = stat.get('plateAppearances', 0)
    so = stat.get('strikeOuts', 0)
    bb = stat.get('baseOnBalls', 0)
    return {
        'season': season_label,
        'kind': kind,
        'team_name': team_name,
        'team_logo_url': team_logo,
        'g': stat.get('gamesPlayed', 0),
        'pa': pa,
        'h': stat.get('hits', 0),
        'r': stat.get('runs', 0),
        'double': stat.get('doubles', 0),
        'triple': stat.get('triples', 0),
        'hr': stat.get('homeRuns', 0),
        'avg': stat.get('avg', '.000'),
        'obp': stat.get('obp', '.000'),
        'slg': stat.get('slg', '.000'),
        'ops': stat.get('ops', '.000'),
        'babip': stat.get('babip', '-'),
        'so': so,
        'bb': bb,
        'so_pct': _fmt_pct(so_pct(so, pa)),
        'bb_pct': _fmt_pct(bb_pct(bb, pa)),
        'sb': stat.get('stolenBases', 0),
        'cs': stat.get('caughtStealing', 0),
    }


def _shape_year_pitcher(split, season_label, kind):
    team_name, team_logo = _team_display(split)
    stat = split.get('stat', {})
    bf = stat.get('battersFaced', 0)
    so = stat.get('strikeOuts', 0)
    bb = stat.get('baseOnBalls', 0)
    return {
        'season': season_label,
        'kind': kind,
        'team_name': team_name,
        'team_logo_url': team_logo,
        'g': stat.get('gamesPlayed', 0),
        'gs': stat.get('gamesStarted', 0),
        'bf': bf,
        'ip': stat.get('inningsPitched', '0.0'),
        'era': stat.get('era', '0.00'),
        'whip': stat.get('whip', '0.00'),
        'so': so,
        'bb': bb,
        'so_pct': _fmt_pct(so_pct(so, bf)),
        'bb_pct': _fmt_pct(bb_pct(bb, bf)),
        'so9': stat.get('strikeoutsPer9Inn', '0.00'),
        'bb9': stat.get('walksPer9Inn', '0.00'),
        'sobb': stat.get('strikeoutWalkRatio', '0.00'),
        'hr': stat.get('homeRuns', 0),
        'hr9': stat.get('homeRunsPer9', '0.00'),
    }


def stat_rows(person, group):
    if group == 'hitting':
        shape = _shape_year_hitter
    else:
        shape = _shape_year_pitcher

    year_by_year = []
    projected = None
    career = None

    for s in person.get('stats', []):
        if s.get('group', {}).get('displayName') != group:
            continue
        type_name = s.get('type', {}).get('displayName')
        splits = s.get('splits', [])
        if type_name == 'yearByYear':
            year_by_year = splits
        elif type_name == 'projected' and splits:
            projected = splits[0]
        elif type_name == 'career' and splits:
            career = splits[0]

    rows = []
    for split in year_by_year:
        rows.append(shape(split, split.get('season', ''), 'regular'))
    if projected:
        row = shape(projected, projected.get('season', ''), 'projected')
        row['team_name'] = 'Projected'
        row['team_logo_url'] = ''
        rows.append(row)
    if career:
        rows.append(shape(career, 'Career', 'career'))
    return rows


def _fmt_date(date_str):
    if not date_str:
        return ''
    parts = date_str.split('-')
    if len(parts) != 3:
        return date_str
    y, m, d = parts
    return f'{int(m)}/{int(d)}/{y}'


def _shape_hitter_game(split):
    opp = split.get('opponent', {})
    opp_id = opp.get('id')
    stat = split.get('stat', {})
    return {
        'date': _fmt_date(split.get('date', '')),
        'opponent_abbr': TEAM_ABBR.get(opp_id, ''),
        'opponent_logo_url': team_logo_url(opp_id) if opp_id else '',
        'summary': stat.get('summary', ''),
        'h': stat.get('hits', 0),
        'hr': stat.get('homeRuns', 0),
        'rbi': stat.get('rbi', 0),
        'k': stat.get('strikeOuts', 0),
        'bb': stat.get('baseOnBalls', 0),
        'avg': stat.get('avg', '.000'),
    }


def _shape_pitcher_game(split):
    opp = split.get('opponent', {})
    opp_id = opp.get('id')
    stat = split.get('stat', {})
    return {
        'date': _fmt_date(split.get('date', '')),
        'opponent_abbr': TEAM_ABBR.get(opp_id, ''),
        'opponent_logo_url': team_logo_url(opp_id) if opp_id else '',
        'summary': stat.get('summary', ''),
        'ip': stat.get('inningsPitched', '0.0'),
        'er': stat.get('earnedRuns', 0),
        'h': stat.get('hits', 0),
        'bb': stat.get('baseOnBalls', 0),
        'k': stat.get('strikeOuts', 0),
        'era': stat.get('era', '0.00'),
    }


def recent_games(player_id, group, limit=7):
    data = get_player_gamelog(player_id, group)
    people = data.get('people', [])
    if not people:
        return []
    stats = people[0].get('stats', [])
    splits = []
    for s in stats:
        if s.get('group', {}).get('displayName') != group:
            continue
        if s.get('type', {}).get('displayName') != 'gameLog':
            continue
        splits = s.get('splits', [])
        break

    regular = [sp for sp in splits if sp.get('gameType') == 'R']
    regular.sort(key=lambda sp: sp.get('date', ''), reverse=True)
    last = regular[:limit]
    shape = _shape_hitter_game if group == 'hitting' else _shape_pitcher_game
    return [shape(sp) for sp in last]


def leader_chart(category, label, stat_group=None, limit=10):
    data = get_leaders(category, limit=limit, stat_group=stat_group)
    categories = data.get('leagueLeaders', [])
    if not categories or not categories[0].get('leaders'):
        return {'label': label, 'top_player': None, 'chart_html': ''}

    leaders = categories[0]['leaders'][:limit]
    names = []
    values = []
    player_ids = []
    for leader in leaders:
        player_name = leader.get('person', {}).get('fullName', '')
        team_abbr = TEAM_ABBR.get(leader.get('team', {}).get('id'), '')
        display = f'{player_name} ({team_abbr})' if team_abbr else player_name
        names.append(display)
        try:
            values.append(float(leader.get('value', 0)))
        except (TypeError, ValueError):
            values.append(0)
        player_ids.append(leader.get('person', {}).get('id'))

    top_leader = leaders[0]
    top_player_id = top_leader.get('person', {}).get('id')
    top_team = top_leader.get('team', {})
    top_team_id = top_team.get('id')
    top_player = {
        'name': top_leader.get('person', {}).get('fullName', ''),
        'team_name': top_team.get('name', ''),
        'team_abbr': TEAM_ABBR.get(top_team_id, ''),
        'team_logo_url': team_logo_url(top_team_id) if top_team_id else '',
        'headshot_url': headshot_url(top_player_id) if top_player_id else '',
        'value': values[0] if values else '',
    }

    max_val = max(values) if values else 1

    fig = go.Figure(data=[go.Bar(
        y=names,
        x=values,
        orientation='h',
        marker_color='#7ab0e0',
        text=values,
        textposition='outside',
        textfont=dict(color='#ffffff'),
        hovertemplate='%{y}: %{x}<extra></extra>',
    )])

    for i, (val, pid) in enumerate(zip(values, player_ids)):
        if pid:
            fig.add_layout_image(dict(
                source=headshot_url(pid),
                xref='x',
                yref='y',
                x=val,
                y=names[i],
                xanchor='right',
                yanchor='middle',
                sizex=max_val * 0.07,
                sizey=0.85,
                layer='above',
            ))

    fig.update_layout(
        paper_bgcolor='#1a4874',
        plot_bgcolor='#1a4874',
        font=dict(family='Inter, sans-serif', color='#ffffff', size=12),
        yaxis=dict(
            autorange='reversed',
            gridcolor='rgba(255,255,255,0.05)',
            automargin=True,
            ticksuffix='  ',
        ),
        xaxis=dict(
            gridcolor='rgba(255,255,255,0.1)',
            range=[0, max_val * 1.15],
        ),
        margin=dict(l=20, r=30, t=10, b=20),
    )

    return {
        'label': label,
        'top_player': top_player,
        'chart_html': fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            default_width='100%',
            default_height='420px',
            config={'responsive': True, 'displayModeBar': False},
        ),
    }
