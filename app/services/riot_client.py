import urllib.parse
import aiohttp
import asyncio
from app.models.player import Player
from app.models.match import Match
from app.exceptions import PlayerNotFoundError, RiotAPIError


class RiotAPIClient:
    """Cliente para consumir la API de Riot Games con manejo de reintentos y límites."""

    def __init__(self, api_key, region_routing="europe", region_platform="euw1"):
        """Inicializa base URLs, cabeceras de auth y semáforo de concurrencia."""
        self.api_key = api_key
        self.headers = {"X-Riot-Token": self.api_key}
        self.base_routing = f"https://{region_routing}.api.riotgames.com"
        self.base_platform = f"https://{region_platform}.api.riotgames.com"

        # Se limita la concurrencia para no saturar la cuota de llamadas.
        self.semaphore = asyncio.Semaphore(15)

    async def get_puuid(self, session, game_name, tag_line):
        """Obtiene el puuid de un jugador usando game_name#tag_line."""
        safe_name = urllib.parse.quote(game_name)
        safe_tag = urllib.parse.quote(tag_line)
        url = f"{self.base_routing}/riot/account/v1/accounts/by-riot-id/{safe_name}/{safe_tag}"

        for _ in range(3):
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["puuid"]
                elif response.status == 429:
                    retry_after = float(response.headers.get("Retry-After", 2))
                    await asyncio.sleep(retry_after)
                    continue
                elif response.status == 404:
                    raise PlayerNotFoundError(f"Jugador '{game_name}#{tag_line}' no encontrado")
                else:
                    raise RiotAPIError(f"Error al obtener PUUID: status {response.status}")

        raise RiotAPIError("Rate limit persistente al obtener PUUID")

    async def fetch_player_rank(self, session: aiohttp.ClientSession, player_obj: Player):
        """Recupera el ranking solo/dúo de un summoner por puuid y lo asigna."""
        url = f"{self.base_platform}/lol/league/v4/entries/by-puuid/{player_obj.puu_id}"

        async with session.get(url, headers=self.headers) as response:
            if response.status != 200:
                return  # Si la API no devuelve 200, dejamos valores por defecto.
            entries = await response.json()

            # Filtramos la cola de solo/duo y actualizamos los datos del jugador.
            for entry in entries:
                if entry["queueType"] == "RANKED_SOLO_5x5":
                    player_obj.tier = entry["tier"]
                    player_obj.rank = entry["rank"]
                    player_obj.lp = entry["leaguePoints"]
                    player_obj.wins = entry["wins"]
                    player_obj.losses = entry["losses"]

    async def fetch_summoner_info(self, session: aiohttp.ClientSession, player_obj: Player):
        """Recupera icono y nivel del summoner por puuid."""
        url = f"{self.base_platform}/lol/summoner/v4/summoners/by-puuid/{player_obj.puu_id}"

        async with session.get(url, headers=self.headers) as response:
            if response.status != 200:
                return  # No interrumpe el flujo si falla.
            data = await response.json()
            player_obj.profile_icon_id = data.get("profileIconId", 0)
            player_obj.summoner_level = data.get("summonerLevel", "--")

    async def _fetch_single_match(self, session: aiohttp.ClientSession, match_id: str) -> dict | None:
        """Obtiene los datos de una partida, con reintentos al rate-limit."""
        url = f"{self.base_routing}/lol/match/v5/matches/{match_id}"

        for _ in range(3):
            async with self.semaphore:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        retry_after = float(response.headers.get("Retry-After", 1.5))
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        return None
        return None

    def _parse_match(self, data: dict, puu_id: str, rol_filtro: str) -> Match | None:
        """Convierte datos de API en objeto Match o descarta si no corresponde."""
        info = data["info"]

        # Excluye partidas demasiado cortas para evitar outliers.
        if info["gameDuration"] < 210:
            return None

        try:
            p = next(part for part in info["participants"] if part["puuid"] == puu_id)
        except StopIteration:
            return None

        rol_jugador = p.get("teamPosition", "")
        if rol_filtro.upper() != "ALL" and rol_jugador != rol_filtro.upper():
            return None

        team = [part for part in info["participants"] if part["teamId"] == p["teamId"]]
        t_kills = sum(m["kills"] for m in team)
        t_dmg = sum(m["totalDamageDealtToChampions"] for m in team)

        return Match(
            match_id=data["metadata"]["matchId"],
            creation_time=info["gameCreation"],
            champ_played=p["championName"],
            role=rol_jugador,
            win=p["win"],
            duration=info["gameDuration"],
            kills=p["kills"],
            deaths=p["deaths"],
            assists=p["assists"],
            kp=(p["kills"] + p["assists"]) / t_kills * 100 if t_kills > 0 else 0,
            vision=p["visionScore"],
            dmg=p["totalDamageDealtToChampions"],
            gold=p["goldEarned"],
            total_cs=p["totalMinionsKilled"] + p["neutralMinionsKilled"],
            dmg_share=(p["totalDamageDealtToChampions"] / t_dmg * 100) if t_dmg > 0 else 0,
        )

    async def fetch_matches(
        self,
        session: aiohttp.ClientSession,
        player_obj: Player,
        start_t: int = None,
        end_t: int = None,
        rol_filtro: str = "ALL",
        max_partidas: int = 20,
    ):
        """Recupera y parsea el historial de partidas de un jugador."""
        match_ids = []
        start_index = 0
        usar_limite_duro = (start_t is None and end_t is None)

        while True:
            url = (
                f"{self.base_routing}/lol/match/v5/matches/by-puuid/{player_obj.puu_id}/ids"
                f"?queue=420&start={start_index}&count=100"
            )
            if start_t:
                url += f"&startTime={start_t}"
            if end_t:
                url += f"&endTime={end_t}"

            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    break
                chunk = await response.json()
                if not chunk:
                    break
                match_ids.extend(chunk)
                start_index += 100

                if usar_limite_duro and len(match_ids) >= max_partidas:
                    break
                if len(chunk) < 100:
                    break

        if usar_limite_duro:
            match_ids = match_ids[:max_partidas]

        match_tasks = [self._fetch_single_match(session, m_id) for m_id in match_ids]
        timeline_tasks = [self._fetch_timeline(session, m_id) for m_id in match_ids]

        matches_data, timelines_data = await asyncio.gather(
            asyncio.gather(*match_tasks),
            asyncio.gather(*timeline_tasks),
        )

        for data, timeline in zip(matches_data, timelines_data):
            if not data:
                continue

            match = self._parse_match(data, player_obj.puu_id, rol_filtro)
            if not match:
                continue

            try:
                p = next(
                    part
                    for part in data["info"]["participants"]
                    if part["puuid"] == player_obj.puu_id
                )
                match.xp_diff_15 = self._calc_xp_diff_15(timeline, p["participantId"])
            except (StopIteration, KeyError):
                match.xp_diff_15 = 0

            player_obj.add_match(match)

    def _calc_xp_diff_15(self, timeline: dict, participant_id: int) -> float:
        """Calcula la diferencia de XP al minuto 15 con el enemigo de carril."""
        if not timeline:
            return 0

        frames = timeline.get("info", {}).get("frames", [])
        if len(frames) <= 15:
            return 0

        frame_15 = frames[15]
        participant_frames = frame_15.get("participantFrames", {})

        player_xp = participant_frames.get(str(participant_id), {}).get("xp", 0)
        opponent_id = participant_id + 5 if participant_id <= 5 else participant_id - 5
        opponent_xp = participant_frames.get(str(opponent_id), {}).get("xp", 0)

        return player_xp - opponent_xp

    async def _fetch_timeline(self, session: aiohttp.ClientSession, match_id: str) -> dict | None:
        """Obtiene el timeline minuto a minuto de una partida con reintentos."""
        url = f"{self.base_routing}/lol/match/v5/matches/{match_id}/timeline"

        for _ in range(3):
            async with self.semaphore:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        retry_after = float(response.headers.get("Retry-After", 2))
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        return None
        return None