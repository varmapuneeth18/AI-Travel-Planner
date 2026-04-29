from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import BaseTravelAgent


class ItineraryAgentInput(BaseModel):
    destination: str
    dates: str
    travelers: int
    interests: list[str] = []
    budget_tier: str
    travel_style: str
    research_notes: str = ""
    weather_info: str = ""
    hotel_recommendations: str = ""


class ItineraryAgentOutput(BaseModel):
    activities_recommendations: str


class ItineraryAgent(BaseTravelAgent[ItineraryAgentInput, ItineraryAgentOutput]):
    name = "itinerary_agent"

    async def run(self, structured_input: ItineraryAgentInput) -> ItineraryAgentOutput:
        from app.agents.activities import build_activities_output

        activities_recommendations = await build_activities_output(structured_input)
        return ItineraryAgentOutput(activities_recommendations=activities_recommendations)
