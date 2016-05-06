# -*- coding:utf-8 -*-

from django.db import transaction
from django.contrib.auth import authenticate

from customs.services import BaseService
from .models import User, AuthToken, Friendship, Captcha
from .serializers import UserSerializer, AuthTokenSerializer, CaptchaSerializer
from .serializers import FriendshipSerializer
from datetime import datetime, timedelta
from django.db.models import Q
from utils import utils
from customs.services import MessageService
from customs.api_tools import api
import binascii
import os
from django.conf import settings
from customs.delegates import delegate


class UserService(BaseService):

    model = User
    serializer = UserSerializer

    @api
    def delete_by_id(self, user_id):
        user = self.get(id=user_id)
        if user:
            user = super(UserService, self).delete(user)
        return user
            
    def create(self, phone, password, **kwargs):
        kwargs['password'] = password
        kwargs['phone'] = phone
        user = super(UserService, self).create(**kwargs)
        user.set_password(password)
        user.save()
        return user

    @api
    def set_password_by_phone_and_password(self, phone, password):
        user = self.get(phone=phone)
        if user:
            self.set_password(user, password)
        return user

    def set_password(self, user, password):
        user.set_password(password)
        user.save()
        return user

    def check_if_registed(self, phone, password=''):
        return self.exist(phone=phone)

    def check_user_is_valid(self, **kwargs):
        user = self.get(**kwargs)

        if user and not user.deleted:
            return True
        else:
            return False
    
    @api
    def update_by_id(self, user_id, **kwargs):
        new_user = super(UserService, self).update_by_id(user_id, **kwargs)
        return new_user

    @transaction.atomic
    @api
    def lazy_delete_user(self, user):
        user = self.update(user, deleted=True)
        return user

    def check_phone_valid(self, phone):
        PHONE_LENGTH = 11
        return len(phone) == PHONE_LENGTH

    def check_register_info(self, phone, password):
        valid_info = self.check_phone_valid(phone) and self.check_pwd_formatted(password)
        registed_again = self.check_if_registed(phone)
        return valid_info, registed_again

    @api
    def register(self, phone, password, **kwargs):
        user = None

        if not self.check_if_registed(phone):
            user = self.create(phone, password, **kwargs)
            user = authenticate(username=phone, password=password)
            
        return user

    def check_pwd_formatted(self, password):
        PWD_LENGTH = 6
        return len(password) >= PWD_LENGTH

    def check_if_credential(self, phone, password):
        user = authenticate(username=phone, password=password)
        if user:
            return True
        return False

    def check_if_activated(self, phone):
        user = self.get(phone=phone)
        if user:
            return user.activated
        else:
            return False

    @api
    def login_user(self, phone, password):
        user = authenticate(username=phone, password=password)
        return user


class AuthService(BaseService):
    model = AuthToken
    serializer = AuthTokenSerializer

    def refresh_user_token(self, user_id):
        token = self.get(user_id=user_id)
        if token:
            token.key = self._generate_key()
            token.created_at = datetime.now()
            token.expired_at = datetime.now() + timedelta(hours=24 * settings.AUTHTOKEN_EXPIRED_DAYS)
            token.save()
            UserService().update_by_id(user_id, token=token)
            return token.key
        else:
            return None

    def get_token(self, user_id):
        token = self.get(user_id=user_id)
        if not token:
            return None
        else:
            return token.key

    def _generate_key(self):
        return binascii.hexlify(os.urandom(16)).decode()

    def check_auth_token(self, user_id, token):
        token_obj = self.get(user_id=user_id)
        valid = False
        if token_obj:
            if token_obj.key == token and not token_obj.expired():
                valid = True
        return valid


class CaptchaService(BaseService):
    model = Captcha
    serializer = CaptchaSerializer

    def _expired(self, captcha_obj):
        VALID_MIN = 10
        valid_time = 60 * VALID_MIN
        # valid time is 10 mins.
        
        created_time = captcha_obj.created_at
        if (datetime.now() - created_time).seconds > valid_time:
            return True
        return False
        
    def get_new_captch(self, phone):
        captcha_code = MessageService.random_code(phone, plus=datetime.now().microsecond)
        return captcha_code

    def get_captcha_code_from_obj(self, captcha_obj):
        captcha_code = captcha_obj.code

        if self._expired(captcha_obj):
            captcha_code = self.get_new_captch(captcha_obj.phone)
            self.update(captcha_obj, code=captcha_code)

        return captcha_code

    def get_captch(self, phone):
        captcha_obj = self.get(phone=phone)
        captcha_code = None
        if captcha_obj:
            captcha_code = self.get_captcha_code_from_obj(captcha_obj)
        else:
            captcha_code = self.get_new_captch(str(phone))
            self.create(phone=phone, code=captcha_code)

        return captcha_code

    def send_captcha(self, phone, captcha):
        send_succeed = MessageService.send_captcha(phone=phone, captcha=captcha)
        return send_succeed

    def check_captcha(self, phone, captcha):
        captcha_obj = self.get(phone=phone, code=captcha)
        if captcha_obj and not self._expired(captcha_obj):
            return True
        return False


