import datetime
from typing import List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings
from app.schemas import ParsedResult

DATABASE_URL = settings.DATABASE_URL
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    raw_title = Column(String, index=True)
    parsed_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    client_ip = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def add_submission(
    db: AsyncSession, 
    raw_title: str, 
    parsed_result: ParsedResult,
    client_ip: str,
    user_agent: str
):
    submission = Submission(
        raw_title=raw_title,
        parsed_json=parsed_result.model_dump(),
        client_ip=client_ip,
        user_agent=user_agent
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission

async def get_recent_submissions(db: AsyncSession, limit: int = 50) -> List[Submission]:
    result = await db.execute(
        Submission.__table__.select().order_by(Submission.created_at.desc()).limit(limit)
    )
    return result.fetchall()
