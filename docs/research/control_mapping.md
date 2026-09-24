# Finding-to-Control Mapping for an Indian Cyber Risk Platform: ISO 27001, NIST CSF 2.0, CIS v8.1, RBI and SEBI CSCRF (status as of 24 Sept 2026)

Build the platform on NIST CSF 2.0 as its backbone. It is free, public, machine-readable (JSON/Excel) and uses the same six-Function structure as SEBI's CSCRF. Map ISO/IEC 27001:2022 Annex A and CIS Controls v8.1 onto it by ID and short title only, because both are licence-restricted. The Indian layer has changed a lot. On 31 July 2026 RBI replaced its 2016 "Cyber Security Framework in Banks" with entity-specific "Cybersecurity, Technology: Risk, Resilience and Assurance Framework" Directions, which require reporting on DAKSH within six hours. SEBI's CSCRF has been clarified five times since August 2024, and in August 2026 its incident reporting portal moved to the FSB FIRE format. Neither RBI nor SEBI publishes a machine-readable control list.

## TL;DR
- **Frameworks:** Current versions are ISO/IEC 27001:2022 with Amd 1:2024 (climate clauses only; Annex A unchanged at 93 controls), NIST CSF 2.0 (6 Functions, 22 Categories, 106 Subcategories) and CIS Controls v8.1, currently published as v8.1.2 (18 Controls, 153 Safeguards; IG1 has 56). Only NIST is free to redistribute. CIS is CC BY-NC-ND 4.0, which bars commercial use. ISO is copyrighted and paywalled.
- **Indian regulators:**
  - RBI: the July 2026 Directions (e.g., RBI/DoS/2026-27/410 for commercial banks) require reporting on DAKSH within six hours of detection and notification to CERT-In. VA is half-yearly and PT annual for critical and DMZ systems, and DR drills are half-yearly.
  - SEBI CSCRF (SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113): a 6-hour email to SEBI and CERT-In, a 24-hour portal filing, then 3-, 7-, 30- and 75-day follow-ups.
  - CERT-In: 6 hours, running in parallel. DPDP: a 72-hour Board report once the breach rule commences (13 May 2027 on the 18-month clock in Rule 1(4)).
- **Import strategy:**
  - Ingest NIST CSF 2.0 from CPRT or the CSF 2.0 Reference Tool (JSON/Excel).
  - Use the Secure Controls Framework (CC BY-ND) or CISO Assistant (AGPLv3) as the crosswalk layer.
  - Store only IDs and short titles for ISO and CIS unless you license them. CIS commercial use needs a CIS SecureSuite or other licence.
  - Hand-build RBI and SEBI catalogues from the PDFs, citing paragraph and standard IDs.

## Key Findings

### 1a. ISO/IEC 27001 Annex A

| Item | Status (Sept 2026) | Confidence |
|---|---|---|
| Current edition | ISO/IEC 27001:2022 (third edition, 2022-10) | High |
| Amendment | ISO/IEC 27001:2022/Amd 1:2024 "Climate action changes" (2024-02). It adds one sentence to clause 4.1 ("The organization shall determine whether climate change is a relevant issue") and a note to 4.2. It does not change Annex A. | High |
| Newer revision | No verified source of a newer edition or a further amendment as of Sept 2026. Check the iso.org catalogue page for ISO/IEC 27001. | Medium (absence of evidence) |
| Themes / counts | Organizational A.5.1–A.5.37 (37), People A.6.1–A.6.8 (8), Physical A.7.1–A.7.14 (14), Technological A.8.1–A.8.34 (34). Total 93. | High (widely corroborated; verify against ISO OBP) |
| ID format | A.<theme>.<n>, e.g., A.8.8. In ISO/IEC 27002:2022 the same control is clause 8.8. | High |
| 2013 → 2022 | The 2013 edition had 114 controls in 14 domains (A.5–A.18). The 2022 edition merged many of them into 93 and added 11 new controls (e.g., A.5.7 Threat intelligence, A.5.23 Cloud services, A.8.9 Configuration management, A.8.12 Data leakage prevention, A.8.16 Monitoring activities, A.8.23 Web filtering, A.8.28 Secure coding). ISO/IEC 27002:2022 Annex B gives the official 2013↔2022 correspondence tables, which are paywalled. | Medium–High (verify the new-control list) |

