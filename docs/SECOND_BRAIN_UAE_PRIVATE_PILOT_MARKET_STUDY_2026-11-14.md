# Second Brain — UAE Invite-Only Subscription Pilot
## Market, product, go-to-market, KPI, unit economics, API and release plan

**Decision memo | 14 November 2026 | Market: UAE, starting in Ajman/Dubai | Status: PROPOSAL — not deployed or commercially approved.**
**Owner:** Roben Edwan. **Target:** a private, mobile-friendly, one-page AI chat experience for 5–10 invited adults, initially marketed through personal trust and one shared link, not an app-store release.

> **Document boundary:** This is a secondary market research and source-code review with an executable test plan. There has been no UAE customer interview, no live production load test, no consumer billing test, no legal opinion, and no proof of special fine-tuning of the underlying model weights. All prices, goals, conversion rates and success thresholds proposed below are hypotheses unless explicitly sourced. No probability such as “70% chance of success” is evidence-based.

## 1. Executive decision

**Recommendation: conditional GO for a tightly controlled 30-day concierge pilot; NO-GO for exposing the existing Second Brain API or connecting outsiders to the owner's code knowledge base.** Start with 5 adult participants; expand to 10 only after all security, quality, legal and uptime gates pass. Charge **AED 49 per person per 30 days** as a test price, with manual renewal and clearly stated limits, only once the correct commercial activity and payment eligibility have been confirmed. Until then, use a free, private, non-production demonstration.

The product promise is **a candid Arabic/English AI discussion partner that remembers user-approved preferences and does not needlessly decline benign requests**. Do not promise “100% uncensored,” that answers are always correct, that conversation data never leaves the UAE, or that the platform is more intelligent than premium frontier models. Local memory and personalization are *future testable features*, not established capabilities of this customer-facing implementation.

**Why this may work:** high AI adoption, low marginal cost if existing local hardware can serve constrained traffic, personal trust and a demonstrable niche. **Why it may fail:** readily available free chat products, substantially stronger commercial models, limited 7B generation throughput, hosting uptime, safety exposure and lack of multi-tenant isolation in the current code.

## 2. What is actually in the repository (verified source review, not runtime verification)

| Evidence | Actual finding | Commercial implication |
|---|---|---|
| unified-llm-local/README.md | “Second Brain v4” is a self-evolving, code-focused knowledge base with chat, RAG, agent actions, Neon/project repositories and an existing web UI. | It is NOT an already isolated public consumer chatbot; reuse only audited parts. |
| api.py | FastAPI defines POST /api/chat, /api/search, /api/agent; GET /api/agent/stream, /api/memory, /api/projects, /api/system, plus POST /api/memory. No authentication dependency was observed on these handlers. | **BLOCKER:** do not expose these routes or the container to customers. |
| api.py chat handler | Every chat request retrieves code chunks, sends a “use provided code context; max 3 sentences” system prompt, and does not implement subscriber-specific conversation memory. | Not yet the general open-discussion value proposition. Need a distinct chat route and config. |
| api.py configuration | ALLOWED_ORIGINS defaults to “*”. API responses can show project paths, memories and diagnostics. | Block access by default; segregate data and infrastructure. CORS is not authentication. |
| docker-compose.yml | Port 8000 and 3000 host mappings; mounted developer project directories and shared service credentials; CHAT_MODEL configured as qwen2.5-coder:32b (contradicts simpler README defaults). | Never reuse the existing deployment directly; verify exact live model and memory/VRAM. |
| ui/index.html | A development web UI exists, with search, chat, memory and agent controls. | A one-page UI is feasible, but the existing UI is privileged/internal and unsafe to hand out. |
| local-llm-rig docs/MODEL_SELECTION.md (separate repo) | Benchmark on i7-8700 / GTX 1060 6 GB / 32 GB, Sept 2026: measured 23.8 output tokens/s for qwen2.5:7b and abliterated variant, on one machine; a 15-prompt lawful “false refusal” set produced 0/15 refusals for both variants, but the abliterated variant generated shorter replies. | Do not claim “uncensored accuracy” or multi-user capacity from this narrow benchmark. Re-test the actual proposed model under concurrent load. |
| personal-ai-core/README.md (separate repo) | A CLI-oriented AI core and scoped memory design exists; model selector is configurable and deployment is local-first. | Potential reuse after an isolation and licensing design review; NOT evidence that multi-tenant subscription service already exists. |
| Code/model provenance | This repo includes orchestration, retrieval, prompts and configuration. Reviewed files do not substantiate proprietary weight fine-tuning or dedicated model training. | Market the complete customer experience, never claim a newly trained foundation model without training artifacts, base/adapter lineage and repeatable evaluation. |

