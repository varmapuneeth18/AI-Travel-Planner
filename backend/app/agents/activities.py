from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from app.graph.state import TripState
from app.core.prompts import ACTIVITIES_SYSTEM_PROMPT
from app.tools.web_search import web_search_tool
from app.tools.google_places import search_places
import os


async def build_activities_output(agent_input):
    research_notes = getattr(agent_input, "research_notes", "")
    weather_info = getattr(agent_input, "weather_info", "")
    hotel_recommendations = getattr(agent_input, "hotel_recommendations", "")

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
        activities_context = f"\n\n=== ACTIVITIES & EXPERIENCES ===\n"
        activities_context += (
            f"Based on your interests: {', '.join(agent_input.interests) if agent_input.interests else 'general sightseeing'}\n\n"
        )
        dest_encoded = agent_input.destination.replace(" ", "+")
        activities_context += "TOURS & ACTIVITIES:\n"
        activities_context += f"  • Walking Tour of {agent_input.destination}\n"
        activities_context += f"    Platform: GetYourGuide\n"
        activities_context += f"    Link: https://www.getyourguide.com/s/?q={dest_encoded}+walking+tour\n\n"
        activities_context += "DINING RESERVATIONS:\n"
        activities_context += f"  • Top-rated restaurants in {agent_input.destination}\n"
        activities_context += (
            f"    Link: https://www.opentable.com/s?covers=2&dateTime={agent_input.dates.split(' to ')[0]}+19:00&term={dest_encoded}\n\n"
        )
        activities_context += "SUGGESTED DAILY ACTIVITIES:\n"
        activities_context += "  Day 1: Arrival, light exploration, welcome dinner\n"
        activities_context += f"  Day 2-{num_days - 1}: Mix of tours, activities, and free time\n"
        activities_context += f"  Day {num_days}: Final exploration and departure\n"
        return activities_context

    interests_str = " ".join(agent_input.interests) if agent_input.interests else "sightseeing"
    attraction_results = search_places(
        f"best tourist attractions in {agent_input.destination}",
        page_size=6,
        included_type="tourist_attraction",
    )
    restaurant_results = search_places(
        f"best restaurants in {agent_input.destination}",
        page_size=4,
        included_type="restaurant",
    )
    search_queries = [
        f"best tours and activities in {agent_input.destination} 2026",
        f"{agent_input.destination} {interests_str} experiences",
    ]
    search_results = []
    for query in search_queries:
        try:
            results = web_search_tool.invoke({"query": query, "max_results": 2})
            search_results.extend(results)
        except Exception as e:
            print(f"Search error for '{query}': {e}")

    search_context = "\n\n".join(
        [f"**{r['title']}**\n{r['snippet']}\nSource: {r['url']}" for r in search_results[:6]]
    )
    attraction_context = "\n".join(
        [
            f"- {place['name']} | {place['address']} | rating={place.get('rating', 'N/A')} | maps={place.get('maps_uri', '')}"
            for place in attraction_results
        ]
    )
    restaurant_context = "\n".join(
        [
            f"- {place['name']} | {place['address']} | rating={place.get('rating', 'N/A')} | maps={place.get('maps_uri', '')}"
            for place in restaurant_results
        ]
    )
    full_context = "\n\n".join(
        part
        for part in [
            f"Google Places Attractions:\n{attraction_context}" if attraction_context else "",
            f"Google Places Restaurants:\n{restaurant_context}" if restaurant_context else "",
            search_context,
        ]
        if part
    )
    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project=project,
        location=location,
        temperature=0.4,
        max_tokens=2500,
    )
    prompt = ChatPromptTemplate.from_template(
        ACTIVITIES_SYSTEM_PROMPT + "\n\nWeb Search Results:\n{search_context}"
    )
    chain = prompt | llm
    response = await chain.ainvoke(
        {
            "destination": agent_input.destination,
            "dates": agent_input.dates,
            "num_days": num_days,
            "travelers": agent_input.travelers,
            "budget_tier": agent_input.budget_tier,
            "travel_style": agent_input.travel_style,
            "interests": ", ".join(agent_input.interests) if agent_input.interests else "general sightseeing",
            "research_notes": research_notes,
            "weather_info": weather_info,
            "hotel_recommendations": hotel_recommendations,
            "search_context": full_context,
        }
    )
    return response.content


async def activities_node(state: TripState):
    """
    Activities Agent: Finds and recommends bookable activities, tours, experiences,
    and dining options with direct booking links from platforms like Viator,
    GetYourGuide, TripAdvisor, and OpenTable.
    """
    spec = state['spec']
    from app.agents.itinerary_agent import ItineraryAgentInput

    activities_recommendations = await build_activities_output(
        ItineraryAgentInput(
            destination=spec.destination,
            dates=spec.dates,
            travelers=spec.travelers,
            interests=spec.interests,
            budget_tier=spec.budget_tier,
            travel_style=spec.travel_style,
            research_notes=state.get("research_notes", ""),
            weather_info=state.get("weather_info", ""),
            hotel_recommendations=state.get("hotel_recommendations", ""),
        )
    )
    return {"activities_recommendations": activities_recommendations}
