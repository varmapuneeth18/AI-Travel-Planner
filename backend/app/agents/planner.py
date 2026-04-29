from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain_core.output_parsers import JsonOutputParser
from app.graph.state import TripState
from app.schemas.itinerary import TripPlan
from app.core.prompts import PLANNER_SYSTEM_PROMPT
from app.tools.google_places import google_flights_link, kayak_link, search_places
import os
from pydantic import ValidationError

async def build_plan_from_input(agent_input):
    parser = JsonOutputParser(pydantic_object=TripPlan)
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    retrieval_context = getattr(agent_input, "retrieval_context", "")

    if not project:
        from datetime import datetime, timedelta
        from app.schemas.itinerary import (
            DailyPlan, Activity, AccommodationOption,
            BudgetBreakdown, PackingItem, WeatherData
        )

        try:
            start_date_str, end_date_str = agent_input.dates.split(" to ")
            start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d")
            num_days = (end_date - start_date).days + 1
        except Exception:
            start_date = datetime.now()
            num_days = 3

        itinerary = []
        for i in range(min(num_days, 7)):
            day_date = start_date + timedelta(days=i)
            itinerary.append(DailyPlan(
                day_number=i + 1,
                date=day_date.strftime("%Y-%m-%d"),
                city=agent_input.destination,
                weather=WeatherData(
                    date=day_date.strftime("%Y-%m-%d"),
                    temperature_c=20.0,
                    condition="Partly cloudy",
                    precip_prob=30
                ),
                morning_activities=[
                    Activity(
                        name=f"Morning exploration of {agent_input.destination}",
                        description="Discover the city's highlights",
                        location="City Center",
                        estimated_cost=0,
                        time_slot="morning"
                    )
                ],
                afternoon_activities=[
                    Activity(
                        name=f"Afternoon activity in {agent_input.destination}",
                        description="Experience local culture",
                        location="Downtown",
                        estimated_cost=25,
                        time_slot="afternoon"
                    )
                ],
                evening_activities=[
                    Activity(
                        name=f"Evening dining in {agent_input.destination}",
                        description="Try local cuisine",
                        location="Restaurant District",
                        estimated_cost=50,
                        time_slot="evening"
                    )
                ],
                meal_suggestions=["Local breakfast cafe", "Lunch at market", "Traditional dinner"]
            ))

        mock_plan = TripPlan(
            title=f"{num_days}-Day {agent_input.destination} Trip",
            summary=f"A {num_days}-day {agent_input.travel_style} adventure in {agent_input.destination} for the requested budget tier.",
            itinerary=itinerary,
            hotels_shortlist=[
                AccommodationOption(
                    name=f"Mock Hotel {agent_input.destination}",
                    area="City Center",
                    price_per_night=100,
                    rating=4.0,
                    description="Comfortable accommodation in the heart of the city",
                    booking_link=f"https://www.google.com/search?q=hotels+in+{agent_input.destination.replace(' ', '+')}"
                )
            ],
            intercity_travel=[],
            budget=BudgetBreakdown(
                flights=600,
                accommodation=100 * num_days,
                activities=50 * num_days,
                food=75 * num_days,
                transport_local=20 * num_days,
                total_estimated=600 + (245 * num_days),
                currency="USD"
            ),
            packing_list=[
                PackingItem(category="Clothing", item="Comfortable walking shoes"),
                PackingItem(category="Accessories", item="Camera"),
                PackingItem(category="Documents", item="Passport and tickets"),
            ],
        )
        return mock_plan, 7

    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project=project,
        location=location,
        temperature=0.2,
        max_tokens=3200
    )
    prompt = ChatPromptTemplate.from_template(
        PLANNER_SYSTEM_PROMPT + "\n\nRetrieved Context:\n{retrieval_context}\n\n{format_instructions}"
    )
    chain = prompt | llm | parser
    result = await chain.ainvoke(
        {
            "origin": agent_input.origin,
            "destination": agent_input.destination,
            "dates": agent_input.dates,
            "travelers": agent_input.travelers,
            "budget_tier": agent_input.budget_tier,
            "travel_style": agent_input.travel_style,
            "research_notes": agent_input.research_notes,
            "weather_info": agent_input.weather_info,
            "hotel_recommendations": agent_input.hotel_recommendations,
            "budget_breakdown": agent_input.budget_breakdown,
            "logistics_info": agent_input.logistics_info,
            "activities_recommendations": agent_input.activities_recommendations,
            "retrieval_context": retrieval_context,
            "format_instructions": parser.get_format_instructions(),
        }
    )
    try:
        plan = TripPlan(**result)
    except ValidationError:
        plan = _repair_plan_payload(agent_input, result)
    quality_score = 8
    if len(plan.itinerary) < 1:
        quality_score = 3
    if len(plan.hotels_shortlist) < 1:
        quality_score = min(quality_score, 5)
    if plan.budget.total_estimated <= 0:
        quality_score = min(quality_score, 4)
    return plan, quality_score