Technological controls most relevant to technical findings are listed below as IDs and short titles only. They are taken from ISO/IEC 27002:2022 titles, reproduced from knowledge rather than fetched from ISO, so verify them against the ISO Online Browsing Platform (OBP).

| ID | Title | Typical findings |
|---|---|---|
| A.8.1 | User endpoint devices | Unmanaged or unencrypted endpoints |
| A.8.2 | Privileged access rights | Excess admin accounts |
| A.8.3 | Information access restriction | Public S3/blob buckets, open shares |
| A.8.5 | Secure authentication | Missing MFA, weak auth on exposed services |
| A.8.7 | Protection against malware | EDR/AV absent |
| A.8.8 | Management of technical vulnerabilities | Unpatched CVEs, KEV exposure |
| A.8.9 | Configuration management | Misconfigurations, default creds, CIS-benchmark drift |
| A.8.12 | Data leakage prevention | Exposed data stores, leaked secrets |
| A.8.13 | Information backup | No or untested backups |
| A.8.15 | Logging | Missing CloudTrail/audit logs |
| A.8.16 | Monitoring activities | No SIEM/alerting |
| A.8.17 | Clock synchronization | NTP drift (relevant to CERT-In NTP rule) |
| A.8.20 | Networks security | Open ports, exposed RDP/SSH/DB |
| A.8.21 | Security of network services | Insecure exposed services |
| A.8.22 | Segregation of networks | Flat networks |
| A.8.24 | Use of cryptography | Weak TLS, expired or self-signed certs |
| A.8.25–A.8.29 | Secure development life cycle … Security testing in development and acceptance | App vulns, secrets in code |
| A.8.32 | Change management | Unauthorised config changes |

Also relevant from outside A.8: A.5.15 Access control, A.5.17 Authentication information, A.5.18 Access rights, A.5.23 Information security for use of cloud services, A.5.24–A.5.28 (incident management), and A.5.7 Threat intelligence.

**What is freely available:** the clause and control titles are browsable in the ISO OBP preview (the free preview normally covers the foreword, introduction and scope, not Annex A in full). The ISO catalogue page and national-body previews (e.g., SIS, ANSI webstore, iTeh) are also free. The control text, attributes and guidance in 27001 Annex A and 27002 are copyrighted and sold per user. Do not reproduce control wording. IDs plus your own paraphrased descriptions are the common industry practice, but get legal advice before relying on it.

### 1b. NIST CSF 2.0

Published 26 February 2024 as NIST CSWP 29. There are 6 Functions, 22 Categories and 106 Subcategories. Subcategory IDs use the form FUNCTION.CATEGORY-NN (e.g., GV.OC-01, PR.AA-01).

| Function | Categories (IDs) | # |
|---|---|---|
| Govern (GV) | GV.OC Organizational Context; GV.RM Risk Management Strategy; GV.RR Roles, Responsibilities & Authorities; GV.PO Policy; GV.OV Oversight; GV.SC Cybersecurity Supply Chain Risk Management | 6 |
| Identify (ID) | ID.AM Asset Management; ID.RA Risk Assessment; ID.IM Improvement | 3 |
| Protect (PR) | PR.AA Identity Management, Authentication & Access Control; PR.AT Awareness & Training; PR.DS Data Security; PR.PS Platform Security; PR.IR Technology Infrastructure Resilience | 5 |
| Detect (DE) | DE.CM Continuous Monitoring; DE.AE Adverse Event Analysis | 2 |
| Respond (RS) | RS.MA Incident Management; RS.AN Incident Analysis; RS.CO Incident Response Reporting & Communication; RS.MI Incident Mitigation | 4 |
| Recover (RC) | RC.RP Incident Recovery Plan Execution; RC.CO Incident Recovery Communication | 2 |

**Differences from CSF 1.1:**
- Govern added as a sixth Function.
- Scope widened from critical infrastructure to all organisations.
- 23 Categories became 22, and 108 Subcategories became 106.
- Supply-chain outcomes moved into GV.SC, and the new PR.PS and PR.IR Categories replaced the old PR.IP, PR.PT and PR.MA.
- Implementation Examples and Informative References moved online, and Tiers were reframed.
- Withdrawn IDs (e.g., the 1.1 PR.AC-x, DE.CM-8, RS.RP-01) remain in NIST data as "withdrawn". Filter them out on import.

