from fastapi import APIRouter, Request, Body, HTTPException, status, APIRouter
import time
import jwt
from typing import Dict
from fastapi.encoders import jsonable_encoder
from ..user.model import UserModel, UserLoginSchema, SessionModel
from ..db import db, jwt_algorithm, jwt_secret
from email_validator import validate_email, EmailNotValidError
from fastapi.responses import JSONResponse
from collections import namedtuple
from flask import jsonify
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import boto3
import requests
import base64
import os
import json
from botocore.exceptions import ClientError
from fastapi import UploadFile, File

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


async def save_token_in_db(token: SessionModel = Body(...), id: str = Body(...)):
    token = jsonable_encoder(token)
    userId = jsonable_encoder(id)
    insert_obj = {"token": token, "userId": userId}
    already_in_db = await db['user-sessions'].find_one({"userId": userId})

    if already_in_db is None:
        new_token = await db['user-sessions'].insert_one(jsonable_encoder(insert_obj))
        created_token = await db['user-sessions'].find_one({"_id": new_token.inserted_id})
        return created_token
    else:
        await db['user-sessions'].update_one({"userId": userId}, {"$set": {
            "token": insert_obj['token']
        }})


async def get_user(email):
    if (user := await db['users'].find_one({"email": email})) is not None:
        return user
    raise HTTPException(status_code=404, detail=f"User {id} not found")


def new_token_response(access_token: str):
    return {
        "access_token": access_token
    }


def sign_new_jwt(user_id: str) -> Dict[str, str]:
    access_payload = {
        "user_id": user_id,
        "expires": time.time() + 600
    }
    access_token = jwt.encode(
        access_payload, jwt_secret, algorithm=jwt_algorithm)
    return new_token_response(access_token)


async def reIssueAccessToken(token):

    def decodeJWT(token: str) -> dict:
        decoded_token = jwt.decode(
            token, jwt_secret, algorithms=[jwt_algorithm])
        return decoded_token if decoded_token['expires'] <= time.time() else None

    new_decoded = decodeJWT(token)

    new_token = sign_new_jwt(new_decoded['user_id'])

    await save_token_in_db(new_token, str(new_decoded['user_id']))
    return new_token


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

        password = user['password'].encode("utf-8")
        encoded = base64.b64encode(password)
        # decoded = base64.b64decode(encoded)

        user['password'] = str(encoded, 'utf-8')

        await db['users'].insert_one(user)

        created_user = await db['users'].find_one({"email": user['email']})

        await db['userImagesModel'].insert_one({'userId': user['_id'], 'images': []})

        return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_user)
    except EmailNotValidError as e:
        return {"error": str(e)}


@router.post('/login')
async def login(user: UserLoginSchema = Body(...)):
    async def check_user(data=Body(...)):

        all_users = await db['users'].find().to_list(1000)
        for user in all_users:
            del user['_id']
            object_name = namedtuple("ObjectName", user.keys())(*user.values())

            if object_name.email == data.email and str(base64.b64decode(object_name.password), 'utf-8') == data.password:
                return True
        return False

    res = await check_user(user)

    if res:
        user = jsonable_encoder(user)
        user_details = await get_user(user['email'])
        user_id = user_details['_id']
        token = signJWT(user_id)

        await save_token_in_db(token, str(user_id))
        return_obj = {
            'user_id': user_id,
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token']
        }

        return return_obj
    return {
        "error": "Wrong login details"
    }


@router.get('/getLinkToken')
async def getPlaidLinkToken(request: Request):
    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        user_id = isAllowed['user_id']
        plaid_client_id = os.getenv('plaid_client_id')
        secret = os.getenv('plaid_development_secret')
        data = {
            'client_id': plaid_client_id,
            'secret': secret,
            'client_name': 'Dans app',
            'country_codes': ['gb'],
            'language': 'en',
            'user': {
                'client_user_id': user_id,
            },
            # 'products': ['auth']
            'products': ['auth', 'transactions']
        }
        token = requests.post(
            'https://development.plaid.com/link/token/create', data=json.dumps(data), headers={'Content-type': 'application/json'})

        jsonified = json.loads(token.text)
        if jsonified['link_token']:
            return JSONResponse(status_code=status.HTTP_201_CREATED, content={'token': jsonified['link_token']})
        else:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={'error': 'Error getting token'})
    else:
        return {"error": "Unable to verify, please log in again"}


