from dagster import AssetSelection, define_asset_job

from esaj_dagster.source_crawler import assets as wo_assets

daily_wo_miner_job = define_asset_job(
    name="esaj_daily",
    selection=wo_assets,
)

# wo_treatment_job = s3file_treatment_job_factory(
#     name="job_treatment_S3_file",
#     sa_engine_resource_key=ResourcesEnum.SQLALCHEMY_ENGINE_KEY.value,
#     s3_resource_key=ResourcesEnum.CRAWLER_S3_CONNECTOR_KEY.value,
#     description="treat_S3_file",
#     source="crawler-copel",
#     treatment_function=treatment,
# )

# jobs = [
#     *park_jobs.values(),
#     *complex_jobs.values(),
#     daily_reports_job,
#     ts_control_job,
# ]

jobs = []