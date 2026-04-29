from __future__ import annotations

from pydantic import BaseModel

from app.agents.base import BaseTravelAgent


class BudgetAgentInput(BaseModel):
    origin: str
    destination: str
    dates: str
    travelers: int
    budget_tier: str
    travel_style: str
    research_notes: str = ""
    hotel_recommendations: str = ""
    logistics_info: str = ""
    retrieval_context: str = ""


class BudgetAgentOutput(BaseModel):
    budget_breakdown: str


class BudgetAgent(BaseTravelAgent[BudgetAgentInput, BudgetAgentOutput]):
    name = "budget_agent"

    async def run(self, structured_input: BudgetAgentInput) -> BudgetAgentOutput:
        from app.agents.budget import build_budget_output

        budget_breakdown = await build_budget_output(structured_input)
        return BudgetAgentOutput(budget_breakdown=budget_breakdown)
