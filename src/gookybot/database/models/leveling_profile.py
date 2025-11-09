from sqlalchemy import BigInteger, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class LevelingProfile(Base):
    __tablename__ = "leveling_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_discord_id: Mapped[str] = mapped_column(BigInteger, nullable=False)
    guild_discord_id: Mapped[str] = mapped_column(BigInteger, nullable=False)

    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_discord_id', 'guild_discord_id', name='_leveling_profiles_user_guild_uc'),
    )
