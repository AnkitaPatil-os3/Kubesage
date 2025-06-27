# Add this function to the services.py file

def delete_user_kubeconfigs(user_id: int):
    """Delete all kubeconfigs belonging to a specific user when they are deleted"""
    from sqlmodel import select, Session
    from app.database import engine
    from app.models import Kubeconfs
    import os
    from app.logger import logger
    
    try:
        with Session(engine) as session:
            # Find all kubeconfigs for this user
            kubeconfs = session.exec(
                select(Kubeconfs).where(Kubeconfs.user_id == user_id)
            ).all()
            
            for kubeconf in kubeconfs:
                # Delete the file if it exists
                file_path = kubeconf.path
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted kubeconfig file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting kubeconfig file {file_path}: {str(e)}")
                
                # Delete from database
                session.delete(kubeconf)
            
            # Commit all deletions
            session.commit()
            logger.info(f"Deleted all kubeconfigs for user {user_id}")
    
    except Exception as e:
        logger.error(f"Error deleting kubeconfigs for user {user_id}: {str(e)}")
        # Don't re-raise the exception as this is called from message queue
