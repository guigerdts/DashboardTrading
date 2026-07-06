# Design: Base Architecture — Trade Intelligence Platform (TIP)

## Technical Approach

Monorepo con `backend/` (FastAPI app factory + 10 módulos skeleton con registro pluggable + SQLite async configurado sin modelos) y `frontend/` (React + Vite + Tailwind, JS sin TypeScript). Dev workflow unificado via Makefile. Sin lógica de negocio — solo scaffolding (C2).

## Architecture Decisions

| Decisión | Opciones | Tradeoff | Decisión |
|----------|----------|----------|----------|
| App factory | `create_app()` vs app global | Testabilidad vs simplicidad | `create_app()` — testable, DI-friendly |
| Módulos como paquetes | `app/modules/{name}` vs `app/api/v1/{name}` | Aislamiento vs flat routing | `app/modules/{name}` — cada módulo autocontenido (C1) |
| Registro pluggable | Auto-discovery vs manual includes | Conveniencia vs explicitud | Auto-discovery via `modules/__init__.py` (C6) |
| Config | Pydantic Settings v2 vs env raw | Validación vs simplicidad | Pydantic Settings v2 — tipado, defaults, `.env` |
| Router discovery | `importlib` scan vs hardcoded list | Dinámico vs explícito | `importlib.import_module` — cero modificación al agregar módulo |
| DB engine | Lifespan (lazy) vs eager | Startup time vs fail-fast | Lifespan — conexión al arrancar, cierre limpio |
| Frontend lenguaje | JSX vs TSX | Velocidad inicial vs type safety | JSX — spec mandate, TS se añade después |

## Estructura completa del monorepo

```
DashboardTrading/
├── Makefile                  # install, dev, lint, format, test, db-migrate, db-init, db-upgrade
├── README.md
├── .gitignore
├── backend/
│   ├── pyproject.toml        # fastapi, uvicorn, sqlalchemy, aiosqlite, alembic, pytest, httpx, ruff
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/         # Vacío — sin migraciones (C2)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # create_app(), lifespan, CORS
│   │   ├── config.py         # Settings(BaseSettings)
│   │   ├── database.py       # async_engine + session factory (WAL)
│   │   ├── dependencies.py   # get_db() placeholder
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── health.py     # GET /api/health → {"status":"ok"}
│   │   └── modules/
│   │       ├── __init__.py   # discover_modules()
│   │       ├── dashboard/           {__init__.py, router.py, README.md}
│   │       ├── trading_journal/     {__init__.py, router.py, README.md}
│   │       ├── analytics/           {__init__.py, router.py, README.md}
│   │       ├── risk_management/     {__init__.py, router.py, README.md}
│   │       ├── psychology/          {__init__.py, router.py, README.md}
│   │       ├── strategies/          {__init__.py, router.py, README.md}
│   │       ├── setups/              {__init__.py, router.py, README.md}
│   │       ├── screenshot_library/  {__init__.py, router.py, README.md}
│   │       ├── error_management/    {__init__.py, router.py, README.md}
│   │       └── settings/            {__init__.py, router.py, README.md}
│   └── tests/
│       ├── __init__.py
│       └── test_health.py    # httpx → GET /api/health
└── frontend/
    ├── package.json           # react, react-dom, react-router-dom, tailwindcss, vite
    ├── vite.config.js         # proxy: /api → localhost:8000
    ├── index.html
    ├── postcss.config.js
    ├── tailwind.config.js
    ├── src/
    │   ├── main.jsx           # ReactDOM.createRoot
    │   ├── App.jsx            # React Router <Routes>
    │   ├── index.css          # @tailwind directives
    │   ├── api/
    │   │   └── client.js      # fetch wrapper (URL vacía — via proxy)
    │   ├── lib/
    │   │   └── utils.js       # cn() helper
    │   ├── components/
    │   │   └── ui/            # futuros shadcn/ui
    │   └── pages/
    │       ├── Home.jsx       # Landing con navegación a 10 módulos
    │       └── ModuleTemplate.jsx  # Placeholder genérico para rutas módulo
```

## Flujo de comunicación React ⇄ FastAPI

```
Navegador ──→ Vite Dev Server (:5173)
                ├── /api/*    → proxy → FastAPI/Uvicorn (:8000)
                │                                     GET /api/health → 200
                └── /*        → React Router SPA
```

**Dev**: Vite `server.proxy` reescribe `/api/*`. Sin headers CORS.  
**Prod**: FastAPI sirve `frontend/dist/` como static files del mismo origen, o CORS middleware si hay separación.

