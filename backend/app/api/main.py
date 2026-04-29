from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.schemas.requests import TripSpec
from app.graph.graph import build_graph
from app.services import build_services
import uuid

load_dotenv()

app = FastAPI(title="AI Travel Planner")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for MVP
trips_db = {}
services = build_services()
graph_app = build_graph(services=services)


def _seed_retrieval_corpus() -> None:
    existing = services.retrieval.vector_store.similarity_search([0.0] * 16, top_k=1)
    if existing:
        return
    services.retrieval.seed_documents(
        [
            {
                "id": "faq-budget",
                "category": "faqs",
                "content": "Budget-conscious travelers should prioritize public transit, neighborhood hotels, and timed attraction passes for better cost control.",
            },
            {
                "id": "doc-itinerary-balance",
                "category": "travel_documents",
                "content": "Strong itineraries balance transit time, weather risk, food planning, and at least one flexible activity block per day.",
            },
            {
                "id": "meta-destination-city-break",
                "category": "destination_metadata",
                "content": "Cultural city trips benefit from museum clustering, reservation management, and neighborhood-by-neighborhood routing.",
            },
            {
                "id": "faq-family-travel",
                "category": "faqs",
                "content": "Family itineraries should include rest windows, low-friction transport, and backup indoor activities for weather changes.",
            },
        ]
    )


_seed_retrieval_corpus()

@app.get("/health")
def health():
    return {"status": "ok", "system_health": services.health_monitor.status()}

@app.post("/plan")
async def create_plan(spec: TripSpec):
    run_id = str(uuid.uuid4())
    run_record = services.observability.create_run_record(run_id, spec.model_dump())

    # Initialize state
    inputs = {
        "run_id": run_id,
        "spec": spec,
        "revision_count": 0,
        "research_notes": "",
        "weather_info": "",
        "hotel_recommendations": "",
        "budget_breakdown": "",
        "logistics_info": "",
        "activities_recommendations": "",
        "plan_quality_score": 0,
        "messages": [],
        "retrieval_context": "",
        "retrieval_metrics": {},
        "agent_metrics": [],
        "degraded": False,
    }
    
    # Run graph
    # In production, use background tasks or a queue (Celery/Redis)
    # For MVP, we await it (might timeout on Vercel, but okay for local)
    try:
        result = await graph_app.ainvoke(inputs)
        plan = result.get("plan")
        run_record.agent_metrics = result.get("agent_metrics", [])
        run_record.response_payload = {"status": result.get("status"), "degraded": result.get("degraded", False)}
        if plan:
            trips_db[run_id] = plan
            run_record.status = "completed"
            services.observability.finalize_run_record(run_record)
            return {
                "run_id": run_id,
                "status": "completed",
                "plan": plan,
                "degraded": result.get("degraded", False),
                "agent_metrics": result.get("agent_metrics", []),
            }
        else:
            run_record.status = "failed"
            run_record.response_payload = {"error": "No plan generated"}
            services.observability.finalize_run_record(run_record)
            return {"run_id": run_id, "status": "failed", "error": "No plan generated"}

    except Exception as e:
        run_record.status = "failed"
        run_record.response_payload = {"error": str(e)}
        services.observability.finalize_run_record(run_record)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trips/{run_id}")
def get_trip(run_id: str):
    if run_id not in trips_db:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trips_db[run_id]

@app.get("/trips")
def list_trips():
    return [{"id": k, "destination": v.itinerary[0].city if v.itinerary else "Unknown"} for k,v in trips_db.items()]
