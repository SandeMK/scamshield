# ScamShield — System Architecture

Visual documentation of the integrated system. All diagrams are Mermaid and
render directly on GitHub.

## 1. System overview

```mermaid
flowchart LR
    subgraph Device["Android Device"]
        SMS[Incoming SMS] -->|platform channel| APP[Flutter App]
        APP --> LR[Local Rule Checks<br/>FR-10 instant warning]
    end

    subgraph Cloud["Cloud (Render / local)"]
        API[FastAPI Scoring API<br/>/api/v1]
        RULES[Rule Engine]
        ML[ML Classifier<br/>TF-IDF + LogReg]
        FUSE[Hybrid Fusion<br/>40% rules + 60% ML<br/>+ critical override]
        API --> RULES --> FUSE
        API --> ML --> FUSE
    end

    subgraph Data["Supabase (PostgreSQL)"]
        DB[(Threat Intelligence DB<br/>hashed indicators)]
        REPORTS[(User Reports)]
    end

    subgraph Feeds["Public Threat Feeds"]
        UH[URLhaus]
        OP[OpenPhish]
    end

    APP -->|HTTPS + X-API-Key| API
    FUSE -->|risk score, classification,<br/>explanation codes| APP
    API <-->|indicator lookup| DB
    API -->|scam reports become<br/>indicators, NFR-07| DB
    API --> REPORTS
    UH & OP -->|daily GitHub Actions<br/>ingestion| DB
    FIN[Fintech Client<br/>third-party system] -->|HTTPS + X-API-Key| API
```

## 2. Scoring flow (one message, end to end)

```mermaid
sequenceDiagram
    participant U as User's Phone
    participant F as Flutter App
    participant A as Scoring API
    participant D as Threat Intel DB

    U->>F: SMS arrives (platform channel)
    F->>F: Local rule checks (FR-10)
    F-->>U: Provisional card shown instantly
    F->>A: POST /api/v1/score/sms
    A->>A: Rule engine sub-score
    A->>A: ML classifier confidence
    A->>D: Lookup URL hash, then domain hash
    D-->>A: Match / no match
    A->>A: Hybrid fusion + critical override
    A-->>F: risk_score, classification,<br/>explanation_codes (>=3)
    F-->>U: Final colour-coded card
    Note over F,A: Offline? Local result stands,<br/>card marked "cloud offline" (NFR-08)
```

## 3. Intelligence propagation (user report protects everyone)

```mermaid
sequenceDiagram
    participant V as User A (reporter)
    participant A as Scoring API
    participant D as Threat Intel DB
    participant W as User B (protected)

    V->>A: POST /api/v1/report (scam + URL)
    A->>A: Extract URLs, SHA-256 hash
    A->>D: Upsert url + domain indicators<br/>(source: user_report)
    Note over D: Target: influences scoring<br/>within 30 s (NFR-07)
    W->>A: Same scam URL scored later
    A->>D: Hash lookup
    D-->>A: MATCH
    A-->>W: INTEL_MATCH, score floored at 90<br/>(CRITICAL)
```

## 4. Database schema

```mermaid
erDiagram
    INDICATORS {
        bigint id PK
        text indicator_hash "SHA-256, privacy by design"
        text indicator_type "url | domain | template"
        text source "urlhaus | openphish | user_report"
        text threat_tag
        int reputation "0-100"
        int hit_count
        timestamptz first_seen
        timestamptz last_seen
    }
    REPORTS {
        bigint id PK
        text report_type "scam | false_positive"
        text text_hash
        text url_hash
        timestamptz created_at
    }
    REPORTS ||--o{ INDICATORS : "scam reports create/refresh"
```

## 5. Mobile app structure

```mermaid
flowchart TD
    NAV[Bottom Navigation] --> S[Scans<br/>colour-coded results feed]
    NAV --> SIM[Simulate<br/>demo-safe message injector]
    NAV --> DASH[Dashboard<br/>FR-08 analytics]
    NAV --> SET[Settings<br/>API URL + key]
    S --> DET[Detail Sheet<br/>explanation codes, ML confidence,<br/>report scam / false positive]
    SIM -->|same pipeline as real SMS| S
```

## 6. Repository map

| Folder | Role | Key entry point |
|---|---|---|
| `ml/` | Detection engine + training | `train.py`, `score.py` |
| `api/` | Cloud scoring service | `main.py` |
| `ingestion/` | DB schema + feed pipeline | `schema.sql`, `ingest.py` |
| `mobile-app/` | Flutter app source | `lib/main.dart`, `setup.sh` |
| `fintech-client/` | Interoperability demo | `client.py` |
| `perf/` | §14.6 measurement scripts | `latency_test.py`, `propagation_test.py` |
| `.github/workflows/` | CI, daily ingestion, keep-alive | `ci.yml`, `ingest.yml` |
