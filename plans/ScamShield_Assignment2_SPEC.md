**TSHWANE UNIVERSITY OF TECHNOLOGY**

Faculty of Information and Communication Technology

Department of Computer Science

**ISJ107V: Integrated Software Project**

Assignment 2: Formal System Proposal and Specification

**ScamShield**

*A Mobile-First Cloud-Powered Threat Intelligence Network for Detecting SMS Phishing Campaigns in South Africa*

| **Student number** | **Student name**     | **Email**                | **Module** |
|--------------------|----------------------|--------------------------|------------|
| 216432363          | Philasande Makhubela | 216432363@tut4life.ac.za | ISJ107V    |

Assessment type: Individual \| Total marks: 50 \| Due date: 19 September 2026

**Question 1: Project Introduction and Motivation**

**1.1 Project title, description, intended users and emerging technology**

**Project title:** ScamShield: A Mobile-First Cloud-Powered Threat Intelligence Network for Detecting SMS Phishing Campaigns in South Africa.

ScamShield is an integrated mobile and cloud software system that detects SMS phishing (smishing) messages and malicious links in near real time. An Android application captures incoming SMS messages, extracts the message text, sender and any embedded URLs, and submits them to a cloud scoring service over HTTPS. The service returns a risk score between 0 and 100, a classification label ranging from SAFE to CRITICAL, and at least three plain-language explanation codes stating why the message was judged risky. Indicators confirmed by users, together with indicators imported daily from public threat feeds, are stored as irreversible hashes in a shared threat intelligence database, so that a scam reported by one user improves protection for every other user.

The intended users are three groups. The primary user is the everyday South African smartphone owner who receives impersonation messages purporting to come from banks, the South African Revenue Service or courier companies. The second is a system administrator, who triggers and monitors threat feed ingestion and reviews system analytics. The third is an authorised third-party client system, represented in this project by a mock fintech client, which consumes the same scoring API to check content in its own workflow.

The emerging technology integrated into the system is artificial intelligence, specifically supervised machine learning for text classification. A TF-IDF vectoriser and a Logistic Regression classifier, trained on a labelled corpus of SMS messages, produce a probability that a message is a scam. This probability is fused with a deterministic rule engine so that the system gains the generalisation of machine learning while retaining the explainability that a consumer-facing security product requires.

**1.2 Problem statement**

South Africans are exposed to a growing volume of SMS phishing that impersonates trusted institutions. The messages are cheap to send, arrive on a channel that users instinctively trust, and increasingly carry links to domains registered hours before the campaign begins. Existing defences are reactive: they rely on static blocklists and on manual reporting after a victim has already lost money. A domain registered this morning is absent from every blocklist this afternoon, which is precisely the window in which a campaign does its damage.

Those affected are ordinary smartphone users, who are the direct targets; the banks, revenue services and logistics companies whose brands are impersonated and whose support channels absorb the fallout; and any organisation whose employees can be phished into surrendering credentials. Users who are older, less digitally confident, or who do not read English as a first language carry a disproportionate share of the risk, because the cues that mark a message as fraudulent are subtle and easily missed.

Three specific gaps sustain the problem. First, detection is slow, because it depends on lists that are updated only after a campaign has been observed. Second, intelligence is fragmented: a scam identified by one person does not protect anyone else, so the same campaign succeeds repeatedly against different victims. Third, where automated filtering does exist, it is opaque: a message is silently classified as spam with no explanation, which teaches users nothing and leaves them equally vulnerable to the next variant.

If the problem is left unresolved, the consequences are direct financial loss through fraudulent transfers, compromise of identity documents and banking credentials, erosion of trust in legitimate SMS communication from banks and government, and rising recovery and support costs for the impersonated institutions. As mobile money and digital government services continue to expand, the exposed population and the value at risk both grow.

**1.3 Aim, objectives, scope and success criteria**

**Project aim**

To design and deliver an integrated mobile and cloud system that detects SMS phishing messages and malicious links in near real time, explains every decision to the user in plain language, and shares confirmed threat indicators across all users of the system.

**Measurable objectives**

| **ID**     | **Objective**                                                                                           | **Measure of achievement**                                                                                                                     |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|
| **OBJ-01** | Deliver a hybrid detection engine that combines rule-based analysis with a machine-learning classifier. | F1-score of at least 0.85 for the scam class on a held-out test set drawn from a labelled corpus of at least 500 messages.                     |
| **OBJ-02** | Deliver an integrated mobile and cloud pipeline that returns an explained result fast enough to act on. | At least 95% of scoring requests return a risk score, a classification label and at least three explanation codes within 2 seconds.            |
| **OBJ-03** | Establish a shared threat intelligence network fed by public feeds and by user reports.                 | At least two public feeds ingested on a daily schedule, and a user-reported indicator influences the scoring of other users within 30 seconds. |

