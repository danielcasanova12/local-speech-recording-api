from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import microphones, recording, streaming


app = FastAPI(title="API local de gravação", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(microphones.router)
app.include_router(recording.router)
app.include_router(streaming.router)


@app.get("/health")
def health():
    return {"success": True, "message": "API local de gravação ativa."}

