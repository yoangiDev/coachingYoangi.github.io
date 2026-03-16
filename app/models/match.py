class Match:
    def __init__(
        self, match_id, creation_time, champ_played, role, win, duration,
        kills, deaths, assists, kp, vision, dmg, gold, total_cs, dmg_share,
        xp_diff_15=0   # ← nuevo, con default 0 por si falla el timeline
    ):
        self.match_id       = match_id
        self.creation_time  = creation_time
        self.champ_played   = champ_played
        self.role           = role
        self.win            = win
        self.duration_seconds = duration
        self.kills          = kills
        self.deaths         = deaths
        self.assists        = assists
        self.kp             = kp
        self.vision         = vision
        self.dmg            = dmg
        self.gold           = gold
        self.total_cs       = total_cs
        self.dmg_share      = dmg_share
        self.xp_diff_15     = xp_diff_15   # ← nuevo

    def get_duration_minutes(self):
        return self.duration_seconds / 60

    def calc_cs_min(self):   return self.total_cs / self.get_duration_minutes()
    def calc_dmg_min(self):  return self.dmg      / self.get_duration_minutes()
    def calc_gold_min(self): return self.gold      / self.get_duration_minutes()
    def calc_dmg_gold(self): return self.dmg / self.gold if self.gold > 0 else 0