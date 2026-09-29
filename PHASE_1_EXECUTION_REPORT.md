# PHASE 1 EXECUTION REPORT
## SIH 2026 — Problem Statement 26078
### NCMRWF / Ministry of Earth Sciences — Prahari Extreme Weather Pipeline
**Report Generated:** 2026-09-27 21:12 IST  
**Environment:** Development (Docker Compose on Windows + WSL2)  
**Executing Agent:** Senior Systems Architect / SRE

---

## 1. Executive Summary

Phase 1 of the **Prahari** backend infrastructure for SIH 2026 (PS-26078 — NCMRWF Extreme Weather Pipeline) has been **fully completed and verified**. The objective was to diagnose and resolve a container crash preventing `ncmrwf_api` from starting, complete all database migrations, and bring the entire service mesh to a healthy, verified state.

### Accomplishments

| # | Objective | Status |
|---|-----------|--------|
| 1 | Root-cause diagnosis of `ncmrwf_api` crash | ✅ Completed |
| 2 | Port conflict resolution (Redis `6379` collision) | ✅ Resolved |
| 3 | Full 4-container stack launch (db, redis, api, worker) | ✅ Running |
| 4 | PostGIS extension verified | ✅ Confirmed (v3.4.3) |
| 5 | Alembic migration authored and applied | ✅ Applied (`d56e6a00c0d0`) |
| 6 | Database schema with PostGIS geometries and GIST indexes | ✅ Verified |
| 7 | `/api/v1/health` returns HTTP 200 — all services UP | ✅ Confirmed |
| 8 | Celery worker online with 2 registered tasks | ✅ Verified |
| 9 | Local disk storage directories initialized | ✅ Verified |

---

## 2. Issues Identified & Remediation

### Issue 1 — Redis Host Port Collision (PRIMARY CRASH CAUSE)

**Root Cause:**  
Another Docker project (`wtf-redis`) was already bound to host port `6379`. When the Prahari `docker-compose.yml` attempted to start `ncmrwf_redis` with `"6379:6379"`, Docker's networking layer rejected it with:

```
Bind for 0.0.0.0:6379 failed: port is already allocated
```

This caused `ncmrwf_redis` to remain in `Created` state (ExitCode 128), which caused `ncmrwf_api` to never start (it declares `depends_on: redis: condition: service_healthy`).

**Resolution:**  
Changed the Redis host port mapping in `docker-compose.yml` from `"6379:6379"` to `"6380:6379"`. The container-internal port remains `6379`, so **zero changes** were required to `.env`, Celery broker URLs, or application code — all Docker-internal service communication uses the container port, not the host port.

```yaml
# Before (BROKEN):
ports:
  - "6379:6379"

# After (FIXED):
ports:
  - "6380:6379"   # host 6380 -> container 6379 (avoids conflict with wtf-redis on 6379)
```

**Port Landscape at Time of Diagnosis:**

| Host Port | Bound By | Project |
|-----------|----------|---------|
| 5432 | `sih_postgis_db` | Other SIH project |
| 5433 | `wtf-postgres` | wtf project |
| 5434 | `ncmrwf_db` ✅ | Prahari |
| 6379 | `wtf-redis` ⚠️ | wtf project (CONFLICT) |
| 8000 | `sih_fastapi_backend` | Other SIH project |
| 8001 | `ncmrwf_api` ✅ | Prahari |

---

### Issue 2 — Alembic Autogenerate Producing Empty Migration Files

**Root Cause:**  
`alembic/env.py` used `process_revision_directives=alembic_helpers.writer` (a GeoAlchemy2 `Rewriter` object). In GeoAlchemy2 v0.15.2, the `Rewriter` intercepts autogenerate output and attempts to convert standard `CreateTable` ops into `CreateGeospatialTable` ops. A bug in this pipeline caused the generated revision file to be written as 0 bytes (empty), which then caused Alembic's revision ID parser to fail with:

```
Could not determine revision id from filename ... Be sure the 'revision' variable is declared inside the script
```

**Additionally**, the PostGIS/postgis Docker image includes Tiger geocoder schemas (`tiger`, `tiger_data`, `topology`) that were being reflected during autogenerate, flooding logs with thousands of "Detected removed table" entries.

