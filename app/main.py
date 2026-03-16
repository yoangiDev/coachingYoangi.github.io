from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.routes import router as api_router

# Cargamos las variables de entorno (el archivo .env)
load_dotenv()

app = FastAPI(title="Riot Stats API", version="1.0")

# Configuramos CORS para permitir peticiones desde tu Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectamos las rutas
app.include_router(api_router, prefix="/api/v1")