@router.post('/exchangePublicToken')
async def exchange_public_token_for_access_token(request: Request, public_token=Body(...)):

    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        plaid_client_id = os.getenv('plaid_client_id')
        secret = os.getenv('plaid_development_secret')
        data = {
            'client_id': plaid_client_id,
            'secret': secret,
            'public_token': public_token['public_token']
        }
        try:

            access_token = requests.post(
                'https://development.plaid.com/item/public_token/exchange', data=json.dumps(data), headers={'Content-type': 'application/json'})

            jsonified = json.loads(access_token.text)

            access = jsonified['access_token']

            # decoded = base64.b64decode(encoded)

            new_access_token = access.encode("utf-8")

            encoded = base64.b64encode(new_access_token)

            user_id = isAllowed['user_id']
            insert_obj = {
                "token": str(encoded, 'utf-8'), "userId": user_id}
            already_has_access_token = await db['plaidAccessTokens'].find_one({"userId": user_id})

            if already_has_access_token is None:

                await db['plaidAccessTokens'].insert_one(jsonable_encoder(insert_obj))
            else:
                await db['plaidAccessTokens'].update_one({"userId": user_id}, {"$set": {
                    "token": str(encoded, 'utf-8')
                }})

            return {"accessToken": str(encoded, 'utf-8')}
        except:
            return {"error": "Unable to link accounts"}
    else:
        return {"error": "Unable to verify, please log in again"}


@router.get('/decodeAccessToken')
async def exchange_public_token_for_access_token(request: Request):

    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        user_id = isAllowed['user_id']
        token = await db['plaidAccessTokens'].find_one({"userId": user_id})

        decoded = base64.b64decode(token['token'])

        return {"token": decoded}
    else:
        return {"error": "Unable to verify, please log in again"}


@router.get('/getTransactions/{time}')
async def get_all_transactions(request: Request, time: str):

    today = datetime.today().strftime('%Y-%m-%d')

    if time == 'day':
        start_date = date.today() + relativedelta(days=-1)
    if time == 'week':
        start_date = date.today() + relativedelta(weeks=-1)
    if time == 'month':
        start_date = date.today() + relativedelta(months=-1)
    if time == 'year':
        start_date = date.today() + relativedelta(years=-1)

    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        user_id = isAllowed['user_id']
        token = await db['plaidAccessTokens'].find_one({"userId": user_id})

        if token is None:
            return {"message": "No linked accounts"}

        decoded = base64.b64decode(token['token'])

        plaid_access_token = decoded.decode("utf-8")

        plaid_client_id = os.getenv('plaid_client_id')
        secret = os.getenv('plaid_development_secret')
        data = {
            'client_id': plaid_client_id,
            'secret': secret,
            'access_token': plaid_access_token,
            'start_date': str(start_date),
            'end_date': today
        }
        if token is None:
            return {"message": "No linked accounts"}
        res = requests.post('https://development.plaid.com/transactions/get',
                            data=json.dumps(data), headers={'Content-type': 'application/json'})

        all_transaction_info = json.loads(res.text)
        print(all_transaction_info, 'all_transaction_info123')
        if 'error_code' in all_transaction_info:
            return {"error": "Need to link account again"}
        transactions = all_transaction_info['transactions']

        return {"transactions": transactions}
    else:
        return {"error": "Unable to verify, please log in again"}


@router.get('/linkedAccounts')
async def get_all_transactions(request: Request):

    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        user_id = isAllowed['user_id']
        token = await db['plaidAccessTokens'].find_one({"userId": user_id})

        decoded = base64.b64decode(token['token'])

        plaid_access_token = decoded.decode("utf-8")

        plaid_client_id = os.getenv('plaid_client_id')
        secret = os.getenv('plaid_development_secret')
        data = {
            'client_id': plaid_client_id,
            'secret': secret,
            'access_token': plaid_access_token,
        }
        if token is None:
            return {"message": "No linked accounts"}
        res = requests.post('https://development.plaid.com/accounts/get',
                            data=json.dumps(data), headers={'Content-type': 'application/json'})

        jsonified = json.loads(res.text)

        accounts = jsonified['accounts']
        return {"accounts": accounts}
    else:
        return {"error": "Unable to verify, please log in again"}


