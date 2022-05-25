from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import user
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

# uvicorn app.main:app --reload
# source ./django_env/bin/activate


@app.get("/")
async def root():
    return {"message": "money-management api V0.0.1!"}