**Critical separation:** A customer must never query the existing chunks_v4, owner memory, personal project roots, agent endpoints, shell tools or developer telemetry. A customer-facing gateway should communicate with a separate, minimally privileged Ollama inference endpoint only. No link to the live development services.

**Repository evidence links:**
- https://github.com/Binz2008-star/unified-llm-local/blob/master/README.md
- https://github.com/Binz2008-star/unified-llm-local/blob/master/api.py
- https://github.com/Binz2008-star/unified-llm-local/blob/master/docker-compose.yml
- https://github.com/Binz2008-star/unified-llm-local/blob/master/ui/index.html
- https://github.com/Binz2008-star/local-llm-rig/blob/main/docs/MODEL_SELECTION.md
- https://github.com/Binz2008-star/personal-ai-core/blob/main/README.md

## 3. UAE market evidence, scope and uncertainty

**Demand signals from external sources:**
- DataReportal Digital 2026 reports approximately **11.3 million UAE internet users and 99.0% internet penetration** in late 2025. High reach is not proof of willingness to pay for another chatbot. [S1]
- Deloitte's 2025 UAE/Saudi digital consumer study surveyed **2,000 people aged 18–50 across two countries**; **58% of those combined respondents** reported having used GenAI tools. Do not mislabel the combined 58% as the UAE-only result. The study flags privacy and subscription cost concerns. [S2]
- KPMG/University of Melbourne, reported 9 October 2025, found **97% of surveyed UAE respondents used AI** for work/study/personal purposes; **84% said trustworthy use would increase their confidence**. This is a survey of respondents, not a census or a paid-chat purchase rate. [S3]
- Microsoft AI Economy Institute reported **64.0% of the UAE working-age population using AI in H2 2025** under its own adoption method. Different studies use different populations and definitions; do not combine rates into a single market-size estimate. [S4]

**Competitor reference as checked 14 Nov 2026:** ChatGPT Plus lists **USD 20/month** [S5] and Claude Pro **USD 20/month on monthly billing** [S6]. Both have free tiers; real local invoices, taxes, FX conversion and features may differ. The proposed **AED 49/month** pilot is below roughly AED 73.45 for a USD 20 reference using AED 3.6725 per USD, but the products are **not capability-equivalent**. The low price tests perceived differentiation, not performance parity. No credible UAE-specific willingness-to-pay data for “less restricted” personal chat was found in the cited sources.

**SAM/SOM discipline:** UAE internet users are not the serviceable market. We do NOT invent an addressable-user total. The first reachable market is the founder's **30 personally invited relevant adult contacts**. First-month serviceable objective: 5 paid customers; later 10. Validate paid demand before broader market sizing.

### Initial customer hypotheses (not observed demand)

| Segment | Job-to-be-done | Value proposition to test | Sales risk |
|---|---|---|---|
| Arabic-speaking independent professionals, 25–40, UAE | Brainstorm, write, challenge ideas without formulaic replies | Direct, clear Arabic, follow-up context | Already have free alternatives; quality mismatch |
| Creators and freelancers, 21–40 | Candid creative drafts and counterarguments | Adjustable tone, fewer unnecessary refusals on legal fiction | Inconsistent length or hallucinations |
| Privacy-conscious bilingual power users, 25–45 | Keep an assistant profile and handle Arabic/English | Clear consent and retention controls | Local hosting does not automatically mean secure/private |
| Curious AI hobbyists, 18+ | Compare response style and model limits | Invite-only beta and side-by-side evaluation | Novelty may not become repeat paid usage |

**Priority:** recruit 5 adults already using at least one AI assistant weekly and willing to compare outputs. Age 25–40 is a targeting hypothesis, **not** a measured result. No minors in the pilot. Exclude professional high-stakes medical/legal/financial advice as a marketed use case.

## 4. Differentiation and customer promise

**Candidate position:** “Second Brain Private — AI يحكي معك بصراحة، يفهم سؤالك بالعربي والإنجليزي، ويساعدك تفكر من زاوية ثانية.”

