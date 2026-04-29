from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from app.graph.state import TripState
from app.core.prompts import HOTEL_SYSTEM_PROMPT
from app.tools.web_search import web_search_tool
from app.tools.google_places import search_places
from app.tools.mocks import BookingMocks
import os


async def build_hotel_output(agent_input):
    retrieval_context = getattr(agent_input, "retrieval_context", "")
    research_notes = getattr(agent_input, "research_notes", "")
    weather_info = getattr(agent_input, "weather_info", "")

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    places_hotels = search_places(
        f"best hotels in {agent_input.destination} for travelers",
        page_size=5,
        included_type="lodging",
    )
    if not project:
        hotels = BookingMocks.search_hotels(agent_input.destination, agent_input.budget_tier)
        hotel_context = "\n\n=== ACCOMMODATION OPTIONS ===\n"
        for hotel in hotels:
            hotel_context += f"\n• {hotel.name} ({hotel.area})\n"
            hotel_context += f"  Price: ${hotel.price_per_night}/night\n"
            hotel_context += f"  Rating: {hotel.rating}/5.0\n"
            hotel_context += f"  Description: {hotel.description}\n"
            hotel_context += f"  Booking: {hotel.booking_link}\n"
        if places_hotels:
            hotel_context += "\nGoogle Places Matches:\n"
            for place in places_hotels[:4]:
                hotel_context += (
                    f"- {place['name']} | {place['address']} | rating={place.get('rating', 'N/A')} | "
                    f"maps={place.get('maps_uri', '')}\n"
                )
        if retrieval_context:
            hotel_context += f"\nRAG CONTEXT:\n{retrieval_context}\n"
        return hotel_context

    search_queries = [
        f"best hotels in {agent_input.destination} {agent_input.budget_tier} budget 2026",
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
    places_context = "\n".join(
        [
            f"- {place['name']} | {place['address']} | rating={place.get('rating', 'N/A')} | maps={place.get('maps_uri', '')}"
            for place in places_hotels[:5]
        ]
    )
    full_context = "\n\n".join(
        part
        for part in [
            f"Google Places Hotels:\n{places_context}" if places_context else "",
            search_context,
            retrieval_context,
        ]
        if part
    )
    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project=project,
        location=location,
        temperature=0.3,
        max_tokens=2500,
    )
    prompt = ChatPromptTemplate.from_template(
        HOTEL_SYSTEM_PROMPT + "\n\nWeb Search Results:\n{search_context}\n\nRetrieved Context:\n{retrieval_context}"
    )
    chain = prompt | llm
    response = await chain.ainvoke(
        {
            "destination": agent_input.destination,
            "dates": agent_input.dates,
            "budget_tier": agent_input.budget_tier,
            "travelers": agent_input.travelers,
            "travel_style": agent_input.travel_style,
            "interests": ", ".join(agent_input.interests) if agent_input.interests else "general sightseeing",
            "research_notes": research_notes,
            "weather_info": weather_info,
            "search_context": full_context,
            "retrieval_context": retrieval_context,
        }
    )
    return response.content


async def hotel_node(state: TripState):
    """
    Hotel Agent: Researches and recommends accommodations based on destination,
    budget, dates, and traveler preferences.
    """
    spec = state['spec']
    from app.agents.hotel_agent import HotelAgentInput

    hotel_recommendations = await build_hotel_output(
        HotelAgentInput(
            destination=spec.destination,
            dates=spec.dates,
            budget_tier=spec.budget_tier,
            travelers=spec.travelers,
            travel_style=spec.travel_style,
            interests=spec.interests,
            research_notes=state.get("research_notes", ""),
            weather_info=state.get("weather_info", ""),
            retrieval_context=state.get("retrieval_context", ""),
        )
    )
    return {"hotel_recommendations": hotel_recommendations}