### 1c. CIS Critical Security Controls

| Item | Status | Confidence |
|---|---|---|
| Current version | v8.1, released June 2024. The document CIS currently distributes is labelled v8.1.2 (March 2025), with typo and glossary fixes. There is no verified source of a v9 as of Sept 2026. | Medium–High |
| Controls / Safeguards | 18 Controls, 153 Safeguards (unchanged from v8). ID format "Control.Safeguard", e.g., 6.3. | High |
| IGs | IG1 = 56 Safeguards ("essential cyber hygiene"). IG2 = IG1 + 74 (130 in total, per Compliance Manager GRC's CIS v8.1 page; one vendor, verifywise.ai, gives 131). IG3 = all 153. | High for 56; confirm 74/130 against the CIS XLSX |
| Security functions | Govern, Identify, Protect, Detect, Respond, Recover. Govern was added in v8.1 to align with CSF 2.0. | High |
| Asset classes | Devices, Software, Data, Users, Network, Documentation. Documentation was added in v8.1, making six. | Medium–High |
| Licence | CC BY-NC-ND 4.0. Non-commercial use only, no derivatives. Commercial use requires CIS SecureSuite membership or a separate licence. | High |

**The 18 Controls:**
1. Inventory and Control of Enterprise Assets
2. Inventory and Control of Software Assets
3. Data Protection
4. Secure Configuration of Enterprise Assets and Software
5. Account Management
6. Access Control Management
7. Continuous Vulnerability Management
8. Audit Log Management
9. Email and Web Browser Protections
10. Malware Defenses
11. Data Recovery
12. Network Infrastructure Management
13. Network Monitoring and Defense
14. Security Awareness and Skills Training
15. Service Provider Management
16. Application Software Security
17. Incident Response Management
18. Penetration Testing

### 1d. Official crosswalks

| Crosswalk | Source | Notes |
|---|---|---|
| CSF 2.0 ↔ SP 800-53 r5, CIS v8, ISO 27001:2022 and others | NIST CSF 2.0 Informative References (direct Excel download, CSF 2.0 Reference Tool, OLIR) | Which third-party mappings (e.g., CIS, ISO) appear depends on what has been submitted to OLIR. Check the current OLIR catalogue. |
| CIS v8.1 ↔ NIST CSF 2.0 | Built into the CIS v8.1 Safeguard spreadsheet (security-function column), plus CIS mapping documents | CIS licence applies |
| CIS v8/v8.1 ↔ ISO 27001:2022 | CIS mapping downloads | Verify the version on cisecurity.org |
| SCF ↔ 200+ frameworks, incl. ISO 27001/27002, CSF 2.0, CIS v8.1 | Secure Controls Framework, using the NIST IR 8477 STRM method. SCF is a NIST OLIR participant. | STRM PDFs are free; the Excel bundle is paid ($25) |

### 1e. Worked finding-to-control mapping

Starter mapping. Validate every row with an assessor before use.

| Finding | ISO 27001:2022 | NIST CSF 2.0 | CIS v8.1 | RBI 2026 Directions (CB) | SEBI CSCRF |
|---|---|---|---|---|---|
| Open / unnecessary ports, exposed RDP/SSH/DB | A.8.20, A.8.21, A.8.22 | PR.IR-01, PR.PS-01, ID.AM-03 | 4.4, 4.5, 4.8, 12.x, 13.x | Ch. V baseline (network security); VA/PT para 151 | DE.CM.S5 (VAPT scope); ID.AM.S1/S4 (critical systems incl. internet-facing) |
| Missing MFA | A.8.5, A.5.17 | PR.AA-03, PR.AA-01 | 6.3, 6.4, 6.5 | Ch. V access controls (MFA for privileged and critical systems) | PR.AA family. No verified specific standard ID for MFA. |
| Unpatched CVEs | A.8.8, A.8.19, A.8.32 | ID.RA-01, PR.PS-02, ID.RA-08 | 7.1–7.7 | Ch. V patch/vulnerability management; VA/PT para 151 | PR.MA.S3 (patch management timelines and policy) |
| Weak TLS / bad certs | A.8.24, A.8.21 | PR.DS-02 | 3.10, 12.6 | Ch. V cryptographic controls (2023 MD para 16 equivalent) | PR.DS family. No verified specific ID. |
| Exposed S3 / public storage | A.8.3, A.8.12, A.5.23, A.8.9 | PR.DS-01, PR.AA-05, PR.PS-01 | 3.3, 4.1, 3.x | Ch. V data security / cloud | PR.DS.S1–S3; Annexure-J (cloud) |
| Missing logging / monitoring | A.8.15, A.8.16, A.8.17 | PR.PS-04, DE.CM-01/-03/-09, DE.AE-03 | 8.2, 8.5, 8.9, 8.11 | Ch. V SOC/SIEM log collection (2023 MD para 15 audit trails) | PR.AA.S8–S9 (log management and retention); DE.CM.S3 (SOC) |
| No asset inventory | A.5.9 | ID.AM-01/-02 | 1.1, 2.1 | Ch. V inventory management | ID.AM.S1, ID.AM.S4, ID.AM.S6 |

RBI paragraph numbers for the 2026 Directions were checked only against a third-party copy of the text (see Caveats). RBI's 2016 Annex 1 baseline control numbering: no verified item-level source was retrieved, so do not hard-code those IDs.

## Details: Indian Regulatory Frameworks

### 2a. RBI

| Instrument | Reference / date | Status Sept 2026 | Key reporting content |
|---|---|---|---|
| Cyber Security Framework in Banks | RBI/2015-16/418, DBS.CO/CSITE/BC.11/33.01.001/2015-16, 2 June 2016. Annex 1 baseline controls; Annex 2 C-SOC / CCMP; Annex 3 incident reporting template. | Reported as repealed for commercial banks on 31 July 2026 (see below). Keep it as a legacy mapping for audit history. | Report all unusual incidents, successful or attempted. Annex 3 template: "Security Incident Reporting (SIR) to RBI (within two to 6 hours)". Gap assessment was due by 31 July 2016. |
| Master Direction on IT Governance, Risk, Controls and Assurance Practices | RBI/2023-24/107, DoS.CO.CSITEG/SEC.7/31.01.015/2023-24, 7 Nov 2023; effective 1 Apr 2024 | Superseded by the 2026 Directions for the entity classes they cover (the repeal Annex was not retrieved) | Para 26: VA half-yearly, PT annually for critical and DMZ systems. Para 29: half-yearly DR drills. Para 27: report incidents to CERT-In and RBI with no fixed hour limit. |
| Outsourcing of IT Services MD | 10 Apr 2023 | Reportedly consolidated into RBI (Commercial Banks – Managing Risks in Outsourcing) Directions, 2025 (RBI/DOR/2025-26/171, 28 Nov 2025). Existing IT outsourcing agreements had until 10 Apr 2026 to comply. | Third-party / vendor controls |
| Cyber Resilience and Digital Payment Security Controls for non-bank PSOs | RBI/DPSS/2024-25/123, 30 Jul 2024 | No evidence of replacement. Phased deadlines: large PSOs 1 Apr 2025, medium 1 Apr 2026, small 1 Apr 2028. | Incident reporting per the MD |
| **Cybersecurity, Technology: Risk, Resilience and Assurance Framework Directions, 2026** | 31 July 2026. Commercial Banks: RBI/DoS/2026-27/410, DoS.CO.CSITEG.4/31.01.015/2026-27. Reported siblings: SFBs /419, Payments Banks /428, UCBs /437, AIFIs /456, NBFCs /461, CICs /470. | In force immediately; no transition window | Para 182: "report cyber incidents within six hours of detection on DAKSH platform … also pro-actively notify CERT-In". Para 151: VA ≥ 6-monthly and PT ≥ 12-monthly for critical and DMZ customer-facing systems. Para 165: DR drills ≥ half-yearly. Para 230: repeals "existing Directions … relating to Cybersecurity Framework and IT Governance as applicable to Commercial Banks" via circular DoS.CO.PPG.66/11.01.005/2026-27. |

**Interpretation:**
- For banks and NBFCs the live clock is now DAKSH within 6 hours, not the old "2–6 hours".
- The 2026 text gives no hour limit for CERT-In. CERT-In's own 2022 Directions still impose six hours, so the platform should start both clocks at detection.
- Securitybrigade.com and Matrixgard (citing SCC Online and CorpLawUpdates) report that the covering repeal circular, RBI/DoS/2026-27/221, "retired 628 circulars with immediate effect" and that the Department of Supervision "issued 64 Directions". These are secondary sources; neither figure has been checked on rbi.org.in.
- Local Area Banks and RRBs are outside this family.
- The NBFC sibling (RBI/DoS/2026-27/461, DoS.CO.CSITEG.55/31.01.015/2026-27, 31 Jul 2026, as quoted by Taxguru) uses the same clock in para 141: "The NBFC shall report cyber incidents to RBI within six hours of detection on DAKSH platform… shall also pro-actively notify… CERT-In". Separate "(Digital Payment Security Controls) Directions, 2026" were also issued that day to several of the same entity classes.

### 2b. SEBI CSCRF

**Structure:**
- The framework is aligned to the NIST CSF Functions (GV, ID, PR, DE, RS, RC). It sets out cyber resilience goals, standards with IDs such as PR.MA.S3, DE.CM.S5 and GV.SC.S2, guidelines with page references, and Annexures.
- Annexures verified by reference: A and B (VAPT and cyber audit report formats), J (cloud), K (Cyber Capability Index), L (VAPT scope), N (SOC efficacy), O (incident classification and handling).
- It supersedes earlier SEBI cyber circulars.

**Categories:** MIIs, Qualified REs, Mid-size, Small-size and Self-certification REs. Category is fixed each financial year on the previous year's data.

**Entities covered (per the Aug 2025 addressee list):** AIFs, BTIs/SCSBs, clearing corporations, CIS, CRAs, custodians, debenture trustees, depositories, DDPs, DPs, IAs/RAs, KRAs, merchant bankers, MFs/AMCs, portfolio managers, RTAs, stock brokers, stock exchanges and VCFs.

| Date | Circular | Content |
|---|---|---|
| 20 Aug 2024 | SEBI/HO/ITD-1/ITD_CSC_EXT/P/CIR/2024/113 | CSCRF issued |
| 31 Dec 2024 | …/P/CIR/2024/184 | Clarifications. Data localisation placed in abeyance. |
| 28 Mar 2025 | …/P/CIR/2025/45 | Extension; MIIs, KRAs and QRTAs to comply by 30 Jun 2025 |
| 30 Apr 2025 | …/P/CIR/2025/60 | Revised category thresholds (brokers, AIFs, KRA recategorisation, etc.) |
| 11 Jun 2025 | FAQs (CSCRF + cloud framework) | E.g., Q.60: small and self-certification REs with their own SOC may use it instead of onboarding to the Market-SOC |
| 30 Jun 2025 | …/P/CIR/2025/96 | Extension for all REs except MIIs, KRAs and QRTAs, reported as to 31 Aug 2025 |
| 28 Aug 2025 | …/P/CIR/2025/119 | Technical clarifications, summarised below |
| 24 Aug 2026 | HO/(449)2026-ITD-5_DIV1/I/19448/2026 (secondary source only); Press Release 51/2026 | Incident portal aligned to FSB FIRE with staged reporting; Cyber Suraksha Portal launched |

**What the 28 Aug 2025 technical clarifications changed:**
- Added the Principles of Exclusivity and Equivalence for REs under more than one regulator.
- Made mobile app guidelines and BAS/CART recommendatory rather than mandatory.
- Recast the RTO as a two-hour resumption objective, with RPO at 15 minutes.
- Made ISO 27001 recommended, not mandatory, for Qualified REs.
- Said REs must submit VAPT and audit summaries only in the CSCRF format and must not submit explicit vulnerabilities unless SEBI asks.
- Recategorised portfolio managers and merchant bankers.
- Required REs to follow the CERT-In Cyber Security Audit Policy Guidelines.

**Reporting requirements (secondary sources, consistent across several):**
- 6-hour email alert to mkt_incidents@sebi.gov.in and CERT-In. Brokers and DPs must also notify their exchanges or depositories.
- Portal filing on the SEBI incident reporting portal within 24 hours.
- Interim report at 3 days, mitigation update at 7 days, RCA at 30 days, and forensic/closure report up to 75 days.
- VAPT: closure of findings within 3 months of report submission. One source reports a 1-week window for high-severity unpatched findings (FAQ 17), so verify.
- Cyber audit by a CERT-In-empanelled auditor, with frequency set by category.
- CCI: third-party assessed half-yearly for MIIs; self-assessed by Qualified REs.

A reported May 2026 SEBI "AI advisory" (cyber-suraksha.ai task force) appears only in vendor blogs. There is no verified source; treat it as unconfirmed.

### 2c. CERT-In and DPDP overlap

| Regime | Trigger / clock | Recipient | Platform relevance |
|---|---|---|---|
| CERT-In Directions No. 20(3)/2022-CERT-In under s.70B(6) IT Act, 28 Apr 2022 | 20 listed incident types, numbered i–xx, from "Targeted scanning/probing of critical networks/systems" to attacks on AI/ML systems: report "within 6 hours of noticing such incidents or being brought to notice" (Direction ii). Logs kept "for a rolling period of 180 days … within the Indian jurisdiction" (Direction iv). Clocks synced to the NTP server of NIC or NPL (Direction i). | CERT-In | Applies to all service providers and body corporates, so every client. Findings on missing logs and NTP drift map directly to it. Details confirmed against the CERT-In Directions PDF on cert-in.org.in. |
| DPDP Act 2023 + DPDP Rules 2025 (notified as G.S.R. 846(E), 13 Nov 2025) | Personal data breach: tell affected Data Principals and the Data Protection Board without delay, then a detailed Board report within 72 hours (Rule 7). Under Rule 1(4), "Rules 3, 5 to 16, 22 and 23 shall come into force eighteen months after the date of publication", which puts Rule 7's start at 13 May 2027 (computed from dpdprules.org's transcription of the Gazette). | Data Protection Board + individuals | A bank's single incident may trigger RBI (6h), CERT-In (6h), SEBI (6h/24h) and later DPDP (72h). Model them as parallel clocks keyed to detection time. |