**Scope boundaries**

**Within scope:**

- Android SMS capture, URL extraction and on-device heuristic checks.

- A cloud scoring API that fuses rule-based and machine-learning sub-scores into an explained risk score.

- A shared threat intelligence database of hashed indicators, with reputation and first/last-seen metadata.

- Automated daily ingestion from at least two public threat intelligence feeds.

- User reporting of scams and false positives, an in-app analytics dashboard, and an authenticated third-party client interface.

**Outside scope:**

- iOS SMS scanning, which the platform does not permit.

- Direct interception of messages inside WhatsApp, Telegram or email clients; content from these applications is only assessed when the user deliberately shares it into ScamShield.

- Enterprise security operations centre integration and automated domain or website takedown.

- Automated blocking, deletion or financial intervention; the system advises, it does not act on the user's behalf.

**Success criteria**

| **ID**    | **Success criterion**                                                                                                                                                    | **Target**                                                                                                                                                                           |
|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **SC-01** | End-to-end integration: the mobile application, the cloud scoring API and the shared threat intelligence database operate together over REST without integration errors. | At least 95% of scoring requests during system testing return a complete, well-formed response containing a risk score, a classification label and at least three explanation codes. |
| **SC-02** | Detection performance: the hybrid engine distinguishes scam messages from legitimate traffic with accuracy sufficient for consumer use.                                  | F1-score of at least 0.85 for the scam class on the held-out test set.                                                                                                               |

**Question 2: Functional and Non-Functional Requirements**

**2.1 Prioritised functional requirements**

Requirements are prioritised using the MoSCoW scheme: Must (required for the system to be viable), Should (important but not fatal if deferred) and Could (desirable extension). Acceptance criteria are expressed in Given–When–Then form so that each requirement is directly testable. FR-01 to FR-10 below are the ten prioritised functional requirements required by this question; two further requirements that form part of the delivered scope are recorded separately after them.

| **ID**    | **Priority** | **Requirement**                                                                                                                                                                                                                                            | **Acceptance criterion**                                                                                                                                                                                                                                                                                                                                                                                                        |
|-----------|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **FR-01** | Must         | The system shall capture incoming SMS messages on the Android device through a persistent foreground service and extract the message text, the sender identifier and any embedded URLs.                                                                    | Given the application holds SMS and notification permissions and the protection service is running, when an SMS is delivered to the device, then the message text, sender and extracted URL list are passed to the scanning pipeline within 1 second and without user interaction.                                                                                                                                              |
| **FR-02** | Must         | The system shall expose authenticated RESTful endpoints under /api/v1 that accept scoring requests over HTTPS from the mobile application and from authorised third-party client systems.                                                                  | Given a client presents a valid X-API-Key header, when it sends POST /api/v1/score/sms with a valid JSON body, then the API returns HTTP 200 with a scoring payload; and given the key is absent or invalid, when the request is received, then the API returns HTTP 401 and performs no scoring.                                                                                                                               |
| **FR-03** | Must         | The system shall score every submitted message with a hybrid engine that fuses a deterministic rule sub-score with a machine-learning confidence value, returning a risk score from 0 to 100, a classification label and at least three explanation codes. | Given a valid scoring request, when the hybrid engine completes, then the response contains risk_score between 0 and 100, classification drawn from SAFE, LOW_RISK, MEDIUM_RISK, HIGH_RISK or CRITICAL, at least three explanation_codes, ml_confidence, rule_sub_score and model_version.                                                                                                                                      |
| **FR-04** | Must         | The system shall compare the SHA-256 hash of every extracted URL against the shared threat intelligence database and adjust the risk score when a known indicator matches.                                                                                 | Given an extracted URL whose hash is present in the indicators table, when scoring completes, then an exact URL match raises the risk score to at least 90 and a domain-level match adds 15 points, and in both cases an INTEL_MATCH explanation code naming the indicator source is returned.                                                                                                                                  |
| **FR-05** | Must         | The system shall display each result in the mobile application as a colour-coded card showing the risk score, the classification label and the explanation codes in plain language.                                                                        | Given a scoring response is received, when the result card is rendered, then the card colour corresponds to the classification band and every returned explanation code is legible on the detail view without horizontal scrolling.                                                                                                                                                                                             |
| **FR-06** | Must         | The system shall perform lightweight heuristic checks on the device and present a provisional warning before the cloud response arrives, retaining the local result when the cloud service is unreachable.                                                 | Given an incoming SMS, when the local rule engine produces a score of 90 or above, then a provisional critical warning is displayed within 1 second; and given the scoring API is unreachable, when the request times out, then the local result is retained and the card is marked “cloud offline”.                                                                                                                            |
| **FR-07** | Must         | The system shall allow a user to report a message as a confirmed scam or to flag a detection as a false positive, and shall store reported indicators as SHA-256 hashes in the shared threat intelligence database.                                        | Given a scan result is open, when the user submits a scam report, then the API returns HTTP 201, the indicator hash is written to the indicators table with source user_report, and a subsequent scan of the same URL by any user returns an INTEL_MATCH explanation code.                                                                                                                                                      |
| **FR-08** | Should       | The system shall ingest threat indicators from at least two public threat intelligence feeds on an automated daily schedule, normalising and hashing each indicator before storage.                                                                        | Given the scheduled ingestion job runs, when indicators are retrieved from URLhaus and OpenPhish, then each entry is normalised, hashed and upserted, hit_count is incremented for indicators already present, and the job reports the number of indicators processed.                                                                                                                                                          |
| **FR-09** | Should       | The system shall allow the phone's owner to designate one trusted contact number in Settings and, when a message is classified CRITICAL, automatically send that contact a plain-language SMS alert without requiring the user to tap send.                | Given a trusted contact number has been saved and SEND_SMS permission granted, when a message scores CRITICAL, then an SMS containing the risk classification and a plain-language summary is sent automatically to the saved number with no additional user interaction; and given no contact number has been saved, when a message scores CRITICAL, then no SMS is sent and the in-app warning behaves as for any other user. |
| **FR-10** | Could        | The system shall accept message content shared from any other application through the Android share sheet and process it through the same scoring pipeline.                                                                                                | Given the user selects text in another application and shares it to ScamShield, when the application receives the ACTION_SEND intent, then the text is scored through the standard pipeline, tagged with source SHARED, and the resulting card appears in the scan list.                                                                                                                                                        |

