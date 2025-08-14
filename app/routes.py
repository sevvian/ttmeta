import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db, add_submission, get_recent_submissions
from app.parser_regex import parse_with_regex
from app.schemas import ParseRequest, ParseBatchRequest, ParsedResult

logger = logging.getLogger(__name__)

api_router = APIRouter()

# --- Dependencies ---
async def get_api_key(x_api_key: str = Header(None)):
    if settings.API_KEY:
        if x_api_key != settings.API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

async def get_llm_parser(request: Request):
    return request.app.state.app_state.get("llm_parser")

# --- Health and Readiness ---
@api_router.get("/healthz", status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    return {"status": "ok"}

@api_router.get("/readyz", status_code=status.HTTP_200_OK, tags=["Health"])
async def readiness_check(request: Request):
    model_loaded = request.app.state.app_state.get("model_loaded", False)
    if not model_loaded and settings.LLM_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not loaded or not ready.",
        )
    return {"status": "ready", "model_loaded": model_loaded}

# --- Core Parsing Logic ---
async def process_single_title(title: str, llm_parser, db: AsyncSession, request: Request, background_tasks: BackgroundTasks) -> ParsedResult:
    # Stage 1: Regex parsing
    regex_results, remaining_text = parse_with_regex(title)
    
    # Stage 2: LLM refinement (if enabled and loaded)
    if llm_parser:
        final_result = llm_parser.refine_with_llm(regex_results, remaining_text, title)
    else:
        # Fallback if LLM is disabled or failed to load
        final_result = ParsedResult(**regex_results, raw=title, title=remaining_text.strip())
        if not settings.LLM_ENABLED:
            final_result.notes = "LLM is disabled. Title is based on regex leftovers."
        else:
            final_result.notes = "LLM failed to load. Title is based on regex leftovers."

    # Log request and response
    log_data = {
        "request": {"title": title, "client_ip": request.client.host},
        "response": final_result.model_dump(),
    }
    logger.info("Parsing complete", extra=log_data)
    
    # Persist to DB in the background
    background_tasks.add_task(
        add_submission, 
        db, 
        raw_title=title, 
        parsed_result=final_result,
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    return final_result

# --- API Endpoints ---
@api_router.post("/v1/parse", response_model=ParsedResult, tags=["Parsing"], dependencies=[Depends(get_api_key)])
async def parse_title(
    payload: ParseRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    llm_parser = Depends(get_llm_parser),
    db: AsyncSession = Depends(get_db)
):
    return await process_single_title(payload.title, llm_parser, db, request, background_tasks)


@api_router.post("/v1/parse_batch", response_model=List[ParsedResult], tags=["Parsing"], dependencies=[Depends(get_api_key)])
async def parse_title_batch(
    payload: ParseBatchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    llm_parser = Depends(get_llm_parser),
    db: AsyncSession = Depends(get_db)
):
    results = []
    for title in payload.titles:
        result = await process_single_title(title, llm_parser, db, request, background_tasks)
        results.append(result)
    return results

@api_router.get("/v1/recent", response_model=List[ParsedResult], tags=["Submissions"])
async def get_recent(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Get recent submissions. This endpoint is not protected by default.
    To protect it, add `dependencies=[Depends(get_api_key)]` like other endpoints.
    """
    if limit > 200:
        limit = 200 # Safety cap
    submissions = await get_recent_submissions(db, limit)
    return [sub.parsed_json for sub in submissions]
