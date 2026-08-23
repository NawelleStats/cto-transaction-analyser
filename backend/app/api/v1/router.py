from fastapi import APIRouter
from app.api.v1.endpoints import transactions

api_router = APIRouter()

# Inclusion des routes pour les opérations boursières
api_router.include_router(
    transactions.router, 
    # prefix="/transactions", 
    tags=["transactions"]
)

