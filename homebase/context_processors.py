from homebase.services.statsapi import TEAM_ABBR, TEAMS_NAV_ORDER


def teams_nav(request):
    return {
        'teams_nav': [(tid, TEAM_ABBR.get(tid, '')) for tid in TEAMS_NAV_ORDER],
    }
