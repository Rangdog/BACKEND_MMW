from .models import *
from .serializers import *
from base.models import Profile
from knox.models import AuthToken
from rest_framework.response import Response
from rest_framework import permissions, generics

from django.contrib.auth import get_user_model, authenticate

User = get_user_model()


class LoginAPIView(generics.CreateAPIView):
    permissions_classes = [permissions.AllowAny]
    serializer_class = LoginSerialiazer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]

            user = authenticate(username=username, password=password)
            if user:
                profile_id = Profile.objects.get(user=user).id

                _, token = AuthToken.objects.create(user)
                return Response(
                    {
                        "profile_id": profile_id,
                        "token": token,
                        "is_superuser": user.is_superuser,
                        "user_id": user.id,
                    }
                )
            else:
                return Response({"error": "Invalid credentials"}, status=401)
        else:
            return Response(serializer.errors, status=400)
