from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from app.graph.state import TripState
from app.core.prompts import RESEARCHER_SYSTEM_PROMPT
from app.tools.web_search import web_search_tool
from app.tools.google_places import search_places
import os

async def research_node(state: TripState):
    spec = state['spec']

    # Check for Vertex AI configuration
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project:
        return {"research_notes": "Simulation: The user likes museums and spicy food. Recommended: Grand Museum, Spicy Noodle House."}

    places_query = f"top attractions in {spec.destination}"
    food_query = f"best restaurants in {spec.destination}"
    places = search_places(places_query, page_size=5)
    restaurants = search_places(food_query, page_size=4, included_type="restaurant")
    search_results = []
    for query in [
        f"best things to do in {spec.destination} {' '.join(spec.interests)}",
        f"top restaurants {spec.destination} {spec.budget_tier} budget",
    ]:
        try:
            search_results.extend(web_search_tool.invoke({"query": query, "max_results": 1}))
        except Exception as e:
            print(f"Search error for '{query}': {e}")

    places_context = "\n".join(
        [
            f"- {place['name']} | {place['address']} | rating={place.get('rating', 'N/A')} | maps={place.get('maps_uri', '')}"
            for place in places
        ]
    )
    restaurant_context = "\n".join(
        [
            f"- {place['name']} | {place['address']} | rating={place.get('rating', 'N/A')} | maps={place.get('maps_uri', '')}"
            for place in restaurants
        ]
    )
    search_context = "\n\n".join(
        part
        for part in [
            f"Google Places Attractions:\n{places_context}" if places_context else "",
            f"Google Places Restaurants:\n{restaurant_context}" if restaurant_context else "",
            "\n\n".join(
                [f"**{r['title']}**\n{r['snippet']}\nSource: {r['url']}" for r in search_results[:4]]
            ),
        ]
        if part
    )

    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project=project,
        location=location,
        temperature=0.7,
        max_tokens=2500
    )

    prompt = ChatPromptTemplate.from_template(
        RESEARCHER_SYSTEM_PROMPT + "\n\nWeb Search Results:\n{search_context}"
    )
    chain = prompt | llm

    response = await chain.ainvoke({
        "destination": spec.destination,
        "interests": ", ".join(spec.interests) if spec.interests else "general sightseeing",
        "budget_tier": spec.budget_tier,
        "search_context": search_context
    })

    return {"research_notes": response.content}
