# Free Cyber-Risk Data and Loss Calibration for a FAIR Monte Carlo Prototype (Status as of 24 September 2026)

You can build a credible FAIR prototype entirely from free data, but do not treat NVD as your complete source of CVSS/CPE data: since April 15, 2026 NIST enriches only KEV-listed, federal-use and EO 14028 "critical software" CVEs by default, and marks everything else "Lowest Priority – not scheduled for immediate enrichment." Build your vulnerability layer on CVE.org/cvelistV5 (CNA scores + CISA-ADP/Vulnrichment), CISA KEV, FIRST EPSS and OSV/GitHub Advisories, and use NVD as one enrichment source among several. For loss magnitude, calibrate from populations that match your fictional firm: claims data (Coalition, NetDiligence) for SMEs, and Cyentia IRIS or IBM for large enterprises. Never average them together.

## TL;DR
- **NVD status (verified from NIST, April 15, 2026):** enrichment is now risk-triaged. KEV CVEs are targeted within one business day; federal-use and EO 14028 critical-software CVEs are prioritized; all others are "Not Scheduled." Unenriched backlog CVEs published before March 1, 2026 moved to "Not Scheduled." NIST no longer routinely adds its own CVSS score when the CNA supplied one. Enrichment is requested by emailing nvd@nist.gov. The only newer official development I found is an August 12, 2026 Federal Register RFI on NVD modernization (docket NIST-2026-0100, comments due October 13, 2026). The CVE Program itself was reported funded and stable as of March 2026.
- **Calibration:** use IBM Cost of a Data Breach 2026 (global mean $4.99M, 602 orgs) only as a large-enterprise, survey-based, mean-of-breach anchor. Use Coalition's 2026 Cyber Claims Report (average claim $116K; ransomware $269K) and NetDiligence's 2026 Cyber Claims Study (10,309 claims, 2021–2025) for insured SMEs. Use Cyentia IRIS 2025 (median about $3M, 95th percentile $32M, publicly reported incidents 2008–2024) for heavy-tail shape. These populations and loss definitions are incompatible. Pick one per firm-size segment.
- **Synthetic data:** generate a latent "security maturity" variable per business unit, derive correlated control scores from it, and draw asset counts and criticality from heavy-tailed distributions. Seed patch-latency and breach-cost distributions from published medians (DBIR 2026: median time-to-patch 43 days, secondary source) and validate the synthetic marginals against them. Use real-log datasets (Splunk BOTS v3, LANL, Splunk attack_data) and AD graph generators (adsimulator, BloodHound DBCreator) for realism, and Faker for identities. SDV is now Business Source License, not MIT.

## Key Findings

### 1. NVD: what changed, what it means, and what fills the gap

**Verified from the primary NIST announcement ("NIST Updates NVD Operations to Address Record CVE Growth," nist.gov, released April 15, 2026, updated April 17, 2026):**
- **Drivers:** CVE submissions grew 263% between 2020 and 2025. Q1 2026 submissions were "nearly one-third higher" than Q1 2025. NIST enriched "nearly 42,000 CVEs in 2025 — 45% more than any prior year."
- **Prioritized for enrichment from April 15, 2026:** (1) CVEs in CISA's KEV Catalog, with a goal of enrichment "within one business day of receipt"; (2) CVEs for software used within the federal government; (3) CVEs for critical software as defined by Executive Order 14028.
- **Everything else:** still added to NVD but labeled "Lowest Priority - not scheduled for immediate enrichment." Users can request enrichment by emailing nvd@nist.gov, and NIST will schedule "as resources allow."
- **CNA-supplied CVSS:** NIST "will no longer routinely provide a separate severity score" where the CNA already supplied one. You can request a NIST score by email.
- **Modified CVEs:** NIST now reanalyzes them only when a change "materially impacts the enrichment data." CVEs marked "Deferred" in 2025 moved to "Modified After Enrichment."
- **Backlog:** all backlogged CVEs with an NVD publish date before March 1, 2026 moved to "Not Scheduled." KEV CVEs were never in the backlog. NIST says it will consider enriching the older CVEs "as resources allow."
- **Documentation:** new status labels are defined on the NVD CVE statuses page (nvd.nist.gov/vuln/vulnerability-status). The workflow is described at nvd.nist.gov/general/cve-process, and the NVD Dashboard (nvd.nist.gov/general/nvd-dashboard) reports real-time status counts.

