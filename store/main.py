import asyncio
import json
from typing import Set, Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    DateTime, update, delete,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.sql import select
from datetime import datetime
from pydantic import BaseModel, field_validator, model_serializer
from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

# FastAPI app setup
app = FastAPI()
# SQLAlchemy setup
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ProcessedAgentDataModel(Base):
    __tablename__ = "processed_agent_data"
    id = Column(Integer, primary_key=True, index=True)
    road_state = Column(String)
    user_id = Column(Integer)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    timestamp = Column(DateTime)


class ProcessedAgentDataInDB(BaseModel):
    id: int
    road_state: str
    user_id: int
    x: float
    y: float
    z: float
    latitude: float
    longitude: float
    timestamp: datetime


# FastAPI models
class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float


class GpsData(BaseModel):
    latitude: float
    longitude: float


class AgentData(BaseModel):
    user_id: int
    accelerometer: AccelerometerData
    gps: GpsData
    timestamp: datetime

    @classmethod
    @field_validator("timestamp", mode="before")
    def check_timestamp(cls, value):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError(
                "Invalid timestamp format. Expected ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)."
            )


class ProcessedAgentData(BaseModel):
    road_state: str
    agent_data: AgentData

    @model_serializer
    def ser_model(self):
        return {
            "road_state": self.road_state,
            "user_id": self.agent_data.user_id,
            "x": self.agent_data.accelerometer.x,
            "y": self.agent_data.accelerometer.y,
            "z": self.agent_data.accelerometer.z,
            "latitude": self.agent_data.gps.latitude,
            "longitude": self.agent_data.gps.longitude,
            "timestamp": self.agent_data.timestamp,
        }


# WebSocket subscriptions
subscriptions: Dict[int, Set[WebSocket]] = {}


# FastAPI WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    if user_id not in subscriptions:
        subscriptions[user_id] = set()
    subscriptions[user_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        subscriptions[user_id].remove(websocket)


# Function to send data to subscribed users
async def send_data_to_subscribers(user_id: int, data):
    if user_id in subscriptions:
        for websocket in subscriptions[user_id]:
            await websocket.send_json(json.dumps(data))


# FastAPI CRUDL endpoints


@app.post("/processed_agent_data/")
async def create_processed_agent_data(data: List[ProcessedAgentData]):
    db = SessionLocal()
    try:
        await send_data_to_subscribers(1, data)
        for item in data:
            new_item = ProcessedAgentDataModel(**item.model_dump())
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
    finally:
        db.close()


@app.get(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def read_processed_agent_data(processed_agent_data_id: int):
    db = SessionLocal()
    try:
        item = db.get(ProcessedAgentDataModel, processed_agent_data_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Data not found")
        return item
    finally:
        db.close()


@app.get("/processed_agent_data/", response_model=List[ProcessedAgentDataInDB])
def list_processed_agent_data():
    db = SessionLocal()
    try:
        items = db.query(ProcessedAgentDataModel).all()
        if items is None:
            raise HTTPException(status_code=404, detail="Data not found")
        return items
    finally:
        db.close()


@app.put(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def update_processed_agent_data(processed_agent_data_id: int, data: ProcessedAgentData):
    db = SessionLocal()
    try:
        item = db.get(ProcessedAgentDataModel, processed_agent_data_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Data not found")
        query = update(ProcessedAgentDataModel).where(ProcessedAgentDataModel.id == processed_agent_data_id).values(**data.model_dump())
        db.execute(query)
        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()


@app.delete(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def delete_processed_agent_data(processed_agent_data_id: int):
    db = SessionLocal()
    try:
        item = db.get(ProcessedAgentDataModel, processed_agent_data_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Data not found")
        db.execute(delete(ProcessedAgentDataModel).where(ProcessedAgentDataModel.id == processed_agent_data_id))
        db.commit()
        return item
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
