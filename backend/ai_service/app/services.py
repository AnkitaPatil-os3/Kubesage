from app.logger import logger
from sqlmodel import Session, select
from app.database import engine
from app.models import QueryHistory

def delete_user_history(user_id: int):
    """Delete all query history belonging to a specific user when they are deleted"""
    try:
        with Session(engine) as session:
            # Find all history entries for this user
            history_entries = session.exec(
                select(QueryHistory).where(QueryHistory.user_id == user_id)
            ).all()
            
            # Delete all history entries
            for entry in history_entries:
                session.delete(entry)
            
            # Commit all deletions
            session.commit()
            logger.info(f"Deleted all query history for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error deleting query history for user {user_id}: {str(e)}")
        # Don't re-raise the exception as this is called from message queue
