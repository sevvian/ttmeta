import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.db import init_db
from app.logging_conf import setup_logging
from app.parser_llm import LLMParser
from app.routes import api_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Application state
app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events.
    """
    logger.info("Application startup...")
    # Initialize Database
    await init_db()
    logger.info("Database initialized.")

    # Load LLM model
    if settings.LLM_ENABLED:
        try:
            llm_parser = LLMParser(model_path=settings.LLM_MODEL_PATH)
            app_state["llm_parser"] = llm_parser
            app_state["model_loaded"] = True
            logger.info(f"Successfully loaded model from {settings.LLM_MODEL_PATH}")
        except Exception as e:
            app_state["llm_parser"] = None
            app_state["model_loaded"] = False
            logger.error(f"Failed to load LLM model: {e}", exc_info=True)
    else:
        app_state["llm_parser"] = None
        app_state["model_loaded"] = False
        logger.warning("LLM is disabled by configuration.")
        
    yield
    
    # Shutdown
    logger.info("Application shutdown.")
    app_state.clear()


app = FastAPI(
    title="Torrent Title Parser API",
    description="A hybrid Regex + LLM API to parse torrent titles into structured JSON.",
    version="1.0.0",
    lifespan=lifespan,
)

# Attach application state
app.state.app_state = app_state

# CORS Middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Include API router
app.include_router(api_router)

@app.get("/", include_in_schema=False)
async def read_root(request: Request):
    """Serve the minimal frontend."""
    return templates.TemplateResponse("index.html", {"request": request})
