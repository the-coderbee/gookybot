from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AutoVC(Base):
    __tablename__ = "autovcs"
    
    voice_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, primary_key=True)

    user_discord_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    guild_discord_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('user_discord_id', 'guild_discord_id', name='_autovc_user_guild_uc'),
    )