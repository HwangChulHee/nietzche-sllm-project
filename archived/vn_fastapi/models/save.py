"""
save.py — 비주얼 노벨 세이브 슬롯 모델 (단일 슬롯).

학습자의 진행 상태(에피소드, 화면 인덱스, 차라투스트라 1인칭 요약, 최근 대화 이력)를
단일 행으로 저장. id=1로 고정.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SaveSlot(Base):
    __tablename__ = "save_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    episode: Mapped[str] = mapped_column(String(8), nullable=False)
    scene_index: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recent_messages: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
