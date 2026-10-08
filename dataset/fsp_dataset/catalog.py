"""Pinned source references; unknown permissions are not inferred from access."""

SOURCES = [
    {
        "source_id": "team_synthetic",
        "title": "ФСП: контрольные сценарии команды",
        "url": "https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp/dataset",
        "version": "1.0.0",
        "license": "MIT",
        "redistribution": "allowed",
        "label_semantics": "team_rule_oracle; not human professional validation",
    },
    {
        "source_id": "mvp",
        "title": "Проверяемая реализация MVP и независимые решатели",
        "url": "https://github.com/ImmortalDR/CV_hakaton/tree/codex/fsp-mvp",
        "version": "snapshot hashes in manifest",
        "license": "MIT",
        "redistribution": "allowed",
        "label_semantics": "application predictions, not reference relevance labels",
    },
    {
        "source_id": "trudvsem",
        "title": "Работа в России / ИНИД",
        "url": "https://data.rcsi.science/data-catalog/datasets/186/",
        "version": "2021-12-02",
        "license": "CC-BY-SA-4.0",
        "redistribution": "local_only_pending_privacy_review",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "label_semantics": "historical events; direction must be verified independently of table name",
    },
    {
        "source_id": "tianchi",
        "title": "Tianchi / Zhaopin 44080",
        "url": "https://tianchi.aliyun.com/dataset/44080",
        "version": "user-supplied files; SHA-256 pinned",
        "license": None,
        "redistribution": "local_only_terms_unverified",
        "label_semantics": "original browsed/delivered/satisfied flags; not skill or grade confirmation",
    },
    {
        "source_id": "confit",
        "title": "ConFit (RecSys 2024)",
        "url": "https://github.com/jasonyux/ConFit",
        "paper_url": "https://arxiv.org/abs/2401.16349",
        "version": "user-supplied ConFit-master.zip; SHA-256 pinned",
        "license": None,
        "redistribution": "local_only_terms_unverified",
        "label_semantics": "legacy classification / ranking; -1 is zero gain in original evaluator, not semantic rejection",
    },
    {
        "source_id": "talentclef",
        "title": "TalentCLEF 2025",
        "url": "https://zenodo.org/records/15038364",
        "doi": "10.5281/zenodo.15038364",
        "version": "0.3.0",
        "license": None,
        "redistribution": "local_only_terms_unverified",
        "label_semantics": "job-title / skill qrels, not individual candidate qualification",
    },
    {
        "source_id": "careercorpus",
        "title": "CareerCorpus",
        "url": "https://data.mendeley.com/datasets/wzzwn37gmd/1",
        "doi": "10.17632/wzzwn37gmd.1",
        "version": "1",
        "license": "CC-BY-4.0",
        "redistribution": "local_only_pending_privacy_review",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "label_semantics": "two original resume scores; rubric not established for pair matching; AI-assisted source preprocessing",
    },
]

for item in SOURCES:
    item["terms_checked_on"] = "2026-10-08"


def sources_markdown():
    rows = [
        "# Источники",
        "",
        "Права на код и документы источников различаются. "
        "Локальный доступ не является разрешением публиковать реальные профили.",
        "",
        "| ID | Источник | Версия | Лицензия / статус |",
        "|---|---|---|---|",
    ]
    for s in SOURCES:
        rows.append(
            f"| {s['source_id']} | [{s['title']}]({s['url']}) | {s['version']} | "
            f"{s['license'] or 'не установлена'}; {s['redistribution']} |"
        )
    rows += [
        "",
        "Tianchi: страница доступна как JS-приложение; условия NC/SA из старого "
        "описания не подменяют проверку точной лицензии. ConFit содержит заглушки "
        "текстов; они не используются как документы. TalentCLEF: в предоставленных "
        "архивах test/ пуст. CareerCorpus: оценки исходных авторов не являются "
        "нашей разметкой или подтверждением Python/Data-грейда.",
        "",
    ]
    return "\n".join(rows)
