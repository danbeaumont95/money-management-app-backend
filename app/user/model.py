from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    firstName: str = Field(...)
    lastName: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)
    mobileNumber: int = Field(...)
    username: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "firstName": "Jane",
                "lastName": "Doe",
                "email": "test@email.com",
                "password": "password",
                "username": "janedoe",
                "mobileNumber": 447515538351,
            }
        }


class UserLoginSchema(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "email": "test@hotmail.com",
                "password": "password"
            }
        }


class SessionModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    accessToken: str = Field(...)
    userId: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "accessToken": "accesstoken",
            }
        }


class UserImagesModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    images: list = Field(...)
    userId: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "accessToken": "accesstoken",
            }
        }
