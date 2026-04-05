from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.auth import UserCreate

logger = get_logger(__name__)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, data: UserCreate) -> User:
        # Check email uniqueness
        existing = await self.db.execute(
            select(User).where(func.lower(User.email) == data.email.lower())
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Email already registered: {data.email}")

        # Check username uniqueness
        existing = await self.db.execute(
            select(User).where(func.lower(User.username) == data.username.lower())
        )
        if existing.scalar_one_or_none():
            raise ConflictError(f"Username already taken: {data.username}")

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info("user_created", user_id=user.id, email=user.email)
        return user

    async def get_by_id(self, user_id: str) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def get_by_username_or_email(self, identifier: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                or_(
                    func.lower(User.username) == identifier.lower(),
                    func.lower(User.email) == identifier.lower(),
                )
            )
        )
        return result.scalar_one_or_none()

    async def authenticate(self, identifier: str, password: str) -> User:
        user = await self.get_by_username_or_email(identifier)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid username or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")
        return user

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        user.hashed_password = hash_password(new_password)
        await self.db.flush()
        logger.info("password_changed", user_id=user.id)
