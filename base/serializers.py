from django_rest_passwordreset.serializers import EmailSerializer
from django_rest_passwordreset.models import ResetPasswordToken
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import *
from django.core.exceptions import ValidationError


class CustomEmailSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100)
    email = serializers.EmailField()

    def validate_email(self, value):
        if not Profile.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email không tồn tại')
        return value


class CustomResetPasswordConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        token = attrs.get('token')
        password = attrs.get('password')
        try:
            reset_password_token = ResetPasswordToken.objects.get(key=token)
        except ResetPasswordToken.DoesNotExist:
            raise ValidationError('Token không hợp lệ')

        user = reset_password_token.user
        if not user.is_active:
            raise ValidationError('Tài khoản không hoạt động')

        # Đặt lại mật khẩu cho người dùng
        user.set_password(password)
        user.save()

        # Xóa tất cả các token password reset của người dùng
        ResetPasswordToken.objects.filter(user=user).delete()

        return attrs


class CustomRepalcePasswordConfirmSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()


class DepotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Depot
        fields = '__all__'


class ProfileSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField(read_only=True)
    is_superuser = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            'id',
            'first_name',
            'last_name',
            'gender',
            'birthdate',
            'address',
            'email',
            'phone',
            'is_active',
            'is_superuser',
        )

    def get_is_active(self, obj):
        if obj.user:
            return obj.user.is_active
        return False

    def get_is_superuser(self, obj):
        if obj.user:
            return obj.user.is_superuser
        return False


class BusinessPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPartner
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = '__all__'

    def validate(self, value):
        if type(value) == 'dict':
            return value
        category = Category.objects.create(name=value)
        return CategorySerializer(category).data


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    inventory = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = (
            'id',
            'name',
            'unit',
            'inventory',
            'category',
            'price',
        )

    def get_inventory(self, obj):
        # Lấy inventory từ Product_Depot
        product_depot = ProductDepot.objects.filter(product=obj).first()
        return product_depot.inventory if product_depot else None

    def get_price(self, obj):
        # Lấy price từ ProductPrice
        product_price = ProductPrice.objects.filter(
            product=obj, pricelist=Pricelist.objects.last()).first()
        return product_price.price if product_price else 0

    def create(self, validated_data):
        category_data = validated_data.pop('category')
        category_serializer = CategorySerializer(data=category_data)

        if category_serializer.validate():
            category_instance = category_serializer.save()
            validated_data['category'] = category_instance
            product_instance = Product.objects.create(**validated_data)
            return product_instance
        else:
            raise serializers.ValidationError(category_serializer.errors)


class ProductDepotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDepot
        fields = '__all__'


class PricelistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricelist
        fields = '__all__'


class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'


class OrderFormSerializer(serializers.ModelSerializer):
    partner = serializers.SerializerMethodField(read_only=True)
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessPartner.objects.all(), source='partner', write_only=True)
    depot = serializers.SerializerMethodField(read_only=True)
    depot_id = serializers.PrimaryKeyRelatedField(
        queryset=Depot.objects.all(), source='depot', write_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), write_only=True)

    class Meta:
        model = OrderForm
        fields = (
            'id',
            'partner',
            'partner_id',
            'depot',
            'depot_id',
            'user',
            'created_date',
            'total',
        )

    def get_partner(self, obj):
        return {
            'id': obj.partner.id,
            'name': obj.partner.name
        }

    def get_depot(self, obj):
        return {
            'id': obj.depot.id,
            'name': obj.depot.name
        }


class OrderDetailSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True)

    class Meta:
        model = OrderDetail
        fields = (
            'form',
            'product',
            'product_id',
            'quantity',
            'price',
        )

    def get_product(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'unit': obj.product.unit,
        }


class ImportFormSerializer(serializers.ModelSerializer):
    order = OrderFormSerializer(read_only=True)
    order_id = serializers.PrimaryKeyRelatedField(
        queryset=OrderForm.objects.all(), source='order', write_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), write_only=True)

    class Meta:
        model = ImportForm
        fields = (
            'id',
            'order',
            'order_id',
            'user',
            'created_date',
            'total'
        )


class ImportDetailSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField(read_only=True)
    price = serializers.SerializerMethodField(read_only=True)
    order_detail = serializers.PrimaryKeyRelatedField(
        queryset=OrderDetail.objects.all(), write_only=True)

    class Meta:
        model = ImportDetail
        fields = (
            'form',
            'product',
            'order_detail',
            'quantity',
            'price',
        )

    def get_product(self, obj):
        return {
            "id": obj.order_detail.product.id,
            'name': obj.order_detail.product.name,
            'unit': obj.order_detail.product.unit,
        }

    def get_price(self, obj):
        return obj.order_detail.price


class ExportFormSerializer(serializers.ModelSerializer):
    partner = serializers.SerializerMethodField(read_only=True)
    depot = serializers.SerializerMethodField(read_only=True)
    partner_id = serializers.PrimaryKeyRelatedField(
        queryset=BusinessPartner.objects.all(), source='partner', write_only=True)
    depot = serializers.PrimaryKeyRelatedField(
        queryset=Depot.objects.all(), source='partner', write_only=True)
    pricelist = serializers.PrimaryKeyRelatedField(
        queryset=Pricelist.objects.all(), write_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), write_only=True)

    class Meta:
        model = ExportForm
        fields = (
            'id',
            'partner',
            'partner_id',
            'depot',
            'depot_id',
            'user',
            'created_date',
            'pricelist',
            'total',
        )

    def get_partner(self, obj):
        return {
            'id': obj.partner.id,
            'name': obj.partner.name,
        }

    def get_depot(self, obj):
        return {
            'id': obj.depot.id,
            'name': obj.depot.name,
        }


class ExportDetailSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = ExportDetail
        fields = (
            'form',
            'product',
            'product_id',
            'quantity',
            'price',
        )

    def get_product(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'unit': obj.product.unit,
        }
