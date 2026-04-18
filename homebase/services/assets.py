TEAM_LOGO_URL = 'https://www.mlbstatic.com/team-logos/{team_id}.svg'
HEADSHOT_URL = 'https://img.mlbstatic.com/mlb-photos/image/upload/w_120/v1/people/{player_id}/headshot/silo/current'
BALLPARK_URL = 'https://prod-gameday.mlbstatic.com/responsive-gameday-assets/1.2.0/images/fields/{venue_id}.svg'


def team_logo_url(team_id):
    return TEAM_LOGO_URL.format(team_id=team_id)


def headshot_url(player_id):
    return HEADSHOT_URL.format(player_id=player_id)


def ballpark_url(venue_id):
    return BALLPARK_URL.format(venue_id=venue_id)
