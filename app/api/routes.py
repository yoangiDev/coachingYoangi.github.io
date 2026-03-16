import os
import aiohttp
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.models.player import Player
from app.services.riot_client import RiotAPIClient
from app.exceptions import PlayerNotFoundError, RiotAPIError

# Creamos un router de FastAPI para agrupar endpoints relacionados.
router = APIRouter()


@router.get("/player/stats")
async def get_player_stats(
    game_name: str,
    tag_line: str,
    fecha_inicio: str = Query(None, description="Formato YYYY-MM-DD"),
    fecha_fin: str = Query(None, description="Formato YYYY-MM-DD"),
    rol: str = "BOTTOM",
    ventana_movil: int = 10,
    routing: str = "europe",
    platform: str = "euw1",
    limit: int = Query(20, description="Número máximo de partidas a devolver"),
):
    """Endpoint para obtener estadísticas de un jugador de Riot.

    Parámetros:
    - game_name, tag_line: identificadores del jugador.
    - fecha_inicio, fecha_fin: rango de fechas (opcional).
    - rol: rol en la partida (por defecto BOTTOM).
    - ventana_movil: tamaño de ventana para media móvil.
    - routing, platform: configuración de servidor Riot.
    - limit: máximo de partidas a devolver.
    """

    # Obtenemos la clave de API desde variable de entorno.
    api_key = os.getenv("RIOT_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="API Key de Riot no configurada en el servidor")

    # Inicializamos filtros temporales en None si no se proporcionan.
    epoch_inicio = None
    epoch_fin = None

    # Convertimos fecha_inicio a timestamp en segundos.
    if fecha_inicio:
        try:
            epoch_inicio = int(datetime.strptime(fecha_inicio, "%Y-%m-%d").timestamp())
        except ValueError:
            raise HTTPException(status_code=400, detail="El formato de fecha_inicio debe ser YYYY-MM-DD")

    # Convertimos fecha_fin a timestamp hasta el último segundo del día.
    if fecha_fin:
        try:
            epoch_fin = int(
                datetime.strptime(fecha_fin, "%Y-%m-%d")
                .replace(hour=23, minute=59, second=59)
                .timestamp()
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="El formato de fecha_fin debe ser YYYY-MM-DD")

    # Instanciamos el cliente Riot con las credenciales y la región.
    client = RiotAPIClient(api_key, routing, platform)

    # Usamos sesión HTTP asíncrona para llamar a Riot API.
    async with aiohttp.ClientSession() as session:
        try:
            # Primero obtenemos el puuid del jugador usando nombre y tag.
            puuid = await client.get_puuid(session, game_name, tag_line)

            # Creamos el objeto de dominio Player con datos básicos.
            alumno = Player(game_name, tag_line, routing, platform, puuid)

            # Cargamos información adicional del summoner.
            await client.fetch_summoner_info(session, alumno)

            # Cargamos el rango de clasificación del jugador.
            await client.fetch_player_rank(session, alumno)

            # Obtenemos historial de partidas con filtros de fecha, rol y límite.
            await client.fetch_matches(
                session,
                alumno,
                start_t=epoch_inicio,
                end_t=epoch_fin,
                rol_filtro=rol,
                max_partidas=limit,
            )

            # Generamos métricas de medias móviles para los datos de la partida.
            ma_data = alumno.generate_moving_averages(window_size=ventana_movil)

            # Si no hay datos válidos, devolvemos lista vacía.
            if ma_data is None:
                ma_data = []

            # Formateamos texto de rango (ELO) para devolver en la respuesta.
            rango_texto = (
                f"{alumno.tier} {alumno.rank} ({alumno.lp} LP)"
                if alumno.tier != "UNRANKED"
                else "Unranked"
            )

            # Construimos el objeto player_info con información esencial.
            player_info = {
                "summonerLevel": alumno.summoner_level,
                "profileIconId": alumno.profile_icon_id,
                "rank": rango_texto,
            }

            # Derivamos el historial de partidas con métricas calculadas.
            match_history = [
                {
                    "creation_time": m.creation_time,
                    "championName": m.champ_played,
                    "kills": m.kills,
                    "deaths": m.deaths,
                    "assists": m.assists,
                    "cs": m.total_cs,
                    "cs_min": round(m.calc_cs_min(), 2),
                    "visionScore": m.vision,
                    "damage": m.dmg,
                    "damage_min": round(m.calc_dmg_min(), 0),
                    "damage_share": round(m.dmg_share, 1),
                    "gold": m.gold,
                    "gold_min": round(m.calc_gold_min(), 0),
                    "dmg_gold": round(m.calc_dmg_gold(), 2),
                    "xp_diff_15": round(m.xp_diff_15, 0),
                    "win": m.win,
                }
                for m in alumno.match_history
            ]

            # Devolvemos la respuesta con información de jugador y partidas.
            return {
                "player_info": player_info,
                "moving_averages": ma_data,
                "match_history": match_history,
            }

        except PlayerNotFoundError as e:
            # Si el jugador no existe se devuelve 404.
            raise HTTPException(status_code=404, detail=str(e))
        except RiotAPIError as e:
            # Errores de la API de Riot se convierten a 502.
            raise HTTPException(status_code=502, detail=str(e))
        except HTTPException:
            # Propaga HTTPException existente.
            raise
        except Exception:
            # Error genérico de servidor para casos no previstos.
            raise HTTPException(status_code=500, detail="Error interno del servidor")