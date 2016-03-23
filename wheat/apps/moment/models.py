# -*- coding:utf-8 -*-

import uuid
from django.db import models
from uuidfield import UUIDField
from jsonfield import JSONField

from customs.models import EnhancedModel, CommonUpdateAble, CacheableManager


class Moment(CommonUpdateAble, models.Model, EnhancedModel):
    TYPES = (
        ('text', u'文字'),
        ('pics', u'图片'),
        ('pics-text', u'图文'),
        ('link', u'链接'),
        ('voice', u'语音'),
        ('video', u'视频'),
        ('song', u'歌曲'),
        ('location', u'位置'),
    )
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = UUIDField(db_index=True)
    content_type = models.CharField(max_length=10, choices=TYPES)
    content = JSONField(default={})  # {"text": "xx", "pics": []}
    post_date = models.DateTimeField(auto_now_add=True, db_index=True)
    moment_date = models.DateTimeField(auto_now_add=True, db_index=True)
    visible = models.CharField(max_length=32, db_index=True, default='private')  # private, public, friends, group_id
    deleted = models.BooleanField(default=False)

    objects = CacheableManager()

    class Meta:
        db_table = "moment"

    @classmethod
    def valid_content_type(cls, content_type, content):
        TEXT, PICS = 'text', 'pics'
        if not isinstance(content, dict):
            return False
        if content_type == TEXT:
            return TEXT in content.keys() 
        elif content_type == PICS:
            return PICS in content.keys() and isinstance(content['pics'], list)
        elif content_type == 'pics-text':
            return TEXT in content.keys() and PICS in content.keys() and isinstance(content['pics'], list)
        return False

    @classmethod
    def valid_visible_field(cls, visible):
        PRIVATE, PUBLIC, FRIENDS = 'private', 'public', 'friends'
        AVALIABLE_SCOPES = [PRIVATE, PUBLIC, FRIENDS]
        return visible in AVALIABLE_SCOPES or len(visible) == 32


class Comment(CommonUpdateAble, models.Model, EnhancedModel):
    pass


class Mark(CommonUpdateAble, models.Model, EnhancedModel):
    TYPES = (
        ('like', 'like'),
    )


class MomentStat(CommonUpdateAble, models.Model, EnhancedModel):
    moment_id = UUIDField(primary_key=True)
    likes = JSONField(default=[])
    shares = JSONField(default=[])
    like_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)

    objects = CacheableManager()

    class Meta:
        db_table = "moment_stat"
