from django.shortcuts import render

from homebase.services import news, statsapi


def home(request):
    context = {
        'divisions': statsapi.standings_grid(),
        'news_items': news.league_news(limit=4),
        'leaders': [
            statsapi.leader_card('homeRuns', 'Home Runs'),
            statsapi.leader_card('onBasePlusSlugging', 'OPS'),
            statsapi.leader_card('strikeouts', 'Strikeouts'),
            statsapi.leader_card('earnedRunAverage', 'ERA'),
        ],
    }
    return render(request, 'home.html', context)


def standings(request):
    return render(request, 'standings.html', {
        'divisions': statsapi.standings_grid(),
    })


def team(request, team_id):
    hitters, pitchers = statsapi.roster_split(team_id)
    slug = statsapi.TEAM_SLUGS.get(team_id)
    context = {
        'header': statsapi.team_header(team_id),
        'hitters': hitters,
        'pitchers': pitchers,
        'news_items': news.team_news(slug) if slug else [],
        'leaders': [
            statsapi.leader_card('homeRuns', 'Home Runs', team_id=team_id),
            statsapi.leader_card('onBasePlusSlugging', 'OPS', team_id=team_id),
            statsapi.leader_card('strikeouts', 'Strikeouts', team_id=team_id),
            statsapi.leader_card('earnedRunAverage', 'ERA', team_id=team_id),
        ],
    }
    return render(request, 'team.html', context)


def player(request, player_id):
    data = statsapi.get_player_stats(player_id)
    people = data.get('people', [])
    if not people:
        return render(request, 'player.html', {
            'header': None,
            'is_pitcher': False,
            'rows': [],
            'recent_games': [],
        })
    person = people[0]
    is_pitcher = person.get('primaryPosition', {}).get('type') == 'Pitcher'
    group = 'pitching' if is_pitcher else 'hitting'
    return render(request, 'player.html', {
        'header': statsapi.player_header(person),
        'is_pitcher': is_pitcher,
        'rows': statsapi.stat_rows(person, group),
        'recent_games': statsapi.recent_games(player_id, group),
    })


def leaderboards(request):
    hitting_categories = [
        ('homeRuns', 'Home Runs'),
        ('battingAverage', 'Batting Average'),
        ('onBasePlusSlugging', 'On-base Plus Slugging'),
        ('runsBattedIn', 'Runs Batted In'),
    ]
    pitching_categories = [
        ('strikeouts', 'Strikeouts'),
        ('earnedRunAverage', 'Earned Run Average'),
        ('whip', 'Walks + Hits per Inning Pitched'),
        ('wins', 'Wins'),
    ]
    return render(request, 'leaderboards.html', {
        'hitting_charts': [statsapi.leader_chart(cat, label, stat_group='hitting') for cat, label in hitting_categories],
        'pitching_charts': [statsapi.leader_chart(cat, label, stat_group='pitching') for cat, label in pitching_categories],
    })
