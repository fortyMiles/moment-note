# -*- coding:utf-8 -*-

import uuid
from datetime import datetime
from uuidfield import UUIDField
from django.db import models
from jsonfield import JSONCharField, JSONField

from customs.models import EnhancedModel, CommonUpdateAble, CacheableManager


class Author(CommonUpdateAble, models.Model, EnhancedModel):
    USER = 'user'

    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator_id = UUIDField(db_index=True)  # 创建者
    members = JSONField(default={USER: []})  # 成员列表
    max_members = models.SmallIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CacheableManager()

    def add_group_member(self, user_list):
        USER = Author.USER
        map(lambda user_id: self.members[USER].append(str(user_id)), user_list)

    class Meta:
        db_table = "muti_author_group"


class Book(CommonUpdateAble, models.Model, EnhancedModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator_id = UUIDField(db_index=True)
    group_id = UUIDField(db_index=True)
    remark_name = models.CharField(max_length=50, default="")  # The remark name of this book.
    avatar = models.CharField(max_length=100, default="")  # The book avatar.
    cover = JSONCharField(max_length=200, default={})
    book_name = models.CharField(max_length=50, default="")
    author = models.CharField(max_length=50)  # wroten name
    page_format = models.CharField(max_length=50, default="")
    page_num = models.IntegerField(default=0)
    from_date = models.DateTimeField(default=None, null=True, blank=True)
    to_date = models.DateTimeField(default=None, null=True, blank=True)
    more_info = JSONCharField(max_length=1000, default={})  # for extension
    preview_url = models.CharField(max_length=100, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.SmallIntegerField(default=0)  # 0: making 1: finished
    deleted = models.BooleanField(default=False)

    objects = CacheableManager()

    def delete(self):
        try:
            self.deleted = True
            self.save()
            return True
        except Exception as e:
            print e
            return False

    class Meta:
        db_table = "book"