**Newer developments (April–September 2026):**
- **August 12, 2026:** NIST published a Federal Register RFI, "Request for Information (RFI) on Modernizing the National Vulnerability Database in the Age of Artificial Intelligence" (FR document 2026-16371, docket NIST-2026-0100). Comments are due October 13, 2026 via regulations.gov. This is a consultation, not a policy change. I found no official announcement after April reversing or extending the triage model.
- **Conflicting backlog size (flagged):** the Cloud Security Alliance research note (April 2026) says about 29,000 backlogged CVEs were reclassified. Semgrep's blog says "nearly 300,000." NIST's own announcement gives no number. Read the actual count from the NVD Dashboard before quoting either figure.
- **"15–20% of CVEs will be enriched" is an estimate** from CSA and vendor blogs, not a NIST figure.

**NVD API (verified from nvd.nist.gov/developers/start-here):** 5 requests per rolling 30 seconds without a key and 50 with a free key. NIST recommends sleeping between requests, doing an initial bulk pull with startIndex paging (2,000 results per page per API docs, secondary), then running incremental lastModStartDate/lastModEndDate syncs no more than once every two hours. The legacy JSON 1.1 feeds were retired in 2023 (secondary: Wazuh issue). Use API 2.0.

**What this means for your project (my assessment):**
- Any field you derive from NVD CVSS or CPE (likelihood of exploit, "vulnerability" in FAIR, asset-to-CVE matching) will be systematically missing for most non-KEV, non-federal software. The missingness is not random: it skews toward open-source libraries, niche vendors and pre-March-2026 CVEs.
- In a demo, NVD-only matching will under-count exposures on exactly the long-tail software a real SMB runs. Treat "NVD Not Scheduled" as a data-quality flag in your model rather than as "no vulnerability."
- Precedence rule: CNA CVSS (from the CVE record) → CISA-ADP/Vulnrichment CVSS → NVD CVSS → your own default prior. Log which source was used.

**Gap-fillers (verified unless flagged):**

| Source | Official location | Terms | What it gives you |
|---|---|---|---|
| CVE List V5 | github.com/CVEProject/cvelistV5 | CVE Program Terms of Use | Full CVE JSON 5 records incl. CNA CVSS/CWE and ADP containers; updated about every 7 minutes; baseline and hourly zip releases |
| CISA Vulnrichment | github.com/cisagov/vulnrichment | CC0-1.0 | CISA's ADP enrichment: SSVC decision points and, for some CVEs, CWE, CVSS, CPE, KEV |
| CISA KEV | cisa.gov/known-exploited-vulnerabilities-catalog; JSON at cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json; CSV at cisa.gov/sites/default/files/csv/known_exploited_vulnerabilities.csv; mirror github.com/cisagov/kev-data (CC0) | Public, no auth | Confirmed in-the-wild exploitation |
| FIRST EPSS | API base api.first.org/data/v1/epss; docs first.org/epss/api | Public, no auth | Daily 30-day exploitation probability and percentile; history back to April 14, 2021 |
| OSV.dev | api.osv.dev/v1/query, /v1/querybatch (up to 1,000), /v1/vulns/{id}; bulk gs://osv-vulnerabilities | No key; no documented rate limit | Aggregates GHSA, PyPA, RustSec, Go, Linux distros; per-record source license |
| GitHub Advisory Database | github.com/github/advisory-database | CC-BY 4.0 | Advisories in OSV format; GitHub-reviewed flag, CWE IDs, severity |
| VulnCheck KEV (Community) | vulncheck.com/kev | Free account; "prominent attribution to VulnCheck" | Larger exploited list than CISA KEV. The "3,700+ KEVs, ~175% more than CISA" claim (June 2025) is a vendor claim |
| EU Vulnerability Database (ENISA) | Launched (per CSO Online, March 2026, linking to the EC digital-strategy announcement) | Not verified | European identifier/database; the URL was not verified in this session |