**Additional functional requirements (beyond the required ten)**

The following six requirements form part of the delivered system but are listed separately so that the ten prioritised requirements above remain distinct. FR-11 corresponds to use case UC-12 in the use-case diagram. FR-13 is the analytics dashboard, moved to this list to make room for the guardian-alert requirement above; it is otherwise unchanged and remains a fully delivered feature. FR-14 and FR-15 correspond to the new use case UC-13 Manage Profile & Notifications. FR-16 has no dedicated use case, since profile recovery is a background continuation of UC-13 rather than a separate user-facing interaction.

| **ID**    | **Priority** | **Requirement**                                                                                                                                                                                                                        | **Acceptance criterion**                                                                                                                                                                                                                                                                                                                                                                             |
|-----------|--------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **FR-11** | Should       | The system shall allow the user to configure the scoring service base URL and API key from within the application, persisting both values between sessions.                                                                            | Given the settings screen is open, when the user saves a new base URL and API key, then subsequent scoring requests are sent to that host with that key, and both values survive an application restart.                                                                                                                                                                                             |
| **FR-12** | Could        | The system shall provide a message simulation facility that injects sample message text into the same scoring pipeline used for live SMS, supporting testing and demonstration without waiting for a real scam message.                | Given the simulation screen, when the user submits sample text, then it is scored through the standard pipeline, the resulting card is tagged as simulated, and its behaviour is otherwise identical to a live SMS scan.                                                                                                                                                                             |
| **FR-13** | Should       | The system shall provide an in-app analytics dashboard summarising the number of messages scanned, the breakdown of detections by risk level and the number of reports submitted.                                                      | Given at least one scan has been performed, when the dashboard is opened, then the total scan count, a breakdown by classification band and the report count are displayed, sourced from the local scan store and GET /api/v1/analytics/summary.                                                                                                                                                     |
| **FR-14** | Could        | The system shall allow a user to optionally create a profile from Settings using a display name and/or recovery email, independent of the anonymised device identifier generated automatically on first launch.                        | Given the settings screen is open, when the user enters a display name and/or email and saves, then a user_profiles row is created linked to the device’s identifier, and the application continues to function normally for any user who declines to create one.                                                                                                                                    |
| **FR-15** | Could        | The system shall allow a user with a profile to configure notification preferences, comprising the alert risk threshold, retroactive re-classification alerts, report-outcome alerts and digest frequency, persisting across sessions. | Given a user has an active profile, when they change any notification preference and save, then subsequent alerts follow the saved preference and the setting persists after an application restart.                                                                                                                                                                                                 |
| **FR-16** | Could        | The system shall allow a user with a recovery email on file to re-link their profile to a new installation by requesting and entering a time-limited emailed verification code.                                                        | Given a profile exists with a recovery email, when the user requests recovery on a new installation and enters the correct code within its validity window, then their display name, notification preferences and activity counters are restored to the new device identifier; and given the code is incorrect or expired, then the profile is not re-linked and the original profile is unaffected. |