@router.post('/refreshToken', tags=['user'], response_description="Returns a new access token if original access token has expired")
async def refresh_token(request: Request):

    refresh_token = request.headers.get('x-refresh')

    bearer_token = request.headers.get('authorization')

    if refresh_token is None or bearer_token is None:
        return {"error": "Missing token"}

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is None and refresh_token:
        new_access_token = await reIssueAccessToken(access_token)
        return new_access_token
    return


@router.get('/getMe', tags=['user'], response_description="Returns logged in users details")
async def get_my_details(request: Request):
    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        user_id = isAllowed['user_id']
        user = await db['users'].find_one({"_id": user_id})
        return user
    return {"error": "Unable to verify, please log in again"}


@router.patch('/updateMyDetails', tags=['user'], response_description="Updates logged in users details")
async def update_my_details(request: Request, user_details=Body(...)):
    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        user_id = isAllowed['user_id']
        firstName, lastName, email, mobileNumber, username, password = itemgetter(
            'firstName', 'lastName', 'email', 'mobileNumber', 'username', 'password')(user_details)

        encoded_password = password.encode("utf-8")
        encoded = base64.b64encode(encoded_password)

        new_password = str(encoded, 'utf-8')

        await db['users'].update_one({"_id": user_id}, {"$set": {
            "firstName": firstName,
            "lastName": lastName,
            "email": email,
            "mobileNumber": mobileNumber,
            "username": username,
            "password": new_password
        }})
        return {'message': 'Details updated'}
    return {"error": "Unable to verify, please log in again"}


@router.post('/uploadImage', tags=['user'], response_description='uploads an image')
async def update_user_image(request: Request, fileobject: UploadFile = File(...)):
    print(request, 'reww')
    bearer_token = request.headers.get('authorization')

    access_token = bearer_token[7:]

    isAllowed = decodeJWT(access_token)

    if isAllowed is not None:
        filename = fileobject.filename

        current_time = datetime.now()
        split_file_name = os.path.splitext(filename)

        file_name_unique = str(current_time.timestamp()).replace('.', '')

        file_extension = split_file_name[1]  # file extention

        data = fileobject.file._file  # Converting tempfile.SpooledTemporaryFile to io.BytesIO

        uploads3 = await upload_fileobj(
            data,  'python-e-commerce-app', filename)
        if uploads3:
            created_item = {
                "userId": isAllowed['user_id'], "image": f"https://python-e-commerce-app.s3.eu-west-2.amazonaws.com/{filename}"}

            # new_item = await db['userImagesModel'].insert_one(created_item)
            test = await db['userImagesModel'].find_one({'userId': isAllowed['user_id']})

            new_item = await db['userImagesModel'].find_one_and_update({'userId': isAllowed['user_id']}, {"$push": {
                "images": f"https://python-e-commerce-app.s3.eu-west-2.amazonaws.com/{filename}"
            }})

            """
            test = await db['addresses'].find_one_and_update({"userId": user_id, "addresses.id": id}, {"$set": {
                      "addresses.$.firstLine": body['firstLine'],
                      "addresses.$.secondLine": body['secondLine'],
                      "addresses.$.TownCity": body['TownCity'],
                      "addresses.$.Postcode": body['Postcode'],
                      "addresses.$.Country": body['Country']
                  }})



            """

            return {"status": True, "message": "Item inserted in DB"}
        else:
            raise HTTPException(
                status_code=400, detail="Failed to upload in S3")
    else:
        return {
            "Message": "Token expired, please log in again"
        }


async def upload_fileobj(file_name, bucket, key):

    """Upload a file to an S3 bucket
    :param key:
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if (key is None) or (bucket is None):
        print("key and bucket cannot be None")
        return False

    # Upload the file
    s3_client = boto3.client('s3')

    try:

        response = s3_client.upload_fileobj(
            file_name, bucket, key, ExtraArgs={'ACL': 'public-read'})

    except ClientError as e:
        print("INFO: Failed to upload image")
        print(e)
        return False

    print(
        "File object uploaded to https://s3.amazonaws.com/{}{}".format(bucket, key))
    return True
