---
sidebar_position: 2
---

# Login API

The Login API endpoint allows existing users to authenticate themselves by providing their credentials. Upon successful authentication, the API generates and returns a JSON Web Token (JWT) access token along with a refresh token. These tokens are used to authorize subsequent requests to protected resources without requiring the user to re-enter their credentials repeatedly. The access token has a limited lifespan, after which the refresh token can be used to obtain a new access token, ensuring continuous and secure access. This endpoint supports multi-session management by uniquely identifying each login session with a session ID.

**Endpoint:** `POST /login`

### Request Body

The request body must include the user's credentials to authenticate. The `username` field represents the user's login identifier (usually their email or username), and the `password` field is the user's secret password.

```json
{
  "username": "user@example.com",
  "password": "yourpassword"
}
```

### Response

On successful authentication, the API returns an access token and a refresh token. The `access_token` is a JWT used for authorizing subsequent requests. The `refresh_token` is used to obtain new access tokens without re-authenticating. The `token_type` indicates the token scheme (usually "bearer"). The `expires_at` field shows the expiration time of the access token. The `session_id` uniquely identifies the login session.

```json
{
  "access_token": "<jwt-token>",
  "refresh_token": "<refresh-token>",
  "token_type": "bearer",
  "expires_at": "2024-06-01T12:00:00Z",
  "session_id": "uuid-session-id"
}
```

### Use Case

Used during login to authenticate users and start a session.
