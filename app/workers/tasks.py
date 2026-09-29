import time
from loguru import logger
from app.workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.job import JobModel, JobStatus

@celery_app.task(bind=True, name="tasks.health_ping")
def health_ping(self):
    return {"status": "PONG", "timestamp": time.time()}

@celery_app.task(bind=True, name="tasks.orchestrate_pipeline")
def orchestrate_pipeline(self, job_id: str, file_uri: str):
    logger.info(f"Starting pipeline orchestration for Job: {job_id}")
    db = SessionLocal()
    try:
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found.")
            return

        job.status = JobStatus.INGESTING
        job.stage = "PARSING_NETCDF"
        db.commit()
        
        # Pipeline execution steps (GNN -> Diffusion) will be hooked here
        time.sleep(2)  # Mock initial stage
        
        job.status = JobStatus.COMPLETED
        job.stage = "FINISHED"
        db.commit()
        logger.info(f"Pipeline finished for Job: {job_id}")
    except Exception as exc:
        db.rollback()
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            db.commit()
        raise exc
    finally:
        db.close()