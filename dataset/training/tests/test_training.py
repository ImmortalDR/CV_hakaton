import json
from pathlib import Path
import sys
import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare import clean, event_date, stream, digest
from pairs import asof, split_pairs
from train import assert_isolated, metrics, pair_features, remove_near_duplicates, train


def test_versions_cannot_see_future_or_same_day():
    rows = [
        {"day": d, "text": t, "rownum": i}
        for i, (d, t) in enumerate(
            [
                ("2020-01-01", "old"),
                ("2020-01-04", "future"),
                ("2020-01-03", "same day"),
            ]
        )
    ]
    chosen, reason = asof(rows, "2020-01-03")
    assert reason is None and chosen["text"] == "old"
    assert asof(rows, "2020-01-01") == (None, "no_pre_event_version")


def test_ambiguous_snapshot_fails_closed():
    rows = [
        {"day": "2020-01-01", "text": t, "rownum": i}
        for i, t in enumerate(["python", "java"])
    ]
    assert asof(rows, "2020-01-02") == (None, "ambiguous_pre_event_version")


def test_identical_snapshot_duplicates_are_deterministic():
    rows = [{"day": "2020-01-01", "text": "python", "rownum": i} for i in (8, 2)]
    assert asof(rows, "2020-01-02")[0]["rownum"] == 2


def test_status_not_backdated_and_invalid_date_not_repaired():
    r = {
        "date_creation": "2020-01-01",
        "date_modify": "2020-02-01",
        "date_modify_mistake": "0",
    }
    assert event_date(r) == "2020-02-01"
    r["date_modify_mistake"] = "1"
    assert event_date(r) == ""
    r["date_modify_mistake"] = "0"
    r["date_modify"] = "bad"
    assert event_date(r) == ""


