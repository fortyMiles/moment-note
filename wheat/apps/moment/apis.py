# -*- coding:utf-8 -*-

from rest_framework import permissions, viewsets, status
from rest_condition import Or

from customs.permissions import AllowPostPermission
from customs.response import SimpleResponse
from customs.viewsets import ListModelMixin
from apps.user.permissions import login_required
from .services import MomentService
from . import services
from rest_framework.decorators import list_route, detail_route
from .serializers import MomentSerializer
from apps.book.services import AuthorService
from itertools import chain
from customs.utility import get_image_from_maili_by_img_list
from .services import CommentService, MarkService


class MomentViewSet(ListModelMixin,
                    viewsets.GenericViewSet):

    """
    麦粒和家系统相关API.
    ### Resource Description
    """
    model = MomentService._get_model()
    queryset = model.get_queryset()
    serializer_class = MomentService.get_serializer()
    lookup_field = 'id'
    permission_classes = [
        Or(permissions.IsAuthenticatedOrReadOnly, AllowPostPermission,)]

    @login_required
    def list(self, request):
        '''
        List all moments by pages. Admin Required.
        获取和家信息

        ### Example Request:
        Url: {API_URL}/moments/?receiver={id}&sender={id}&number={int}&begin-id={id}&compare={previous/after}

        获取某人的和家页面的moments（不限制非得本人发的）

        具体使用说明请参加以下参数说明，经过各种组合即可获得想要的数据

        ### Example Requests

        e.g 01.
        /moment/?receiver=b231asd&begin=ajkdajkwld123&step=15&compare=previous

        表示，获取与begin最接近的15条数据，会获得包括自己在内的所有好友发送的和家信息

        e.g 02.
        /moment?receiver=b123dwad&sender=dakwdjlka21231&compare=previous

        表示，获取sender发送的且receiver能够看到的和家信息

        e.g 03
        /moment?receiver=alskjdajkls12&compare=previous

        表示，获取receiver能接受到的最近的10条信息

        e.g 04

        /moment?receiver=b123asd128hjkasdhjk&begin=ajkhsd1234hkjasdhjk&step＝15compare=after
        表示，获取比begin更新的15条数据

        e.g 05
        /moment?receiver=b123asd128hjkasdhjk&begin=ajkhsd1234hkjasdhjk&step＝15compare=after&query=1&sender={String}
        表示，获得author_group的id为XXX的全部用户的状态，且该状态要求比begin更早，返回数量最大为15条


        receiver -- 接收者的id, 为保证信息的安全，接收者的id必须与当前 token 的user_id一致，否则请求错误
        sender -- 发送者的id， 可以为空，为空则返回所有好友的和家信息
        number -- 获得的信息数量， 可以为空，为空则至多返回10条
        begin-id -- 起始信息的id，可以为空，为空则返回系统中该用户可见的最新的信息（该信息有可能意见阅读或尚未阅读过）
        compare -- 在begin－id之前发送的（previous）还是之后发送的（after），可以为空，为空时，既获得历史消息
        group -- 当该值为1的时候，所传送的id为查询某个“作者组”的和家状态, 如果该参数为空，默认为0，既查询的是关于个人的和家状态


        ---
        omit_serializer: true
        '''

        RECEIVER, SENDER, STEP = 'receiver', 'sender', 'number'
        BEGIN_ID, COMPARE = 'begin-id', 'compare'
        GROUP = 'group'

        receiver_id = request.query_params.get(RECEIVER, None)
        sender_id = request.query_params.get(SENDER, None)
        step = request.query_params.get(STEP, 10)
        begin_id = request.query_params.get(BEGIN_ID, None)
        compare = request.query_params.get(COMPARE, None)
        group = request.query_params.get(GROUP, False)

        if receiver_id == str(request.user.id):
            moments = self._get_moment_by_condition(
                receiver_id,
                sender_id, step, begin_id, compare, group
            )
            moments_json_data = MomentService.serialize_objs(moments)
            return SimpleResponse(moments_json_data)
        else:
            return SimpleResponse(
                status=status.HTTP_401_UNAUTHORIZED,
                errors='need receiver_id the same as the id of login use'
            )

    def _get_moment_by_condition(self, receiver, sender, step, begin_id, compare, group):
        if str(group) == '1':
            # moments = AuthorService.get_author_list_by_author_group(sender)
            moments = services.get_moment_from_author_list(receiver, sender)
        else:
            moments = services.get_moment_by_receiver_and_sender_id(receiver, sender)

        moments = services.get_moment_compare_with_begin_id(moments, compare, begin_id)

        moments = services.confine_moment_number(moments, step)

        try:
            moments = map(self._get_moment_img_size, moments)
        except IOError:
            print('Cannot find this picture')

        return moments

    def _get_moment_img_size(self, moment):
        PICS, IMG_SIZE = 'pics', 'img_size'
        if PICS in moment.content:
            pictures = moment.content[PICS]
            moment.content.setdefault(IMG_SIZE, get_image_from_maili_by_img_list(pictures))

        return moment

    @login_required
    def create(self, request):
        '''
        Create Moment.
        ### Request Example

            {
                "user_id": "xxx",
                "content_type": "text/pics/pics-text",
                "content": {"text": "xxx", "pics": "xxx"},
                "visible": "private/public/friends/group_id"
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        user_id = request.data.get('user_id')
        content_type = request.data.get('content_type')
        content = request.data.get('content')
        visible = request.data.get('visible')

        if user_id != str(request.user.id):
            return SimpleResponse(status=status.HTTP_401_UNAUTHORIZED)

        moment = MomentService.create_moment(
            user_id=user_id,
            content_type=content_type,
            content=content,
            visible=visible)
        if not moment:
            return SimpleResponse(
                status=status.HTTP_400_BAD_REQUEST,
                errors='please check request format, pic must be an array'
            )
        return SimpleResponse(MomentService.serialize(moment))

    @login_required
    def retrieve(self, request, id):
        '''
        获得某个moment为id的moment详情，如果想获得某个作者组，或者某个作者的状态的详情，请
        访问：{API_URL}/moments/
        Retrieve moment.
        ---
        omit_serializer: true
        '''
        moment = MomentService.get_moment(id=id)
        if not moment:
            return SimpleResponse(status=status.HTTP_404_NOT_FOUND)
        # elif moment.user_id != request.user.id:
        #   return SimpleResponse(status=status.HTTP_401_UNAUTHORIZED)
        return SimpleResponse(MomentService.serialize(moment))

    @login_required
    def destroy(self, request, id):
        '''
        Delete moment
        ---
        omit_serializer: true
        '''
        moment = MomentService.get_moment(id=id)
        if not moment:
            return SimpleResponse(status=status.HTTP_404_NOT_FOUND)
        elif moment.user_id == request.user.id:
            return SimpleResponse(success=MomentService.delete_moment(moment))
        else:
            return SimpleResponse(status=status.HTTP_401_UNAUTHORIZED)

    @login_required
    @detail_route(methods=['post'])
    def mark(self, request, id=None):
        '''
        Operations with moments's mark

        ###Example Data:

        ## 1. action == add

        URL: moments/{id}/mark?action=add

        Requset:

            {
                'mark': 'like' | 'argry' // etc, like facebook
                'user_id': {UID}
            }

        Response:

            {
                'success': true | false
            }

        ## 2. aciton == delete

        URL: moments/{id}/mark?action=delete

            {
                'mark': 'like' | 'argry' // etc, like facebook
                'user_id': {UID}
            }

        Response:

            {
                'success': true | false
            }

        action -- action , 'add' | 'delete',  ('add' for none)
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        if str(request.user.id) != str(request.data.get('user_id', None)):
            return SimpleResponse(success=False, errros='unvlid user')
        else:
            ACTION = 'action'
            action = request.query_params.get(ACTION, None)
            return self._comment_moment(request, id, MarkService, action)

    @login_required
    @detail_route(methods=['post'])
    def comment(self, request, id=None):
        '''
        Add comment to the moment

        ###Example Data:

        ##1. action == add

        Request:

            {
                "msg": {String},
                "at": {UID} | None // if you want mention someone, you need write this clause. 
                "user_id": {UID}
            }

        Explaination: Add a comment to moment that id is **id**

        Response:

                {
                  "data": {
                    "comment_id": "546bd26cf6fa4f57842125b542210a9f",
                    "moment_id": "09366f07f5754bd5af77da4a144d7f07"
                  },
                  "request": "success"
                }

        ##2. action == cancle

        URL: moments/{id}/comment?action=delete

        Request:

            {
                "comment_id": {String}, //the comment you want to delete
                "user_id": {UID}
            }

        Response:

            {
                'request': succuss | fail,
            }

        action -- action , 'add' | 'delete',  ('add' for none)
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        if str(request.user.id) != str(request.data.get('user_id', None)):
            return SimpleResponse(success=False, errros='unvlid user')
        else:
            ACTION = 'action'
            action = request.query_params.get(ACTION, None)
            return self._comment_moment(request, id, CommentService, action)

    def _comment_moment(self, request, moment_id, service, action):
            func = self._get_cancle_or_add_func(action, service)
            try:
                comment_id = func(moment_id, request.user.id, request.data)
                return SimpleResponse(
                    success=True,
                    data={
                        'moment_id': moment_id,
                        'comment_id': comment_id
                    })
            except ReferenceError:
                return SimpleResponse(
                    success=False,
                    errors="this user cannot operated with this moment"
                )
            except TypeError:
                return SimpleResponse(success=False, errors='unvalid action')
            except Exception as e:
                return SimpleResponse(success=False, errors=str(e))

    def _get_cancle_or_add_func(self, action,  service):
            DELETE, ADD = 'delete', 'add'
            if action == DELETE:
                return service.cancle
            elif action == ADD:
                return service.add