**Resolution:**
1. **Removed `process_revision_directives=alembic_helpers.writer`** from `alembic/env.py` — this was the direct cause of empty files.
2. **Added `include_schemas=False`** to prevent reflection of Tiger/topology schemas.
3. **Extended `include_object` filter** to explicitly exclude tiger/topology schema objects and unowned reflected tables.
4. **Authored the migration manually** (`d56e6a00c0d0_initial_schema.py`) with precise column definitions, ENUMs, foreign keys, and `spatial_index=True` on Geometry columns (allowing GeoAlchemy2 to auto-create GIST indexes during `create_table`).
5. **Removed duplicate explicit `op.create_index` calls** — GeoAlchemy2 auto-creates GIST spatial indexes when a `Geometry(spatial_index=True)` column is created via `create_table`, so explicit index creation was causing `DuplicateTable` errors on second run.

---

### Issue 3 — Configuration Verification (All Correct — No Changes Required)

The following checklist items from the SRE brief were **verified as already correct** and required no modification:

| Check | File | Finding |
|-------|------|---------|
| `POSTGRES_PORT=5432` (internal) | `.env` | ✅ Already correct |
| `POSTGRES_SERVER=db` | `.env` | ✅ Already correct |
| Port `8001:8000` for API | `docker-compose.yml` | ✅ Already correct |
| Port `5434:5432` for DB | `docker-compose.yml` | ✅ Already correct |
| `alembic.ini` full INI headers | `alembic.ini` | ✅ Already correct |
| `storage_service` exported from `app/services/s3.py` | `s3.py` | ✅ Already correct |
| `main.py` imports `storage_service` (not `minio_service`) | `main.py` | ✅ Already correct |
| `health.py` imports `storage_service` | `health.py` | ✅ Already correct |
| All 4 models registered in `app/db/base.py` | `base.py` | ✅ Already correct |

---

## 3. Active Architecture Inventory

### 3.1 Container Fleet

| Container | Image | Internal Port | Host Port | Status | Health |
|-----------|-------|--------------|-----------|--------|--------|
| `ncmrwf_db` | `postgis/postgis:16-3.4` | 5432 | **5434** | Running | ✅ Healthy |
| `ncmrwf_redis` | `redis:7-alpine` | 6379 | **6380** | Running | ✅ Healthy |
| `ncmrwf_api` | `prahari-api` (custom) | 8000 | **8001** | Running | ✅ Up 5 min |
| `ncmrwf_worker` | `prahari-worker` (custom) | — | — | Running | ✅ Up 5 min |

### 3.2 PostgreSQL / PostGIS Versions

```
PostgreSQL 16.4 (Debian 16.4-1.pgdg110+2) on x86_64-pc-linux-gnu
  compiled by gcc (Debian 10.2.1-6) 10.2.1 20210110, 64-bit

PostGIS 3.4.3 e365945 [EXTENSION]
  PGSQL=160 | GEOS=3.9.0-CAPI-1.16.2 | PROJ=7.2.1 | LIBXML=2.9.10
  LIBPROTOBUF=1.3.3 | WAGYU=0.5.0 (Internal) | TOPOLOGY
```

**Installed Extensions:**

| Extension | Version |
|-----------|---------|
| `postgis` | 3.4.3 |
| `postgis_topology` | 3.4.3 |
| `fuzzystrmatch` | 1.2 |

### 3.3 Storage Directory Layout

```
/workspace/storage/              (mounted from D:\projects\Prahari\storage)
├── raw-forecasts/               ← NetCDF / GRIB2 ingestion target
└── highres-grids/               ← Processed high-resolution grid output
```

Initialized by `StorageService.initialize_storage()` during FastAPI lifespan startup.

---

## 4. Database Schema State

**Migration Applied:** `d56e6a00c0d0` — *Initial schema*  
**Alembic Version Stamp:** `d56e6a00c0d0`

### 4.1 Table Definitions

#### `jobs` — Ingestion Job Registry

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| `id` | `VARCHAR` | NOT NULL | PRIMARY KEY |
| `status` | `ENUM(jobstatus)` | NOT NULL | `PENDING\|INGESTING\|GNN_PROCESSING\|DIFFUSION_PROCESSING\|COMPLETED\|FAILED` |
| `stage` | `VARCHAR(64)` | NULL | — |
| `error_message` | `TEXT` | NULL | — |
| `created_at` | `TIMESTAMP` | NOT NULL | — |
| `updated_at` | `TIMESTAMP` | NOT NULL | — |

