from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from chronofeature.feature_store import Event, FeatureError, FeatureStore, InjectedCrash, Label, Query, Spec
from chronofeature.experiments import evaluate
from chronofeature.oracle import scan


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = FeatureStore(Path(self.temporary.name) / "features.sqlite")

    def values(self, time, spec=Spec(), cutoff=None, generation=None):
        return self.store.query(Query("a", time, cutoff), spec, source_generation=generation)["windows"]

    def test_observation_cutoff_prevents_event_time_only_label_leak(self):
        self.store.ingest([Event("late", "a", 5, 20, 100)])
        self.assertEqual(self.values(10)["10"]["count"], 0)
        self.assertEqual(self.values(20)["30"]["sum"], 100)
        self.assertEqual(self.values(20, cutoff=19)["30"]["count"], 0)

    def test_future_revision_does_not_change_past_features(self):
        self.store.ingest(
            [Event("one", "a", 5, 5, 10), Event("one", "a", 5, 20, 40, 1), Event("one", "a", 5, 30, None, 2, True)]
        )
        self.assertEqual(self.values(10)["10"]["sum"], 10)
        self.assertEqual(self.values(20)["30"]["sum"], 40)
        self.assertEqual(self.values(30)["30"]["count"], 0)

    def test_late_lower_revision_cannot_override_authoritative_newer_revision(self):
        self.store.ingest([Event("one", "a", 5, 20, 100, 2), Event("one", "a", 5, 30, 1, 1)])
        self.assertEqual(self.values(30, Spec(ttl=100))["30"]["sum"], 100)

    def test_windows_are_lower_exclusive_and_upper_inclusive(self):
        self.store.ingest(
            [
                Event("lower", "a", 10, 10, 3),
                Event("inside", "a", 11, 11, 4),
                Event("upper", "a", 20, 20, 5),
                Event("future", "a", 21, 21, 100),
            ]
        )
        value = self.values(20)["10"]
        self.assertEqual((value["count"], value["sum"], value["mean"], value["last"]), (2, 9, 4.5, 5))

    def test_equal_event_time_latest_tie_uses_event_id(self):
        self.store.ingest([Event("z", "a", 10, 10, 99), Event("b", "a", 10, 10, 1)])
        self.assertEqual(self.values(10)["10"]["last"], 99)

    def test_ttl_boundary_is_inclusive_then_values_are_withheld(self):
        self.store.ingest([Event("one", "a", 10, 10, 7)])
        spec = Spec(windows=(100,), ttl=5)
        self.assertEqual(self.values(15, spec)["100"]["sum"], 7)
        value = self.values(16, spec)["100"]
        self.assertEqual(value["status"], "stale")
        self.assertIsNone(value["sum"])

    def test_online_expires_before_rolling_window_changes_even_if_ttl_fresh(self):
        self.store.ingest([Event("old", "a", 10, 10, 3), Event("new", "a", 15, 15, 7)])
        spec = Spec(windows=(10,), ttl=100)
        self.store.materialize("v1", ["a"], 15, spec)
        self.assertEqual(self.store.serve("a", 19)["features"]["windows"]["10"]["sum"], 10)
        value = self.store.serve("a", 20)["features"]["windows"]["10"]
        self.assertEqual(value["status"], "expired")
        self.assertIsNone(value["sum"])

    def test_empty_materialized_windows_also_have_cache_ttl(self):
        self.store.materialize("v1", ["a"], 15, Spec(windows=(10,), ttl=5))
        self.assertEqual(self.store.serve("a", 20)["features"]["windows"]["10"]["count"], 0)
        self.assertIsNone(self.store.serve("a", 21)["features"]["windows"]["10"]["count"])

    def test_duplicate_ingest_is_idempotent_but_conflict_rolls_back_batch(self):
        event = Event("one", "a", 10, 10, 5)
        self.assertEqual(self.store.ingest([event])["generation"], 1)
        self.assertEqual(self.store.ingest([event])["generation"], 1)
        with self.assertRaises(FeatureError):
            self.store.ingest([Event("new", "a", 11, 11, 100), replace(event, value=999)])
        self.assertEqual(len(self.store.export_events()), 1)
        self.assertEqual(self.store.query(Query("a", 20))["source_generation"], 1)

    def test_event_entity_and_time_are_immutable_across_revisions(self):
        self.store.ingest([Event("one", "a", 10, 10, 5)])
        for event in (Event("one", "b", 10, 11, 7, 1), Event("one", "a", 11, 11, 7, 1)):
            with self.assertRaisesRegex(FeatureError, "identity"):
                self.store.ingest([event])

    def test_ingestion_generation_preserves_historical_materialization_parity(self):
        self.store.ingest([Event("one", "a", 10, 10, 5)])
        old = self.store.query(Query("a", 20))
        self.store.ingest([Event("backfill", "a", 12, 12, 100)])
        self.assertEqual(self.store.query(Query("a", 20), source_generation=1), old)
        self.assertNotEqual(self.store.query(Query("a", 20))["windows"], old["windows"])

    def test_offline_join_does_not_use_targets_and_rows_do_not_alias(self):
        self.store.ingest([Event("one", "a", 10, 10, 5)])
        labels = [Label("x", "a", 20, 0), Label("y", "a", 20, 1)]
        joined = self.store.offline_join(labels)
        self.assertEqual(joined["rows"][0]["features"], joined["rows"][1]["features"])
        joined["rows"][0]["features"]["windows"]["30"]["sum"] = 999
        self.assertNotEqual(joined["rows"][0]["features"], joined["rows"][1]["features"])
        with self.assertRaises(FeatureError):
            self.store.offline_join([labels[0], labels[0]])

    def test_offline_batch_retains_one_source_snapshot_during_concurrent_ingest(self):
        self.store.ingest([Event("one", "a", 1, 1, 5)])
        labels = [Label("a", "a", 10, 0), Label("b", "b", 10, 1)]
        original = self.store._query
        invoked = False

        def interleaved(*args, **kwargs):
            nonlocal invoked
            result = original(*args, **kwargs)
            if not invoked:
                invoked = True
                self.store.ingest([Event("late", "b", 2, 2, 99)])
            return result

        with patch.object(self.store, "_query", side_effect=interleaved):
            joined = self.store.offline_join(labels)
        self.assertEqual(joined["source_generation"], 1)
        self.assertEqual(joined["rows"][1]["features"]["windows"]["30"]["count"], 0)
        self.assertEqual(self.store.query(Query("b", 10))["windows"]["30"]["count"], 1)

    def test_feature_specification_identity_is_versioned_immutable(self):
        self.store.query(Query("a", 10))
        with self.assertRaisesRegex(FeatureError, "redefined"):
            self.store.query(Query("a", 10), Spec(ttl=99))
        self.store.materialize("v2", ["a"], 10, Spec(version=2, ttl=99))
        self.assertEqual(self.store.serve("a", 10)["features"]["spec_version"], 2)

    def test_atomic_feature_version_publish_and_retry(self):
        self.store.materialize("v1", ["a"], 10)
        old = self.store.serve("a", 10)
        with self.assertRaises(InjectedCrash):
            self.store.materialize("v2", ["a", "b"], 20, crash_before_commit=True)
        self.assertEqual(self.store.serve("a", 10), old)
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM online WHERE version_id='v2'").fetchone()[0], 0)
        self.store.materialize("v2", ["a", "b"], 20)
        self.assertEqual(self.store.serve("a", 20)["version_id"], "v2")

    def test_materialization_replay_does_not_reactivate_old_version(self):
        self.store.materialize("v1", ["a"], 10)
        self.store.materialize("v2", ["a"], 20)
        self.assertTrue(self.store.materialize("v1", ["a"], 10)["replayed"])
        self.assertEqual(self.store.serve("a", 20)["version_id"], "v2")
        with self.assertRaises(FeatureError):
            self.store.materialize("v1", ["a"], 11)

    def test_unavailable_entity_and_time_travel_are_explicit(self):
        self.assertEqual(self.store.serve("a", 10)["reason"], "no_active_version")
        self.store.materialize("v1", ["a"], 20)
        self.assertEqual(self.store.serve("unknown", 20)["reason"], "entity_not_materialized")
        with self.assertRaises(FeatureError):
            self.store.serve("a", 19)

    def test_future_cutoff_and_invalid_clocks_values_specs_are_rejected(self):
        for args in (("a", 10, 11), ("a", True), ("a", -1)):
            with self.assertRaises(FeatureError):
                Query(*args)
        for value in (True, 1.0, 10**10):
            with self.assertRaises(FeatureError):
                Event("one", "a", 1, 1, value)
        with self.assertRaises(FeatureError):
            Event("one", "a", 2, 1, 5)
        with self.assertRaises(FeatureError):
            Spec(windows=(30, 10))
        with self.assertRaises(FeatureError):
            Spec(windows=(10, 10))

    def test_unknown_source_snapshot_is_rejected(self):
        for generation in (-1, 1, True):
            with self.assertRaises(FeatureError):
                self.store.query(Query("a", 10), source_generation=generation)

    def test_independent_scan_matches_corrections_tombstones_and_generations(self):
        self.store.ingest([Event("a", "a", 5, 5, 7), Event("b", "a", 10, 15, 9)])
        self.store.ingest([Event("a", "a", 5, 20, None, 1, True)])
        for generation in (1, 2):
            for time in (5, 10, 15, 20, 30):
                query = Query("a", time)
                self.assertEqual(
                    self.store.query(query, source_generation=generation),
                    scan(self.store.export_events(), query, Spec(), generation),
                )

    def test_seeded_end_to_end_experiment_across_seeds(self):
        for seed in (17, 23, 101):
            report = evaluate(seed)
            self.assertEqual(report["passed"], report["checks"])
            self.assertEqual(report["oracle_comparisons"], 120)


if __name__ == "__main__":
    unittest.main()