def test_stream_multiline_records_and_hash(tmp_path):
    import hashlib

    p = tmp_path / "input.csv"
    p.write_text('a;b\n"two\nlines";ok\n')
    report = {}
    rows = list(stream(p, report))
    assert rows == [(1, {"a": "two\nlines", "b": "ok"})]
    assert report[p.name]["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    p.write_text("a;b\na;b;unexpected\n")
    with pytest.raises(ValueError, match="Malformed"):
        list(stream(p, {}))


def test_text_cleanup():
    s = clean(
        "<b>Python</b> person@example.com https://example.com +7 (900) 123-45-67 SQL"
    )
    assert s == "python sql"


def row(i, **kwargs):
    p = {
        "pair_id": str(i),
        "person_id": f"p{i}",
        "cv_id": f"c{i}",
        "job_id": f"j{i}",
        "candidate_text": f"candidate {i}",
        "need_text": f"job {i}",
        "label": i % 2,
    }
    return p | kwargs


def test_connected_entities_and_copies_never_cross_splits():
    rows = [
        row(0),
        row(1, person_id="p0"),
        row(2, job_id="j1"),
        row(3, candidate_text="candidate 2"),
    ]
    report = split_pairs(rows)
    assert report["connected_components"] == 1
    assert len({p["split"] for p in rows}) == 1
    first = [dict(p) for p in rows]
    split_pairs(rows)
    assert rows == first


def test_split_leakage_guard():
    a = row(1, group_id="g1")
    b = row(2, group_id="g2", person_id="p1")
    with pytest.raises(ValueError, match="person_id"):
        assert_isolated({"train": [a], "validation": [b], "test": []})


def test_model_features_ignore_labels_ids_and_sensitive_fields():
    a = row(1, candidate_text="python pandas sql", need_text="python sql development")
    v = TfidfVectorizer().fit([a["candidate_text"], a["need_text"]])
    b = a | {
        "label": 0,
        "person_id": "changed",
        "gender": "secret",
        "event_day": "2099-01-01",
    }
    assert np.array_equal(
        pair_features(v, [a])[0].toarray(), pair_features(v, [b])[0].toarray()
    )


def test_near_duplicate_guard_and_empty_vector():
    base = " ".join("term" + str(i) for i in range(80))
    splits = {
        "train": [row(1, candidate_text=base, need_text="abc")],
        "validation": [row(2, candidate_text=base + " extra")],
        "test": [row(3, candidate_text="z")],
    }
    removed = remove_near_duplicates(splits)
    assert removed["validation"] == 1
    assert len(splits["test"]) == 1


def test_ranking_metrics_do_not_invent_unknown_negatives():
    rows = [
        row(0, job_id="j", need_text="same job"),
        row(1, job_id="j", need_text="same job"),
    ]
    m = metrics(rows, np.zeros(2))
    assert m["precision_at_min_5_n"] == 0.5 and m["mixed_vacancy_pools"] == 1
    assert metrics([row(0)], np.zeros(1))["ndcg_at_5"] is None


def test_frozen_input_hash_required(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    (root / "pairs.jsonl").write_text("{}\n")
    (root / "pairs-report.json").write_text(json.dumps({"pairs_sha256": "wrong"}))
    with pytest.raises(ValueError, match="hash mismatch"):
        train(root, tmp_path / "out")


def small_source(tmp_path):
    import csv

    source = tmp_path / "source"
    source.mkdir()

    def save(name, rows):
        with (source / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=";")
            w.writeheader()
            w.writerows(rows)

    events = []
    jobs = []
    cvs = []
    for i in range(4):
        events.append(
            {
                "id_response": f"e{i}",
                "id_reply": "",
                "id_cv": f"c{i}",
                "id_candidate": f"p{i}",
                "id_vacancy": f"j{i}",
                "id_hiring_organization": "org",
                "response_type": ["Приглашение", "Отказ", "Принятие", "Отказ"][i],
                "date_creation": "2020-02-01",
                "date_modify": "",
                "date_last_updated": "2020-03-01",
            }
        )
        jobs.append(
            {
                "identifier": f"j{i}",
                "id_hiring_organization": "org",
                "date_last_updated": "2020-01-01",
                "title": "Python разработчик",
                "requirements_qualifications": "Python SQL databases and reliable backend systems",
                "responsibilities": f"разработка серверной системы номер {i}",
            }
        )
        cvs.append(
            {
                "id_cv": f"c{i}",
                "id_candidate": f"p{i}",
                "date_last_updated": "2020-01-01",
                "position_name": "Python разработчик",
                "skills": f"python sql тестирование проектирование систем номер {i}",
            }
        )
    # Both a future CV and conflicting observed history must be excluded.
    cvs[3]["date_last_updated"] = "2020-04-01"
    events.append(
        events[3]
        | {
            "id_response": "e4",
            "response_type": "Приглашение",
            "date_creation": "2020-05-01",
            "date_last_updated": "2020-06-01",
        }
    )
    save("responses.csv", events)
    save("vacancies.csv", jobs)
    save("curricula_vitae.csv", cvs)
    app = events[0].copy()
    app["id_invitation"] = "a0"
    del app["id_response"]
    app["id_reply"] = "e0"
    app["response_type"] = "Отклик соискателя"
    save("invitations.csv", [app])
    return source


def test_prepare_and_join_real_schema_fixture(tmp_path):
    from prepare import build as scan
    from pairs import build as join

    source = small_source(tmp_path)
    out = tmp_path / "build"
    scan(source, out)
    join(out)
    rows = [json.loads(x) for x in (out / "pairs.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and {p["label"] for p in rows} == {0, 1}
    assert all(p["cv_snapshot_day"] < p["event_day"] for p in rows)
    rep = json.loads((out / "pairs-report.json").read_text())
    assert rep["counts"]["events_from_conflicting_pair_histories"] == 2
    assert rep["counts"]["other_status_not_negative"] == 1
    assert rep["production_promotion_allowed"] is False
    assert rep["explicit_links"]["explicit_link_same_pair"] == 1
    with pytest.raises(FileExistsError):
        join(out)


def test_training_artifact_and_final_metrics(tmp_path):
    import hashlib
    import random
    from train import predict

    rng = random.Random(20261009)
    rows = []
    for split in ("train", "validation", "test"):
        for i in range(24):
            key = f"{split}{i}"
            words = [
                "".join(rng.choices("abcdefghijklmnopqrstuvwxyz", k=10))
                for _ in range(12)
            ]
            rows.append(
                {
                    "pair_id": key,
                    "cv_id": key,
                    "person_id": key,
                    "job_id": key,
                    "group_id": key,
                    "candidate_text": " ".join(words[:6])
                    + (" python" if i % 2 else " java"),
                    "need_text": " ".join(words[6:]) + " python backend development",
                    "label": i % 2,
                    "split": split,
                }
            )
    root = tmp_path / "input"
    root.mkdir()
    raw = "".join(json.dumps(r) + "\n" for r in rows).encode()
    (root / "pairs.jsonl").write_bytes(raw)
    (root / "pairs-report.json").write_text(
        json.dumps(
            {
                "pairs_sha256": hashlib.sha256(raw).hexdigest(),
                "target": "test_fixture_only",
            }
        )
    )
    out = tmp_path / "model"
    train(root, out)
    report = json.loads((out / "training-report.json").read_text())
    assert report["artifact_reload_equal"] and report["status"] == "trained_offline"
    assert report["scores"]["test"]["learned_pair"]["n"] == 24
    score = predict(
        out / "model.joblib",
        "python backend developer with sql knowledge",
        "python backend development with sql and testing of reliable applications",
    )
    assert score["production_promotion_allowed"] is False
    assert isinstance(score["observed_event_score"], float)
    assert predict(out / "model.joblib", "", "")["observed_event_score"] is None


@pytest.mark.parametrize("legacy", [False, True])
def test_resume_partial_stage_reproduces_pairs(tmp_path, legacy):
    import sqlite3
    from prepare import build as scan
    from pairs import build as join

    source = small_source(tmp_path)
    out = tmp_path / "build"
    scan(source, out)
    join(out)
    expected = (out / "pairs.jsonl").read_bytes()
    for name in ("scan.json", "pairs.jsonl", "pairs-report.json"):
        (out / name).unlink()
    with sqlite3.connect(out / "index.sqlite") as db:
        db.executescript(
            "DROP INDEX cv_id; DROP INDEX app_eid; DROP INDEX app_reply; DROP INDEX app_pair; DELETE FROM cvs WHERE rownum>1; DELETE FROM applications;"
        )
        if legacy:
            db.execute("DELETE FROM scan_checkpoints")
    scan(source, out, resume=True)
    join(out)
    assert (out / "pairs.jsonl").read_bytes() == expected
    with pytest.raises(ValueError, match="interrupted"):
        scan(source, out, resume=True)


def test_resume_rejects_changed_completed_input(tmp_path):
    from prepare import build as scan

    source = small_source(tmp_path)
    out = tmp_path / "build"
    scan(source, out)
    (out / "scan.json").unlink()
    p = source / "vacancies.csv"
    p.write_text(p.read_text().replace("Python", "JavaXX"))
    with pytest.raises(ValueError, match="input changed"):
        scan(source, out, resume=True)


def test_pairs_reject_incomplete_scan(tmp_path):
    from pairs import build

    with pytest.raises(ValueError, match="Incomplete scan"):
        build(tmp_path)


def test_technology_slice_handles_punctuation_and_word_boundaries():
    from prepare import technology_mentioned

    assert technology_mentioned("Python, SQL.", "python")
    assert technology_mentioned("Python, SQL.", "sql")
    assert not technology_mentioned("NoSQL", "sql")
