from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import decode_access_token
from api.admin_user.models import AdminUser
from fastapi import Depends, HTTPException

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    cred: HTTPAuthorizationCredentials = Depends(bearer),
) -> AdminUser:

    if not cred:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        payload = decode_access_token(cred.credentials)
        username = payload.get("sub")
        if not username:
            raise Exception()
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(AdminUser).filter(AdminUser.username == username).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return user
def require_role(*roles: str):
    def checker(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Admin only")
        return user
    return checker