**2.2 Non-functional requirements**

| **ID**     | **FURPS+ category**               | **Requirement**                                                                                                                                                                                 | **Acceptance criterion**                                                                                                                                                                             |
|------------|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **NFR-01** | Performance                       | The cloud scoring API shall return a complete scoring response within 2 seconds for at least 95% of requests under normal network conditions.                                                   | Measured 95th-percentile response time over 100 consecutive requests is 2 seconds or less.                                                                                                           |
| **NFR-02** | Reliability                       | The mobile application shall remain usable when the cloud scoring service is unavailable, by falling back to local rule-based scoring.                                                          | Given the API is unreachable, when 10 messages are scanned, then all 10 produce a local result marked “cloud offline” and no unhandled error is presented to the user.                               |
| **NFR-03** | Usability                         | A first-time user shall be able to interpret a scan result without training, supported by plain-language explanation codes and consistent colour coding.                                        | At least 8 of 10 pilot participants correctly state whether a message is safe or dangerous within 5 seconds of opening the result card.                                                              |
| **NFR-04** | Constraint (security and privacy) | All client-to-server communication shall use HTTPS with TLS 1.2 or higher and API-key authentication, and threat indicators shall be persisted only as SHA-256 hashes under row-level security. | A TLS scan of the deployed endpoint reports TLS 1.2 or higher; unauthenticated requests return HTTP 401; and inspection of the indicators table shows no plaintext URLs, domains or message content. |

**2.3 Emerging-technology requirements**

The following requirements apply directly to the machine-learning component and are measured independently of the surrounding application.

| **ID**    | **Requirement**                                                                                                                                                                         | **Acceptance criterion**                                                                                                                                                                                                                                       |
|-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **ET-01** | The machine-learning classifier shall achieve an F1-score of at least 0.85 for the scam class on a held-out test set drawn from a labelled corpus of at least 500 messages.             | Evaluation on the held-out split reports F1 ≥ 0.85. The selected model achieves 0.942 on the 5,572-message UCI SMS Spam Collection; Logistic Regression was chosen by five-fold cross-validation ahead of Random Forest (0.923) and Gradient Boosting (0.915). |
| **ET-02** | Server-side inference and hybrid fusion shall complete within 200 milliseconds per message, excluding network transit.                                                                  | The instrumented latency_ms value returned by the API is 200 ms or less for at least 95 of 100 consecutive requests.                                                                                                                                           |
| **ET-03** | Every scoring response shall include at least one machine-learning-derived explanation code together with the model confidence and the version of the model that produced the decision. | For 100 sampled responses, each contains ml_confidence, model_version and at least one code of ML_PHISHING_PATTERN or ML_BENIGN_PATTERN in addition to rule-derived codes.                                                                                     |

**Question 3: Technical Environment**

**3.1 Proposed technology stack**

| **Layer**                 | **Technology**                                                                                           | **Justification**                                                                                                                                                                                                                                            |
|---------------------------|----------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **User interface**        | Flutter 3.22+ (Dart), Material 3                                                                         | A single declarative codebase produces a responsive Android client, and the widget model suits the colour-coded result cards and animated risk gauge that carry the usability requirement NFR-03.                                                            |
| **Device platform layer** | Kotlin foreground service, EventChannel and MethodChannel                                                | Android exposes incoming SMS through an official broadcast API, so no unsupported interception is required. A foreground service keeps the listener alive after the application is swiped away, which FR-01 depends on.                                      |
| **Application layer**     | Python 3.11, FastAPI, Uvicorn                                                                            | Pydantic models validate every request at the boundary, OpenAPI documentation is generated automatically for third-party integrators, and the service shares a language with the machine-learning code, removing a serialisation boundary.                   |
| **Emerging technology**   | scikit-learn: TF-IDF vectoriser with Logistic Regression, persisted with joblib                          | Inference is CPU-only and takes milliseconds, the model coefficients remain inspectable, and the approach is well established in the SMS phishing literature. No GPU or paid inference service is needed, which keeps the project inside a free-tier budget. |
| **Database**              | Supabase (managed PostgreSQL) with row-level security                                                    | The indicator workload is relational: unique hash-and-type upserts with hit-count increments and reputation merging are expressed as one SQL function. Row-level security restricts all access to the service key.                                           |
| **APIs and integration**  | REST over HTTPS with JSON payloads, X-API-Key authentication, PostgREST RPC to the database              | A simple, widely understood contract that the mobile client and any authorised third-party system can consume without a bespoke SDK.                                                                                                                         |
| **External data sources** | URLhaus and OpenPhish public threat feeds                                                                | Both are free, frequently refreshed and provide baseline coverage of malicious URLs before user-generated reports accumulate.                                                                                                                                |
| **Development tools**     | Android Studio, Visual Studio Code, Git and GitHub, GitHub Actions, pytest, Postman                      | Version control with automated continuous integration, a scheduled workflow for daily ingestion, and a Postman collection that tests the published API contract.                                                                                             |
| **Deployment platform**   | Render (containerised API) with managed Supabase database; the client is distributed as a sideloaded APK | Deployment is declared as code in render.yaml, so the environment is reproducible, and neither platform requires a billing account for the pilot.                                                                                                            |

