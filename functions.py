from datetime import datetime, time, timedelta, date
import random
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from db import Post, Session, User, user_post_likes_association
from classes import UserDB, UserRegistration, TokenData
from constants import MINIMUM_PASSWORD_LENGTH, MINIMUM_USERNAME_LENGTH, SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')
pwd_context = CryptContext(schemes=['bcrypt'], deprecated = "auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(username: str):
    with Session.begin() as session:
        user = session.query(User).where(User.username==username).scalar()
        if user:
            return UserDB(**user.__dict__)
    
def check_and_extract_data(user_data: UserRegistration):
    if get_user(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username already exists",
        )
    if len(user_data.username) < MINIMUM_USERNAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username must be at least {MINIMUM_USERNAME_LENGTH} characters long",
        )
    if user_data.username[0].isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can't start with digit",
        )
    if len(user_data.password) < MINIMUM_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters long",
        )
    return user_data.model_dump()

def add_user_to_db(user_data: dict):
    with Session.begin() as session:
        new_user = User(
            username=user_data["username"],
            hashed_password = get_password_hash(user_data['password']),
            email = user_data['email']
        )
        session.add(new_user)
        session.commit()

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def update_user_last_login(user: UserDB):
    with Session.begin() as session:
        user = session.query(User).where(User.username == user.username).scalar()
        user.last_login = datetime.now()
        user.last_request = datetime.now()
        session.commit()

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if not username:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if not user:
        raise credentials_exception
    return user

def like_post(session, username: str, post_id: int, like_date: date | None = None):
    user = session.query(User).where(User.username==username).scalar()
    post = session.query(Post).where(Post.id == post_id).scalar()

    if post:
        post.number_of_likes += 1
        if like_date:
            random_time = time(random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
            needed_date = datetime.combine(like_date, random_time)
            like = session.execute(user_post_likes_association.insert().values(
                user_id = user.id, 
                post_id = post.id, 
                date = needed_date
            ))
        else:
            post.liked_by.append(user)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No post with such id',
        )


def unlike_post(session, username: str, post_id: int):
    user = session.query(User).where(User.username==username).scalar()
    post = session.query(Post).where(Post.id == post_id).scalar()

    if user in post.liked_by:
        post.number_of_likes -= 1
        id_of_like_to_delete = session.query(
            user_post_likes_association.c.id
            ).filter(
                user_post_likes_association.c.user_id == user.id, 
                user_post_likes_association.c.post_id == post.id
            ).first()[0]
        delete_like = session.query(
            user_post_likes_association
            ).filter(
                user_post_likes_association.c.user_id == user.id, 
                user_post_likes_association.c.post_id == post.id,
                user_post_likes_association.c.id == id_of_like_to_delete
            ).delete(synchronize_session=False)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can't unlike post you didn't liked previously",
        )