"""Initial schema

Revision ID: d56e6a00c0d0
Revises: 
Create Date: 2026-09-27 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = 'd56e6a00c0d0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- jobs table ---
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'PENDING', 'INGESTING', 'GNN_PROCESSING',
                'DIFFUSION_PROCESSING', 'COMPLETED', 'FAILED',
                name='jobstatus'
            ),
            nullable=False,
        ),
        sa.Column('stage', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- forecast_runs table ---
    op.create_table(
        'forecast_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(length=32), nullable=False),
        sa.Column('run_date', sa.DateTime(), nullable=False),
        sa.Column('forecast_horizon_hours', sa.Float(), nullable=False),
        sa.Column('storage_path', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- anomalies table ---
    # NOTE: GeoAlchemy2 auto-creates GIST index on Geometry columns during
    # create_table; we do NOT manually create them to avoid DuplicateTable errors.
    op.create_table(
        'anomalies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('anomaly_type', sa.String(length=32), nullable=False),
        sa.Column('valid_time', sa.DateTime(), nullable=False),
        sa.Column('efi_score', sa.Float(), nullable=False),
        sa.Column(
            'bbox_geom',
            Geometry(
                geometry_type='POLYGON',
                srid=4326,
                spatial_index=True,  # GeoAlchemy2 handles GIST index creation
            ),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- alerts table ---
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('anomaly_id', sa.String(), nullable=True),
        sa.Column(
            'severity',
            sa.Enum('LOW', 'MODERATE', 'SEVERE', name='alertseverity'),
            nullable=False,
        ),
        sa.Column('peak_metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(length=16), nullable=False),
        sa.Column(
            'center_point',
            Geometry(
                geometry_type='POINT',
                srid=4326,
                spatial_index=True,
            ),
            nullable=False,
        ),
        sa.Column(
            'impact_zone_5km',
            Geometry(
                geometry_type='POLYGON',
                srid=4326,
                spatial_index=True,
            ),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['anomaly_id'], ['anomalies.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('anomalies')
    op.drop_table('forecast_runs')
    op.drop_table('jobs')

    # Drop custom ENUM types
    sa.Enum(name='alertseverity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='jobstatus').drop(op.get_bind(), checkfirst=True)
