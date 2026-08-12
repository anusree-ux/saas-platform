from fastapi import FastAPI

from app.routers import events, tenants


app = FastAPI()

app.include_router(tenants.router)
app.include_router(events.router)

@app.get("/")
def root():
    return {"message": "Analytics Platform API is running"}
