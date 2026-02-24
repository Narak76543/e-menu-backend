from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import get_db
from core.security import verify_password, create_access_token, hash_password
from deps.auth import get_current_user

from .models import AdminUser
from .schemas import LoginIn, TokenOut, AdminUserOut


def init_admin_auth(app):

    # 🔐 LOGIN
    @app.post("/auth/login", response_model=TokenOut, tags=["Auth"])
    def login(payload: LoginIn, db: Session = Depends(get_db)):

        user = db.query(AdminUser).filter(
            AdminUser.username == payload.username
        ).first()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        token = create_access_token(
            subject=user.username,
            extra={"role": user.role}
        )

        return TokenOut(access_token=token)


    # 👤 CURRENT USER
    @app.get("/auth/me", response_model=AdminUserOut, tags=["Auth"])
    def me(current_user: AdminUser = Depends(get_current_user)):
        return current_user


    # 🚀 CREATE FIRST ADMIN (dev only)
    @app.post("/auth/seed-admin", response_model=AdminUserOut, tags=["Auth"])
    def seed_admin(db: Session = Depends(get_db)):

        existing = db.query(AdminUser).filter(
            AdminUser.username == "admin"
        ).first()

        if existing:
            return existing

        user = AdminUser(
            username="admin",
            full_name="System Admin",
            role="admin",
            is_active=True,
            hashed_password=hash_password("admin123"),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user