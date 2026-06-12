from typing import Callable, Optional
from jose import jwt, JWTError
from ..base import AuthAdapter, UserInfo


class JinhuiErpAuthAdapter(AuthAdapter):

    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256",
                 user_loader: Optional[Callable] = None):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.user_loader = user_loader

    async def verify_token(self, token: str) -> Optional[UserInfo]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except JWTError:
            return None
        if payload.get("type") and payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        if self.user_loader:
            return await self.user_loader(str(user_id))
        return UserInfo(id=str(user_id), username="", display_name="")

    async def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        if self.user_loader:
            return await self.user_loader(user_id)
        return UserInfo(id=user_id, username="", display_name="")
