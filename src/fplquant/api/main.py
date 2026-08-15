from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fplquant.api.routers import form, market, optimizer, players, risk
from fplquant.optimizer.types import InfeasibleSquadError

app = FastAPI(
    title="FPL Quant API",
    description="Fantasy Premier League analytics and squad optimization.",
    version="0.1.0",
)

# Permissive CORS for local development against the (separately-run) frontend.
# Tighten this before any non-local deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(InfeasibleSquadError)
def infeasible_squad_handler(_request: Request, exc: InfeasibleSquadError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(players.router)
app.include_router(form.router)
app.include_router(risk.router)
app.include_router(market.router)
app.include_router(optimizer.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
