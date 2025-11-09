from sqlalchemy import ARRAY, BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression
from .base import Base


class Guild(Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(BigInteger, unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), default="g!")

    engagement_channels: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), default=[], server_default="{}"
    )
    
    welcome_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.false(), nullable=False
    )
    welcome_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

    leveling_enabled: Mapped[bool] = mapped_column(Boolean, server_default=expression.false(), nullable=False)
    leveling_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    leveling_notify_on_levelup: Mapped[bool] = mapped_column(Boolean, server_default=expression.false(), nullable=False)

    auto_vc_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)

    antispam_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=expression.false(), nullable=False
    )

    mod_log_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
