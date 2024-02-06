from __future__ import annotations

from time import time
from unittest import mock
from unittest.mock import MagicMock

from sentry import tsdb
from sentry.grouping.result import CalculatedHashes
from sentry.models.group import Group
from sentry.testutils.cases import TestCase
from sentry.testutils.helpers.datetime import freeze_time
from sentry.testutils.helpers.eventprocessing import save_new_event
from sentry.testutils.silo import region_silo_test
from sentry.testutils.skips import requires_snuba
from sentry.tsdb.base import TSDBModel

pytestmark = [requires_snuba]


def get_relevant_metrics_calls(mock_fn: MagicMock, key: str) -> list[mock._Call]:
    return [call for call in mock_fn.call_args_list if call.args[0] == key]


@region_silo_test
class EventManagerGroupingTest(TestCase):
    def test_puts_events_with_matching_fingerprints_in_same_group(self):
        event = save_new_event(
            {"message": "Dogs are great!", "fingerprint": ["maisey"]}, self.project
        )
        # Normally this should go into a different group, since the messages don't match, but the
        # fingerprint takes precedence.
        event2 = save_new_event(
            {"message": "Adopt don't shop", "fingerprint": ["maisey"]}, self.project
        )

        assert event.group_id == event2.group_id

        group = Group.objects.get(id=event.group_id)

        assert group.times_seen == 2
        assert group.last_seen == event2.datetime
        assert group.message == event2.message

    def test_puts_events_with_different_fingerprints_in_different_groups(self):
        event = save_new_event(
            {"message": "Dogs are great!", "fingerprint": ["maisey"]}, self.project
        )
        # Normally this should go into the same group, since the message matches, but the
        # fingerprint takes precedence.
        event2 = save_new_event(
            {"message": "Dogs are great!", "fingerprint": ["charlie"]}, self.project
        )

        assert event.group_id != event2.group_id

    def test_adds_default_fingerprint_if_none_in_event(self):
        event = save_new_event({"message": "Dogs are great!"}, self.project)

        assert event.data.get("fingerprint") == ["{{ default }}"]

    @freeze_time()
    def test_ignores_fingerprint_on_transaction_event(self):
        event1 = save_new_event(
            {"message": "Dogs are great!", "fingerprint": ["charlie"]}, self.project
        )
        event2 = save_new_event(
            {
                "transaction": "dogpark",
                "fingerprint": ["charlie"],
                "type": "transaction",
                "contexts": {
                    "trace": {
                        "parent_span_id": "1121201212312012",
                        "op": "sniffing",
                        "trace_id": "11212012123120120415201309082013",
                        "span_id": "1231201211212012",
                    }
                },
                "start_timestamp": time(),
                "timestamp": time(),
            },
            self.project,
        )

        assert event1.group is not None
        assert event2.group is None
        assert event1.group_id != event2.group_id
        assert (
            tsdb.backend.get_sums(
                TSDBModel.project,
                [self.project.id],
                event1.datetime,
                event1.datetime,
                tenant_ids={"organization_id": 123, "referrer": "r"},
            )[self.project.id]
            == 1
        )

        assert (
            tsdb.backend.get_sums(
                TSDBModel.group,
                [event1.group.id],
                event1.datetime,
                event1.datetime,
                tenant_ids={"organization_id": 123, "referrer": "r"},
            )[event1.group.id]
            == 1
        )

    def test_none_exception(self):
        """Test that when the exception is None, the group is still formed."""
        event = save_new_event({"exception": None}, self.project)

        assert event.group


@region_silo_test
class EventManagerGroupingMetricsTest(TestCase):
    @mock.patch("sentry.event_manager.metrics.incr")
    def test_records_num_calculations(self, mock_metrics_incr: MagicMock):
        project = self.project
        project.update_option("sentry:grouping_config", "legacy:2019-03-12")
        project.update_option("sentry:secondary_grouping_config", None)

        save_new_event({"message": "Dogs are great!"}, self.project)

        hashes_calculated_calls = get_relevant_metrics_calls(
            mock_metrics_incr, "grouping.hashes_calculated"
        )
        assert len(hashes_calculated_calls) == 1
        assert hashes_calculated_calls[0].kwargs["amount"] == 1

        project.update_option("sentry:grouping_config", "newstyle:2023-01-11")
        project.update_option("sentry:secondary_grouping_config", "legacy:2019-03-12")
        project.update_option("sentry:secondary_grouping_expiry", time() + 3600)

        save_new_event({"message": "Dogs are great!"}, self.project)

        hashes_calculated_calls = get_relevant_metrics_calls(
            mock_metrics_incr, "grouping.hashes_calculated"
        )
        assert len(hashes_calculated_calls) == 2
        assert hashes_calculated_calls[1].kwargs["amount"] == 2

    @mock.patch("sentry.event_manager.metrics.incr")
    @mock.patch("sentry.grouping.ingest._should_run_secondary_grouping", return_value=True)
    def test_records_hash_comparison(self, _, mock_metrics_incr: MagicMock):
        project = self.project
        project.update_option("sentry:grouping_config", "newstyle:2023-01-11")
        project.update_option("sentry:secondary_grouping_config", "legacy:2019-03-12")

        cases = [
            # primary_hashes, secondary_hashes, expected_tag
            (["maisey"], ["maisey"], "no change"),
            (["maisey"], ["charlie"], "full change"),
            (["maisey", "charlie"], ["maisey", "charlie"], "no change"),
            (["maisey", "charlie"], ["cory", "charlie"], "partial change"),
            (["maisey", "charlie"], ["cory", "bodhi"], "full change"),
        ]

        for primary_hashes, secondary_hashes, expected_tag in cases:
            with mock.patch(
                "sentry.grouping.ingest._calculate_primary_hash",
                return_value=CalculatedHashes(
                    hashes=primary_hashes, hierarchical_hashes=[], tree_labels=[]
                ),
            ):
                with mock.patch(
                    "sentry.grouping.ingest._calculate_secondary_hash",
                    return_value=CalculatedHashes(
                        hashes=secondary_hashes, hierarchical_hashes=[], tree_labels=[]
                    ),
                ):
                    save_new_event({"message": "Dogs are great!"}, self.project)

                    hash_comparison_calls = get_relevant_metrics_calls(
                        mock_metrics_incr, "grouping.hash_comparison"
                    )
                    assert len(hash_comparison_calls) == 1
                    assert hash_comparison_calls[0].kwargs["tags"]["result"] == expected_tag

                    mock_metrics_incr.reset_mock()
