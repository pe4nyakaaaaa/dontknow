import pathlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from webapp.database import engine
from webapp.models import Base, Case, CaseSkin, Skin
from webapp.routes.auth import router as auth_router
from webapp.routes.cases import router as cases_router
from webapp.routes.payments import router as payments_router
from webapp.routes.profile import router as profile_router
from webapp.routes.support import router as support_router

BASE_DIR = pathlib.Path(__file__).resolve().parent

RARITY_WEIGHTS = {
    "consumer": 40.0,
    "industrial": 30.0,
    "mil_spec": 20.0,
    "restricted": 7.0,
    "classified": 2.5,
    "covert": 0.45,
    "extraordinary": 0.05,
}

app = FastAPI(title="SHADOWDROP — Case Battle", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(profile_router)
app.include_router(payments_router)
app.include_router(support_router)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


async def _seed_data():
    from webapp.data.cases import CASES
    from webapp.data.skins import SKINS
    from webapp.database import async_session

    async with async_session() as session:
        existing = await session.execute(select(Skin).limit(1))
        if existing.scalar_one_or_none():
            return

        skin_map: dict[str, int] = {}
        for s in SKINS:
            skin = Skin(
                name=s["name"],
                weapon=s["weapon"],
                rarity=s["rarity"],
                price=s["price"],
                color=s["color"],
            )
            session.add(skin)
            await session.flush()
            skin_map[s["name"]] = skin.id

        for c in CASES:
            case = Case(
                name=c["name"],
                price=c["price"],
                description=c["description"],
                category=c["category"],
            )
            session.add(case)
            await session.flush()

            for skin_name in c["skins"]:
                if skin_name not in skin_map:
                    continue
                skin_id = skin_map[skin_name]
                skin_result = await session.execute(select(Skin).where(Skin.id == skin_id))
                skin_obj = skin_result.scalar_one_or_none()
                if not skin_obj:
                    continue
                weight = RARITY_WEIGHTS.get(skin_obj.rarity, 1.0)
                cs = CaseSkin(case_id=case.id, skin_id=skin_id, drop_weight=weight)
                session.add(cs)

        await session.commit()


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_data()


@app.get("/")
async def index():
    return FileResponse(str(BASE_DIR / "templates" / "index.html"))


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={}, status_code=204)
