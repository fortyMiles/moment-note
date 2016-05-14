# -*- coding:utf-8 -*-
from customs import class_tools
from customs import request_tools
from errors import codes
from customs.response import APIResponse
from .services import order_service
from .services import address_service
from .services import invoice_service
from rest_framework import viewsets, status
from rest_framework.decorators import list_route, detail_route

from apps.user.permissions import login_required


@class_tools.set_service(order_service)
class OrderViewSet(viewsets.GenericViewSet):

    @login_required
    def create(self, request):
        '''
        Creates Order

        Request:

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
        }
        '''

        # oreder = create_oreder

        kwargs = request.post.data
        order = order_service.create_payment(**kwargs)

        result = {
            'order': order,
        }

        if kwargs['paid_type'] == 'alipay':
            sign = order_service.create_sign(order['order_no'])
            result['sign'] = sign
            
        return APIResponse(result)

    @list_route(methods=['post'])
    def notify(self, request):
        valid = order_service.check_params(request.data)
        if valid:
            order_service.valid_order(
                order_no=request.data['out_trade_no'],  # order number self defined
                trade_no=request.data['trade_no'],  # trade no alipay given.
            )

        return APIResponse({})

    def retrieve(self, reqeust, id):
        '''
        Get order info by order No.
        '''
        order = order_service.retrieve(order_no=id)

        if order:
            return APIResponse(order)
        else:
            return APIResponse(status_code=404)

    def update(self, request, id):
        '''
        Update order info by order No.
        '''
        order = order_service.update_order(order_no=id, **request.data)

        if order:
            return APIResponse(order)
        else:
            return APIResponse(status_code=404)
        
    def alipay(self, request, id):
        '''
        Check one notification if is from Alipay.
        '''
        pass

    def delete(self, request, id):
        order = order_service.delete_order(order_no=id, **request.data)

        if order:
            return APIResponse(order)
        else:
            return APIResponse(status_code=404)


@class_tools.set_service(address_service)
class AddressViewSet(viewsets.GenericViewSet):

    def create(self, request):
        pass


@class_tools.set_service(invoice_service)
class InvoiceViewSet(viewsets.GenericViewSet):

    def create(self, request):
        pass

    def list(self, request):
        pass

    def delete(self, request, id):
        pass
        