**3.2 Hardware requirements**

| **Component**                                        | **Minimum**                                                                                                      | **Recommended**                                                                                                              |
|------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| **Processor (client device)**                        | Quad-core 1.8 GHz ARM (64-bit)                                                                                   | Octa-core 2.4 GHz ARM (64-bit)                                                                                               |
| **Processor (server)**                               | 0.1 shared vCPU (Render free tier)                                                                               | 1 dedicated vCPU                                                                                                             |
| **Memory (client device)**                           | 3 GB RAM                                                                                                         | 6 GB RAM or more                                                                                                             |
| **Memory (server)**                                  | 512 MB RAM                                                                                                       | 2 GB RAM                                                                                                                     |
| **Storage (client device)**                          | 150 MB free space for the application and local scan history                                                     | 500 MB free space                                                                                                            |
| **Storage (server and database)**                    | 1 GB application storage plus 500 MB database                                                                    | 5 GB application storage plus 2 GB database                                                                                  |
| **Network and connectivity**                         | 3G, approximately 1 Mbps, intermittent; the system degrades to local rule scoring when offline (NFR-02)          | LTE or Wi-Fi at 5 Mbps or more with stable connectivity                                                                      |
| **Client device platform**                           | Android 8.0 (API level 26), SMS-capable handset                                                                  | Android 13 or later; validated on a Samsung S938B running Android 16                                                         |
| **Specialised hardware for the emerging technology** | None. Inference is CPU-only; the serialised model is a few megabytes and loads into the API process at start-up. | None required. Concurrency is addressed by vertical scaling of the API instance or by running additional stateless replicas. |
| **Developer workstation**                            | Dual-core processor, 8 GB RAM, 20 GB free storage                                                                | Quad-core processor, 16 GB RAM, SSD storage for the Flutter toolchain and Android emulator                                   |

**3.3 Architecture and deployment approach**

The system follows a three-tier client–server architecture with an additional scheduled batch pipeline. The presentation tier is the Flutter application on the user's device, which also hosts a lightweight local rule engine so that a provisional verdict is available without network access. The application tier is the stateless FastAPI scoring service, which owns the rule engine, the machine-learning classifier, the hybrid fusion logic and the threat intelligence client. The data tier is the managed PostgreSQL database that stores hashed indicators and report records. The batch pipeline is a scheduled ingestion job that imports indicators from public feeds into the same database.

Components communicate exclusively over documented interfaces. The mobile client calls the scoring service with JSON over HTTPS, authenticating with an X-API-Key header; the same contract serves the third-party fintech client, which is why no special-case integration code exists for it. Within the device, the Kotlin foreground service passes captured messages to the Dart layer over an EventChannel, and the Dart layer calls back into Kotlin over a MethodChannel to raise notifications. The scoring service reaches the database through PostgREST, including a server-side function that performs batch indicator upserts in a single round trip.

Scalability is addressed by keeping the application tier stateless: no session or scan data is held in the API process, so additional replicas can be added behind the platform load balancer without coordination. Indicator lookups are single-row queries against a unique index on the indicator hash, so lookup cost stays flat as the table grows, and ingestion writes are batched through one remote procedure call rather than one call per indicator. The machine-learning model is loaded once at start-up and reused across requests, which keeps per-request inference in the low milliseconds.

Security follows a privacy-by-design position. All traffic uses TLS 1.2 or higher, every endpoint except the health check requires an API key, and administrative operations such as triggering ingestion require a separate administrator key. Indicators and report records are stored only as SHA-256 hashes of normalised values, so the database holds no plaintext URLs, domains or message content; row-level security is enabled on both tables, restricting access to the service key. Message text is transmitted for scoring but is never persisted server-side, which keeps the design aligned with the minimality principle of the Protection of Personal Information Act.

Backup and recovery rest on three separable assets. The database is a managed service with automated daily backups and point-in-time recovery, and the full schema is held in version control as schema.sql so the structure can be rebuilt from source. The application and the serialised, version-stamped model are held in the Git repository, and the deployment is declared in render.yaml, so a failed instance is restored by redeploying the last known-good commit rather than by repairing a server. Indicator data is itself partly reproducible, because the daily ingestion job can be re-run to restore public-feed indicators; only user-reported indicators are unique to the database, and these are the smallest and most frequently backed-up portion of the dataset.

