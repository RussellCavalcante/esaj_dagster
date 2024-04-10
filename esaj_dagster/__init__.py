import warnings

from dagster import Definitions, ExperimentalWarning, in_process_executor

warnings.filterwarnings("ignore", category=ExperimentalWarning)

from esaj_dagster.assets import assets
from esaj_dagster.jobs import jobs
# from esaj_dagster.resources import resource_defs
from esaj_dagster.schedulers import schedulers

defs = Definitions(
    executor=in_process_executor,
    assets=assets,
    # resources=resource_defs,
    jobs=[*jobs],
    schedules=[*schedulers],
)