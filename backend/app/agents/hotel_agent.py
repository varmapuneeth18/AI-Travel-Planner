from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import BaseTravelAgent


class HotelAgentInput(BaseModel):
    destination: str
    dates: str
    budget_tier: str
    travelers: int
    travel_style: str
    interests: list[str] = []
    research_notes: str = ""
    weather_info: str = ""
    retrieval_context: str = ""


class HotelAgentOutput(BaseModel):
    hotel_recommendations: str


class HotelAgent(BaseTravelAgent[HotelAgentInput, HotelAgentOutput]):
    name = "hotel_agent"

    async def run(self, structured_input: HotelAgentInput) -> HotelAgentOutput:
        from app.agents.hotel import build_hotel_output

        hotel_recommendations = await build_hotel_output(structured_input)
        return HotelAgentOutput(hotel_recommendations=hotel_recommendations)
