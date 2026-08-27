from fastapi import APIRouter, Request, HTTPException, Query
from uuid import uuid4
from .models import UserCreate, UserUpdate, UserOut, UserLogin

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.post("/login", response_model=UserOut)
async def login_user(login_data: UserLogin, request: Request):
    """
    Login endpoint.
    This avoids the insecure and unscalable practice of downloading the entire
    user list to the frontend just to verify credentials.
    """
    db = request.app.state.db
    # Iterate over all users to find a match (In a real production system with thousands of users, 
    # an index on email should be used, but for this NoSQL key-value DB, scanning is the standard approach).
    records = await db.scan_prefix("user_")
    input_email = login_data.user_email.strip().lower()
    for uid, payload in records:
        db_email = payload.get("user_email", "").strip().lower()
        if db_email == input_email and payload.get("user_password") == login_data.user_password:
            return UserOut(id=uid, **payload)
            
    raise HTTPException(status_code=401, detail="Invalid email or password")


# O(1) Metrics Helper for Users
# ==========================================
async def _update_user_metrics(db, user_delta=0):
    """Fetches the global metrics record, applies the user delta, and saves it."""
    metrics = await db.get("admin_metrics_global")
    if not metrics:
        return  # Failsafe in case lifespan hasn't initialized it yet

    metrics["total_users"] = metrics.get("total_users", 0) + user_delta
    await db.upsert("admin_metrics_global", metrics)


@users_router.post("/", response_model=UserOut)
async def create_user(user: UserCreate, request: Request):
    db = request.app.state.db
    
    # Verify that the email is not already registered
    records = await db.scan_prefix("user_")
    input_email = user.user_email.strip().lower()
    for uid, existing_payload in records:
        if existing_payload.get("user_email", "").strip().lower() == input_email:
            raise HTTPException(status_code=400, detail="Email already registered")
            
    id = f"user_{uuid4().hex}"

    # mode="json" ensures Enums and Bools are perfectly formatted for Rust's simd_json
    payload = user.model_dump(mode="json")
    await db.insert(id, payload)

    # Update metrics: +1 User
    await _update_user_metrics(db, user_delta=1)

    return UserOut(id=id, **payload)


@users_router.get("/", response_model=list[UserOut])
async def get_users(
    request: Request,
    limit: int = Query(100, le=1000),  # Cap maximum items to prevent CPU spikes
    offset: int = Query(0),
):
    db = request.app.state.db
    records = await db.scan_prefix("user_")

    # Slice the array BEFORE Pydantic validation to save CPU
    paginated_records = records[offset : offset + limit]

    users = [UserOut(id=uid, **payload) for uid, payload in paginated_records]
    return users


@users_router.get("/{id}", response_model=UserOut)
async def get_user(id: str, request: Request):
    db = request.app.state.db
    payload = await db.get(id)
    if not payload:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=id, **payload)


@users_router.put("/{id}", response_model=UserOut)
async def update_user(id: str, user_update: UserUpdate, request: Request):
    db = request.app.state.db
    existing = await db.get(id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for email uniqueness if the email is being updated
    if user_update.user_email and user_update.user_email.strip().lower() != existing.get("user_email", "").strip().lower():
        records = await db.scan_prefix("user_")
        input_email = user_update.user_email.strip().lower()
        for uid, existing_payload in records:
            if uid != id and existing_payload.get("user_email", "").strip().lower() == input_email:
                raise HTTPException(status_code=400, detail="Email already registered")

    update_data = user_update.model_dump(exclude_unset=True, mode="json")
    existing.update(update_data)

    await db.upsert(id, existing)

    return UserOut(id=id, **existing)


@users_router.delete("/{id}")
async def delete_user(id: str, request: Request):
    db = request.app.state.db

    # We must read the user first to ensure they actually exist before decrementing the counter.
    existing = await db.get(id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(id)

    # Update metrics: -1 User
    await _update_user_metrics(db, user_delta=-1)

    return {"message": "User deleted successfully", "id": id}
