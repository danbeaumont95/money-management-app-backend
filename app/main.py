from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
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
# go to app file and run pytest test.py -o log_cli=true -s


@app.get("/")
async def root():
    return {"message": "money-management api V0.0.1!"}


client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "moneys-management api V0.0.1!"}
