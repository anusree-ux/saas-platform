from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.websocket import router as websocket_router
from app.routers.analytics import router as analytics_router
from app.routers import events, tenants


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants.router)
app.include_router(events.router)
app.include_router(websocket_router)
app.include_router(analytics_router)


@app.get("/")
def root():
    return {"message": "Analytics Platform API is running"}