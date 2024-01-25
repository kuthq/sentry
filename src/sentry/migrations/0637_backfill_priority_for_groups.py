# Generated by Django 3.2.23 on 2024-01-23 23:32

import logging
from enum import Enum

from django.db import connection, migrations
from psycopg2.extras import execute_values

from sentry.issues.grouptype import (
    PerformanceP95EndpointRegressionGroupType,
    ProfileFunctionRegressionType,
    get_group_type_by_type_id,
)
from sentry.new_migrations.migrations import CheckedMigration
from sentry.utils import json
from sentry.utils.query import RangeQuerySetWrapper

# copied to ensure migraitons work if the enums change #


class GroupSubStatus:
    # GroupStatus.IGNORED
    UNTIL_ESCALATING = 1
    # Group is ignored/archived for a count/user count/duration
    UNTIL_CONDITION_MET = 4
    # Group is ignored/archived forever
    FOREVER = 5

    # GroupStatus.UNRESOLVED
    ESCALATING = 2
    ONGOING = 3
    REGRESSED = 6
    NEW = 7


class PriorityLevel:
    LOW = 25
    MEDIUM = 50
    HIGH = 75


class GroupCategory(Enum):
    ERROR = 1
    PERFORMANCE = 2
    PROFILE = 3  # deprecated, merging with PERFORMANCE
    CRON = 4
    REPLAY = 5
    FEEDBACK = 6


# end copy #

BATCH_SIZE = 100

UPDATE_QUERY = """
    UPDATE sentry_groupedmessage
    SET priority = new_data.priority,
    data = new_data.data::text
    FROM (VALUES %s) AS new_data(id, priority, data)
    WHERE sentry_groupedmessage.id = new_data.id AND sentry_groupedmessage.priority IS NULL
"""

logger = logging.getLogger(__name__)


def _get_priority_level(group_id, level, type_id, substatus):
    group_type = get_group_type_by_type_id(type_id)

    # Replay and Feedback issues are medium priority
    if group_type.category in [GroupCategory.REPLAY.value, GroupCategory.FEEDBACK.value]:
        return PriorityLevel.MEDIUM

    # All escalating issues are high priority for all other issue categories
    if substatus == GroupSubStatus.ESCALATING:
        return PriorityLevel.HIGH

    if group_type.category == GroupCategory.ERROR.value:
        if level in [logging.INFO, logging.DEBUG]:
            return PriorityLevel.LOW
        elif level == logging.WARNING:
            return PriorityLevel.MEDIUM
        elif level in [logging.ERROR, logging.FATAL]:
            return PriorityLevel.HIGH

        logger.warning('Unknown log level "%s" for group %s', level, group_id)
        return PriorityLevel.MEDIUM

    if group_type.category == GroupCategory.CRON.value:
        if level == logging.WARNING:
            return PriorityLevel.MEDIUM

        return PriorityLevel.HIGH

    # Profiling issues should be treated the same as Performance issues since they are merging
    if group_type.category in [GroupCategory.PERFORMANCE.value, GroupCategory.PROFILE.value]:
        # Statistical detectors are medium priority
        if type_id in [
            ProfileFunctionRegressionType.type_id,
            PerformanceP95EndpointRegressionGroupType.type_id,
        ]:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    # All other issues are the default medium priority
    return PriorityLevel.MEDIUM


def update_group_priority(apps, schema_editor):
    Group = apps.get_model("sentry", "Group")

    cursor = connection.cursor()
    batch = []

    for group_id, data, level, group_type, substatus, priority in RangeQuerySetWrapper(
        # TODO: add a group_id key in redis to pickup from if this fails
        Group.objects.all().values_list("id", "data", "level", "type", "substatus", "priority"),
        result_value_getter=lambda item: item[0],
    ):
        if priority is not None:
            continue

        priority = _get_priority_level(group_id, level, group_type, substatus)
        data.get("metadata", {})["initial_priority"] = priority
        data = json.dumps(data)
        batch.append((group_id, priority, data))

        if len(batch) >= BATCH_SIZE:
            execute_values(cursor, UPDATE_QUERY, batch, page_size=BATCH_SIZE)
            batch = []

    if batch:
        execute_values(cursor, UPDATE_QUERY, batch, page_size=BATCH_SIZE)


class Migration(CheckedMigration):
    # This flag is used to mark that a migration shouldn't be automatically run in production. For
    # the most part, this should only be used for operations where it's safe to run the migration
    # after your code has deployed. So this should not be used for most operations that alter the
    # schema of a table.
    # Here are some things that make sense to mark as dangerous:
    # - Large data migrations. Typically we want these to be run manually by ops so that they can
    #   be monitored and not block the deploy for a long period of time while they run.
    # - Adding indexes to large tables. Since this can take a long time, we'd generally prefer to
    #   have ops run this and not block the deploy. Note that while adding an index is a schema
    #   change, it's completely safe to run the operation after the code has deployed.
    is_dangerous = True

    dependencies = [
        ("sentry", "0636_monitor_incident_env_resolving_index"),
    ]

    operations = [
        migrations.RunPython(
            update_group_priority,
            reverse_code=migrations.RunPython.noop,
            hints={"tables": ["sentry_groupedmessage"]},
        ),
    ]