**Question 4: UML Models**

The four models below use the same actor, component, class and requirement names as the rest of this document. All diagrams were produced in PlantUML.

**4.1 Use-case diagram**

The system boundary encloses the ScamShield system. The Mobile User is the primary actor and drives scanning, viewing, reporting, dashboard and configuration use cases. The System Administrator triggers feed ingestion and reviews analytics. Four supporting actors sit outside the boundary: the Fintech Partner System, which consumes the scoring interface directly; the Public Threat Feed services URLhaus and OpenPhish, which supply indicators; the Daily Scheduler, a time-based actor that initiates ingestion; and the Trusted Contact, a passive recipient notified only when UC-14 fires. UC-01 and UC-02 both include UC-03 Score Message, which in turn includes UC-04 Look Up Threat Indicator. UC-05 Show Instant Local Warning extends UC-01, because it occurs only when the local heuristic score is high. UC-08 and UC-09 are specialisations of UC-07 Submit Report, since both follow the same reporting flow with a different report type. UC-13 Manage Profile & Notifications lets the Mobile User optionally create a profile and configure alert preferences, entirely independent of the anonymous scanning and reporting flows available to every user. UC-14 Send Guardian Alert extends UC-01 in the same way as UC-05, firing only when a message is classified CRITICAL, and notifies the Trusted Contact directly.

<img src="media/ccea9e0a006c15e5f0e1ddb4e356a5f08b68a989.png" style="width:6.66667in;height:4.33131in" />

*Figure 1: ScamShield use-case diagram*

**4.2 Activity diagram**

The workflow modelled is UC-01 Scan Incoming SMS, from message arrival to the final result and optional user report. Three partitions separate the mobile application, the cloud scoring API and the threat intelligence database. The alternative path taken when the cloud service is unreachable terminates with the local result retained and marked offline, in support of NFR-02. The emerging-technology step is the machine-learning inference, immediately followed by hybrid fusion of the rule and model sub-scores. A further decision, added for FR-09 (UC-14), sits immediately after the final result is shown and before the reporting branch: when the classification is CRITICAL and a trusted contact has been saved, the mobile application sends the guardian SMS alert automatically, with no further action required from the user.

<img src="media/076e2dcd6dec8b241ca9aa753bf868e406caf247.png" style="width:5.98958in;height:8.27282in" />

*Figure 2: Activity diagram for UC-01 Scan Incoming SMS*

**4.3 Class diagram**

The domain model centres on Scan, which produces at most one ScanResult. The composition between ScanResult and ExplanationCode carries a multiplicity of three to six, enforcing FR-03 at the model level. ScamScorer is the hybrid engine; it queries a ThreatIntelClient, which is abstract so that the concrete SupabaseThreatIntelClient can be substituted by a stub when no database is configured, which is the inheritance relationship shown in the diagram. Its run-time collaboration with a rule engine and an ML classifier is described in Section 3.1 rather than modelled as separate classes here, keeping the diagram to genuinely structural, persisted or shared domain concepts. A Scan may raise zero or more Reports, and a Report creates or refreshes Indicator records, which is the mechanism by which one user's report protects other users. Report now carries a deviceId attribute, matching the schema change described in Section 5.1, and UserProfile is linked to Report by that shared identifier rather than by direct ownership, so scan and report history is retained independently of whether a profile exists. UserProfile in turn configures exactly one NotificationPrefs value object, which reuses the RiskLevel enumeration already defined for ScanResult as its alert threshold.

<img src="media/6688f6c29542dad869be846ea962bf79625398dd.png" style="width:6.66667in;height:5.13439in" />

*Figure 3: ScamShield class diagram*

**4.4 Sequence diagram**

The sequence covers UC-01 Scan Incoming SMS across all four layers required: the user interface (the Scans screen), the application logic (ScanStore, LocalRuleEngine and ApiClient), the data service (SupabaseThreatIntelClient and the threat intelligence database) and the emerging-technology component (ScamScorer, containing the rule engine and the machine-learning classifier). The provisional local result is returned to the user before the network call completes, satisfying FR-06. The alternative fragment shows the three possible outcomes of the indicator lookup, and the closing fragment shows the reporting flow of FR-07. A further alternative fragment, placed immediately after the final result is shown and before the reporting fragment, covers FR-09: when the returned classification is CRITICAL and a trusted contact number has been saved, the mobile application sends an automatic SMS to the Trusted Contact, an actor added to this diagram for that single interaction.

<img src="media/15a80a8e3b617043c27ca2c9468e77a432c842da.png" style="width:6.66667in;height:5.91574in" />

*Figure 4: Sequence diagram for UC-01 Scan Incoming SMS*

