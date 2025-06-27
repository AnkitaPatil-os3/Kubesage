from sqlmodel import Session, select
from app.models import Role, Permission
import datetime

def seed_roles_and_permissions(session: Session):
    # Define permissions
    permissions = [
        {"name": "observing", "description": "Can observe system status"},
        {"name": "security", "description": "Can manage security settings"},
        {"name": "onboarding", "description": "Can perform onboarding tasks"},
        {"name": "devops", "description": "DevOps related permissions"},
        # Add other permissions as needed
    ]

    # Create or get permissions
    permission_objs = {}
    for perm in permissions:
        existing = session.exec(select(Permission).where(Permission.name == perm["name"])).first()
        if not existing:
            p = Permission(name=perm["name"], description=perm["description"], created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
            session.add(p)
            session.commit()
            session.refresh(p)
            permission_objs[perm["name"]] = p
        else:
            permission_objs[perm["name"]] = existing

    # Define roles with permissions
    roles = [
        {
            "name": "manager",
            "description": "Manager role with observing, security, and onboarding permissions",
            "permissions": ["observing", "security", "onboarding"]
        },





        
        {
            "name": "devops engineer",
            "description": "DevOps engineer role with remaining permissions",
            "permissions": ["devops"]
        },
        {
            "name": "admin",
            "description": "Administrator role with all permissions",
            "permissions": list(permission_objs.keys())
        },
        {
            "name": "non-admin",
            "description": "Non-admin role with limited permissions",
            "permissions": []
        }
    ]

    # Create or get roles and assign permissions
    for role_data in roles:
        existing_role = session.exec(select(Role).where(Role.name == role_data["name"])).first()
        if not existing_role:
            role = Role(name=role_data["name"], description=role_data["description"], created_at=datetime.datetime.now(), updated_at=datetime.datetime.now())
            session.add(role)
            session.commit()
            session.refresh(role)
        else:
            role = existing_role

        # Assign permissions
        role.permissions = [permission_objs[perm_name] for perm_name in role_data["permissions"] if perm_name in permission_objs]
        session.add(role)
        session.commit()
