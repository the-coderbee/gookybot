from sqlalchemy import BigInteger, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from sqlalchemy.sql.sqltypes import TIMESTAMP


class Infraction(Base):
    __tablename__ = "infractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    infraction_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")

    issuer_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=True)
    