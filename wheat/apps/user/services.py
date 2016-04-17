# -*- coding:utf-8 -*-

from django.db import transaction
from django.contrib.auth import authenticate, login

from customs.services import BaseService
from customs.response import Result
from errors import codes
from .models import User, AuthToken, FriendShip
from .serializers import UserSerializer, AuthTokenSerializer
import datetime


UserUpdateFields = ('phone', 'marital_status', 'nickname', 'first_name', 'last_name', 'avatar',
                    'tagline', 'gender', 'city', 'province', 'country', 'password')


class UserService(BaseService):

    @classmethod
    def _get_model(cls, name='User'):
        if name == 'User':
            return User
        elif name == 'AuthToken':
            return AuthToken

    @classmethod
    def get_serializer(cls, model='User'):
        if model == 'User':
            return UserSerializer
        elif model == 'AuthToken':
            return AuthTokenSerializer

    @classmethod
    def serialize(cls, obj, context={}):
        if isinstance(obj, User):
            return UserSerializer(obj, context=context).data
        elif isinstance(obj, AuthToken):
            return AuthTokenSerializer(obj, context=context).data

    @classmethod
    def is_logged_in(cls, user):
        return isinstance(user, UserService._get_model())

    @classmethod
    def get_user(cls, **kwargs):
        return User.objects.get_or_none(**kwargs)

    @classmethod
    def get_users(cls, **kwargs):
        return User.objects.filter(**kwargs)

    @classmethod
    @transaction.atomic
    def create_user(cls, phone='', password='', **kwargs):
        user = UserService.get_user(phone=phone)  # phone is unique
        if user:
            return user
        user = User.objects.create_user(phone, password)
        if kwargs:
            UserService.update_user(user, **kwargs)
        return user

    @classmethod
    @transaction.atomic
    def update_user(cls, user, **kwargs):
        PASSWORD = 'password'
        for field in UserUpdateFields:
            if field in kwargs:
                if field == PASSWORD:
                    user.set_password(kwargs[field])
                else:
                    setattr(user, field, kwargs[field])
        user.save()
        return user

    @classmethod
    @transaction.atomic
    def lazy_delete_user(cls, user):
        if user:
            user.update(deleted=True)
            return True
        return False

    @staticmethod
    def set_session_user_id(request, user_id):
        '''
        Set session user id. When user login or created.
        '''
        request.session.setdefault('user_id', user_id)

    @classmethod
    def login_user(cls, request, phone, password):
        user = authenticate(username=phone, password=password)
        if user:
            if user.activated:
                login(request, user)
                UserService.set_session_user_id(request, user.id)
                AuthService.refresh_token(user_id=user.id)
                return Result(data=user)
            else:
                return Result(code=codes.INACTIVE_ACCOUNT)
        else:
            return Result(code=codes.INCORRECT_CREDENTIAL)

    @classmethod
    def check_auth_token(cls, user_id, token):
        token_obj = UserService.get_auth_token(user_id=user_id)
        if token_obj and token_obj.key == token and not token_obj.expired():
            return True
        return False

    @classmethod
    def get_auth_token(cls, **kwargs):
        return AuthToken.objects.get_or_none(**kwargs)

    @classmethod
    @transaction.atomic
    def refresh_auth_token(cls, token):
        token = AuthToken.objects.refresh_token(token)
        return token

    @classmethod
    @transaction.atomic
    def create_friendship(cls, user_a, user_b):
        if user_a == user_b:
            return None
        if user_a > user_b:
            user_a, user_b = user_b, user_a
        friendship, created = FriendShip.objects.get_or_create(user_a=user_a, user_b=user_b)
        return friendship

    @classmethod
    @transaction.atomic
    def create_friendships(cls, user_id, friend_ids):
        friendships = []
        for friend_id in friend_ids:
            user_a, user_b = user_id, friend_id
            if user_a > user_b:
                user_a, user_b = user_b, user_a
            friendships.append(FriendShip(user_a=user_a, user_b=user_b))
        if friendships:
            FriendShip.objects.bulk_create(friendships)
        return friendships

    @classmethod
    def get_user_friend_ids(cls, user_id):
        friend_ids = []
        ids = FriendShip.objects.filter(user_a=user_id, deleted=False).values_list('user_b', flat=True)
        for id in ids:
            friend_ids.append(str(id))
        ids = FriendShip.objects.filter(user_b=user_id, deleted=False).values_list('user_a', flat=True)
        for id in ids:
            friend_ids.append(str(id))
        return friend_ids

    @staticmethod
    def update_avatar(user_id, avatar):
        try:
            user = UserService.get_user(id=user_id)
            user.avatar = avatar
            user.save()
        except:
            return None
        else:
            return {'user_id': user_id, 'avatar': avatar}

    @staticmethod
    def is_friend(user_a, user_b):
        friend = True
        if user_a is None or user_b is None:
            friend = True
        elif str(user_a) == str(user_b):
            friend = True
        elif not UserService.exist_friendship(user_a, user_b):
            friend = False

        return friend

    @staticmethod
    def exist_friendship(user1, user2):
        exist = True
        if len(FriendShip.objects.filter(user_a=user1, user_b=user2)) == 0:
            if len(FriendShip.objects.filter(user_a=user2, user_b=user1)) == 0:
                exist = False
        return exist

    @staticmethod
    def all_is_friend(user_list):
        for u1 in user_list:
            for u2 in user_list:
                if not UserService.is_friend(u1, u2):
                    return False
        return True




class AuthService(object):
    @staticmethod
    def check_if_token_valid(token):
        auth_token = AuthToken.objects.get_or_none(key=token)

        if auth_token:
            expired_time = auth_token.expired_at
            return expired_time > datetime.datetime.now()
        else:
            return False

    @staticmethod
    def refresh_token(user_id):
        token = AuthToken.objects.get_or_none(user_id=user_id)
        token = AuthToken.objects.refresh_token(token)
        return token
