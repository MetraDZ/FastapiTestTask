from enum import Enum
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserModel(BaseModel):
    username: str
    email: str


class UserRegistration(UserModel):
    password: str


class UserDB(UserModel):
    hashed_password: str


class UserPostAction(Enum):
    LIKE = 'like'
    UNLIKE = 'unlike'