import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    webauthn_user_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    # Optional one-way password hash for the demo's six-digit PIN login.
    pin_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    credentials: Mapped[list["PasskeyCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasskeyCredential(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    device_type: Mapped[str] = mapped_column(String(80))
    backed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    transports_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User] = relationship(back_populates="credentials")

    @property
    def transports(self) -> list[str]:
        return json.loads(self.transports_json or "[]")

    @transports.setter
    def transports(self, value: list[str]) -> None:
        self.transports_json = json.dumps(value or [])


def find_user(username: str) -> User | None:
    return db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()


def find_credential(credential_id: str) -> PasskeyCredential | None:
    return db.session.execute(
        db.select(PasskeyCredential).filter_by(credential_id=credential_id)
    ).scalar_one_or_none()
