from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database import engine, Base
from .routers import auth_router, students, faculty, evaluations, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI Learning Companion API",
    description="University-grade intelligent answer sheet evaluation platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(faculty.router, prefix="/faculty", tags=["Faculty"])
app.include_router(evaluations.router, prefix="/evaluations", tags=["Evaluations"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}
