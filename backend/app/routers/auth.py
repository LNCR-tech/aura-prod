"""Use: Handles login and authentication API endpoints.
Where to use: Use this through the FastAPI app when the frontend or an API client needs login and authentication features.
Role: Router layer. It receives HTTP requests, checks access rules, and returns API responses.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.core.rate_limit import (
    build_forgot_password_rule,
    build_login_rule,
    client_ip_identity,
    enforce_rate_limit,
)
from app.core.security import (
    PASSWORD_CHANGE_PROMPT_DISMISS_ENDPOINT,
    authenticate_user,
    get_current_application_user,
    has_any_role,
    verify_password,
)
from app.core.dependencies import get_db
from app.schemas.auth import ChangePasswordRequest, Token, LoginRequest
from app.schemas.common import MessageResponse
from app.schemas.password_reset import (
    ForgotPasswordRequestCreate,
    ForgotPasswordRequestResponse,
)
from app.models.user import User, UserRole
from app.services.auth_session import (
    issue_login_token_response,
    validate_login_account_state,
)
from app.services.notification_center_service import send_account_security_notification
from app.services.password_change_policy import (
    must_change_password_for_new_account,
    should_prompt_password_change_for_new_account,
)
from app.services.security_service import (
    record_login_history,
)
from app.utils.passwords import hash_password_bcrypt

router = APIRouter(tags=["authentication"])
FORGOT_PASSWORD_GENERIC_MESSAGE = (
    "If the account exists, a password reset request has been submitted for administrator approval."
)


def _is_platform_admin_account(user: User | None) -> bool:
    return bool(user) and has_any_role(user, ["admin"]) and getattr(user, "school_id", None) is None


def _requires_platform_admin_password_reset_approval(user: User | None) -> bool:
    return bool(user) and has_any_role(user, ["admin", "campus_admin"])


def _can_submit_public_password_reset_request(user: User | None) -> bool:
    if user is None or not getattr(user, "is_active", True):
        return False
    if getattr(user, "school_id", None) is None:
        return False
    return not _is_platform_admin_account(user)


def _login_rate_limit_identity(request: Request, email: str) -> str:
    return f"{client_ip_identity(request)}:email:{email.strip().lower()}"

@router.post("/token", response_model=Token)
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(default=False),
    db: Session = Depends(get_db)
):
    """OAuth2-compatible token endpoint (for Swagger UI)"""
    enforce_rate_limit(
        build_login_rule(),
        _login_rate_limit_identity(request, form_data.username),
        request=request,
    )
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        record_login_history(
            db,
            email_attempted=form_data.username,
            user=None,
            success=False,
            auth_method="password",
            failure_reason="invalid_credentials",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    validate_login_account_state(db, user)

    response_payload = issue_login_token_response(
        db=db,
        user=user,
        request=request,
        remember_me=remember_me,
    )
    record_login_history(
        db,
        email_attempted=user.email,
        user=user,
        success=True,
        auth_method="password",
        request=request,
    )
    db.commit()
    return response_payload

@router.post("/login", response_model=Token)
def login_with_email(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Alternative login endpoint that returns extended user info"""
    enforce_rate_limit(
        build_login_rule(),
        _login_rate_limit_identity(request, login_data.email),
        request=request,
    )
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        record_login_history(
            db,
            email_attempted=login_data.email,
            user=None,
            success=False,
            auth_method="password",
            failure_reason="invalid_credentials",
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    validate_login_account_state(db, user)

    response_payload = issue_login_token_response(
        db=db,
        user=user,
        request=request,
        remember_me=login_data.remember_me,
    )
    record_login_history(
        db,
        email_attempted=user.email,
        user=user,
        success=True,
        auth_method="password",
        request=request,
    )

    db.commit()
    return response_payload


@router.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_application_user),
    db: Session = Depends(get_db),
):
    # Use the same verifier as login so temporary passwords work consistently
    # regardless of which hashing helper originally created the stored hash.
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.set_password(payload.new_password)
    current_user.must_change_password = False
    current_user.should_prompt_password_change = False
    try:
        send_account_security_notification(
            db,
            user=current_user,
            subject="Password Changed",
            message="Your password was changed successfully.",
            metadata_json={"event": "password_change"},
        )
    except Exception:
        pass
    db.commit()

    return {"message": "Password updated successfully"}


@router.post(PASSWORD_CHANGE_PROMPT_DISMISS_ENDPOINT, response_model=MessageResponse)
def dismiss_password_change_prompt(
    current_user: User = Depends(get_current_application_user),
    db: Session = Depends(get_db),
):
    current_user.should_prompt_password_change = False
    db.commit()
    return {"message": "Password change prompt dismissed."}


@router.post("/auth/forgot-password", response_model=ForgotPasswordRequestResponse)
def request_forgot_password(
    request: Request,
    payload: ForgotPasswordRequestCreate,
    db: Session = Depends(get_db),
):
    """Self-service password reset.

    Email-based admin approval was removed because outgoing email volume cannot
    cope with the current student population. Instead, an eligible user's
    password is immediately reset to their lowercase last name (matching the
    bulk/manual import default), and case-insensitive first login is restored
    via using_default_import_password=True.
    """
    normalized_email = payload.email.strip().lower()
    enforce_rate_limit(
        build_forgot_password_rule(),
        _login_rate_limit_identity(request, normalized_email),
        request=request,
    )
    target_user = (
        db.query(User)
        .options(joinedload(User.roles).joinedload(UserRole.role))
        .filter(User.email == normalized_email)
        .first()
    )

    if not target_user:
        return ForgotPasswordRequestResponse(message=FORGOT_PASSWORD_GENERIC_MESSAGE)

    if not _can_submit_public_password_reset_request(target_user):
        return ForgotPasswordRequestResponse(message=FORGOT_PASSWORD_GENERIC_MESSAGE)

    last_name = (target_user.last_name or "").strip()
    if not last_name:
        # Stay generic so this endpoint cannot be used to enumerate accounts
        # with missing last names.
        return ForgotPasswordRequestResponse(message=FORGOT_PASSWORD_GENERIC_MESSAGE)

    # Bypass User.set_password() because it enforces an 8-char minimum and
    # clears using_default_import_password.
    target_user.password_hash = hash_password_bcrypt(last_name.lower())
    target_user.using_default_import_password = True
    target_user.must_change_password = must_change_password_for_new_account()
    target_user.should_prompt_password_change = should_prompt_password_change_for_new_account()

    try:
        send_account_security_notification(
            db,
            user=target_user,
            subject="Password Reset",
            message=(
                "Your password has been reset to your last name (lowercase). "
                "Please contact your administrator if you need help."
            ),
            metadata_json={"event": "password_reset_self_service"},
        )
    except Exception:
        pass

    db.commit()

    return ForgotPasswordRequestResponse(message=FORGOT_PASSWORD_GENERIC_MESSAGE)

