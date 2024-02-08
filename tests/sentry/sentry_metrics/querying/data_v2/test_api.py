from datetime import datetime, timedelta

import pytest
from django.utils import timezone as django_timezone

from sentry.sentry_metrics.querying.data_v2 import run_metrics_queries_plan
from sentry.sentry_metrics.querying.data_v2.api import MetricsQueriesPlan
from sentry.sentry_metrics.use_case_id_registry import UseCaseID
from sentry.snuba.metrics.naming_layer import TransactionMRI
from sentry.testutils.cases import BaseMetricsTestCase, TestCase
from sentry.testutils.helpers.datetime import freeze_time

pytestmark = pytest.mark.sentry_metrics

MOCK_DATETIME = (django_timezone.now() - timedelta(days=1)).replace(
    hour=10, minute=0, second=0, microsecond=0
)


@freeze_time(MOCK_DATETIME)
class MetricsAPITestCase(TestCase, BaseMetricsTestCase):
    def setUp(self):
        super().setUp()

        release_1 = self.create_release(
            project=self.project, version="1.0", date_added=MOCK_DATETIME
        )
        release_2 = self.create_release(
            project=self.project, version="2.0", date_added=MOCK_DATETIME + timedelta(minutes=5)
        )

        for value, transaction, platform, env, release, time in (
            (1, "/hello", "android", "prod", release_1.version, self.now()),
            (6, "/hello", "ios", "dev", release_2.version, self.now()),
            (5, "/world", "windows", "prod", release_1.version, self.now() + timedelta(minutes=30)),
            (3, "/hello", "ios", "dev", release_2.version, self.now() + timedelta(hours=1)),
            (2, "/hello", "android", "dev", release_1.version, self.now() + timedelta(hours=1)),
            (
                4,
                "/world",
                "windows",
                "prod",
                release_2.version,
                self.now() + timedelta(hours=1, minutes=30),
            ),
        ):
            self.store_metric(
                self.project.organization.id,
                self.project.id,
                "distribution",
                TransactionMRI.DURATION.value,
                {
                    "transaction": transaction,
                    "platform": platform,
                    "environment": env,
                    "release": release,
                },
                self.ts(time),
                value,
                UseCaseID.TRANSACTIONS,
            )

        self.prod_env = self.create_environment(name="prod", project=self.project)
        self.dev_env = self.create_environment(name="dev", project=self.project)

    def now(self):
        return MOCK_DATETIME

    def ts(self, dt: datetime) -> int:
        return int(dt.timestamp())

    def mql(self, aggregate: str, metric_mri: str, filters: str = "", group_by: str = "") -> str:
        query = aggregate + f"({metric_mri})"
        if filters:
            query += "{" + filters + "}"
        if group_by:
            query += " by" + f"({group_by})"

        return query

    def test_query_with_empty_results(self) -> None:
        for aggregate, expected_identity in (
            ("count", 0.0),
            ("avg", None),
            ("sum", 0.0),
            ("min", 0.0),
        ):
            query_1 = self.mql(aggregate, TransactionMRI.DURATION.value, "transaction:/bar")
            plan = MetricsQueriesPlan().declare_query("query_1", query_1).apply_formula("$query_1")
            results = run_metrics_queries_plan(
                metrics_queries_plan=plan,
                start=self.now() - timedelta(minutes=30),
                end=self.now() + timedelta(hours=1, minutes=30),
                interval=3600,
                organization=self.project.organization,
                projects=[self.project],
                environments=[],
                referrer="metrics.data.api",
            )
            data = results["data"]
            assert len(data) == 1
            assert data[0][0]["by"] == {}
            assert data[0][0]["series"] == [expected_identity, expected_identity, expected_identity]
            assert data[0][0]["totals"] == expected_identity

    def test_query_with_one_aggregation(self) -> None:
        query_1 = self.mql("sum", TransactionMRI.DURATION.value)
        plan = MetricsQueriesPlan().declare_query("query_1", query_1).apply_formula("$query_1")

        results = run_metrics_queries_plan(
            metrics_queries_plan=plan,
            start=self.now() - timedelta(minutes=30),
            end=self.now() + timedelta(hours=1, minutes=30),
            interval=3600,
            organization=self.project.organization,
            projects=[self.project],
            environments=[],
            referrer="metrics.data.api",
        )
        data = results["data"]
        assert len(data) == 1
        assert data[0][0]["by"] == {}
        assert data[0][0]["series"] == [0.0, 12.0, 9.0]
        assert data[0][0]["totals"] == 21.0
