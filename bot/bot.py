import random
from typing import List
import requests
import json
import string
from enum import Enum
from threading import Thread
from datetime import datetime, timedelta

class Endpoint(Enum):
    LOGIN = '/login'
    REGISTER = '/register'
    CREATE_POST = '/create_post'
    RATE_POST = '/rate_post'
    POSTS = '/posts/'
    LIKE_ANALITICS = '/like_analytics'


class RateType(Enum):
    LIKE = 'like'
    

class Bot():
    class User():
        def __init__(self, username, password) -> None:
            self.username = username
            self.password = password
            self.access_token = ''
            self.posts_made = 0
            self.liked_sent = 0
        
        def __repr__(self):
            return f"{self.username}:{self.password}"

    url = 'http://127.0.0.1:8000'

    def __init__(
            self, 
            number_of_users: int, 
            max_posts_per_user: int,
            max_likes_per_user: int) -> None:
        self.number_of_users = number_of_users
        self.max_posts_per_user = max_posts_per_user
        self.max_likes_per_user = max_likes_per_user
        self.users: List[self.User] = []
    
    def set_up_users(self):
        for _ in range(self.number_of_users):
            user = self.User(**{
                "username": ''.join(random.choices(string.ascii_lowercase, k=5)),
                "password": ''.join(random.choices(string.ascii_lowercase, k=6)),
            })
            self.users.append(user)

    def sign_up_user(self, user) -> bool:
        is_registered = requests.post(
            url=self.url + Endpoint.REGISTER.value,
            json={
                "username": user.username,
                "email": f"{user.username}@example.com",
                "password": user.password
            }
        ).status_code
        return is_registered == 201
    
    def sign_in_user(self, user) -> str:
        token = requests.post(
            url=self.url + Endpoint.LOGIN.value, 
            data={
                'username': user.username,
                'password': user.password,
                'grant_type': 'password'
            }
        ).json()['access_token']
        user.access_token = token
        return token

    def create_posts(self, user: User) -> bool:
        results = []
        for i in range(self.max_posts_per_user):
            is_post_created = requests.post(
                url=self.url + Endpoint.CREATE_POST.value,
                params={
                    'post_text': f'Post number {i}, created by {user.username}'
                },
                headers={'Authorization': f'Bearer {user.access_token}'}
            ).status_code
            results.append(is_post_created)
        return all(el == 201 for el in results)

    def get_posts_ids(self, user: User) -> List[int]:
        ids = []
        page = 1
        per_page = 50
        while True:
            posts = requests.get(
                url=self.url + Endpoint.POSTS.value,
                params={'per_page': per_page, 'page': page},
                headers={'Authorization': f'Bearer {user.access_token}'}
            ).json()['posts']
            if len(posts) <= per_page and len(posts) > 0:
                ids.extend([post['id'] for post in posts])
                page += 1
                continue
            break
        return ids

    def like_posts(self, user: User, post_ids: List[int]) -> bool:
        results = []
        for _ in range(self.max_likes_per_user):
            is_liked = requests.post(
                url=self.url + Endpoint.RATE_POST.value,
                params={
                    'action': RateType.LIKE.value,
                    'post_id': random.choice(post_ids),
                    'like_date': datetime.strftime(datetime.now() - timedelta(days=random.randint(1, 30)), '%Y-%m-%d')
                },
                headers={'Authorization': f'Bearer {user.access_token}'}
            ).status_code
            results.append(is_liked)
        return all(el == 200 for el in results)
    
    def like_analytics(self, user: User) -> dict:
        result = requests.get(
            url=self.url + Endpoint.LIKE_ANALITICS.value,
            params={
                'start_date': datetime.strftime(datetime.now() - timedelta(days=31), '%Y-%m-%d'),
                'end_date': datetime.strftime(datetime.now() + timedelta(days=1), '%Y-%m-%d')
            },
            headers={'Authorization': f'Bearer {user.access_token}'}
        ).json()
        return result
    
    def start(self, user: User):
        self.sign_up_user(user)
        self.sign_in_user(user)
        self.create_posts(user)
        posts_ids = self.get_posts_ids(user)
        self.like_posts(user, posts_ids)

if __name__ == "__main__":
    with open("conf.json", "r") as file:
        config = json.load(file)

    bot = Bot(**config)
    bot.set_up_users()

    threads = []
    
    for i in range(bot.number_of_users):
        thread = Thread(target=bot.start, args=(bot.users[i],))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    analytics = bot.like_analytics(bot.users[0])

    print('Like analytics: \n')
    for date, likes in analytics.items():
        print(f'{date}:')
        for like_data in likes:
            for user, number_of_likes in like_data.items():
                print(f'User {user} received {number_of_likes}')