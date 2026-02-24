from fastapi import Depends
from deps.auth import require_role

AdminOnly = Depends(require_role("admin"))