# from app.routers import user
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.db import db
import uvicorn
print('hello')
# from routers import user

app = FastAPI()
origins = ["*"]
# app.include_router(user.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# domain where this api is hosted for example : localhost:5000/docs to see swagger documentation automagically generated.


@app.get("/")
async def root():
    return {"message": "money-management api V0.0.1!"}


@app.get('/allUsers')
async def get_all_users():
    all = all_users = await db['users'].find({}, {"password": 0}).to_list(1000)
    return all