**Flagged uncertainties:**
- **EPSS bulk CSV location.** The FIRST API page I fetched lists `https://epss.cyentia.com/epss_scores-YYYY-MM-DD.csv.gz`, but a search-indexed copy of the same page shows `https://epss.empiricalsecurity.com/...`. The host appears to be changing. Test both.
- **EPSS details not verified this session.** I did not confirm the current EPSS model version (v4 was the release current as of 2025, per my prior knowledge; unverified here) or an official API rate limit. Scores are published daily (secondary: multiple integrator docs).
- **GCVE not verified.** I did not verify GCVE (the Global CVE allocation system) in this session.

### 2. CISA KEV, MITRE ATT&CK, CVE Program

**CISA KEV:**
- **Fields (verified from the official CSV header):** cveID, vendorProject, product, vulnerabilityName, dateAdded, shortDescription, requiredAction, dueDate, knownRansomwareCampaignUse, notes, cwes. knownRansomwareCampaignUse takes "Known"/"Unknown" (secondary). GreyNoise reports the flag was added in October 2023 and that 59 entries silently flipped to "Known" during 2025. That makes it a lagging indicator.
- **Size:** not verified from CISA. Third-party Axis Intelligence reports 1,665 entries at catalog version 2026.08.11, up from 1,484 at end-2025. CISA alerts show at least 20 additions since then, most recently one on September 21, 2026 (CVE-2026-7273, Zyxel GS1900). The current count is probably about 1,685 or more (my estimate). Count the JSON before the demo.
- **Schema:** the CISA KEV catalog page links a "JSON Schema (updated 09-02-2026)" alongside its CSV and JSON feeds; I did not capture the exact schema URL.
- **Governance:** CISA's own page (cisa.gov/known-exploited-vulnerabilities-catalog/reducing-significant-risk-known-exploited-vulnerabilities) confirms that "Binding Operational Directive (BOD) 26-04: Prioritizing Security Updates Based on Risk, issued on June 10, 2026... carries forward the KEV catalog criteria from BOD 22-01." The Cloud Security Alliance says it "formally supersedes BOD 22-01 (2021) and BOD 19-02 (2019)." It sets remediation windows of 3, 14 or 60 days.

**MITRE ATT&CK:**
- **Version:** v19.0 was released April 28, 2026. The official ATT&CK website changelog shows content 19.1 (May 12, 2026) and **19.2 (August 6, 2026)**, so 19.2 is current.
- **Structure (secondary):** v19 split Defense Evasion into Stealth (keeps TA0005) and Defense Impairment (new TA0112). Enterprise has 15 tactics, 222 techniques and 475 sub-techniques (SCYTHE blog).
- **Not verified this session:** the STIX data location (the mitre-attack/attack-stix-data GitHub repo) and the Terms of Use text. ATT&CK has historically been offered royalty-free under MITRE's Terms of Use with attribution. Confirm on attack.mitre.org before redistributing.

**CVE Program:**
- **2025 background:** in April 2025 CISA exercised an 11-month option on its $57.8M MITRE contract, running to March 16, 2026 (The Record; Infosecurity Magazine).
- **Current status:** CSO Online (March 9, 2026) reports that CISA and MITRE renegotiated the contract. Board minutes from January 21, 2026 recorded "no funding cliff in March," and CISA acting director Nick Andersen told CSO the program "is fully funded." Sources say the funding has moved to a protected line in CISA's budget.
- **Caveats:** the contract terms are not public ("a mystery contract with a mystery number," per an anonymous source). The CVE Foundation still exists. I found no evidence of a disruption through September 2026.

