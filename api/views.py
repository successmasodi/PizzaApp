import uuid
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from django.db.models import F

from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly
from django.conf import settings
from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import viewsets, status
from .serializers import CartSerializer, CartItemSerializer, ProductSerializer, OrderSerializer, OrderItemSerializer, \
    ReviewSerializer, AddressSerializer
from pizza.models import Cart, CartItems, Product, Order, OrderItems, Review
import requests


def initiate_payment(amount, email, cart_id, user, address, primary_key):
    url = "https://api.flutterwave.com/v3/payments"
    headers = {
        "Authorization": f"Bearer {settings.FLW_SEC_KEY}"
    }
    first_name = user.first_name
    last_name = user.last_name
    data = {
        "tx_ref": str(uuid.uuid4()),
        "amount": str(amount),
        "currency": "NGN",
        "redirect_url": "http:/127.0.0.1:8000/api/cart/" + primary_key + "/confirm_payment/?c_id=" + cart_id + "&address=" + address,
        "meta": {
            "consumer_id": 23,
            "consumer_mac": "92a3-912ba-1192a"
        },
        "customer": {
            "email": email,
            "phonenumber": "080****4528",
            "name": f"{last_name} {first_name}"
        },
        "customizations": {
            "title": "Pizza App",
            "logo": "https://th.bing.com/th/id/OIP.i0PkSmaiaMw-6epTXz1qvAHaHa?rs=1&pid=ImgDetMain"

        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        return Response(response_data)

    except requests.exceptions.RequestException as err:
        print("the payment didn't go through")
        return Response({"error": str(err)}, status=500)


class ApiCart(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    queryset = Cart.objects.all()

    def get_serializer_class(self):
        if self.action == 'pay':
            return AddressSerializer
        else:
            return super().get_serializer_class()

    @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated])
    def pay(self, request, pk):
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        cart = self.get_object()
        items = cart.items.all()
        total = sum([item.quantity * item.product.price for item in items])
        amount = total
        email = request.user.email
        cart_id = str(cart.id)
        address = serializer.validated_data["address"]
        primary_key = pk
        return initiate_payment(amount, email, cart_id, user, address=address, primary_key=primary_key)

    @action(detail=True, methods=["POST"])
    @transaction.atomic
    def confirm_payment(self, request, pk):
        cart_id = request.GET.get("c_id")
        user = request.user
        address = request.GET.get("address")
        order = Order.objects.create(owner=user, address=address)

        cartitems = CartItems.objects.filter(cart_id=cart_id)
        orderitem = [OrderItems(order=order, product=items.product, quantity=items.quantity, total_cost=items.quantity*items.product.price) for items in cartitems]
        OrderItems.objects.bulk_create(orderitem)
        Cart.objects.filter(id=cart_id).delete()

        serializer = OrderSerializer(order)

        data = {
            "msg": "payment was successful",
            "data": serializer.data
        }
        return Response(data)


class ApiCartItem(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer

    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}

    def get_queryset(self):
        return CartItems.objects.filter(cart_id=self.kwargs['cart_pk'])


class ApiOrder(viewsets.ModelViewSet):
    http_method_names = ["get", "patch", "delete", "options", "head"]
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = [IsAdminOrReadOnly, IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    search_fields = ['flight_no']
    ordering_fields = ['placed_at', 'total_price']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(owner=user)


class ApiOrderItem(viewsets.ModelViewSet):
    serializer_class = OrderItemSerializer
    queryset = OrderItems.objects.all()
    permission_classes = [IsAdminOrReadOnly, IsAuthenticated]

    def get_queryset(self):
        return OrderItems.objects.filter(order_id=self.kwargs['order_pk'])

    def perform_create(self, serializer):
        order_id = self.kwargs['order_pk']
        return serializer.save(order_id=order_id)


class ApiReview(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    queryset = Review.objects.all()
    permission_classes = [IsOwnerOrAdmin, IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs['products_pk'])

    def perform_create(self, serializer):
        product_id = self.kwargs['products_pk']
        user = self.request.user
        return serializer.save(product_id=product_id, owner=user)


class ApiProducts(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.filter(is_available=True)

    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['price']
