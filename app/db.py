import os
import motor.motor_asyncio

from dotenv import load_dotenv
load_dotenv()
db_username = os.getenv("db_username")
db_password = os.getenv("db_password")
jwt_secret = os.getenv('secret')
jwt_algorithm = os.getenv('algorithm')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')

client = motor.motor_asyncio.AsyncIOMotorClient(
    f"mongodb+srv://{db_username}:{db_password}@money-management.xbv9d.mongodb.net/?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
db = client['money-management']
