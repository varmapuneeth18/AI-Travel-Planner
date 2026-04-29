from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from app.graph.state import TripState
from app.core.prompts import BUDGET_SYSTEM_PROMPT
from app.tools.web_search import web_search_tool
import os


async def build_budget_output(agent_input):
    research_notes = getattr(agent_input, "research_notes", "")
    hotel_recommendations = getattr(agent_input, "hotel_recommendations", "")
    logistics_info = getattr(agent_input, "logistics_info", "")
    retrieval_context = getattr(agent_input, "retrieval_context", "")

    try:
        start, end = agent_input.dates.split(" to ")
        from datetime import datetime

        start_date = datetime.strptime(start.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end.strip(), "%Y-%m-%d")
        num_days = (end_date - start_date).days + 1
    except Exception:
        num_days = 3

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        budget_multiplier = {
            "low": 75,
            "medium": 150,
            "high": 300,
            "luxury": 600,
        }.get(agent_input.budget_tier, 150)
        daily_budget = budget_multiplier * agent_input.travelers
        total = daily_budget * num_days
        budget_context = f"""
=== BUDGET BREAKDOWN ===
Trip Duration: {num_days} days
Budget Tier: {agent_input.budget_tier}
Travelers: {agent_input.travelers}

Estimated Costs (USD):
• Flights: ${300 * agent_input.travelers:.2f}
• Accommodation: ${(budget_multiplier * 0.4) * num_days:.2f}
• Food & Dining: ${(budget_multiplier * 0.3) * num_days:.2f}
• Activities: ${(budget_multiplier * 0.2) * num_days:.2f}
• Local Transport: ${(budget_multiplier * 0.1) * num_days:.2f}

TOTAL ESTIMATED: ${total + (300 * agent_input.travelers):.2f} USD

Daily Budget Per Person: ${budget_multiplier:.2f}/day
"""
        if retrieval_context:
            budget_context += f"\nRAG CONTEXT:\n{retrieval_context}\n"
        return budget_context

    search_queries = [
        f"average cost of living {agent_input.destination} 2026 daily budget",
        f"{agent_input.destination} travel budget {agent_input.budget_tier}",
    ]
    search_results = []
    for query in search_queries:
        try:
            results = web_search_tool.invoke({"query": query, "max_results": 2})
            search_results.extend(results)
        except Exception as e:
            print(f"Search error for '{query}': {e}")

    search_context = "\n\n".join(
        [f"**{r['title']}**\n{r['snippet']}\nSource: {r['url']}" for r in search_results[:5]]
    )
    full_context = "\n\n".join(part for part in [search_context, retrieval_context] if part)
    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project=project,
        location=location,
        temperature=0.2,
        max_tokens=2200,
    )
    prompt = ChatPromptTemplate.from_template(
        BUDGET_SYSTEM_PROMPT + "\n\nWeb Search Results:\n{search_context}\n\nRetrieved Context:\n{retrieval_context}"
    )
    chain = prompt | llm
    response = await chain.ainvoke(
        {
            "origin": agent_input.origin,
            "destination": agent_input.destination,
            "dates": agent_input.dates,
            "num_days": num_days,
            "travelers": agent_input.travelers,
            "budget_tier": agent_input.budget_tier,
            "travel_style": agent_input.travel_style,
            "research_notes": research_notes,
            "hotel_recommendations": hotel_recommendations,
            "logistics_info": logistics_info,
            "search_context": full_context,
            "retrieval_context": retrieval_context,
        }
    )
    return response.content


async def budget_node(state: TripState):
    """
    Budget Agent: Analyzes trip requirements and provides detailed cost breakdown
    for flights, accommodation, food, activities, and local transport.
    """
    spec = state['spec']
    from app.agents.budget_agent import BudgetAgentInput

    budget_breakdown = await build_budget_output(
        BudgetAgentInput(
            origin=spec.origin,
            destination=spec.destination,
            dates=spec.dates,
            travelers=spec.travelers,
            budget_tier=spec.budget_tier,
            travel_style=spec.travel_style,
            research_notes=state.get("research_notes", ""),
            hotel_recommendations=state.get("hotel_recommendations", ""),
            logistics_info=state.get("logistics_info", ""),
            retrieval_context=state.get("retrieval_context", ""),
        )
    )
    return {"budget_breakdown": budget_breakdown}