### 3. Loss-calibration reports: what each measures

| Report (edition) | Official link | Population | Loss statistic | Headline numbers (verified unless flagged) |
|---|---|---|---|---|
| IBM Cost of a Data Breach Report 2026 (21st; Ponemon research, IBM analysis) | Newsroom: newsroom.ibm.com/2026-07-29-ibm-study-one-in-four-malicious-breaches-are-ai-enabled,-costing-companies-6-million-on-average; report hub via ibm.com | Survey/interview of 602 breached organizations, March 2025–Feb 2026 (secondary) | Mean total cost per breach, activity-based costing | Global mean $4.99M (+12%); AI-enabled malicious breaches about $6M (primary). US $11.5M; healthcare $6.64M; financial $6.29M; 247-day lifecycle; 63% of cost from detection/escalation + lost business (secondary). Report download has historically required registration (unverified this year) |
| Verizon 2026 DBIR (19th year of DBIR) | verizon.com/business/resources/reports/dbir/ | Breaches/incidents from Verizon + contributors, 2025 data | Frequencies/patterns, not dollar loss | Exploitation 31% of initial access (first time ahead of credentials); ransomware in 48% of breaches; third-party involvement 48% (+60%) (primary). Median time-to-patch 43 days, up from 32 (Tenable, secondary). 26% of KEVs fully remediated vs 38% (secondary) |
| Coalition 2026 Cyber Claims Report (released March 5, 2026) | Press release on GlobeNewswire; report via coalitioninc.com (URL not verified) | 100,000+ Coalition policyholders in five countries, mostly SMB, 2025 claims | Mean claim severity (insured loss) + frequency | Average claim $116K (−19%); frequency +3%; ransomware $269K; FTF $141K; BEC $27K; >$100M-revenue firms: 5× frequency, $268K average; 86% refused ransom. Claims rate 1.54% and 64% of closed claims with no out-of-pocket loss (Risk & Insurance, secondary) |
| NetDiligence Cyber Claims Study 2026 (16th; released September 16, 2026) | netdiligence.com/cyber-claims-study-2026-report/ (form-gated download per press release) | 10,309 insurer-contributed claims, incidents 2021–2025; SME = <$2B revenue | Mean total incident cost (crisis, legal, BI, recovery, ransom) | SMEs 97% of claims; large firms 3% of claims but 56% of costs; ransom demands up to $500M, payments up to $90M. The 2025 edition reported SME average $264K and large-company average $10.3M (Carrier Management, secondary). I found no 2026 per-claim averages. The Insurer (September 16, 2026) reports the average large company had $10.1B in revenue, "nearly 100 times the average SME's $105 million." It also reports 12 claims over $100M, 68 of $10M–$99M and 403 of $1M–$10M, and says ransomware plus BEC made up 51% of SME claims of $1,000 or more (about 64% in 2025 alone) |
| Cyentia IRIS 2025 (sponsored by CISA Office of the Chief Economist) | cyentia.com/publication/iris2025/; PDF cyentia.com/wp-content/uploads/2025/06/IRIS-2025.pdf | Publicly reported cyber events 2008–2024 (150,000+ incidents in the underlying dataset per the report text; IRIS 2022 used Advisen Cyber Loss Data) | Median and tail percentiles, and loss as % of revenue | Median loss rose from $190K (2008) to "almost $3 million"; tail (95th) $32M; pooled median about $600K; median loss 0.65% of revenue; top 5% exceed annual revenue. Kiteworks' webinar summary says "$3.2M median," which conflicts; use the PDF |
| FBI IC3 2025 Internet Crime Report | ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf (also fbi.gov/file-repository/2025_ic3report.pdf) | Complaints voluntarily reported to IC3, mostly individuals | Reported losses (sum) | 1,008,597 complaints; $20.877B losses (+26%); BEC 24,768 complaints and $3,046,598,558 in losses, second only to investment fraud's $8.65B (SOCRadar/HIPAA Journal, citing IC3); ransomware 3,611 complaints and $32.320M in losses, up 259% from $12.473M in 2024 (McDonald Hopkins/HIPAA Journal; the IC3 PDF says "more than 3,600 complaints… losses exceeding $32 million"). Ransomware losses exclude most downtime/response costs |

