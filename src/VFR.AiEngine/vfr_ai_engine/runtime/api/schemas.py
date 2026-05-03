"""Pydantic DTOs exposed by the AI engine HTTP API."""

from pydantic import BaseModel


class AvatarGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str


class GarmentGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str


class ProfileAvatarRequest(BaseModel):
    user_id: str
    height: float
    weight: float
    body_type: str
    gender: str = "neutral"
    muscularity: float = 0
    body_fat_percentage: float = 0
    chest: float = 0
    waist: float = 0
    hip: float = 0
    shoulder: float = 0
    calf: float = 0
    arm_length: float = 0
    torso_length: float = 0
    leg_length: float = 0
    face_image_url: str = ""