class FriendshipService(BaseService):
    model = Friendship
    serializer = FriendshipSerializer

    def _sort_user(self, user_a_id, user_b_id):
        if user_a_id > user_b_id:
            user_a_id, user_b_id = user_b_id, user_a_id
        return user_a_id, user_b_id

    def create_friendship(self, user_a_id, user_b_id):
        '''
        Creates friendship between user_a and user_b
        '''

        user_a_valid = UserService().check_user_is_valid(id=user_a_id)
        user_b_valid = UserService().check_user_is_valid(id=user_b_id)

        created = True

        if not user_a_valid or not user_b_valid:
            created = False
        elif user_a_id != user_b_id:
            self.create(user_a_id, user_b_id)
            created = True

        return created

    def create(self, user_a_id, user_b_id):
        user_a_id, user_b_id = self._sort_user(user_a_id, user_b_id)
        friendship = self.get(user_a_id, user_b_id)
        if not friendship:
            super(FriendshipService, self).create(user_a=user_a_id, user_b=user_b_id)
        elif friendship.deleted:
            super(FriendshipService, self).update(friendship, deleted=False)
        return user_a_id, user_b_id

    def delete(self, user_a_id, user_b_id):
        '''
        Deletes friendship between user_a and user_b
        '''
        user_a_id, user_b_id = self._sort_user(user_a_id, user_b_id)

        friendship = self.get(user_a_id, user_b_id)

        if friendship:
            friendship = super(FriendshipService, self).delete(friendship)
        return friendship

    def update(self, user_a_id, user_b_id, **kwargs):
        '''
        Update info of two user.
        '''
        user_a_id, user_b_id = self._sort_user(user_a_id, user_b_id)
        friendship = self.get(user_a_id, user_b_id)
        if friendship:
            friendship = super(FriendshipService, self).update(friendship, **kwargs)

        return friendship

    def get(self, user_a_id, user_b_id):
        '''
        Get infor of user_a and user_b
        '''
        user_a_id, user_b_id = self._sort_user(user_a_id, user_b_id)
        return super(FriendshipService, self).get(user_a=user_a_id, user_b=user_b_id)

    def add_friends(self, user_id, friend_ids):
        '''
        Lets friend_ids (may be a list, set or some other collection) all user to
        be the friend of user_id, which is the first arg.
        '''
        for u in friend_ids:
            self.create(user_id, u)
        return True

    def is_friend(self, user_a_id, user_b_id):
        '''
        Gets if is frend between user_a and user_b
        '''

        test_self = user_a_id == user_b_id

        result = False

        if not test_self:
            friendship = self.get(user_a_id, user_b_id)
            if friendship and not friendship.deleted:
                result = True
            else:
                result = False
        else:
            result = True

        return result

    def all_is_friend(self, user_ids):
        '''
        Judges if the user of user_ids all is friend each other.
        '''

    '''
    @transaction.atomic
    @staticmethod
    def create_friendship(user_a, user_b):
        friendship = None

        if user_a == user_b:
            friendship = None
        else:
            if user_a > user_b:
                user_a, user_b = user_b, user_a

            friendship, created = FriendShip.objects.get_or_create(user_a=user_a, user_b=user_b)
        return friendship

    @transaction.atomic
    @staticmethod
    def create_friendships(user_id, friend_ids):
        friendships = []
        for friend_id in friend_ids:
            user_a, user_b = user_id, friend_id
            if user_a > user_b:
                user_a, user_b = user_b, user_a
                friendships.append(FriendShip(user_a=user_a, user_b=user_b))
        if friendships:
            FriendShip.objects.bulk_create(friendships)
        return friendships

    @transaction.atomic
    @staticmethod
    def delete_friendship(user_id, user_2_id):
        user_a_b = Q(user_a=user_id, user_b=user_2_id)
        user_b_a = Q(user_a=user_2_id, user_b=user_id)
        condition = user_a_b | user_b_a
        friends = FriendShip.objects.filter(condition)
        for f in friends:
            f.delete()
        return True

    @staticmethod
    def get_user_friend_ids(user_id):
        friend_ids = []
        ids = FriendShip.objects.filter(user_a=user_id, deleted=False).values_list('user_b', flat=True)
        for id in ids:
            friend_ids.append(str(id))
            ids = FriendShip.objects.filter(user_b=user_id, deleted=False).values_list('user_a', flat=True)
        for id in ids:
            friend_ids.append(str(id))
        return friend_ids

    @staticmethod
    def is_friend(user_a, user_b):
        friend = True
        if user_a is None or user_b is None:
            friend = True
        elif str(user_a) == str(user_b):
            friend = True
        elif not FriendshipService.exist_friendship(user_a, user_b):
            friend = False

        return friend

    @staticmethod
    def exist_friendship(user1, user2):
        exist = True
        if len(Friendship.objects.filter(user_a=user1, user_b=user2)) == 0:
            if len(Friendship.objects.filter(user_a=user2, user_b=user1)) == 0:
                exist = False
        return exist

    @staticmethod
    def all_is_friend(user_list):
        for u1 in user_list:
            for u2 in user_list:
                if not FriendshipService.is_friend(u1, u2):
                    return False
        return True
    '''


user_service = delegate(UserService())
captcha_service = delegate(CaptchaService())
auth_service = delegate(AuthService())