- Sell **candour on lawful, controversial, creative and professional questions**, not “lawless AI.”
- Sell **customizable directness** with a clearly disclosed safety policy; safety boundaries still apply for harm, privacy violations and illegal instructions.
- Sell **personalization only after explicit consent and true per-user storage isolation**. User can inspect and delete saved memory; memories never influence another account.
- Sell **human-scale responsiveness** only during stated hours and only after real load tests. Do not promise 24/7 before it is measured.
- Demonstration should show side-by-side **five lawful tasks**: Arabic argumentative analysis, professional drafting, dark fictional writing, constructive criticism, bilingual follow-up; evaluate correctness, helpfulness and safety, not “refusal” alone.

**Marketing claim QA:** Ban “unlimited,” “zero filtering,” “complete anonymity,” “trained from scratch,” “100% private” or “better than ChatGPT” without relevant proof. Set user expectations on beta quality and generation limits.

## 5. Pilot product scope and architecture

**Minimal MVP visible to customer:** single mobile-first page, branded name, invite redemption/login, streaming chat, visible quota, model limitations notice, privacy/terms links, export/delete account request, basic feedback (“useful / not useful”), support contact. No public app store. Manual invitation and renewal for first cohort. No public access to dev tools or code search.

**Suggested isolation (DESIGN; not implemented):**

  Browser (HTTPS) → invite/auth & quota gateway → message/safety gate → isolated chat service → private Ollama model worker
                                  ↘ per-tenant conversation and consent store
                                  ↘ aggregate privacy-preserving metrics

- Deployment is its own new isolated application/container/network, with a separate database and no access to owner's Neon, projects, memory files, repository mounts or agent executors.
- Ollama binds privately (localhost or protected internal network). No open 11434 or existing 8000/3000 endpoints. Put TLS, auth, rate limits and resource quotas at the gateway.
- Persist users and messages separately using tenant_id/user_id from a *verified server-side session*, never a client-selected identity. No cross-user query. Enforce authorization at SQL query level and test isolation.
- Disable old /api/search, /api/memory, /api/projects, /api/system, /api/agent, /api/agent/stream and any shell ability in the customer-facing service. Better: do not mount their router at all.
- Server should restrict max request characters, maximum output tokens, queue length, simultaneous jobs, total daily tokens, idle session length and on-disk storage.
- A model may decline harmful output even if its weights have fewer built-in refusals. Put an input/output safety policy around the model, with careful handling of sensitive content. Do not log prompts or model outputs in analytics by default.
- Explicit deletion flow, consent for remembered preferences, privacy notice and minimal retention; HTTPS, rotating access keys, backups and recovery.
- Payment processor tokenizes card information. Never store raw card numbers. Verify signed payment webhooks, idempotency, entitlement lifecycle and expiration server-side.

**Interface contract:** a proposed non-production OpenAPI 3.1 contract lives in [SECOND_BRAIN_PILOT_OPENAPI_PROPOSAL.yaml](SECOND_BRAIN_PILOT_OPENAPI_PROPOSAL.yaml). It is a future API **design**, not a representation of deployed endpoints.

## 6. Experience limits to test first

Assume the documented GTX 1060 setup and the actual abliterated 7B variant **only as a test candidate**, not a verified currently running service. The September benchmark measured **23.8 generated tokens/s on the reference machine for that model**. A 400-token reply would require approximately **16.8 seconds just for generation** under the same throughput, excluding prompt ingest, queue and model cold start. Two simultaneous users may wait materially longer. Actual runtime can differ.

**Pilot caps (hypotheses; tune after measurements):** 1 active generation per user, 3 new messages/minute, 25 messages/user/day, 2,000 input characters, 512 max output tokens, max 5 pilot accounts initially, and a global queue capacity set by measured GPU memory. Errors should be surfaced clearly with retries and support. If the owner machine is only online for scheduled hours, sell explicit hours rather than promise 24/7 service.

**Gate before offering a paid link:**
1. Run a fresh benchmark on deployed hardware: GPU/CPU split, cold-start, 1/2/5 concurrent users, p50/p95 first token, full-response latency, 30-minute stability and downtime.
2. 40+ bilingual real-world benign task comparisons against an existing mainstream assistant; independent raters blinded where possible. Track length, accuracy, directness and false refusals. Include at least 20 safety/red-team cases and block known dangerous requests.
3. Verify 100% negative tests for unauthorized routes and cross-user chat/memory. Confirm no exposure of code chunks, owner profile, project metadata or credentials.
4. Run delete/export, backup recovery, webhook replay, refund/cancel, payment failure and rate-limit tests.
5. Confirm licensing/compliance; independent review if any sensitive data or additional UAE regulated verticals are involved.

