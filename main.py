# from app.routers import user
from app.routers import user
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.db import db
import uvicorn
# from routers import user
# uvicorn main:app --reload

app = FastAPI()
origins = ["*"]
app.include_router(user.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "money-management api V0.0.1!"}
