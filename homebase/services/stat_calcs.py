def so_pct(strikeouts, plate_appearances):
    if not plate_appearances:
        return None
    return strikeouts / plate_appearances


def bb_pct(walks, plate_appearances):
    if not plate_appearances:
        return None
    return walks / plate_appearances
