from app.models.match import Match


class Player:
    """Modela un jugador con ranking y estadísticas de partidas."""

    def __init__(self, game_name, tag_line, region_routing, region_platform, puu_id):
        """Inicializa los campos del jugador y un historial de partidas vacío."""
        self.game_name = game_name
        self.tag_line = tag_line
        self.region_routing = region_routing
        self.region_platform = region_platform
        self.puu_id = puu_id

        # Estado de clasificación por defecto antes de consulta de la API.
        self.tier = "UNRANKED"
        self.rank = ""
        self.lp = 0
        self.wins = 0
        self.losses = 0

        # Datos adicionales del summoner.
        self.profile_icon_id = 0
        self.summoner_level = "--"

        # Lista de objetos Match para generar estadísticas y medias móviles.
        self.match_history: list[Match] = []

    def add_match(self, match_object: Match):
        """Añade una partida al historial del jugador."""
        self.match_history.append(match_object)

    def generate_moving_averages(self, window_size: int = 10) -> list[dict]:
        """Genera una lista de medias móviles sobre el historial de partidas.

        Un punto de media móvil se genera para cada ventana deslizante donde
        el tamaño coincida con `window_size`.

        Returns:
            lista de diccionarios con métricas de ventana.
            None si no hay suficientes partidas.
        """
        # Asegura orden cronológico para los cálculos de tendencias.
        sorted_history = sorted(self.match_history, key=lambda m: m.creation_time)

        if len(sorted_history) < window_size:
            return None

        moving_averages = []

        for i in range(len(sorted_history) - window_size + 1):
            window = sorted_history[i : i + window_size]
            n = len(window)
            last_match = window[-1]

            # Promedios por ventana de partidas.
            ma_data = {
                "point_timestamp": last_match.creation_time,
                "winrate": round(sum(1 for m in window if m.win) / n * 100, 1),
                "avg_cs_min": round(sum(m.calc_cs_min() for m in window) / n, 2),
                "avg_kp": round(sum(m.kp for m in window) / n, 1),
                "avg_dmg_share": round(sum(m.dmg_share for m in window) / n, 1),
                "avg_deaths": round(sum(m.deaths for m in window) / n, 1),
                "avg_dmg_min": round(sum(m.calc_dmg_min() for m in window) / n, 0),
                "avg_gold_min": round(sum(m.calc_gold_min() for m in window) / n, 0),
                "avg_dmg_gold": round(sum(m.calc_dmg_gold() for m in window) / n, 2),
                "avg_xp_diff_15": round(sum(m.xp_diff_15 for m in window) / n, 0),
            }
            moving_averages.append(ma_data)

        return moving_averages