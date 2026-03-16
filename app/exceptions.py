class PlayerNotFoundError(Exception):
    """El jugador no existe en la región indicada."""
    pass


class RiotAPIError(Exception):
    """Error de comunicación con la API de Riot Games."""
    pass