## 7. Pricing and unit economics — scenario math, NOT profit forecast

**One plan only:** AED **49 / 30 days**, 18+, invite-only, 25 messages per day within fair-use limits, no auto-renewal during pilot, manual renewal after explicit customer agreement. This is an **experimental offer price**. If the correct licensed business and legal payment mechanism are not yet established, free trials only.

**Comparison floor:** ChatGPT Plus and Claude Pro at USD 20/month = approx AED 73.45 *before possible local taxes/FX fees*. Price below competitors alone is not differentiation.

Stripe's published UAE rate is **2.9% + AED 1 per successful domestic card transaction**, excluding possible other fees; use as a scenario, not proof that a Stripe account is eligible/connected. [S7]
- Processing fee at AED 49: **49 × 0.029 + 1 = AED 2.421 per payment**.
- Net cash after this payment fee, before infrastructure or refunds: **AED 46.579 per paid account-month**.
- 5 accounts = gross AED 245, estimated domestic-card fees AED 12.105, **AED 232.895** before operating costs.
- 10 accounts = gross AED 490, estimated domestic-card fees AED 24.21, **AED 465.79** before operating costs.

Illustrative planning scenarios below exclude licensing, taxes, founder time, support time, fixed device purchase/depreciation, internet plan, chargebacks, refunds and marketing costs. These omissions can overwhelm tiny pilot revenue.

| Scenario per 30 days | Paid users | Gross AED | Payment fees AED | Hypothetical platform/energy/backup AED | Balance before omitted items AED |
|---|---:|---:|---:|---:|---:|
| Local narrow pilot | 5 | 245.00 | 12.11 | 120.00 assumed, not measured | **112.89** |
| Local narrow pilot | 10 | 490.00 | 24.21 | 120.00 assumed, not measured | **345.79** |
| Dedicated cloud GPU always on | 10 | 490.00 | 24.21 | approx 714.00 GPU only | **-248.21** (before storage) |

Runpod displayed **RTX A5000 Pod USD 0.27/hour** on its pricing page updated 9 Nov 2026 [S8]; at 720 hours × 0.27 × 3.6725 ≈ **AED 714.04/month** purely for compute. It is a *pricing illustration*, not a tested suitable configuration, guaranteed availability or final bill. 4 operating hours/day over 30 days at the same hourly rate ≈ **AED 119** before storage/setup/idle/warm-up. Pricing changes; re-check before any spend. Reliable 24/7 GPU is economically difficult at 5–10 subscriptions priced AED 49.

**Contribution break-even formula:** ceil(monthly fixed costs / (price - payment fees - other variable cost/user)). With AED 120 assumed fixed cost and zero other variable cost, **ceil(120 / 46.579) = 3 users**; this is NOT true business break-even because license, time and other costs are excluded. Cloud compute AED 714 alone implies at least **16 users** at these assumptions, before any support, tax or storage. Any infrastructure spend requires an explicit monthly cap approved by the owner; initial recommended incremental spend target **AED 0–150/month only if achievable**, not a commitment.

**Commercial uncertainty:** no validated CAC or retention data exists. One month of five subscribers is a *demand signal*, not a profitability proof. Payment initiation may be contingent on a commercial license.

## 8. Acquisition and messaging: 30-day founder-led program

**Primary channel:** private, consent-based WhatsApp or direct personal introductions (no scraped lead lists, spam, mass messages or unsolicited automated calls). UAE is mobile-first; keep link, sign-up and chat optimized for phone.

**Cohort funnel with explicitly hypothetical targets:**
- 30 eligible adults personally invited → 12 express interest (40%) → 8 complete demo (67% of interested) → 5 opt for paid pilot (62.5% of demo) → 3 renew after 30 days (60% of the five).
- These are internal **planning targets**, NOT market benchmarks. Track the exact same people and denominators; 5 subscribers are too few for statistical confidence.
- A/B only two truthful propositions in personal outreach: A “عربي مباشر وإجابات أعمق”; B “خصوصية وتحكم بالذاكرة” (B only after verified). Track response and willingness to pay; don't A/B safety promises.
- Give 7 days of private, no-cost access to a limited demo only if operationally safe and legally permissible, then make the terms explicit. Avoid creating a billing obligation from a free invitation.
- Don't run paid ads until activation and repeat use are measured. Test actual landing page and 5-prompt demo first.
- Content: one 30–45s truthful screen demonstration, three side-by-side lawful use cases, clear limitations, invite-only signup and personal support. Avoid misleading “uncensored, no limits” hooks.