**Not verified in this session (re-check before citing):**
- **Other loss datasets:** Marsh, Munich Re, Chubb and Allianz reports; Advisen/Zywave loss data (commercial, licensed; IRIS 2022 was built on it); Privacy Rights Clearinghouse; state AG breach databases; SEC 8-K Item 1.05 filings (searchable via EDGAR full-text search).
- **HHS OCR breach portal (verified by subagent):** ocrportal.hhs.gov/ocr/breach/breach_report.jsf lists PHI breaches affecting 500+ individuals, with CSV export. Counts of 500/501 are often placeholders.

**Where the numbers disagree, and why (my analysis):**
- **IBM $4.99M vs Coalition $116K is a 40× gap, and it is expected.** IBM surveys breached, mostly large organizations and reports a mean that includes lost business (a secondary, reputation-type loss) estimated with activity-based costing. Coalition reports insured claim payouts for SMBs, dominated by high-frequency, low-severity BEC. That excludes uninsured losses, deductibles and most reputation effects.
- **IRIS median about $3M vs NetDiligence SME mean $264K.** IRIS draws on publicly reported events, which are biased toward large and newsworthy incidents. NetDiligence covers insured claims ≥$1K.
- **Means vs medians.** IBM, Coalition and NetDiligence mostly report means. IRIS reports medians and percentiles. For lognormal-like data the mean far exceeds the median, so never plug a mean in as a lognormal median.
- **IC3 ransomware losses ($32.320M total across 3,611 complaints)** are self-reported by victims and exclude most costs. Do not use them for magnitude.

**Mapping to FAIR loss forms (my mapping; the reports do not use FAIR terms):**

| FAIR form | Primary/secondary | Best source |
|---|---|---|
| Productivity | Primary | NetDiligence business interruption component; IBM lost-business (partly) |
| Response | Primary (and secondary for notification/legal) | NetDiligence crisis services; IBM detection & escalation, notification, post-breach response |
| Replacement | Primary | NetDiligence recovery costs |
| Fines & judgments | Secondary | NetDiligence legal/regulatory (large firms: legal/regulatory averaged over $22M per claim in 2026 edition, per press release) |
| Reputation / competitive advantage | Secondary | IBM lost business (customer churn), the only broad proxy; no clean public source |
| Ransom / fraud transfer (model as primary) | Primary | Coalition ransomware/FTF/BEC severities; IC3 BEC totals for frequency context |

**Heavy-tail fitting guidance (verified citations):**
- **Eling, M. & Wirfs, J. (2019). "What are the actual costs of cyber risk events?"** *European Journal of Operational Research* 272(3):1109–1119, DOI 10.1016/j.ejor.2018.07.021. The authors analyze 1,579 cyber incidents from an operational-risk database. They use a peaks-over-threshold method from extreme value theory to separate "cyber risks of daily life" from "extreme cyber risks." This supports a body-plus-tail (for example, lognormal body with a GPD tail) severity model.
- **Farkas, S., Lopez, O. & Thomas, M. (2021).** "Cyber claim analysis using Generalized Pareto regression trees with applications to insurance," *Insurance: Mathematics and Economics* 98:92–105 (seen in reference lists, secondary).
- **Eling & Wirfs (2015).** "Modelling and management of cyber risk," IAA Life Section Colloquium, Oslo (actuaries.org/oslo2015/papers/IAALS-Wirfs&Eling.pdf; secondary).
- **"Data breaches: Goodness of fit, pricing, and risk measurement,"** *Insurance: Mathematics and Economics* 75:126–136. The author was not confirmed in my sources.
- **Edwards, Hofmann & Forrest "Hype and heavy tails" (2016):** not verified this session.
- **Cyentia IRIS 2025** plots losses on a log scale with median/90th/95th percentiles. That is sufficient to back-solve lognormal parameters. For example, a pooled median of $600K and a 95th percentile of $32M imply σ ≈ ln(32/0.6)/1.645 ≈ 2.4 (my calculation).

