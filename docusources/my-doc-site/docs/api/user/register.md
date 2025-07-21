---
sidebar_position: 3
---

# Register API

The Register API endpoint allows new users to create an account by providing their details such as name, email, and password. Upon successful registration, the API initiates a confirmation process to verify the user's email address. This ensures that the account is associated with a valid email and helps prevent unauthorized registrations. Once the user confirms their email, the account becomes active and ready for use. This endpoint is essential for onboarding new users and securing access to the system.

**Endpoint:** `POST /register`

### Request Body

The request body must include the user's details required for account creation. The `name` field is the user's display name, `email` is the user's email address used for communication and verification, and `password` is the secret string used for authentication.

```json
{
  "name": "user",
  "email": "user@example.com",
  "password": "securepassword"
}
```

### Response

Upon successful registration, the API returns the newly created user's basic information. The `id` is the unique identifier assigned to the user, while `name` and `email` confirm the registered details.

```json
{
  "id": 1,
  "name": "user",
  "email": "user@example.com"
}
