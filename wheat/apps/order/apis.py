# -*- coding:utf-8 -*- import logging
from customs import class_tools
from customs import request_tools
from errors import codes
from customs.response import APIResponse
from django.http import HttpResponse
from .services import order_service
from .services import address_service
from .services import invoice_service
from .services import pay_service
from .services import delivery_carrier_service
from .services import delivery_service
from rest_framework import viewsets, status
from rest_framework.decorators import list_route, detail_route
from customs.viewsets import ListModelMixin

from apps.user.permissions import login_required

import logging
logger = logging.getLogger('order')


@class_tools.set_service(order_service)
class OrderViewSet(viewsets.ViewSet):

    @login_required
    @request_tools.post_data_check(['book_id', 'buyer_id', 'paid_type'])
    def create(self, request):
        '''
        Creates Order
        !注意，当支付方式为微信时， 返回的是prepay_id而不是sign, 如果返回的prepay_id 是null，则说明订单创建失败.
        ### Request Example

            {
                "book_id": {String},
                "binding": <"literary", "econimic", "handcover">,
                "count": {Int},
                "buyer_id": {String},
                "address": {String},
                "consignee": {String},
                "phone": {String},
                "invoice": {String},
                "note": {String},
                "paid_type": <"alipay", "wechat">,
                "transcation_id": [{String}], // could be null, for wechat.
                "promotion_info": {String},
                "delivery_id": {String}, // required, 从/delivery/carriers 进行获得
                "delivery_price": {int}, //required
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        kwargs = request.data
        paid_type = kwargs.pop('paid_type')

        order = order_service.create_payment(paid_type, **kwargs)

        result = {
            'order': order,
        }

        sign = order_service.create_sign(paid_type, order['order_no'], request.META.get('REMOTE_ADDR'))

        if paid_type == 'alipay':
            result['sign'] = sign
        elif paid_type == 'wechat':
            result['prepay_id'] = sign

        return APIResponse(result)

    @list_route(methods=['post'])
    def notify(self, request):
        '''
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        logger.info('notification: ' + str(request.data))
        request_data = request_tools.change_unicode_to_str(request.data)
        valid = order_service.check_params(request_data)
        logger.info(valid)
        if valid:
            order_service.valid_order(
                order_no=request_data['out_trade_no'],  # order number self defined
                trade_no=request_data['trade_no'],  # trade no alipay given.
            )

        return APIResponse({})

    @list_route(methods=['post'])
    def wxnotify(self, request):
        '''
        Wechat Payment notify.
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        xml_doc = request.body

        echo = order_service.check_wechat_recall(xml_doc)

        return HttpResponse(echo)

    @login_required
    def list(self, request):
        '''
        Get Current User's All order list.
        Return value is a list.
        ---
        omit_serializer: true
        '''
        user_id = request.user.id
        orders = order_service.get_user_order(user_id)
        return APIResponse(orders)

    @login_required
    def retrieve(self, reqeust, id):
        '''
        Get order info by order No.
        '''
        order = order_service.retrieve(order_no=id)

        if order:
            return APIResponse(order)
        else:
            return APIResponse(status_code=404)

    @login_required
    def update(self, request, id):
        '''
        Update order info by order No.
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        order = order_service.update_order(order_no=id, **request.data)

        if order:
            return APIResponse(order)
        else:
            return APIResponse(status_code=404)

    @login_required
    def destroy(self, request, id):
        order = order_service.delete_order(order_no=id, **request.data)

        if order:
            return APIResponse(order)
        else:
            return APIResponse(status_code=404)


@class_tools.set_service(address_service)
class AddressViewSet(viewsets.GenericViewSet):

    @login_required
    def create(self, request):
        '''
        ### Example Request:

            {
                "user_id": {String},  //required
                "consignee": {String},  //required, 收货人名字
                "phone": {String},  //required
                "zip_code": {String},
                "address": {String},  //required
                "is_default": {Boolean},  // 非必需，将该地址设置为默认地址
            }
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        address = address_service.create(**request.data)
        return APIResponse(address)

    @login_required
    def update(self, request, id):
        '''
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        address = address_service.update_by_id(id, **request.data)
        return APIResponse(address)

    @login_required
    def list(self, request):
        '''
        Get all adresses of current request user.
        '''
        addresses = address_service.list(request.user.id)
        return APIResponse(addresses)

    @login_required
    def destroy(self, request, id):
        address = address_service.delete_by_id(id)
        return APIResponse(address)


@class_tools.set_service(delivery_service)
class DeliveryViewSet(viewsets.GenericViewSet):

    @login_required
    @list_route(methods=['get', 'post'])
    def carriers(self, request):
        '''
        获得所有快递商的信息/ 新建一个快递商的信息

        ### Request When POST

            {
                "name": {String},
                "price": {String}
            }


        ### Response When GET

            {
                "data": [
                    {
                    "id": "9866fef61f4545e38be1d868462ae680",
                    "name": "其他",
                    "price": 0,
                    "deleted": false
                    },
                    {
                    "id": "cb007c4f60bd4157a8daa915b2f1f70a",
                    "name": "顺丰",
                    "price": 12,
                    "deleted": false
                    }
                ],
                "errors": null,
                "request": "success"
            }

        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        if request.method.upper() == 'GET':
            carriers = delivery_carrier_service.get_all()
        elif request.method.upper() == 'POST':
            carriers = delivery_carrier_service.create(**request.data)

        return APIResponse(carriers)


@class_tools.set_service(invoice_service)
class InvoiceViewSet(viewsets.GenericViewSet):

    @login_required
    def create(self, request):
        '''
        Create Invoice

        ### Example Request:

            {
                "user_id": {String},
                "order_id": {String},
                "invoice": {String},
            }
        
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''

        invoice = invoice_service.create(**request.data)
        return APIResponse(invoice)

    @login_required
    def list(self, request):
        '''
        获得某人的全部发票信息

        ---
        omit_serializer: true
        '''

        user_id = request.user.id

        invoices = invoice_service.list(user_id=user_id)

        return APIResponse(invoices)
        
    @login_required
    def update(self, request, id):
        '''
        Update Invoice by inovice id.

        ### Example Request:

            {
                "user_id": {String},
                "order_id": {String},
                "invoice": {String},
            }
        
        ---
        omit_serializer: true
        omit_parameters:
            - form
        parameters:
            - name: body
              paramType: body
        '''
        invoice = invoice_service.update_by_id(id, **request.data)
        return APIResponse(invoice)

    def retrieve(self, request, id):
        '''
        ---
        omit_serializer: true
        '''

        invoice = invoice_service.get_by_id(id)
        return APIResponse(invoice)

    def delete(self, request, id):
        '''
        ---
        omit_serializer: true
        '''
        invoice = invoice_service.delete_by_id(id)
        return APIResponse(invoice)


@class_tools.set_service(pay_service)
class PriceViewSet(viewsets.GenericViewSet):
    @list_route(methods=['get'])
    def count(self, request):
        '''
        Get books totoal price.

        book_id -- book_id
        count -- count
        binding -- binding literary | economic | hardcover
        promotion_info -- if is 'mailitest', will * 0.01
        ---
        omit_serializer: true
        '''

        price = pay_service.get_price(
            request.query_params.get('book_id'),
            request.query_params.get('binding'),
            request.query_params.get('count'),
            request.query_params.get('promotion_info', None),
        )

        return APIResponse(price)