## Details: Machine-Readable Control Lists

| Framework | Official machine-readable? | Source | Format | Licence / terms | Caveats |
|---|---|---|---|---|---|
| NIST CSF 2.0 | Yes | CPRT (csrc.nist.gov/projects/cprt); CSF 2.0 Reference Tool; Informative References Excel (nist.gov/cyberframework/informative-references); OLIR (csrc.nist.gov/projects/olir) | JSON, Excel; OLIR JSON download endpoint | US Government work, generally public domain in the US (verify notices) | Strip withdrawn 1.1 IDs |
| NIST OSCAL content | Yes | github.com/usnistgov/oscal-content | OSCAL JSON/XML/YAML | Public domain / NIST terms | GitHub issue #311 reports deprecated CSF 2.0 items (e.g., RS.RP-01) in the catalog, so prefer CPRT as the source of truth |
| CIS Controls v8.1 | Yes (Excel), after registration | cisecurity.org/controls (download form); CSAT via SecureSuite | XLSX, PDF | CC BY-NC-ND 4.0; commercial use needs a CIS licence | Redistributing Safeguard text in a paid product is not permitted without a licence |
| ISO/IEC 27001:2022 | No official free list | ISO store / OBP | PDF (paid) | ISO copyright | Store IDs and titles only; license text via ISO or a national body if needed |
| Secure Controls Framework | Community | securecontrolsframework.com; github.com/securecontrolsframework/securecontrolsframework | Excel/CSV, OSCAL JSON | CC BY-ND 4.0 | STRM Excel is paid. ND means you may not redistribute modified versions of SCF itself, but mapping to it is fine. |
| CISO Assistant (intuitem) | Community | github.com/intuitem/ciso-assistant-community | YAML libraries (import from Excel) | AGPLv3 outside /enterprise; each library records its own copyright (ISO library: "See https://www.iso.org/standard/27001") | AGPL network-use obligations if you embed the code; library content does not override ISO or CIS rights |
| OpenCRE (OWASP) | Community | opencre.org | Web / API | Open source. Exact data licence not verified. | Coverage is AppSec-heavy; ISO 27001 links are topic-level |
| RBI Directions | No | rbi.org.in (HTML/PDF) | HTML/PDF | Government publication | No verified structured release; hand-build and key on paragraph number |
| SEBI CSCRF | No | sebi.gov.in circulars and FAQs | PDF | Government publication | No verified structured release; standard IDs (e.g., PR.AA.S8) are parseable from the PDF |

