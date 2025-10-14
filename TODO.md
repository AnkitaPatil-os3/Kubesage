# TODO: Modify /generate-agent-id API to make cluster_id optional

## Steps to Complete
- [x] Update `backend/onboarding_service/app/models.py`: Make `cluster_id` nullable in the `Agent` model.
- [x] Update `backend/onboarding_service/app/schemas.py`: Make `cluster_id` optional in `GenerateAgentIdResponse`.
- [x] Update `backend/onboarding_service/app/routes.py`: Make `cluster_id` parameter optional, adjust logic to handle when cluster_id is None.
- [ ] Test the API endpoint to ensure it works with and without providing cluster_id.
- [x] Update docstring in the route if necessary.
