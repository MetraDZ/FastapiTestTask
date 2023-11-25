from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import Response, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
import uvicorn

from db import Session, User, Post, user_post_likes_association
from constants import ACCESS_TOKEN_EXPIRE_MINUTES
from classes import Token, UserModel, UserPostAction
from functions import authenticate_user, unlike_post, update_user_last_login,\
    create_access_token, check_and_extract_data, add_user_to_db, \
    get_current_user, like_post

app = FastAPI()

@app.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    update_user_last_login(user)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", response_class=Response)
async def register(user_data: Annotated[dict, Depends(check_and_extract_data)]):
    add_user_to_db(user_data)
    return Response('Successful registration', status_code=status.HTTP_201_CREATED)

@app.get("/user/", response_class=JSONResponse)
async def read_user(
    current_user: Annotated[UserModel, Depends(get_current_user)]
):
    with Session.begin() as session:
        user = session.query(User).where(User.username == current_user.username).scalar()
        user.last_request = datetime.now()
        response = user.to_dict()
        session.commit()
    return response

@app.post("/create_post", response_class=Response)
async def create_post(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    post_text: str
):
    with Session.begin() as session:
        author = session.query(User).where(User.username==current_user.username).scalar()
        new_post = Post(text=post_text, number_of_likes = 0)
        new_post.created_by = author.id
        author.last_request = datetime.now()
        session.add(new_post)
        session.commit()
    return Response('Post successfully created', status_code=status.HTTP_201_CREATED)

@app.post("/rate_post", response_class=Response)
async def rate_post(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    action: UserPostAction,
    post_id: int,
    like_date: date | None = None
):
    with Session.begin() as session:
        user = session.query(User).where(User.username==current_user.username).scalar()

        if action == UserPostAction.LIKE:
            like_post(session, current_user.username, post_id, like_date)
            message = 'Post liked successfully'
        else:
            unlike_post(session, current_user.username, post_id)
            message = 'Post unliked successfully'
            
        user.last_request = datetime.now()
        session.commit()
    return Response(message, status_code=status.HTTP_200_OK)

@app.get(
        "/like_analytics/", 
        response_class=JSONResponse, 
        description="Returns info about count of received likes by every user"
)
def like_analytics(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    start_date: date,
    end_date: date
):
    with Session.begin() as session:
        result = session.query(
            func.DATE(user_post_likes_association.c.date).label('date'),
            User.username.label('user_username'),
            func.count().label('like_count')
        ) \
        .join(Post, user_post_likes_association.c.post_id == Post.id)\
        .join(User, Post.created_by == User.id) \
        .filter(user_post_likes_association.c.date.between(start_date, end_date)) \
        .group_by(func.DATE(user_post_likes_association.c.date), User.username) \
        .all()

        result.sort(key = lambda x: x[0])
        response = defaultdict(list)
        for date, username, number_of_likes in result:
            response[date.strftime("%Y-%m-%d")].append({username: f'{number_of_likes} likes'})

        return JSONResponse(response, status_code=status.HTTP_200_OK)

@app.get('/posts/', response_class=JSONResponse)
def view_posts(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    per_page: int = 50,
    page: int = 1
):
    response = []
    with Session.begin() as session:
        posts = session.query(
            Post.id, 
            Post.text, 
            Post.number_of_likes, 
            Post.created_at, 
            User.username
        ).join(User, Post.created_by == User.id).limit(per_page).offset((page - 1) * per_page).all()

    response = [
        {
            'id': _id,
            'text': text,
            'number_of_likes': number_of_likes,
            'created_at': str(created_at),
            'username': username
        } for _id, text, number_of_likes, created_at, username in posts
    ]
    return JSONResponse({'posts': response}, status_code=status.HTTP_200_OK)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True, log_level='debug')