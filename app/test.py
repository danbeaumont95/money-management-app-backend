from fastapi.testclient import TestClient
import os
from .main import app
client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "money-management api V0.0.1!"}


def test_login():
    email = os.getenv('test_login_email')
    password = os.getenv('test_login_password')

    response = client.post(
        '/user/login', json={"email": email, "password": password})
    access_token_exists = 'access_token' in response.json()
    refresh_token_exists = 'refresh_token' in response.json()

    assert response.status_code == 200
    assert access_token_exists
    assert refresh_token_exists
