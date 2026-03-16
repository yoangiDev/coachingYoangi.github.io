# YGG Performance Tracker

Herramienta de coaching para League of Legends que rastrea el rendimiento de un jugador a lo largo del tiempo mediante medias móviles. Construida con **FastAPI** + **Vanilla JS**.

---

## Requisitos

- Python 3.10+
- Una cuenta en [Riot Games Developer](https://developer.riotgames.com)
- Una API Key de Riot válida (se regenera cada 24h en el portal de desarrolladores)

---

## Instalación

### 1. Clona el repositorio

```bash
git clone https://github.com/yoangiDev/ygg-tracker.git
cd ygg-tracker
```

### 2. Crea y activa un entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

### 3. Instala las dependencias

```bash
pip install fastapi uvicorn aiohttp python-dotenv
```

### 4. Configura tu API Key

Crea un archivo `.env` en la raíz del proyecto:

```bash
# .env
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
---

## Estructura del proyecto

```
ygg-tracker/
├── app/
│   ├── api/
│   │   └── routes.py          # Endpoints de la API
│   ├── models/
│   │   ├── match.py           # Modelo de datos de partida
│   │   └── player.py          # Modelo de jugador + medias móviles
│   ├── services/
│   │   └── riot_client.py     # Cliente asíncrono de la API de Riot
│   ├── exceptions.py          # Excepciones personalizadas
│   └── main.py                # Punto de entrada de FastAPI
├── index.html                 # Página de búsqueda
├── dashboard.html             # Dashboard del jugador
├── .env                       # API Key
└── README.md
```

---

## Ejecución

### 1. Arranca el servidor backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Deberías ver algo así en la terminal:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process
```

### 2. Abre el frontend

Abre `index.html` directamente en tu navegador (doble clic o arrástralo a Chrome/Firefox).

> El frontend se conecta a `http://localhost:8000` por defecto. Asegúrate de que el backend está corriendo antes de buscar un jugador.

### 3. Busca un jugador

Rellena la región, el nombre de invocador y el tag (ej. `Faker` `#KR1`) y pulsa **Search** o presiona **Enter**.

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/player/stats` | Obtiene estadísticas, historial de partidas y medias móviles del jugador |

### Parámetros

| Parámetro | Tipo | Por defecto | Descripción |
|-----------|------|-------------|-------------|
| `game_name` | `string` | requerido | Nombre de invocador |
| `tag_line` | `string` | requerido | Tag (sin #) |
| `routing` | `string` | `europe` | Región de enrutamiento de Riot (`europe`, `americas`, `asia`) |
| `platform` | `string` | `euw1` | Plataforma de Riot (`euw1`, `na1`, `kr`, etc.) |
| `rol` | `string` | `BOTTOM` | Filtro de rol (`ALL`, `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `UTILITY`) |
| `limit` | `int` | `20` | Número máximo de partidas a obtener |
| `fecha_inicio` | `string` | `null` | Fecha de inicio del filtro (`YYYY-MM-DD`) |
| `fecha_fin` | `string` | `null` | Fecha de fin del filtro (`YYYY-MM-DD`) |
| `ventana_movil` | `int` | `10` | Tamaño de la ventana de media móvil |

---

## APIs de Riot utilizadas

| API | Uso |
|-----|-----|
| **Account-v1** | Resuelve nombre + tag → PUUID |
| **Summoner-v4** | Obtiene el icono de perfil y el nivel del invocador |
| **League-v4** | Obtiene el tier, división y LP del ranked |
| **Match-v5** | Obtiene lista de partidas, detalles y timelines (XP diff @15) |

---

## Notas sobre la API Key de desarrollo

Las claves de desarrollo caducan cada **24 horas**. Si obtienes un error `502`, ve a [developer.riotgames.com](https://developer.riotgames.com), regenera tu clave y actualiza el archivo `.env`.

Las claves de desarrollo también tienen límites de uso estrictos (**20 req/s, 100 req/2min**). Si ves errores `429`, espera 1-2 minutos antes de volver a intentarlo.

---

## Hecho por [Yoangi](https://x.com/yoangichan)