## Recommendations
1. **Canonical spine:** import NIST CSF 2.0 from CPRT as your internal taxonomy. Add SEBI CSCRF standard IDs as a child layer. They share Function codes, but CSCRF IDs like PR.MA.S3 are SEBI's own, so do not assume a 1:1 match with CSF Subcategories.
2. **Findings layer:** tag each scanner finding with CWE, CVE or CIS Benchmark rule IDs, then map it to CSF Subcategories. Derive ISO and CIS mappings through the NIST Informative References or SCF STRM, not by hand.
3. **ISO:** ship only control IDs, your own paraphrased descriptions, and a link to ISO. Require customers to hold their own copy of the standard. Get legal sign-off on using titles.
4. **CIS:** either buy a CIS commercial licence or SecureSuite arrangement, or display Safeguard IDs only with a link to CIS. Do not bundle the XLSX.
5. **RBI/SEBI:** build versioned catalogues with an effective-date field. Keep the 2016 and 2023 RBI instruments as retired versions. Add an incident-clock engine that runs RBI DAKSH 6h, CERT-In 6h, SEBI 6h/24h/3d/7d/30d/75d and DPDP 72h from a single detection time.
6. **Licensing risk ranking:** ISO highest, then CIS (NC-ND), SCF (ND, attribution) and CISO Assistant (AGPL code copyleft). NIST is lowest.

