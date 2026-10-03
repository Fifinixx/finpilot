from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer, tokens_for

COOKIE = settings.JWT_REFRESH_COOKIE

AuthResponse = inline_serializer(
    name="AuthResponse",
    fields={"access": serializers.CharField(), "user": UserSerializer()},
)


def _set_refresh_cookie(response, refresh):
    response.set_cookie(
        COOKIE["key"],
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=COOKIE["path"],
        httponly=COOKIE["httponly"],
        secure=COOKIE["secure"],
        samesite=COOKIE["samesite"],
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(COOKIE["key"], path=COOKIE["path"], samesite=COOKIE["samesite"])


def _auth_response(user, status_code=status.HTTP_200_OK):
    """Access token goes in the body (kept in memory by the SPA);
    refresh token goes in an httpOnly cookie (invisible to JS)."""
    refresh = tokens_for(user)
    response = Response(
        {"access": str(refresh.access_token), "user": UserSerializer(user).data},
        status=status_code,
    )
    _set_refresh_cookie(response, refresh)
    return response


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=LoginSerializer, responses={200: AuthResponse})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return _auth_response(serializer.validated_data["user"])


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponse})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _auth_response(user, status.HTTP_201_CREATED)


class RefreshView(APIView):
    """Exchange the refresh cookie for a new access token (and rotate the cookie)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses={200: inline_serializer("RefreshResponse", {"access": serializers.CharField()})})
    def post(self, request):
        raw = request.COOKIES.get(COOKIE["key"])
        if not raw:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old = RefreshToken(raw)
            user_id = old["user_id"]
            old.blacklist()  # single-use: a replayed refresh token is rejected
        except TokenError:
            response = Response({"detail": "Session expired."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            response = Response({"detail": "Session expired."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response
        return _auth_response(user)


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        raw = request.COOKIES.get(COOKIE["key"])
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass  # already invalid — nothing to revoke
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(APIView):
    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)
