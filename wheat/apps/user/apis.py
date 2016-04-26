# -*- coding:utf-8 -*-

from rest_framework import viewsets, status
from rest_framework.decorators import list_route

from customs.response import SimpleResponse
from customs.viewsets import ListModelMixin
from errors import codes
from .permissions import admin_required, login_required
from .permissions import user_is_same_as_logined_user
from .services import AuthService
from customs import class_tools
from apps.user.services import user_service
from apps.user.services import captcha_service


@class_tools.set_filter(['phone'])
@class_tools.set_service(user_service)
class UserViewSet(ListModelMixin,
                  viewsets.ModelViewSet):

    """
    麦粒用户系统相关API.
    ### Resource Description
    """

    @list_route(methods=['get'])
    def register(self, request):
        '''
        获取关于注册列表的相关信息
        ### Request example:
        URL: {API_URL}/users/register?phone=18582227569

        phone -- phone number
        ---
        omit_serializer: true
        '''
        PHONE = 'phone'
        phone = request.query_params.get(PHONE, None)

        registed = user_service.check_if_registed(phone)

        data = {
            'phone': phone,
            'registered': registed
        }

        return SimpleResponse(status=200, data=data)

    @list_route(methods=['post'])
    @login_required
    def password(self, request):
        '''
        修改用户的密码，用于重置密码

        ###Example Reqeust

        {
            "phone": "18582227569",
            "password": "12345678"
        }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        phone = request.data.get('phone', None)
        password = request.data.get('password', None)

        if phone != request.user.phone:
            return SimpleResponse(code=codes.OPERATION_FORBIDDEN)
        else:
            user = user_service.set_password_by_phone_and_password(phone, password)
            return SimpleResponse(data=user)

    def create(self, request):
        '''
        Registration.
        ### Request Example

            {
                "phone": "xxx",
                "password": "123456"
                ...and update fields...
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        phone = request.data.pop('phone', None)
        password = request.data.pop('password', None)

        if user_service.check_register_info_valid(phone=phone, password=password):
            user = user_service.register(phone, password, request, **request.data)
            code = 200 if user else codes.PHONE_ALREADY_REGISTERED
            return SimpleResponse(code=code, data=user)
        else:
            return SimpleResponse(status=status.HTTP_400_BAD_REQUEST)

    @admin_required
    def destroy(self, request, id):
        '''
        Delete user, requiring admin permission
        ---
        omit_serializer: true
        '''
        return SimpleResponse(data=user_service.delete(user_id=id))

    @list_route(methods=['post'])
    def login(self, request):
        '''
        User login, return user info if success
        ### Example Request

            {
                "phone": "18582227569",
                "password": "q1w2e3"
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        phone = request.data.get('phone', '')
        password = request.data.get('password', '')

        code, user = user_service.login_user(request, phone, password)

        if code:
            return SimpleResponse(code=code)
        else:
            return SimpleResponse(data=user)

    @login_required
    @user_is_same_as_logined_user
    @list_route(methods=['put'])
    def avatar(self, request):
        '''
        修改用户的头像信息

        ### Example Request:

            {
                "avatar": "new avatar url",
                "user_id": "the id of the updated user"
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: data
              paramType: body
        '''
        avatar = request.data.get('avatar', None)

        user = user_service.update_by_id(request.user.id, avatar=avatar)
        return SimpleResponse(user)

    @list_route(methods=['get'])
    def online(self, request):
        '''
        测试该user_id是否正保持在线，保持在线是指，该client登录之后，session没有中断

        返回样例：

        online ＝ ｛
            “online”： False
        ｝

        该用户未在此session登录

        user_id -- user_id
        ---
        omit_serializer: true
        '''
        user_id = request.query_params.get('user_id', None)

        online = {
            "online": request.user.id == user_id
        }

        return SimpleResponse(online)


class CaptchaViewSet(viewsets.GenericViewSet):
    @login_required
    @list_route(methods=['post'])
    def check(self, request):
        '''
        检查验证码是否相符（action = check）

        ### Example Request

            {
                "phone": "18857453090",
                "captcha": "259070"
                // 该请求为检查验证码是否相符时候的请求
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: phone
              paramType: body
        '''
        phone = request.data.get('phone', None)
        captcha = request.data.get('captcha', None)
        match = captcha_service.check_captcha(phone, captcha)

        return_context = {
            'phone': phone,
            'captcha': captcha,
            'matched': match
        }

        return SimpleResponse(return_context)

    def send(self, request):
        '''
        Does actions for captcha.

        用以处理和验证码相关的信息，根据action不同，可以有
        1. 发送验证码
        2. 测试发送验证码但是不发送短信（test = '1')
        ### Example Request

            {
                "phone": "18582227569"
                // 该请求为发送验证码时候的请求
            }

        test -- if this value is '1', will not send message, just echo with captcha code.
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: phone
              paramType: body
        '''

        test = request.query_params.get('test', None)
        phone = request.data.get('phone', None)

        send = True
        if test == '1':
            send = False

        send_succeed, code = captcha_service.send_captcha(phone=phone, send=send)

        return_context = {
            'phone': phone,
            'captcha': code
        }

        if send_succeed:
            return SimpleResponse(return_context)
        else:
            return SimpleResponse(success=False)


class TokenViewSet(viewsets.GenericViewSet):

    @list_route(methods=['put'])
    @user_is_same_as_logined_user
    @login_required
    def refresh(self, request):
        '''
        ### Example Request

            {
                "user_id": "user_id",
                "token": "old token"
            }
        '''
        token = AuthService.refresh_token(request.user.id)
        return SimpleResponse(token.token)

    @list_route(methods=['get'])
    @login_required
    def check(self, request):
        '''
        GET: check token if valid.

        ## Example Request:

            {URL}/user/token/?token=XXX
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body

        '''
        token = request.query_params.get('token', None)
        valid = AuthService.check_if_token_valid(token)
        data = {'valid': valid}
        return SimpleResponse(data)