## Confidence and verification needed
- **RBI 2026 Directions:** reference numbers, paragraph numbers (151, 165, 182, 230) and quotes were checked only against a third-party copy (lexsite.com) and secondary sources. The rbi.org.in page for id=13643 returned the 2023 MD during research. Verify on rbi.org.in, and check the "Circulars Withdrawn" Annex to confirm that the 2016 circular and RBI/2023-24/107 are named. The repeal circular reference "RBI/DoS/2026-27/221" and the "628 circulars / 64 Directions" figures come only from Securitybrigade.com and Matrixgard (citing SCC Online and CorpLawUpdates), not from rbi.org.in.
- **RBI 2025 Outsourcing Directions** (RBI/DOR/2025-26/171) and whether they repeal the 10 Apr 2023 MD: secondary sources only.
- **PSO 2024 MD still in force:** inferred from absence of evidence.
- **SEBI:** the 31 Aug 2025 deadline, the 3/7/30/45/75-day follow-ups, the FAQ 17 one-week window, the 24 Aug 2026 FIRE circular number and the May 2026 AI advisory come from secondary sources. The 2024/113, 2024/184, 2025/45, 2025/60, 2025/96 and 2025/119 circulars and the 11 Jun 2025 FAQs were corroborated via NSE/NSDL/MSEI copies of SEBI circulars.
- **ISO:** all A.x titles and the list of 11 new controls are from knowledge. Verify on ISO OBP. There is no verified source on any 2025/2026 revision.
- **CIS:** IG2 = 74 additional / 130 cumulative (Compliance Manager GRC; verifywise.ai gives 131, so confirm against the CIS XLSX); the v8.1.2 date (March 2025); the specific Safeguard numbers in the mapping table.
- **CSF 2.0:** the specific Subcategory numbers in the mapping table (e.g., ID.RA-08, DE.CM-09).
- **CERT-In:** the 20 incident types (i–xx), 180-day log retention within India and the NIC/NPL NTP rule are confirmed against CERT-In Directions No. 20(3)/2022-CERT-In on cert-in.org.in.
- **DPDP:** G.S.R. 846(E) of 13 Nov 2025, Rule 7 and Rule 1(4)'s 18-month commencement (13 May 2027) are taken from dpdprules.org's transcription of the Gazette. Check the e-Gazette original.
- **Numbers to verify:** 93/37/8/14/34, 114, 11 new controls; 106/22/108/23; 153/56/74; 6h, 24h, 72h, 180 days; RTO 2h / RPO 15 min; SCF "1,500+ controls / 200+ frameworks" (marketing figures).

## Caveats
- The Sept 2026 developments (the RBI 2026 Directions and SEBI FIRE alignment) are very recent. Much of the commentary is vendor marketing, and the primary texts should be checked before building compliance logic on them.
- This report does not reproduce copyrighted ISO or CIS text beyond identifiers and short titles, and it is not legal advice on licensing.