**Sample Arabic outreach text (opt-in contacts):**

“جرّب Second Brain Private: مساعد ذكاء اصطناعي عربي/إنجليزي، مصمم ليعطيك إجابات مباشرة ونقاشات مفيدة من دون رفض غير ضروري. عم نختبر نسخة خاصة مع عدد قليل من الأشخاص، وفي حدود استخدام واضحة لحماية الخصوصية والسلامة. إذا بتحب تشوف تجربة قصيرة وتقارن بنفسك، ببعثلك الرابط والتفاصيل.”

**Funnel instrumentation events:** invite_created → invite_redeemed → signup_completed → demo_started → first_meaningful_answer → day7_active → checkout_started → payment_confirmed → subscription_started → renewal_due → renewed/churned → support_ticket. Use random opaque user IDs and aggregate counts; no prompt content, phone numbers or emails in analytics.

## 9. KPI scorecard, precise definitions and decision gates

**North Star (pilot): 30-day paid renewals with satisfied, safely served use.** Usage alone is not business success.

| KPI | Definition / numerator & denominator | Proposed 30-day threshold | Actual baseline |
|---|---|---|---|
| Paid pilot customers | Unique users with confirmed settled first payment + active entitlement | 5 first; 10 only after gates | NOT MEASURED |
| Interest-to-demo | People who completed demo / people who expressed interest | ≥ 8/12 | NOT MEASURED |
| Demo-to-paid | Paid activated accounts / distinct completed demos | ≥ 5/8 | NOT MEASURED |
| Activation D7 | Paid users with ≥3 successful conversations in first 7 days / paid users eligible for 7-day observation | ≥ 4/5 (80%) | NOT MEASURED |
| Week-2 active | Paid users with ≥2 successful conversations during days 8–14 / eligible cohort | ≥ 3/5 | NOT MEASURED |
| D30 paid renewal | First-cohort paid accounts that explicitly pay for next 30 days / first-cohort accounts eligible for renewal | ≥ 3/5 (60%) | NOT MEASURED |
| Useful-answer rate | “Useful” feedback / all answered feedback (not total messages); report response coverage too | ≥ 80% of rated answers and ≥ 40% feedback coverage | NOT MEASURED |
| Bilingual eval pass | Human-rated helpful/correct/legal answers / evaluated bilingual prompts | ≥ 80% of 40+ benchmark prompts | NOT MEASURED |
| Safety critical failures | Confirmed unsafe harmful actionable answers and cross-tenant disclosures | **0**; any confirmed high severity stops pilot | NOT MEASURED |
| Unauthorized access tests | Blocked unauthorized/cross-tenant attempts / all negative access tests | **100% blocked** | NOT MEASURED |
| P95 end-to-end answer | 95th percentile among completed responses, measured server receive→final token; state token cap/load | ≤ 45s under verified 1-user load; adjust only with customer disclosure | NOT MEASURED |
| Request error rate | Failed non-user-cancelled chat requests / total eligible chat requests | < 3% during advertised hours | NOT MEASURED |
| Scheduled-hours uptime | Minutes health endpoint serves correctly / total advertised operating minutes | ≥ 95% initially; no 24/7 claim | NOT MEASURED |
| Contribution per user | AED 49 − actual payment fee − measured variable inference/hosting/refund allowance/user | > AED 0; require actual measurement | NOT MEASURED |
| CAC | Verified outbound/acquisition spending / newly paid acquired customers, including zero-paid as “undefined” not zero | Track; no paid acquisition until retention proven | NOT MEASURED |
| Complaint resolution | Support cases resolved within 48h / all cases due for resolution | ≥ 90%, with founder support capacity | NOT MEASURED |

**Metrics processing rules:** UAE local timestamps Asia/Dubai for reporting; store UTC in system. Include cohort start date, event taxonomy version, source and a clear “not measured” status. Never impute missing data as zero. Deduplicate users and transactions, exclude internal tests from public funnel; separate customer-initiated cancellation from payment failures. For 5 users one person moves renewal rate by 20 percentage points: explain instability. Use event-count audits and weekly manual reconciliation of billing vs entitlement.

