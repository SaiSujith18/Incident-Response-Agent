from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.models.postmortem import Postmortem
from backend.services.postmortem_service import PostmortemService
from backend.models.incident import ResolutionRequest
from backend.agent.incident_agent import IncidentAgent

from backend.memory.hindsight_client import (
    initialize_memory_async,
    close_memory,
    retain_memory,
)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="MemoryOps Incident Response Agent",
    description="AI incident response using Hindsight organizational memory",
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST / RESPONSE LOGGER
# =========================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):

    print()
    print("=" * 60)
    print(f"[REQUEST]  {request.method} {request.url.path}")
    print("=" * 60)

    try:

        response = await call_next(request)

        print(
            f"[RESPONSE] {request.method} "
            f"{request.url.path} "
            f"→ {response.status_code}"
        )

        print("=" * 60)
        print()

        return response

    except Exception as exc:

        print(
            f"[ERROR] {request.method} "
            f"{request.url.path} "
            f"→ {type(exc).__name__}: {exc}"
        )

        print("=" * 60)
        print()

        raise


# =========================================================
# REQUEST MODEL
# =========================================================

class IncidentRequest(BaseModel):
    incident: str


# =========================================================
# INCIDENT AGENT
# =========================================================

agent = IncidentAgent()
postmortem_service = PostmortemService()

# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
async def startup_event():

    print()
    print("=" * 60)
    print("Initializing Hindsight...")
    print("=" * 60)

    await initialize_memory_async()

    print("Hindsight initialization complete.")
    print()


# =========================================================
# SHUTDOWN
# =========================================================

@app.on_event("shutdown")
async def shutdown_event():

    print()
    print("=" * 60)
    print("Closing Hindsight...")
    print("=" * 60)

    try:
        close_memory()
    except Exception as exc:
        print(f"Hindsight close warning: {exc}")

    print("Hindsight closed.")
    print()


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "status": "success",
        "message": "MemoryOps Incident Response Agent is running",
    }


# =========================================================
# ANALYZE INCIDENT
# =========================================================

@app.post("/analyze")
async def analyze_incident(request: IncidentRequest):

    print()
    print("[ANALYZE] Incident received:")
    print(request.incident)

    try:

        result = await agent.analyze(
            request.incident
        )

        print("[ANALYZE] Analysis completed successfully.")

        return {
            "status": "success",
            "analysis": result["analysis"],
            "memories": result["memories"],
        }

    except Exception as exc:

        import traceback

        print()
        print("=== ANALYZE ERROR ===")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# RESOLVE INCIDENT
# =========================================================

@app.post("/resolve")
async def resolve_incident(
    request: ResolutionRequest,
):

    print()
    print("[RESOLVE] Resolution request received:")
    print(request)

    try:

        # -------------------------------------------------
        # Create structured organizational memory
        # -------------------------------------------------

        memory_content = f"""
Incident ID: {request.incident_id}

Resolution:
{request.resolution}

Outcome:
{request.outcome}

Recovery Time:
{request.recovery_time}

What Worked:
{request.what_worked}

What Failed:
{request.what_failed}
"""

        # -------------------------------------------------
        # Store resolution asynchronously
        # -------------------------------------------------

        result = await retain_memory(
            content=memory_content,
            context="incident resolution",
          )

        print()
        print("[RESOLVE] Memory stored successfully.")
        print(result)

        return {
            "status": "success",
            "incident_id": request.incident_id,
            "message": "Incident resolution stored successfully",
            "memory": memory_content,
        }

    except Exception as exc:

        import traceback

        print()
        print("=== RESOLVE ERROR ===")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

# =========================================================
# POSTMORTEM → HINDSIGHT
# =========================================================

@app.post("/postmortem")
async def create_postmortem(request: Postmortem):

    try:

        print()
        print("=" * 60)
        print("[POSTMORTEM] Creating postmortem")
        print("=" * 60)

        print(f"Incident ID: {request.incident_id}")
        print(f"Root Cause: {request.root_cause}")
        print(f"Resolution: {request.resolution}")
        print(f"Outcome: {request.outcome}")

        # -------------------------------------------------
        # Create structured Postmortem object
        # -------------------------------------------------

        postmortem = postmortem_service.create_postmortem(
            incident_id=request.incident_id,
            root_cause=request.root_cause,
            resolution=request.resolution,
            outcome=request.outcome,
            recovery_time=request.recovery_time,
            what_worked=request.what_worked,
            what_failed=request.what_failed,
        )

        # -------------------------------------------------
        # Convert Postmortem into organizational memory
        # -------------------------------------------------

        memory_content = postmortem_service.format_for_memory(
            postmortem
        )

        print()
        print("[POSTMORTEM] Structured memory:")
        print(memory_content)

        # -------------------------------------------------
        # Store postmortem in Hindsight
        # IMPORTANT: retain_memory is ASYNC
        # -------------------------------------------------

        result = await retain_memory(
            content=memory_content,
            context="incident postmortem",
        )

        print()
        print("[POSTMORTEM] Memory stored successfully.")
        print(result)

        print("=" * 60)
        print()

        return {
            "status": "success",
            "incident_id": postmortem.incident_id,
            "message": "Postmortem stored successfully in Hindsight",
            "postmortem": postmortem.model_dump(),
            "memory": memory_content,
        }

    except Exception as e:

        import traceback

        print()
        print("=" * 60)
        print("[POSTMORTEM ERROR]")
        print("=" * 60)

        traceback.print_exc()

        print("=" * 60)
        print()

        return {
            "status": "error",
            "incident_id": request.incident_id,
            "error": str(e),
        }