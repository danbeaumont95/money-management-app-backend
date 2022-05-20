from fastapi import APIRouter, Request, Body, HTTPException, status, APIRouter
import time
import jwt
from typing import Dict
from fastapi.encoders import jsonable_encoder
from ..user.model import UserModel
from ..db import db, jwt_algorithm, jwt_secret
from email_validator import validate_email, EmailNotValidError
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/user",
    tags=['user']
    # dependencies=[Depends(get_token_header)],
    # responses={404: {"description": "Not found"}},
)


def decodeJWT(token: str) -> dict:
    try:
        decoded_token = jwt.decode(
            token, jwt_secret, algorithms=[jwt_algorithm])
        return decoded_token if decoded_token['expires'] >= time.time() else None
    except:
        return {}


def token_response(access_token: str, refresh_token: str):
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


def signJWT(user_id: str) -> Dict[str, str]:
    access_payload = {
        "user_id": user_id,
        "expires": time.time() + 600
    }
    refresh_payload = {
        "user_id": user_id,
        "expires": time.time() + 30000000
    }
    access_token = jwt.encode(
        access_payload, jwt_secret, algorithm=jwt_algorithm)
    refresh_token = jwt.encode(
        refresh_payload, jwt_secret, algorithm=jwt_algorithm)
    return token_response(access_token, refresh_token)


async def check_if_user_taken(input: str, value: str):
    user_exists = await db['users'].find_one({f"{value}": input})
    return user_exists


@router.post('/', tags=['user'])
async def create_user(user: UserModel = Body(...)):
    user = jsonable_encoder(user)
    if len(user['firstName']) < 1 or len(user['lastName']) < 1 or len(user['email']) < 1 or len(user['password']) < 1 or len(user['username']) < 1 or len(str(user['mobileNumber'])) < 1:
        return {"error": "Missing required field"}
    try:
        validate_email(user['email']).email
        email_taken = await check_if_user_taken(user['email'], 'email')
        username_taken = await check_if_user_taken(user['username'], 'username')
        mobileNumber_taken = await check_if_user_taken(user['mobileNumber'], 'mobileNumber')

        if email_taken != None:
            return {"error": "Email Already exists"}
        if username_taken != None:
            return {"error": "Username Already exists"}
        if mobileNumber_taken != None:
            return {"error": "Mobile Number Already exists"}

        new_user = await db['users'].insert_one(user)
        created_user = await db['users'].find_one({"_id": new_user.inserted_id})

        return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_user)
    except EmailNotValidError as e:
        return {"error": str(e)}
