from typing import Callable, Optional

from .auth_adapter import XingERPAuthAdapter
from ..base import AssistantAdapter


def create_xing_erp_adapter(
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
    user_loader: Optional[Callable] = None,
) -> AssistantAdapter:
    """Create an AssistantAdapter configured for XingERP.

    Args:
        jwt_secret: The ERP's SECRET_KEY for JWT verification.
        jwt_algorithm: JWT algorithm (default HS256).
        user_loader: Optional async callback(user_id) -> UserInfo.
            When embedded in ERP, this queries the ERP DB for full user info.
    """
    auth = XingERPAuthAdapter(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        user_loader=user_loader,
    )
    return AssistantAdapter(
        auth=auth,
        system_prompt=(
            "你是星鑫财税ERP系统的AI助手。"
            "请用中文回答用户关于系统使用、业务流程、客户管理、"
            "工单处理等方面的问题。回答要简洁准确。"
        ),
    )
