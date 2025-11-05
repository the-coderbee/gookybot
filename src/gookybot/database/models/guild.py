from sqlalchemy import ARRAY, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(BigInteger, unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), default="g!")

    engagement_channels: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), default=[], server_default="{}"
    )
