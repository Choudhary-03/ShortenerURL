from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import services
from .serializers import ChangePasswordSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # public: ignore any (possibly stale) token in the header

    @extend_schema(
        tags=["Auth"], auth=[],
        request=RegisterSerializer, responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.create_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Auth"], auth=[])
class LoginView(TokenObtainPairView):
    """Exchange email and password for access and refresh tokens."""


@extend_schema(tags=["Auth"], auth=[])
class RefreshView(TokenRefreshView):
    """Exchange a refresh token for a new access token."""


@extend_schema_view(
    get=extend_schema(tags=["Auth"], summary="Get current user"),
    put=extend_schema(tags=["Auth"], summary="Update current user"),
    patch=extend_schema(tags=["Auth"], summary="Partially update current user"),
)
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    @extend_schema(
        tags=["Auth"], summary="Change password",
        request=ChangePasswordSerializer, responses={204: None},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_password(user=request.user, **serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)