### 4. Synthetic "fake company" data

**Verified tools and datasets (from subagent verification):**
- **Splunk attack_data** (github.com/splunk/attack_data, Apache-2.0): curated attack datasets.
- **Boss of the SOC v3** (github.com/splunk/botsv3, CC0-1.0): pre-indexed Splunk app of about 320 MB; needs Splunk. v1/v2 exist at github.com/splunk/botsv1 and /botsv2 (licenses not checked).
- **BloodHound DBCreator** (BloodHoundAD/BloodHound-Tools, LGPL-3.0): generates a random AD dataset into Neo4j. The legacy account is deprecated; the successor is SpecterOps/BloodHound CE (Apache-2.0).
- **adsimulator** (github.com/nicolas-carolo/adsimulator; license unverified): "inspired by DBCreator" with configurable probabilities, for example SPNs and pwdneverexpires. **ADSynth** (github.com/adsynthesizer/ADSynth, DSN 2024) benchmarks against both.
- **SDV** (github.com/sdv-dev/SDV): now Business Source License 1.1. Free except for offering a commercial synthetic-data service; each release converts to MIT after 4 years.
- **Faker** (github.com/joke2k/faker, MIT): names, emails, private IPs.
- **LANL "Comprehensive, Multi-Source Cyber-Security Events"** (csr.lanl.gov/data/cyber1/, CC0; Kent 2015, DOI 10.17021/1179829): 58 days, about 1.65B events across auth/proc/flows/dns/redteam. It is the best realism reference for authentication behavior.
- **CIC-IDS2017** (unb.ca/cic/datasets/ids-2017.html): redistribution allowed with citation of Sharafaldin et al., ICISSP 2018.
- **UNSW-NB15** (research.unsw.edu.au/projects/unsw-nb15-dataset): academic-only by default; the terms conflict across listings.
- **MITRE Caldera:** now Apache Caldera (Incubating), Apache-2.0, github.com/apache/caldera. It entered the Apache Incubator in December 2025.
- **Atomic Red Team** (github.com/redcanaryco/atomic-red-team, MIT).
- **FAIR-CAM** (FAIR Institute, launched October 2021): no public license found. It is proprietary/trademarked, but its control categories (Loss Event, Variance Management, Decision Support) are a sound schema for control-effectiveness fields.

**Published anchors for distributions (sourced):**
- **Patch latency:** median time-to-patch 43 days (DBIR 2026, via Tenable).
- **KEV remediation:** 26% of KEVs fully remediated (DBIR 2026, secondary).
- **Breach lifecycle:** 247 days (IBM 2026, secondary).
- **Claim frequency:** 1.54% annual claim frequency for insured SMBs (Coalition, secondary), with 5× frequency for firms above $100M revenue (Coalition).
- **Loss vs revenue:** median loss 0.65% of revenue (IRIS 2025).
- **Initial access mix:** exploitation 31% and credential abuse 13% (DBIR 2026 via Help Net Security).
- **Not found:** I found no verified public MFA-coverage or CIS/NIST CSF maturity distribution in this session, so treat any such number as an assumption.

