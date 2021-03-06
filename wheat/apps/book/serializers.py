# -*- coding:utf-8 -*-

from customs.serializers import XModelSerializer
from customs.fields import XImageField, DictStrField
from .models import Author, Book
from rest_framework import serializers


class AuthorSerializer(XModelSerializer):

    members = DictStrField(required=False, allow_blank=True)

    class Meta:
        model = Author
        fields = ('id', 'creator_id', 'created_at', 'members')


class BookSerializer(XModelSerializer):
    avatar = XImageField(
        max_length=100,
        allow_empty_file=False,
        required=False,
        use_url=True,
        style={'input_type': 'file'}
    )

    cover = DictStrField(required=False, allow_blank=True)
    more_info = DictStrField(required=False, allow_blank=True)
    remark_name = serializers.CharField(required=False, allow_blank=True)
    book_name = serializers.CharField(required=False, allow_blank=True)
    author = serializers.CharField(required=False, allow_blank=True)
    page_format = serializers.CharField(required=False, allow_blank=True)
    preview_url = serializers.URLField(required=False, allow_blank=True)
    deleted = serializers.BooleanField(required=False)

    class Meta:
        model = Book
        fields = ('id', 'creator_id', 'group_id', 'cover', 'more_info',
                  'remark_name', 'avatar', 'book_name',
                  'author', 'page_format', 'preview_url',
                  'created_at', 'page_num', 'from_date', 'to_date', 'status', 'deleted')

