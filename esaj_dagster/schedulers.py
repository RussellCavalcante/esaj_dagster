from itertools import chain
from typing import Any

from dagster import (
    ScheduleDefinition,
)

from esaj_dagster.jobs import (
    daily_wo_miner_job,
)


def create_scheduler_name(job_name: str) -> str:
    """
    Create a scheduler name based on the given job name.

    Parameters
    ----------
    job_name : str
        The name of the job.

    Returns
    -------
    str
        The scheduler name.
    """

    remove_trace = " ".join(job_name.replace("-", " ").split())
    return remove_trace.replace("Job", "Schedule").replace(" ", "_")


TIMEZONE = "America/Fortaleza"

work_order_schedulers = []

work_order_schedulers.append(
    ScheduleDefinition(
        job=daily_wo_miner_job,
        name=create_scheduler_name("job_crawler_schedule"),
        execution_timezone=TIMEZONE,
        cron_schedule="0 9 * * *",
    )
)




schedulers = [
    *work_order_schedulers,
]
