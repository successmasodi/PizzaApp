from pizza.models import Cart, CartItems, Product, Order, OrderItems, Review
from rest_framework import serializers
from django.conf import settings


class CartItemSerializer(serializers.ModelSerializer):

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('there is no product associated with the given id')
        return value

    def save(self, *args, **kwargs):
        cart_id = self.context['cart_id']
        product = self.validated_data['product']
        quantity = self.validated_data['quantity']
        try:
            cartitem = CartItems.objects.get(product_id=product, cart_id=cart_id)
            cartitem.quantity += quantity
            cartitem.save()
            self.instance = cartitem

        except:
            self.instance = CartItems.objects.create(cart_id=cart_id, **self.validated_data)
            return self.instance

    class Meta:
        model = CartItems
        fields = '__all__'
        read_only_fields = ['total_cost', 'cart']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField(method_name='main_total')

    class Meta:
        model = Cart
        fields = ['id', 'items', 'grand_total']
        read_only_fields = ['id']

    def main_total(self, cart: Cart):
        items = cart.items.all()
        total = sum([item.quantity * item.product.price for item in items])
        return total


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItems
        fields = '__all__'
        read_only_fields = ['total_cost', 'order']


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField(method_name='main_total')

    class Meta:
        model = Order
        fields = ['id', 'owner', 'address', 'order_items', 'grand_total']
        read_only_fields = ['id', 'owner']

    def main_total(self, order: Order):
        items = order.order_items.all()
        total = sum([item.quantity * item.product.price for item in items])
        return total


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['owner', 'product']


class AddressSerializer(serializers.Serializer):
    address = serializers.CharField()
