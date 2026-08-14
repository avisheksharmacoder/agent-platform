import os
from dotenv import load_dotenv, set_key
from fastapi import APIRouter, Request


agent_state_router = APIRouter(prefix="/agent", tags=["agent"])


@agent_state_router.get("/state")
def get_agent_state():
    load_dotenv(override=True)
    is_active = os.getenv("AGENT_ACTIVE", "False") == "True"
    return {"active": is_active}


@agent_state_router.post("/state")
async def set_agent_state(request: Request):
    payload = await request.json()
    is_active = payload.get("active", False)

    env_file = ".env"
    set_key(env_file, "AGENT_ACTIVE", str(is_active))
    os.environ["AGENT_ACTIVE"] = str(is_active)

    return {"active": is_active, "message": "Agent state updated"}