*Referenced by: `anomalies.job_id → jobs.id`*

#### `forecast_runs` — NCUM / NEPS Model Run Catalog

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| `id` | `VARCHAR` | NOT NULL | PRIMARY KEY |
| `model_name` | `VARCHAR(32)` | NOT NULL | e.g. `NCUM_12KM`, `NEPS_G` |
| `run_date` | `TIMESTAMP` | NOT NULL | — |
| `forecast_horizon_hours` | `FLOAT8` | NOT NULL | e.g. `240.0` (10 days) |
| `storage_path` | `VARCHAR(512)` | NOT NULL | Local disk path |
| `created_at` | `TIMESTAMP` | NOT NULL | — |

#### `anomalies` — Detected Extreme Weather Events (Spatial)

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| `id` | `VARCHAR` | NOT NULL | PRIMARY KEY |
| `job_id` | `VARCHAR` | NOT NULL | FK → `jobs.id` |
| `anomaly_type` | `VARCHAR(32)` | NOT NULL | `CYCLONE\|HEAT_DOME\|COLD_WAVE` |
| `valid_time` | `TIMESTAMP` | NOT NULL | — |
| `efi_score` | `FLOAT8` | NOT NULL | Extreme Forecast Index (0.0–1.0) |
| `bbox_geom` | **`GEOMETRY(POLYGON, 4326)`** | NOT NULL | 4D envelope (lat/lon WGS84) |
| `created_at` | `TIMESTAMP` | NOT NULL | — |

**Spatial Index:** `idx_anomalies_bbox_geom` USING **GIST** (`bbox_geom`)  
*Referenced by: `alerts.anomaly_id → anomalies.id`*

#### `alerts` — Localized Impact Zone Alerts (Spatial)

| Column | Type | Nullable | Constraints |
|--------|------|----------|-------------|
| `id` | `VARCHAR` | NOT NULL | PRIMARY KEY |
| `anomaly_id` | `VARCHAR` | NULL | FK → `anomalies.id` |
| `severity` | `ENUM(alertseverity)` | NOT NULL | `LOW\|MODERATE\|SEVERE` |
| `peak_metric_value` | `FLOAT8` | NOT NULL | e.g. max wind speed, max rainfall |
| `metric_unit` | `VARCHAR(16)` | NOT NULL | `km/h`, `C`, `mm` |
| `center_point` | **`GEOMETRY(POINT, 4326)`** | NOT NULL | Precise impact centroid |
| `impact_zone_5km` | **`GEOMETRY(POLYGON, 4326)`** | NOT NULL | 5 km radius impact polygon |
| `created_at` | `TIMESTAMP` | NOT NULL | — |

**Spatial Indexes:**  
- `idx_alerts_center_point` USING **GIST** (`center_point`)  
- `idx_alerts_impact_zone_5km` USING **GIST** (`impact_zone_5km`)

### 4.2 Spatial Index Verification

```
         indexname          |   tablename   | method
----------------------------+---------------+-------
alerts_pkey                 | alerts        | btree
idx_alerts_center_point     | alerts        | gist  ✅
idx_alerts_impact_zone_5km  | alerts        | gist  ✅
anomalies_pkey              | anomalies     | btree
idx_anomalies_bbox_geom     | anomalies     | gist  ✅
forecast_runs_pkey          | forecast_runs | btree
jobs_pkey                   | jobs          | btree
```

---

## 5. Verified Verification Artifacts

### 5.1 Health API Response

**Endpoint:** `GET http://localhost:8001/api/v1/health`  
**HTTP Status:** `200 OK`

```json
{
    "status": "HEALTHY",
    "services": {
        "postgres_postgis": "UP (PostGIS 3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1)",
        "redis": "UP",
        "storage": "UP (Local Disk)"
    }
}
```

### 5.2 Celery Worker — Registered Tasks

**Worker Node:** `celery@48a7922c91cd` (1 node online)

```
-> celery@48a7922c91cd: OK
    * tasks.health_ping
    * tasks.orchestrate_pipeline
```

| Task Name | Description | Phase |
|-----------|-------------|-------|
| `tasks.health_ping` | Broker connectivity liveness probe | Phase 1 |
| `tasks.orchestrate_pipeline` | Full ML pipeline orchestrator (GNN → Diffusion) | Phase 2 hook |

### 5.3 OpenAPI / Swagger URL

- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc  
- **OpenAPI JSON:** http://localhost:8001/api/v1/openapi.json

---

## 6. Files Modified / Authored in This Session

| File | Action | Reason |
|------|--------|--------|
| [`docker-compose.yml`](file:///d:/projects/Prahari/docker-compose.yml) | Modified | Changed Redis host port `6379→6380` to resolve port collision |
| [`alembic/env.py`](file:///d:/projects/Prahari/alembic/env.py) | Rewritten | Removed `alembic_helpers.writer` (caused empty files), added Tiger schema exclusion, added `include_schemas=False` |
| [`alembic/versions/d56e6a00c0d0_initial_schema.py`](file:///d:/projects/Prahari/alembic/versions/d56e6a00c0d0_initial_schema.py) | Created | Hand-authored initial schema migration (bypassing broken autogenerate path) |

---

## 7. Phase 2 Readiness Checklist

All of the following prerequisites are confirmed **ready** for Phase 2 (NetCDF/GRIB2 ingestion and ML worker pipeline):

| Prerequisite | Status | Notes |
|---|---|---|
| PostGIS 3.4.3 operational with GIST spatial indexes | ✅ Ready | WGS84 (SRID 4326) confirmed |
| `jobs` table available for pipeline state tracking | ✅ Ready | `PENDING→INGESTING→GNN→DIFFUSION→COMPLETED` FSM |
| `forecast_runs` table for NCUM/NEPS catalog | ✅ Ready | Stores model name, run date, horizon, storage path |
| `anomalies` table with POLYGON geometry | ✅ Ready | Indexed on `bbox_geom` via GIST |
| `alerts` table with POINT + POLYGON geometries | ✅ Ready | Indexed on both geometry columns |
| Redis broker (Celery) healthy and task-ready | ✅ Ready | `tasks.orchestrate_pipeline` registered |
| Local disk storage `/workspace/storage/` mounted | ✅ Ready | `raw-forecasts/` and `highres-grids/` initialized |
| FastAPI uvicorn reload mode active | ✅ Ready | Hot-reload on code change via volume mount |
| `netCDF4`, `xarray`, `rasterio` installed in containers | ✅ Ready | Confirmed in `requirements.txt` + built images |
| `numpy`, `shapely` for ML pre/post-processing | ✅ Ready | Installed in both `api` and `worker` images |
| `GeoAlchemy2` for spatial ORM operations | ✅ Ready | v0.15.2 with GIST index support |

### Phase 2 Next Steps

1. **Data Ingestion Layer:** Implement `app/services/ingestion.py` — parse NCUM 12km and NEPS_G NetCDF/GRIB2 files from `/workspace/storage/raw-forecasts/`, populate `forecast_runs` table.
2. **GNN Worker Task:** Hook `tasks.orchestrate_pipeline` → GNN model inference for anomaly detection; write results to `anomalies` table with spatial bounding polygons.
3. **Diffusion Downscaling Worker:** Chain GNN output → diffusion model → populate `highres-grids/` storage and link back to `forecast_runs`.
4. **Alert Generation:** From `anomalies` detections → create `alerts` records with precise `center_point` and `impact_zone_5km` polygons using Shapely buffering (EPSG:4326 or reproject to UTM for accurate 5km radius).
5. **REST Endpoints:** Add CRUD endpoints for `jobs`, `forecast_runs`, `anomalies`, `alerts` in `app/api/v1/endpoints/`.

---

## 8. Appendix — Key Commands Reference

```bash
# Stack management
docker compose up -d --build       # Rebuild and start all containers
docker compose down                 # Stop all containers (preserves postgres_data volume)
docker compose down -v              # Stop and DESTROY all volumes (fresh DB)
docker compose ps                   # Container status overview
docker compose logs api --tail 50   # API container logs

# Database operations
docker compose exec db psql -U postgres -d weather_db   # psql shell
docker compose exec api alembic upgrade head            # Apply migrations
docker compose exec api alembic current                 # Current migration version
docker compose exec api alembic history                 # Migration history

# Worker operations
docker compose exec worker celery -A app.workers.celery_app inspect registered
docker compose exec worker celery -A app.workers.celery_app inspect active

# Health verification
curl -s http://localhost:8001/api/v1/health | python -m json.tool
```

---

*Report end — Phase 1 complete. System ready for Phase 2 ML pipeline integration.*