**Pilot gate decision at 30–45 days:**
- **GO to 10 people:** zero confirmed privacy/critical safety incidents; billing and license cleared; ≥3/5 renew; ≥4/5 activate; useful feedback ≥80%; positive contribution after **actual** hosting fee (still before founder labour); uptime and latency targets met.
- **ITERATE:** reliability and safety secure but fewer than 3/5 renew or low usefulness; adjust positioning, UX and model before inviting more.
- **STOP:** any owner-data exposure, cross-account leak, unsafe tool execution, uncompensated customer charging, absent required licensing, or sustained negative economics without approved subsidy.

## 10. API product design: minimum stable customer contract

Full proposed request/response schemas and error codes: [SECOND_BRAIN_PILOT_OPENAPI_PROPOSAL.yaml](SECOND_BRAIN_PILOT_OPENAPI_PROPOSAL.yaml).

**Routes to BUILD in separate public service, not available now:**
- POST /v1/invitations/redeem — one-time signed invitation; validates age 18+ assertion and consent.
- GET /v1/me — authenticated account, entitlements, daily quota and scheduled service hours.
- POST /v1/conversations — create isolated user-owned conversation.
- POST /v1/conversations/{conversation_id}/messages — chat response, with idempotency, quota, server-side ownership, configurable output limit and audit-safe metadata.
- GET /v1/conversations/{conversation_id} — scoped history.
- DELETE /v1/conversations/{conversation_id} — delete messages/memories in that conversation.
- GET /v1/usage — permitted message count, remaining daily quota, report date.
- GET /v1/subscription — read plan, expiry and auto-renew=false.
- POST /v1/billing/checkout — hosted verified payment session for licensed seller.
- POST /v1/billing/webhooks/provider — verified signed external provider events, no anonymous entitlement grants.
- POST /v1/feedback — helpful/not-helpful, safe flags, no prompt copy.
- POST /v1/privacy/export — authenticated request for export.
- DELETE /v1/me — authenticated delete with confirmation challenge and retention exceptions documented.
- GET /health/live and GET /health/ready — publicly minimal, no project/PII/telemetry.

**Identity/security mechanics:** HTTPS; short-lived session / JWT; server-set tenant isolation; no API key in shared link; invitation single use, bound to destination identity; invite expires; abuse-resistant login; CSRF for cookie auth; strict CORS; IP/user rate limiting; per-account prompt budgets; payment webhook HMAC signature; Stripe or another PSP only after due diligence; structured request IDs; 401/403/404/409/422/429/503 expected semantics; 429 with Retry-After; 503 for full queue; no internal stack traces. API version independently from old Second Brain /api namespace.

**Events/measurement privacy:** aggregate count-only analytics without storing raw prompts. Use a private operational log with PII redaction and short defined retention; sensitive abuse handling follows applicable privacy rules.

## 11. Legal, consumer and platform gates in UAE (not legal advice)

This is a private invitation **commercial service**, not automatically exempt from business rules because only five people see it.
- UAE Government eCommerce guidance says online sales of services and subscriptions require an **appropriate licence** and cites Federal Decree-Law No. 14 of 2023. Verify the exact permitted activity, whether an existing licence covers SaaS and any emirate-specific e-commerce rules *before collecting money*. [S9]
- UAE consumer protection guidance requires accurate service details and terms; for UAE eCommerce providers, licensing details, Arabic service/contract/payment information and invoices are relevant. Clearly disclose caps, beta status, expiry, renewal, cancellation, refunds and support. [S10]
- UAE PDPL, Federal Decree-Law No. 45 of 2021, governs personal-data handling, rights and applicable consent/other lawful processing grounds; get UAE-specific counsel regarding data location, transfers, the controller/processor relationship and breach procedure. [S11]
- The UAE Government's AI charter emphasizes ethics, privacy and security. The public page for the National Cyber Security Policy for AI describes security and monitoring requirements; implement proportionate controls for a controlled pilot. [S12][S13]
- UAE Government VAT guidance lists **AED 375,000** annual taxable supplies/imports as the standard mandatory registration threshold for UAE-based businesses and **AED 187,500** as voluntary registration threshold (subject to current eligibility and other rules). Low turnover does NOT remove trade-licensing obligations. [S14]
- Ajman DED official licensing portal lists service details and fee categories, but **total licensing cost and activity classification are not established here**. Ask the DED for the actual activity fit and quote; don't assume an unrelated business licence covers subscription software. [S15]
- The upstream Qwen2.5-7B-Instruct card lists Apache-2.0; the third-party “abliterated” Ollama model has a warning that it is experimental and not suitable for all audiences. Review exact model artifacts and licenses before revenue. Open source does not eliminate data protection duties. [S16][S17]