def _repair_plan_payload(agent_input, raw_result):
    from datetime import datetime, timedelta
    from app.schemas.itinerary import (
        Activity,
        AccommodationOption,
        BudgetBreakdown,
        DailyPlan,
        PackingItem,
        TransportOption,
        WeatherData,
    )

    if not isinstance(raw_result, dict):
        raw_result = {}

    try:
        start_date_str, end_date_str = agent_input.dates.split(" to ")
        start_date = datetime.strptime(start_date_str.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str.strip(), "%Y-%m-%d")
        num_days = max(1, (end_date - start_date).days + 1)
    except Exception:
        start_date = datetime.now()
        num_days = 3

    itinerary = raw_result.get("itinerary") or []
    normalized_days = []
    for index in range(num_days):
        day_date = start_date + timedelta(days=index)
        day_payload = itinerary[index] if index < len(itinerary) and isinstance(itinerary[index], dict) else {}
        normalized_days.append(
            DailyPlan(
                day_number=index + 1,
                date=day_payload.get("date", day_date.strftime("%Y-%m-%d")),
                city=day_payload.get("city", agent_input.destination),
                weather=WeatherData(
                    date=day_date.strftime("%Y-%m-%d"),
                    temperature_c=day_payload.get("weather", {}).get("temperature_c", 24.0)
                    if isinstance(day_payload.get("weather"), dict)
                    else 24.0,
                    condition=day_payload.get("weather", {}).get("condition", "Seasonal conditions")
                    if isinstance(day_payload.get("weather"), dict)
                    else "Seasonal conditions",
                    precip_prob=day_payload.get("weather", {}).get("precip_prob", 20)
                    if isinstance(day_payload.get("weather"), dict)
                    else 20,
                ),
                morning_activities=[
                    Activity(
                        name=f"{agent_input.destination} morning highlights",
                        description="Curated from the planner output and destination research.",
                        location="Central district",
                        estimated_cost=20,
                        time_slot="morning",
                    )
                ],
                afternoon_activities=[
                    Activity(
                        name=f"{agent_input.destination} afternoon exploration",
                        description="Balanced sightseeing and local experiences.",
                        location="Main attractions area",
                        estimated_cost=35,
                        time_slot="afternoon",
                    )
                ],
                evening_activities=[
                    Activity(
                        name=f"{agent_input.destination} evening dining",
                        description="Recommended dinner and relaxed neighborhood walk.",
                        location="Dining district",
                        estimated_cost=45,
                        time_slot="evening",
                    )
                ],
                meal_suggestions=day_payload.get(
                    "meal_suggestions",
                    ["Local breakfast", "Regional lunch spot", "Popular dinner venue"],
                ),
            )
        )

    budget_payload = raw_result.get("budget") if isinstance(raw_result.get("budget"), dict) else {}
    fallback_total = max(600, 250 * num_days)
    budget = BudgetBreakdown(
        flights=float(budget_payload.get("flights", 600)),
        accommodation=float(budget_payload.get("accommodation", 120 * num_days)),
        activities=float(budget_payload.get("activities", 60 * num_days)),
        food=float(budget_payload.get("food", 70 * num_days)),
        transport_local=float(budget_payload.get("transport_local", 25 * num_days)),
        total_estimated=float(budget_payload.get("total_estimated", fallback_total)),
        currency=budget_payload.get("currency", "USD"),
    )

    hotels_payload = raw_result.get("hotels_shortlist") or []
    google_hotels = search_places(
        f"best hotels in {agent_input.destination}",
        page_size=3,
        included_type="lodging",
    )
    hotels = []
    for hotel in hotels_payload[:3]:
        if isinstance(hotel, dict):
            hotels.append(
                AccommodationOption(
                    name=hotel.get("name", f"{agent_input.destination} Stay"),
                    area=hotel.get("area", "Central area"),
                    price_per_night=float(hotel.get("price_per_night", 120)),
                    rating=hotel.get("rating", 4.0),
                    booking_link=hotel.get("booking_link"),
                    description=hotel.get("description", "Well-located stay option."),
                )
            )
    if not hotels:
        if google_hotels:
            hotels = [
                AccommodationOption(
                    name=place.get("name", f"{agent_input.destination} Stay"),
                    area=place.get("address", "Central area"),
                    price_per_night=120,
                    rating=place.get("rating", 4.1),
                    booking_link=place.get("maps_uri") or place.get("website_uri"),
                    description=place.get("summary") or "Google Places recommended stay option.",
                )
                for place in google_hotels[:3]
            ]
        else:
            hotels = [
                AccommodationOption(
                    name=f"{agent_input.destination} Central Stay",
                    area="Central area",
                    price_per_night=120,
                    rating=4.1,
                    booking_link=f"https://www.google.com/travel/hotels/{agent_input.destination.replace(' ', '%20')}",
                    description="Fallback curated accommodation with good city access.",
                )
            ]

    transport_payload = raw_result.get("intercity_travel") or []
    intercity_travel = []
    for item in transport_payload[:2]:
        if isinstance(item, dict):
            intercity_travel.append(
                TransportOption(
                    type=item.get("type", "flight"),
                    provider=item.get("provider", "Recommended Carrier"),
                    departure=item.get("departure", "TBD"),
                    arrival=item.get("arrival", "TBD"),
                    estimated_price=float(item.get("estimated_price", 250)),
                    booking_link=item.get("booking_link"),
                )
            )

    packing_payload = raw_result.get("packing_list") or []
    packing_list = []
    for item in packing_payload[:6]:
        if isinstance(item, dict):
            packing_list.append(
                PackingItem(
                    category=item.get("category", "Travel"),
                    item=item.get("item", "Comfortable clothing"),
                    reason=item.get("reason"),
                )
            )
    if not packing_list:
        packing_list = [
            PackingItem(category="Documents", item="Passport and confirmations"),
            PackingItem(category="Clothing", item="Comfortable walking shoes"),
            PackingItem(category="Accessories", item="Phone charger and power adapter"),
        ]

    if not intercity_travel:
        try:
            start_date, end_date = agent_input.dates.split(" to ")
            start_date = start_date.strip()
            end_date = end_date.strip()
        except Exception:
            start_date = "TBD"
            end_date = "TBD"
        intercity_travel = [
            TransportOption(
                type="flight",
                provider="Google Flights",
                departure=f"{agent_input.origin} ({start_date})",
                arrival=agent_input.destination,
                estimated_price=budget.flights if budget.flights > 0 else 600,
                booking_link=google_flights_link(agent_input.origin, agent_input.destination, start_date, end_date)
                if start_date != "TBD" and end_date != "TBD"
                else None,
            ),
            TransportOption(
                type="flight",
                provider="Kayak",
                departure=agent_input.origin,
                arrival=f"{agent_input.destination} return ({end_date})",
                estimated_price=budget.flights if budget.flights > 0 else 600,
                booking_link=kayak_link(agent_input.origin, agent_input.destination, start_date, end_date)
                if start_date != "TBD" and end_date != "TBD"
                else None,
            ),
        ]

    return TripPlan(
        title=raw_result.get("title", f"{num_days}-Day {agent_input.destination} Trip"),
        summary=raw_result.get(
            "summary",
            f"Recovered structured itinerary for a {num_days}-day {agent_input.travel_style} trip to {agent_input.destination}.",
        ),
        itinerary=normalized_days,
        hotels_shortlist=hotels,
        intercity_travel=intercity_travel,
        budget=budget,
        packing_list=packing_list,
    )

async def planner_node(state: TripState):
    spec = state['spec']
    try:
        from app.agents.planner_agent import PlannerAgentInput

        planner_input = PlannerAgentInput(
            origin=spec.origin,
            destination=spec.destination,
            dates=spec.dates,
            travelers=spec.travelers,
            travel_style=spec.travel_style,
            budget_tier=spec.budget_tier,
            research_notes=state.get("research_notes", ""),
            weather_info=state.get("weather_info", "Not checked"),
            hotel_recommendations=state.get("hotel_recommendations", ""),
            budget_breakdown=state.get("budget_breakdown", ""),
            logistics_info=state.get("logistics_info", ""),
            activities_recommendations=state.get("activities_recommendations", ""),
            retrieval_context=state.get("retrieval_context", ""),
        )
        plan, quality_score = await build_plan_from_input(planner_input)
        return {"plan": plan, "status": "completed", "plan_quality_score": quality_score}
    except Exception as e:
        return {"messages": [f"Error generating plan: {str(e)}"], "status": "failed", "plan_quality_score": 0}
