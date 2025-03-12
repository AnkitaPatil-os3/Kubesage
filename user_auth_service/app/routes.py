# Add after importing necessary modules
from app.queue import publish_user_created, publish_user_updated, publish_user_deleted

# Then in the user creation route:
@user_router.post("/", response_model=UserResponse)
async def create_user(user_create: UserCreate, db: SessionDep):
    # ...existing code...
    
    # After user is created and committed to database, publish event
    user_data = {"id": db_user.id, "username": db_user.username, "email": db_user.email}
    publish_user_created(user_data)
    
    return db_user

# Similarly for update and delete routes, add:
# publish_user_updated(user_data)
# publish_user_deleted(user_id)