**Operational must-haves:** adult-only eligibility; acceptable use policy; human escalation for abuse; clear privacy/deletion workflow; signed terms; receipts and cancellation; public business identity if required; no impersonation or false claims. No payments, ads or traffic exposure in this documentation task.

## 12. 30–45 day step-by-step execution, bounded by owner approvals

**Phase 0 — evidence + legal + safety gate (days 1–5):**
1. Inventory actual local models, hashes, weights provenance, runtime, OS, uptime and exact deployment configuration. Verify whether fine-tuning artifacts exist.
2. Check existing repo for a safe frontend component but keep all existing developer services private. Decide on license/activity and billing eligibility with DED/qualified adviser.
3. Write a separate threat model, privacy/retention policy, product use policy, testable acceptance cases and a no-owner-data exposure checklist.
**Exit:** all owner-data paths isolated, model baseline captured, legal payment gate known. Otherwise NO paid launch.

**Phase 1 — isolated demo (days 6–12):**
1. Build smallest *separate* HTTPS single-page customer chat + proposed minimal API, invite auth and quotas; no agent tools, shared knowledge retrieval or development telemetry.
2. Add consent, export/delete, safety behavior, health telemetry and billing-ready (but disabled) entitlement.
3. Run bilingual 40-prompt comparison and 20+ red-team checks, load/latency and unauthorized-access tests.
**Exit:** high-severity vulnerabilities zero, measurable uptime, costs and behavior.

**Phase 2 — 5-person controlled beta (days 13–30):**
1. Invite up to 30 known eligible contacts, offer fair demo, collect structured feedback and a price commitment.
2. If legal and technical gates pass, charge up to 5 at AED 49/30 days with transparent manual renewal. Otherwise no charges.
3. Reconcile daily dashboard for events, billing, cost, latency, safety and support.
**Exit:** 5 paid customers and 3/5 renewal intention or actual renewal when the cohort becomes due; actual confirmed payment is required for the final paid-renewal KPI.

**Phase 3 — validation (days 31–45):**
1. Measure the first cohort at eligibility for renewal; compare helpfulness and cost per full response.
2. Owner approval to expand, iterate or stop. Only then consider 10 users, a larger GPU, automatic billing, or public marketing.
3. Any merge/deploy/payment/purchase is separate and requires explicit authorization; this document only plans work.

### Effort and cost controls
- No new external infrastructure commitment or unreviewed library for the pilot until owner approval.
- No app-store packaging, enterprise dashboards, agents or fine-tuning jobs in initial scope.
- Keep original Second Brain developer instance untouched, and do not merge docs or code to the default branch without owner approval.
- Rollback: revoke customer invites, disable public gateway, preserve audit logs minimally, refund as required, stop paid onboarding, verify owner systems remain isolated.

## 13. Risk register

| Risk | Likelihood (assumption) | Impact | Mitigation & accountable role |
|---|---|---|---|
| Owner repository or personal memory data leak | High if existing API reused | Critical | Separate service/network/DB; test unauthorized routes; owner blocks launch |
| Harmful or illegal outputs from less-restricted model | Medium–high | High | Measured safety layer, strict acceptable use, monitoring, zero-critical-failure gate |
| Five users fail to renew | Medium–high | Business model | 30-day concierge pilot, side-by-side product value interviews, stop/iterate threshold |
| GPU queue, timeouts, home internet downtime | Medium–high | Revenue/trust | Concurrency and fair-use limits, advertised hours, p95 capacity testing |
| Subscription compliance/licence mismatch | Unknown | High | DED classification and qualified local adviser before payment |
| “Fine-tuned by us” / “private” claim unsupported | Medium | Reputation/legal | Audit weights lineage and actual storage before any promotional claim |
| Paid cloud costs exceed revenue | High for 24/7 dedicated GPU at 5–10 users | High | Pre-approved monthly cap, no always-on GPU at this price unless proven |
| Weak Arabic accuracy and generic 7B performance | Medium | Medium–high | Blind comparison, Arabic quality rubric and user feedback |
| Personal data mishandling/retention issues | Medium | High | Minimize collection, consent, per-user deletion/export, security review |

