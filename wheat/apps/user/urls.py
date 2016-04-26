# -*- coding:utf-8 -*-

from customs.urls import get_urlpattern
import apis

urlpatterns = get_urlpattern({
    'users': apis.UserViewSet,
    'captcha': apis.CaptchaViewSet,
    'token': apis.TokenViewSet,
}, api_name='user-api')
