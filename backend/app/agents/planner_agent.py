from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import BaseTravelAgent
from app.schemas.itinerary import TripPlan


class PlannerAgentInput(BaseModel):
    origin: str
    destination: str
    dates: str
    travelers: int
    travel_style: str
    budget_tier: str
    research_notes: str = ""
    weather_info: str = ""
    hotel_recommendations: str = ""
    budget_breakdown: str = ""
    logistics_info: str = ""
    activities_recommendations: str = ""
    retrieval_context: str = ""


class PlannerAgentOutput(BaseModel):
    plan: TripPlan
    quality_score: int


class PlannerAgent(BaseTravelAgent[PlannerAgentInput, PlannerAgentOutput]):
    name = "planner_agent"

    async def run(self, structured_input: PlannerAgentInput) -> PlannerAgentOutput:
        from app.agents.planner import build_plan_from_input

        plan, quality_score = await build_plan_from_input(structured_input)
        return PlannerAgentOutput(plan=plan, quality_score=quality_score)