## 14. Research quality and what remains unknown

**What was directly reviewed:** default branch text of unified-llm-local (api.py, docker-compose.yml, README.md, ui/index.html, Security/inspection documents) and relevant separate repos for model evidence. **What was not tested:** deployed app, runtime network, actual env/secrets, exact live model, privacy isolation in production, payments, inference costs or true consumer demand.

**Primary research still required:** 10 qualitative interviews (five frequent AI users, five less-frequent) with the same standardized questionnaire; 5 blind side-by-side demos; record user consent and actual renewal decision. Never substitute the 97%/58% broad adoption surveys for a conversion estimate.

**Suggested interview questions (5 minutes):**
1. Which AI product do you use today and what do you pay for?
2. What was your last frustrating refusal, shallow answer or privacy concern?
3. Which of the five demo outputs is genuinely better, and why?
4. Would you still use Second Brain once curiosity fades? For what weekly task?
5. Would you pay AED 49 for 30 days with the specified limits? Why/why not?
6. Is your data sensitivity low enough for a beta? What deletion/control do you expect?

**Evidence quality hierarchy:** repo code/direct live tests > measured internal benchmarks with clear hardware/date > primary UAE official rules and platform prices > independent published consumer surveys > our planning assumptions. Do not treat hypothetical funnel results as collected data.

## 15. Sources and verification dates

**External evidence searched 14 Nov 2026; pricing changes and legal rules must be rechecked before commercial release.**
- **[S1]** DataReportal, “Digital 2026: UAE” — https://datareportal.com/reports/digital-2026-united-arab-emirates
- **[S2]** Deloitte Middle East, 2025 Digital Consumer Trends press release and methodology — https://www.deloitte.com/middle-east/en/about/press-room/deloitte-digital-consumer-trends-2025-report-reveals-ai-adoption-surge-social-commerce-boom-and-changing-digital-behaviors-in-the-uaeand-ksa.html
- **[S3]** KPMG UAE, 9 Oct 2025, “97% of UAE residents now use AI” (sample respondents) — https://kpmg.com/ae/en/media/press-releases/2025/10/97-percent-of-uae-residents-now-use-ai.html
- **[S4]** Microsoft AI Economy Institute H2 2025 — https://www.microsoft.com/en-us/corporate-responsibility/topics/AI-Economy-Institute/reports/Global-AI-Adoption-2025/
- **[S5]** OpenAI Help Center ChatGPT Plus price — https://help.openai.com/en/articles/6950777
- **[S6]** Claude pricing — https://claude.com/pricing
- **[S7]** Stripe UAE standard pricing — https://stripe.com/ae/pricing
- **[S8]** Runpod pricing, page dated 9 Nov 2026 — https://www.runpod.io/pricing
- **[S9]** UAE Government eCommerce and trading law overview — https://u.ae/en/information-and-services/business/ecommerce
- **[S10]** UAE Government consumer protection overview — https://u.ae/en/information-and-services/justice-safety-and-the-law/consumer-protection
- **[S11]** UAE Government PDPL overview — https://u.ae/en/about-the-uae/digital-uae/data/data-protection-laws
- **[S12]** UAE AI Charter — https://u.ae/en/about-the-uae/strategies-initiatives-and-awards/policies/Ai/The-UAE-Charter-for-the-Development-and-Use-of-Artificial-Intelligence
- **[S13]** UAE AI Cyber Security Policy overview — https://u.ae/en/about-the-uae/strategies-initiatives-and-awards/policies/cyber-activities/The-National-Cyber-Security-Policy-for-Artificial-Intelligence
- **[S14]** UAE Government VAT thresholds — https://u.ae/en/information-and-services/finance-and-investment/taxation/vat/valueaddedtaxvat
- **[S15]** Ajman DED licence service — https://media.ajman.ae/en/servicecatalog/services/2862
- **[S16]** Qwen2.5-7B-Instruct original model license — https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- **[S17]** Third-party abliterated model warnings — https://ollama.com/huihui_ai/qwen2.5-abliterate:7b

**Next decision the owner must make after reading:** Authorize, separately, a safe branch implementing a fully isolated demo; or stop before touching code. No customer deployment, payment collection, messaging or default-branch merge is authorized by this study.