**How to avoid "obviously random numbers" (my recommendations):**
1. **Latent maturity.** Draw a business-unit maturity score m ~ Beta(a, b), then derive each control's effectiveness as a logistic function of m plus noise. MFA coverage, EDR coverage, patch SLA adherence and backup testing then correlate, as they do in real firms.
2. **Heavy tails.** Draw assets per application, data records per system, and asset criticality from lognormal/Pareto distributions. A few "crown jewel" systems should hold most records.
3. **Patch latency.** Use a lognormal with a median of 43 days, and scale it by (1 − m) so that low-maturity units are slower. Make internet-facing assets faster, and KEV-listed CVEs faster still.
4. **Real CVE mix.** Attach real CVEs from KEV/EPSS/OSV to synthetic software inventories, so that EPSS scores and KEV flags are genuine.
5. **Realistic missingness.** Leave owner fields blank, stale "last seen" dates, and NVD "Not Scheduled" CVSS gaps. Correlate missingness with low maturity.
6. **Graph realism.** Use adsimulator/DBCreator for AD privilege paths, and derive "blast radius" features from the graph.
7. **Reproducibility.** Use a single RNG seed and a config file of every distribution parameter with its source.
8. **Validation.** Compare synthetic marginals (patch-time median, loss percentiles, claim frequency) against the published anchors above, and show the comparison table in the demo.

## Recommendations

**Free data stack for the hackathon:**
- **Core vulnerability data:** cvelistV5 (git clone) + Vulnrichment + CISA KEV JSON + EPSS daily CSV + OSV.dev API.
- **NVD:** API 2.0 with a free key, for CPE where available.
- **Threat context:** ATT&CK v19.2 STIX. Map techniques to Coalition/DBIR event types.
- **Synthetic environment:** Faker + adsimulator + your latent-maturity generator. Use BOTS v3 or LANL samples if you need log realism.

**Calibration table:**

| FAIR parameter | SMB (<$100M revenue) | Mid-market | Large enterprise (>$2B) |
|---|---|---|---|
| Loss Event Frequency | Coalition 1.54% claims rate (secondary) | Coalition (5× for >$100M) | IRIS 2025 annual incident probability by revenue tier |
| Primary loss magnitude (mean) | Coalition by event type ($27K BEC, $141K FTF, $269K ransomware) | NetDiligence SME average ($264K, 2025 edition) | NetDiligence large ($10.3M, 2025 edition) |
| Severity shape / tail | IRIS percentiles, rescaled | IRIS | IRIS median about $3M, P95 $32M; EVT tail per Eling & Wirfs |
| Secondary loss (reputation/fines) | Assume small; NetDiligence legal | NetDiligence legal/regulatory | IBM lost-business share; NetDiligence legal ($22M+ average at large firms) |
| Sanity check only | IBM $4.99M global / $11.5M US | — | IBM |
| Threat event mix | DBIR 2026, Coalition | DBIR 2026 | DBIR 2026 |

**Re-verify before the demo:**
1. NVD Dashboard counts of "Not Scheduled" CVEs, and any new NVD announcements after the RFI closes on October 13.
2. The current KEV count (count the JSON) and any BOD 26-04 deadline changes on cisa.gov.
3. The EPSS model version, the bulk CSV host (cyentia vs empiricalsecurity), and any API limits.
4. ATT&CK version (19.2 or later) and the attack-stix-data repo and Terms of Use.
5. IBM 2026 sample size and US figure from the actual PDF, not blogs.
6. NetDiligence 2026 SME and large-company averages from the PDF.
7. Licenses for adsimulator and BOTS v1/v2.
8. Terms and rate limits for the HIBP, Shodan, Censys, abuse.ch, AlienVault OTX, Exploit-DB, VCDB and CWE/CAPEC sources, none of which I verified in this session.

## Caveats
- **Secondary sources:** several headline figures come from vendor blogs or press coverage rather than the primary PDFs: the IBM US figure, the IBM sample size, DBIR patch time, the Coalition claims rate and the KEV count. They are marked "secondary."
- **Vendor data:** Coalition, NetDiligence and VulnCheck publish vendor datasets with selection bias toward their customers.
- **IBM is a survey:** its figures are modeled costs from interviews, not audited losses.
- **Recommendations vs facts:** all synthetic-data design advice and the FAIR mappings are my recommendations, not sourced standards.