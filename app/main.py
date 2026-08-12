from fastapi import FastAPI
from app.routers.websocket import router as websocket_router

from app.routers import events, tenants


app = FastAPI()

app.include_router(tenants.router)
app.include_router(events.router)
app.include_router(websocket_router)

@app.get("/")
def root():
    return {"message": "Analytics Platform API is running"}