**Question 5: Implementation and Evaluation**

**5.1 Database, dataset and interface design**

The shared threat intelligence database holds three entities. The indicators entity stores one row per unique indicator hash and type, with the attributes indicator_hash, indicator_type (url, domain or template), source (urlhaus, openphish or user_report), threat_tag, reputation, hit_count, first_seen and last_seen. The reports entity stores device_id, report_type (scam or false_positive), text_hash, url_hash and created_at. A unique index on the combination of hash and type ensures that indicators arriving from several sources merge into a single row, incrementing hit_count and retaining the highest reputation observed. On the device, a local scan history stores each Scan and its ScanResult so that the dashboard and the offline path work without network access.

The third entity, user_profiles, backs the optional functionality of UC-13 and is genuinely optional: it stores user_id, device_id, display_name (nullable), email (nullable, unique), notification_prefs (a JSONB column holding alert_threshold, retroactive_updates, report_outcomes and digest_frequency), total_scans, total_reports, created_at and last_active. The device_id column now present on both reports and user_profiles is an anonymised identifier generated on the client at first launch, whether or not a profile is ever created; a profile carries this identifier as a reference rather than owning the scan or report rows outright. Consequently a user's scan and report history survives deleting their profile, and a profile created after weeks of anonymous use immediately inherits the totals already associated with that device (FR-14, FR-16). The trusted contact number used by the guardian-alert requirement (FR-09) is stored only in local application storage on the device itself; it is never transmitted to or persisted in the Supabase database, keeping the single most sensitive field entirely off the server.

The training dataset is the UCI SMS Spam Collection, comprising 5,572 labelled English SMS messages, which exceeds the minimum of 500 samples set in OBJ-01. It is supplemented for qualitative testing with realistic South African impersonation samples covering bank, revenue service and courier lures.

Data is exchanged through a REST interface over HTTPS. Inputs are JSON documents; outputs are JSON scoring payloads. Validation is enforced at the API boundary before any processing: message text must be between 1 and 2,000 characters, a URL between 4 and 500 characters, the sender at most 30 characters, and report_type must match either scam or false_positive. Requests failing validation are rejected with HTTP 422 and are never scored.

| **Endpoint**              | **Method** | **Purpose**                                                                | **Authentication** |
|---------------------------|------------|----------------------------------------------------------------------------|--------------------|
| /api/v1/score/sms         | POST       | Score message text with optional sender; returns the full scoring payload. | X-API-Key          |
| /api/v1/score/url         | POST       | Score a single URL independently of any message.                           | X-API-Key          |
| /api/v1/report            | POST       | Submit a scam or false-positive report; hashes and upserts indicators.     | X-API-Key          |
| /api/v1/analytics/summary | GET        | Return aggregate counters for the dashboard.                               | X-API-Key          |
| /api/v1/intel/ingest      | POST       | Trigger ingestion from the public threat feeds.                            | X-Admin-Key        |
| /api/v1/health            | GET        | Liveness check used by monitoring and the keep-alive workflow.             | None               |

Privacy requirements shape the storage design rather than being added to it. Message text is transmitted for scoring but never persisted on the server; only irreversible SHA-256 hashes of normalised indicators are stored, so the database cannot be mined to reconstruct the messages any user received. No personal identifiers, contact lists or account details are collected by default, and none are required to use any core detection or reporting function; a display name and email are stored only for the minority of users who deliberately opt into a profile through UC-13, and the one field with genuine third-party contact information, the guardian-alert number, is deliberately kept out of the database entirely by staying on-device. Row-level security confines all database access to the service key, and secrets are held in platform environment variables rather than in source control.

**5.2 Integration of the emerging-technology component**

The machine-learning component is integrated at a single point in the workflow: inside the scoring service, after request validation and rule evaluation, and before the threat intelligence lookup. This placement is deliberate. Keeping inference server-side means the model can be retrained and redeployed without shipping a new application build, and running the rule engine alongside it rather than instead of it preserves an explainable floor beneath every decision. The classifier receives the raw message text, transforms it with the fitted TF-IDF vectoriser combined with engineered structural features, and returns a probability. The hybrid scorer then fuses the two sub-scores, weighting the model at 0.6 and the rules at 0.4, and applies a critical override so that a decisive verdict from either layer cannot be diluted by a moderate verdict from the other.

**Pseudocode fragment: hybrid scoring and intelligence enrichment**

