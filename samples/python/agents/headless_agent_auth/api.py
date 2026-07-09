import os

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi_plugin import Auth0FastAPI


auth0 = Auth0FastAPI(
    domain=os.getenv('HR_AUTH0_DOMAIN'),
    audience=os.getenv('HR_API_AUTH0_AUDIENCE'),
)

app = FastAPI()


@app.get('/employees/{employee_id}')
def get_employee(
    employee_id: str,
    _claims: Annotated[
        dict, Depends(auth0.require_auth(scopes='read:employee'))
    ],
) -> dict:
    """Get employee details by ID."""
    # Note: if needed, return more employee details here
    return {'employee_id': employee_id}


hr_api = app