## Organización interna de cada módulo (backend)

```
app/modules/dashboard/
├── __init__.py    # from .router import router
├── router.py      # APIRouter(prefix="/dashboard", tags=["Dashboard"])
│                  #   @router.get("/") → raise NotImplementedError (stub)
│                  #   @router.post("/") → raise NotImplementedError (stub)
└── README.md      # Propósito, alcance, planes futuros
```

Cada `router.py` importa de `app.core` (FastAPI, Depends) únicamente. Sin imports entre módulos.

## Frontend — routing

```jsx
// App.jsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/dashboard" element={<ModuleTemplate name="Dashboard" />} />
    <Route path="/trading-journal" element={<ModuleTemplate name="Trading Journal" />} />
    {/* ... 8 más ... */}
  </Routes>
</BrowserRouter>
```

`ModuleTemplate.jsx` renderiza título + placeholder. Sin lógica de negocio (C3).

## Gestión de configuración

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Trade Intelligence Platform"
    debug: bool = False
    db_path: str = "data/tip.db"           # SQLite
    db_echo: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_prefix": "TIP_"}
```

## Dependencias entre capas

```
app.core (config, database, dependencies) ← sin deps externas
    ↑
app.api (health)                          ← solo core
    ↑
app.modules.*                              ← solo core (C1)
```

**Regla fundamental**: `app.core` es compartido. Los módulos son islas — `trading_journal` nunca importa `analytics`. La comunicación entre módulos será vía servicios definidos en `app.core` en fases posteriores.

## Diagrama de alto nivel

```
┌─────────────────────────────────────────────────────┐
│                    Makefile                          │
│  install │ dev │ lint │ format │ test │ db-migrate   │
└────┬────────────────────┬───────────────────────────┘
     │                    │
┌────▼────────┐    ┌─────▼──────────┐
│  backend/   │    │  frontend/     │
│  FastAPI    │    │  React + Vite  │
│  :8000      │◄───│  :5173         │
│             │    │  proxy /api/*  │
│  modules/   │    │  pages/        │
│  discover() │    │  Home.jsx      │
│  pluggable  │    │  Module*.jsx   │
└─────────────┘    └────────────────┘
```

## Estrategia de escalabilidad (C6)

El patrón `discover_modules()` en `app/modules/__init__.py` escanea el directorio y registra automáticamente todo subdirectorio con `router.py`:

```python
def discover_modules() -> list[APIRouter]:
    modules_dir = Path(__file__).parent
    routers = []
    for entry in sorted(modules_dir.iterdir()):
        if entry.is_dir() and (entry / "router.py").exists():
            mod = importlib.import_module(f"app.modules.{entry.name}.router")
            routers.append(mod.router)
    return routers
```

Agregar módulo → crear carpeta con `router.py`. Cero cambios en `main.py` o archivos existentes.

## Estrategia para futuras integraciones de IA

Los módulos `analytics` y `strategies` están nombrados para alojar lógica de inferencia. En fases posteriores, un directorio `app/ml/` contendrá pipelines de features, modelos serializados, y predictores. Los módulos consumirán ML via interfaces definidas en `app/core/ml.py` — no import directa a modelos. Sin over-engineering: `app/ml/` se crea cuando exista el primer modelo.

## Estrategia Database First (C2)

Tres fases progresivas:

| Fase | Contenido | Cuándo |
|------|-----------|--------|
| 1 (ahora) | `database.py` con engine + session factory async. WAL mode. Sin modelos. | Este cambio |
| 2 | Diseño entidad-relación completo, script DDL, decisión de naming de tablas | Próximo spec+design |
| 3 | Modelos SQLAlchemy con `Mapped`/`mapped_column`, migraciones Alembic, repositorios | Implementación |

El `database.py` expone `get_async_session()` para inyección futura sin cambiar la firma.

---

**Status**: success
**Summary**: Design created for base architecture scaffolding. Monorepo structure defined (backend/ + frontend/), 10 modules with pluggable registration, SQLite async configured without models, Vite proxy for dev, Makefile dev workflow. All specs C1-C6 respected.
**Artifacts**: `openspec/changes/crear-la-arquitectura-base-trade-intelligence-platform/design.md`
**Next**: sdd-tasks
**Risks**: None — scaffolding only, no existing code to conflict
**Skill Resolution**: paths-injected — 1 skill (sdd-design)