> FUNCTION score_message(text):
>
> rules \<- RuleEngine.extract(text) \# codes + rule_sub_score 0..100
>
> features \<- TFIDF.transform(text) + structural_features(text)
>
> ml_conf \<- MLClassifier.predict_proba(features) \# 0.0 .. 1.0
>
> risk \<- 100 \* (0.6 \* ml_conf + 0.4 \* rules.score / 100)
>
> IF MAX(100 \* ml_conf, rules.score) \>= 90 THEN \# critical override
>
> risk \<- MAX(risk, 100 \* ml_conf, rules.score)
>
> codes \<- rules.codes + ml_explanation(ml_conf)
>
> FOR EACH url IN rules.urls: \# threat intelligence
>
> match \<- IntelClient.lookup(SHA256(normalise(url)))
>
> IF match.type = 'url' THEN risk \<- MAX(risk, 90)
>
> IF match.type = 'domain' THEN risk \<- MIN(risk + 15, 100)
>
> IF match THEN codes.prepend('INTEL_MATCH', match.source)
>
> WHILE COUNT(codes) \< 3: codes.append(fallback_code()) \# FR-03 guarantee
>
> RETURN { risk_score: ROUND(MIN(risk, 100)),
>
> classification: label(risk),
>
> explanation_codes: codes,
>
> ml_confidence: ml_conf,
>
> rule_sub_score: rules.score,
>
> model_version: MLClassifier.version }

The interface contract between the mobile client and the scoring service is therefore fixed: a request of { text, sender } returns { risk_score, classification, explanation_codes\[{ code, detail }\], ml_confidence, rule_sub_score, model_version, latency_ms }. Because model_version is stamped on every response, any result observed during testing can be traced back to the exact model that produced it.

**5.3 Testing and evaluation plan**

**Functional testing**

Testing proceeds in four layers. Unit tests cover the rule engine, the hashing and normalisation logic and the fusion arithmetic, including a cross-module test asserting that the API and the ingestion pipeline hash identical input identically, because a silent divergence there would break every indicator match. Integration tests exercise the full request path from the API boundary through scoring to the database. Contract tests run the published Postman collection against each endpoint to confirm the response shape, authentication behaviour and validation rejections of FR-02. Widget and end-to-end tests on the mobile client verify that results render in the correct colour band and that the offline path of FR-06 behaves as specified. Every functional requirement from FR-01 to FR-10 maps to at least one test case, and its Given–When–Then acceptance criterion is the test oracle.

Performance figures are verified against the deployed instance rather than assumed. A latency harness samples response times across consecutive scoring requests to confirm NFR-01, and a propagation harness measures the interval between a report being accepted and the reported indicator influencing another user's score, confirming OBJ-03. Both values are stated in this document as targets and are confirmed during the pilot; the sub-millisecond inference figures quoted for ET-02 were measured against a local instance.

**Emerging-technology metric**

The primary machine-learning metric is the F1-score for the scam class on a held-out test set, chosen over plain accuracy because the class distribution is imbalanced and because both error types carry real cost: a missed scam exposes the user, while a false positive erodes trust in the warnings. The target set in ET-01 is 0.85. Model selection is performed by five-fold cross-validation across three candidate algorithms, and the selected model is then evaluated once on data it has never seen. Precision, recall and the confusion matrix are reported alongside F1 so that the balance between the two error types is visible rather than averaged away.

**User acceptance testing**

User acceptance testing is conducted as a supervised pilot with ten participants of mixed age and digital confidence, each using the application on a physical device. Participants complete scripted tasks: interpret a critical result, interpret a safe result, report a scam and locate the dashboard. Acceptance is measured against NFR-03, namely at least eight of ten participants correctly judging safety within five seconds, and is supplemented by a short post-task questionnaire on whether the explanation codes were understandable. Any explanation code that more than two participants cannot interpret is rewritten before final submission.

**Principal technical risk and mitigation**

| **Risk**                                                                                                                                                                                                                                          | **Likelihood** | **Impact**                                                                                                                                                    | **Mitigation**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| False positives on legitimate bank and one-time-PIN messages. Genuine banking SMS shares vocabulary with scam messages (account references, urgency, verification links), so the classifier can place authentic messages in the MEDIUM_RISK band. | Medium         | High. Users who receive incorrect warnings on real bank messages lose confidence and are likely to disable the application entirely, removing all protection. | Four controls operate together. Risk is presented in tiered bands rather than as a binary block, so a mid-range score produces a caution rather than an alarm. The in-app false-positive report of FR-07 feeds a labelled corrective signal back into the system. The rule engine is tuned so that recognised sender patterns for legitimate institutional traffic reduce rather than raise the rule sub-score. Finally, the confusion matrix is reviewed at every retraining cycle, with the false-positive rate treated as a release gate rather than as a secondary statistic. |

Secondary risks, namely free-tier instance cold starts, public feed downtime and dataset language coverage, are tracked in the project risk register and mitigated respectively by a scheduled keep-alive request, redundancy across two independent feeds, and the local rule engine, which continues to operate on messages the model generalises poorly.
