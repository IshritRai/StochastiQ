# Building a FAIR-Based Cyber Risk Quantification MVP: Standard, Math, Vendors, and Open-Source Starting Points (verified as of 24 Sept 2026)

The Open FAIR standards (O-RT 3.0.1 and O-RA 2.0.1) give you a clear, citable recipe for an MVP. You take min / most-likely / max estimates at 90% confidence, turn them into distributions, and run a Monte Carlo simulation of annual loss. Expected Annual Loss is the mean of the simulated distribution. "VaR" is a percentile of it, such as the 95th. Controls are modelled as changes to specific FAIR factors, which is the basis for ROSI and what-if features.

## TL;DR
- **FAIR math is standardized; the distributions are not.** O-RA says Open FAIR analysts "use Monte Carlo or other stochastic methods" and that the model "is agnostic on what distribution is 'right'". PERT (for frequencies/ranges) and lognormal (for fat-tailed losses) are the de facto choices in open-source tools. They are not required by the standard.
- **The commercial market has consolidated around SAFE.** SAFE acquired RiskLens in July 2023 and Balbix in November 2025. Kovrr and Axio remain independent as of September 2026, and both are pivoting toward AI-risk quantification. Nearly all vendor feature and performance claims are marketing and have not been independently verified.
- **For a hackathon, fork or study pyfair (Python, MIT) or Netflix riskquant (Python, Apache-2.0), or evaluator (R, MIT).** Add a control-effect layer (FAIR-CAM-style or O-RA control categories) and compute ROSI using ENISA's formula. Use Gordon–Loeb (≤ 1/e ≈ 37% of expected loss) as a sanity cap on spending recommendations.

## Key Findings

### 1. The Open FAIR model: inputs and definitions (primary source: The Open Group)

The Open FAIR Body of Knowledge has two parts. The **Risk Taxonomy (O-RT) Standard, Version 3.0.1** (C20B, Nov 2021) defines the factors. The **Risk Analysis (O-RA) Standard, Version 2.0.1** (C20A, Nov 2021) defines how to estimate and compute them. Both are readable online at pubs.opengroup.org/security/o-rt/ and pubs.opengroup.org/security/o-ra/. O-RT defines risk as "the probable frequency and probable magnitude of future loss."

**Frequency side (O-RT Table 1):**

| Factor | O-RT definition (abridged) | Unit |
|---|---|---|
| Loss Event Frequency (LEF) | Probable frequency, within a timeframe, that a Threat Agent will inflict harm upon an Asset | Events/year, or probability of a single event in a timeframe |
| Threat Event Frequency (TEF) | Probable frequency that a Threat Agent will act against an Asset | Events/year |
| Contact Frequency (CF) | Probable frequency a Threat Agent comes into contact with an Asset | Events/year |
| Probability of Action (PoA) | Probability a Threat Agent acts once contact occurs | 0–1 |
| Vulnerability (Vuln; synonym Susceptibility) | Probability a Threat Event becomes a Loss Event; "probability that Threat Capability is greater than Resistance Strength" | 0–1 |
| Threat Capability (TCap) | Relative ranking of a Threat Agent's skill, resources, and time within a Threat Community | Percentile (0–100) |
| Resistance Strength (RS) | Ability to resist a Threat Community's range of skills, resources, and time | Percentile (0–100) |

O-RA states the key relationships explicitly: **LEF ≤ TEF ≤ CF** and **Vuln = Pr(Loss Event | Threat Event) = Pr(TCap > RS)**. O-RA also says that after estimating TCap and RS ranges, "the analyst will use Monte Carlo analysis to compare a random sample from Threat Capability with a random sample from Resistance Strength and derive Vulnerability."

**Magnitude side (O-RT Table 3, O-RA §5.3):**
- **Primary Loss Magnitude (PLM):** direct losses to the Primary Stakeholder. O-RA gives PLM = Σ(Primary Loss Forms).
- **Secondary Loss Event Frequency (SLEF):** "the conditional probability that a Primary Loss will result in a Secondary Loss; it is estimated/expressed as a probability, not as events/year."
- **Secondary Loss Magnitude (SLM):** losses from Secondary Stakeholders' reactions (regulators, customers, media). O-RA gives SLM = Σ(Secondary Loss Forms).
- **Loss Magnitude = PLM + SLM.**
- **The six forms of loss:** Productivity, Response, Replacement, Fines & Judgments, Competitive Advantage, Reputation. O-RA notes that productivity and replacement are more common as primary losses. Fines/judgments, competitive advantage, and reputation are more common as secondary losses. Response costs appear in both.

**Depth of analysis:** You do not have to decompose everything. O-RA says analysts "should estimate factors at the highest level possible in the Open FAIR taxonomy." For example, estimate LEF directly if you have loss history, and decompose into TEF × Vuln (or CF, PoA, TCap, RS) only when that improves data quality or the purpose requires it. Evaluating control options is one such purpose. O-RT also states that the Open FAIR risk factors "are assumed to be independently identically distributed". That independence assumption matters when you design correlation in your engine.

**FAIR Institute version:** The FAIR Institute publishes its own "FAIR Model | Standard Artifact | V3.0" (January 2025, PDF on fairinstitute.org). It uses "Susceptibility" in place of Vulnerability and describes Resistance Strength as control efficacy against the threat population. For example, a control rated 70–90% repels attackers below that range. I only reviewed this document via search excerpt, so check its full text before quoting it.

### 2. How EAL and VaR are actually computed

**Monte Carlo is the standard method, not an optional extra.** O-RA §3.1 says: "Open FAIR analysts use Monte Carlo or other stochastic methods to calculate results." §4.4 says Monte Carlo "models thousands of outcomes... to obtain a distribution of simulated annual losses." §5.4 says: "To quantitatively estimate the risk, the analyst performs a Monte Carlo analysis of the risk."

**Expected Annual Loss (EAL / ALE / "annualized loss exposure"):** The Open FAIR Risk Analysis Process Guide says a Monte Carlo analysis produces "a probability distribution of annual loss, also called the annual loss exposure. The stakeholder should expect that the average of the distribution represents an expected annual cost." O-RA lists "Average – this is the mean of the Monte Carlo simulated results" as a standard single-number summary. Its example qualitative scale bands "Average Annualized Loss Exposure", from Very Low (< $10,000) to Severe (> $10,000,000).

**VaR / 95th percentile:** O-RA does not use the term "Value-at-Risk" in the sections I read. It defines a **"Loss Exceedance Result – this is the percentile threshold result"**, with the example that if losses exceed $1M one time in ten, "the 90th percentile threshold is $1M." A "95% VaR" in your platform is therefore just the 95th percentile of the simulated annual-loss vector. That is an inference from the standard, not wording in the standard. O-RA recommends presenting results as a loss exceedance curve, a distribution curve, or a tornado chart when comparing alternatives.

**Algorithm, per iteration (synthesized from O-RA and O-RT):**
1. Sample TEF, or CF and PoA and multiply them.
2. Sample TCap and RS. Vuln = 1 if TCap > RS, otherwise 0, or estimate the fraction across many samples. Alternatively, sample Vuln directly.
3. LEF = TEF × Vuln. This can be treated as a rate, and the number of events drawn from Poisson(LEF).
4. For each loss event, sample PLM. With probability SLEF, also sample SLM.
5. Annual loss = sum over events.

Repeat 10k–50k times. EAL = mean, VaR95 = 95th percentile, and the loss exceedance curve = 1 − the empirical CDF.

There are two implementation styles in the open-source tools, and they differ:
- Netflix riskquant's `simulate_losses_one_year` generates "a random number of losses, and loss amount for each". This is the event-level method.
- Many simple calculators multiply one sampled LEF by one sampled LM per iteration. That is faster, but it understates variance when LEF > 1.

**Distributions.** O-RA 2.0.1 dropped the old "Confidence Level in the Most Likely Value" parameter in favour of "the choice of distribution". It says the model "is agnostic on what distribution is 'right'". It gives examples: uniform when you know only min and max, **log-normal** "if the risk analyst knows that a modeled potential loss has the potential of a 'fat tail'", and **Poisson** for TEF. It also says O-RA characterizes distributions by "minimum, maximum, and most likely values" that tools convert into distribution parameters.
- **PERT / beta-PERT** is the de facto default in practice. pyfair's `input_data` accepts `low/mode/high` (PERT) or `mean/stdev` (normal), and riskquant uses a "Modified PERT distribution" for frequency. A Medium write-up credited to Ken Nguyen, a secondary source, describes FAIR as using PERT with Monte Carlo.
- **Lognormal:** riskquant maps a [low, high] 90% range to a lognormal "so that they fall at the 5% and 95% cumulative probability points." It explains that a lognormal "allows for no negative loss values, and for a long tail of high losses." Rick Howard's CyberCanon review of Hubbard & Seiersen (2nd ed.) summarizes the same rationale.
- **Triangular:** I found no primary FAIR source recommending it. It is a generic three-point option and is not FAIR-specific.

**Calibrated estimation (O-RA §4.2–4.3, credited to Douglas Hubbard):**
- Estimates "should be accurate 90% of the time". The analyst should believe the true value falls below the minimum no more than "one time out of 20, or 5% of the time", and likewise above the maximum.
- The method is to start with absurd ranges and narrow them, and to decompose the problem Fermi-style.
- The "equivalent bet" wheel test: would you rather win $1,000 if the true value falls in your range, or on a wheel that is 90% black? If you prefer the wheel, widen your range.
- Challenge assumptions and document the rationale for every estimate.
- O-RA explicitly thanks Hubbard, saying: "Many of the ideas in the calibration section of this standard were originally described by him."

**Hubbard & Seiersen:** *How to Measure Anything in Cybersecurity Risk*, 2nd ed. (Wiley, 2023, ISBN 9781119892304).
- It covers the "simple one-for-one substitution" model: replacing each cell of a qualitative risk matrix with a probability and a 90% CI impact.
- It covers calibrated estimates (Ch. 7), a "Rapid Risk Audit", Bayesian examples, methods using the R language, and a foreword by Jack Jones.
- Hubbard's site points to example spreadsheets at howtomeasureanything.com/cybersecurity. I did not open these to verify their current availability.

**Jack Jones:** He created FAIR and co-authored *Measuring and Managing Information Risk: A FAIR Approach* (with Jack Freund, 2014, per CyberCanon). He also authored FAIR-CAM (Controls Analytics Model). SAFE's blog refers readers to "the white paper written by Jack Jones, An Introduction to the FAIR Controls Analytics Model"; I did not retrieve that paper directly.

**Modelling controls (the basis for ROSI and what-ifs).** O-RA §5.5 defines four control categories and the factor each one changes:
- **Avoidance** changes CF.
- **Deterrent** changes PoA.
- **Vulnerability (resistive)** changes RS or Vuln.
- **Responsive** changes PLM, SLEF, or SLM.

These map to NIST CSF: Protect covers avoidance, deterrent, and vulnerability controls, while Detect, Respond, and Recover cover responsive controls. O-RA also defines "Fragile" and "Unstable" risk qualifiers. Fragile means low LEF that depends on a single control; Unstable means low LEF only because TEF is low. Both are worth showing as flags in your UI.

**ROSI and investment ceilings:**
- **ENISA, "Introduction to Return on Security Investment" (Dec 2012).** It defines ALE = SLE × ARO. It defines ROSI as (monetary loss reduction − cost of solution) / cost of solution, where loss reduction = ALE − modified ALE = ALE × mitigation ratio. ENISA's example uses ARO 5, SLE €15,000, 80% mitigation, and €25,000/yr cost. By my arithmetic that gives ALE €75,000, loss reduction €60,000, and ROSI 140%. The formula images did not extract, so the formula is reconstructed from ENISA's verbatim surrounding text and corroborated by Infosecurity Magazine.
- **Gordon & Loeb, "The economics of information security investment"** (ACM TISSEC 5(4):438–457, Nov 2002, DOI 10.1145/581271.581274). For the security breach probability functions they analyze, optimal investment z* ≤ (1/e)·vL, or about 37% of expected loss. Willemson ("On the Gordon & Loeb Model for Information Security Investment", WEIS 2006) showed that the 1/e bound does not hold universally for all functions. The practical takeaway is to treat it as a heuristic, not a law.

### 3. Commercial platforms (status verified to Sept 2026)

| Vendor | Status (Sept 2026) | Data ingested (vendor-stated) | Exec presentation | Investment / what-if features (vendor-stated) |
|---|---|---|---|---|
| **SAFE (Safe Security) – SAFE One / "Cyber Risk Singularity" platform** | Independent, VC-backed. Acquired **RiskLens** on 12 July 2023 and **Balbix** on 18 Nov 2025. Raised a $70M Series C led by Avataar Ventures (31 July 2025 press release: "With this round, total funding exceeds $170 million") | "100-plus API integrations from vendors like Wiz and CrowdStrike"; "over 25 daily threat feeds"; industry benchmark TEF/loss data; loss data structured via FAIR-MAM. A reseller (C-Risk) says "200+ security tools". This conflicts with SAFE's own "100+", so treat both as marketing | FAIR-based dollar outputs (frequency % × $ magnitude), board/C-suite reporting | FAIR-CAM control-effectiveness modelling; "what-if" analyses by changing control status; CRQ now also feeds its CTEM and TPRM "AI Co-Workers" |
| **Balbix** (now part of SAFE) | Acquired by SAFE on 18 Nov 2025 (SAFE press release; Tracxn) | Asset-level data "from your existing tools, including vulnerabilities, threats, exposure, security controls, and business criticality" | Dollar risk sliceable "by business unit, by site, by the owner", with traceability to driving issues | Risk = likelihood × impact per asset; prioritization of remediation. Its 2021 launch claimed users could "reduce breach risk by 95% or more", an unverified marketing claim. Balbix publicly criticized FAIR's subjectivity ("UnFAIR" blog) |
| **Kovrr** | Independent (no acquisition found). Last verified funding: $5.5M (Sept 2019, Insurance Journal). Rebranded positioning as "AI Security and Governance for the Agentic Era"; CRQ is now one product line. Press release on 10 Sept 2026 | "Proprietary cyber insurance loss intelligence"; a real-world event database (regulatory disclosures, filings, legal reports, claims) calibrated "since 2017" and updated quarterly; API integration with control-monitoring tools, vulnerability scanners, SIEM, GRC, and identity providers | Average Annual Loss, loss exceedance curves, CRQ-powered risk register, portfolio views (e.g., for PE firms) | "Decision Simulator" to "calculate return on security investment for every decision"; "Top Recommended Actions" ranks controls by expected annual loss reduction; states 25,000 Monte Carlo trials per quantification. Its "38% of companies reallocated their budgets" figure is an unverified marketing claim |
| **Axio – Axio360** | Independent; CEO Scott Kannry. Named a Leader in *The Forrester Wave: Cyber Risk Quantification Solutions, Q2 2025* (Axio press release). Launched Axio AIR on 13 Aug 2026; Dragos partnership on 10 Feb 2026; Unison Risk Advisors partnership in July 2026 | Control-based assessments (NIST CSF, C2M2, CIS 18, CRI Profile); scenario inputs from business stakeholders; Dragos OT threat intel; insurance policy data | Dynamic risk visualizations "at both the executive and practitioner level", board reporting | Scenario-based Monte Carlo loss simulation; "compare how different improvements will reduce risk"; insurance stress testing; ROI of controls; "CRQ.AI" (May 2026 webinar) |
| **RiskLens** | No longer independent. Acquired by SAFE in July 2023; its FAIR engine is folded into SAFE One. Historically the FAIR Institute's technical advisor and host of the free FAIR-U app | — | — | — |

**Status caveats:**
- The aggregator Tracxn lists "Axio Global ... Acquired by iCapital (Sep 21, 2021)". iCapital's own press release shows the target was **Axio Financial LLC**, a structured-notes firm, not the cyber company. Amazon's 2025 acquisition of "Axio" was the Indian lender formerly called Capital Float. Neither affects Axio360.
- SAFE describes itself as "the category leader in Cyber Risk Quantification (CRQ), according to Forrester Research". Axio also claims Leader status in the same Forrester Wave. I did not read the Forrester report itself.
- I did not research Resilience, Cyentia (IRIS reports), FortifyData, or other vendors, so I make no claims about them here.

**Marketing vs. verified:**
- Independently verifiable facts: acquisitions (multiple outlets plus company releases), funding amounts in press releases, and product launches.
- Vendor-stated and not independently verified: integration counts, "3 billion signals a day", customer lists, 95% risk reduction, the 38% budget reallocation figure, and "category leader" rankings.

### 4. Open-source and academic resources

| Project | Language / License | Maintenance (as observed) | Useful for |
|---|---|---|---|
| **pyfair** (github.com/Hive-Systems/pyfair; originally theonaunheim/Derive-Risk) | Python; MIT (setup.py) | Alpha: PyPI 0.1a13, setup.py 0.1-alpha.14; README says "Managed and maintained by Hive Systems" | Most complete O-RT/O-RA-aligned engine. `FairModel.input_data('Loss Event Frequency', low, mode, high)` (PERT) or `mean/stdev`; `FairMetaModel` aggregates scenarios; `FairSimpleReport` produces HTML reports. Best base for a Python backend |
| **Netflix riskquant** (github.com/Netflix-Skunkworks/riskquant) | Python; Apache-2.0 (file headers "Copyright 2019-2020 Netflix") | Appears dormant; a curated listing showed ~555 stars as of 2022. Depends on TensorFlow (per a Go rewrite's README) | Clean event-level simulation: Poisson frequency, lognormal magnitude from a 90% CI, Modified PERT frequency, loss exceedance. Good reference for correct annual aggregation |
| **schulze/quantrisk** | Go | Self-described "experiment ... not a finished tool" | Lightweight loss-exceedance reimplementation without TensorFlow |
| **evaluator** (github.com/davidski/evaluator; CRAN) | R; MIT | CRAN v0.4.3 | Full OpenFAIR toolkit: domains, controls, scenarios, simulations, risk dashboard, Shiny "Scenario Explorer". Uses TEF/TCap/control-difficulty decomposition. Great for the control-to-risk mapping design |
| **paolocarner/fair-monte-carlo-risk-analysis** | Python/Streamlit; license not verified | Small personal project | Ready-made UI ideas: exceedance curves, 9 preset scenarios, "ROSI analysis and insurance recommendation tools" |
| **neoprehn/pyfair-cam** | Python; MIT for code, but FAIR-CAM KB content is **CC BY-NC-ND 4.0** | Early (loss-side controls "not yet included") | FAIR-CAM resistive-control simulation (efficacy, coverage, variance). **The NC-ND license on the KB content may restrict commercial or derivative use.** Check before shipping |
| **joshua-m-connors/cyber-incident-mcmc-pymc** | Python/PyMC; license not verified | Updated 21 Nov 2025; 42 stars | Bayesian (MCMC) FAIR + MITRE ATT&CK frequency estimation. The closest thing found to a Bayesian cyber-risk implementation |
| **Open Group Open FAIR Risk Analysis Tool Beta (I181)** + **Guide G181 (SIPmath)** | Excel; Open Group terms | Published Jan 2018 | Official reference implementation and algorithm guide. G181 "defines the algorithms that can be used to produce an acceptable implementation of the O-RA Standard" |
| **FAIR Institute FAIR-U** (web app) and **FAIR-U Workbook for Learners (beta, Excel)** | Free with FAIR Institute membership; the workbook is "strictly an educational tool", not for business or client use | FAIR-U was launched Oct 2017 by RiskLens; the workbook is newer | Validating your engine's outputs against an official FAIR calculator. The workbook exposes the calculations |

**Academic and quasi-academic sources found:**
- Gordon & Loeb (2002) and Willemson (2006), as above.
- Callegaro, Fontana, Hillairet & Ongarato, "A stochastic Gordon–Loeb model for optimal cybersecurity investment under clustered attacks" (arXiv 2505.01221; *Annals of Actuarial Science*, 2026, doi:10.1017/S1748499526100359). It models attacks as a Hawkes process and is useful if you want time-clustered attack frequency.
- Henry R.K. Skeoch, "Expanding the Gordon-Loeb model to cyber-insurance" (*Computers & Security* vol. 112, Jan 2022, article 102533, DOI 10.1016/j.cose.2021.102533).
- Luis Enriquez, "A Personal data Value at Risk Approach" (2024, arXiv 2411.03217). It combines FAIR with Beta-PERT Monte Carlo to compute a data-protection VaR.
- **Gap:** I did not locate and verify a specific peer-reviewed Bayesian-network CRQ paper, so none is cited. Hubbard & Seiersen's 2nd edition includes Bayesian methods.

## Recommendations: mapping this to a hackathon MVP

1. **Inputs (UI).** For each scenario, collect min / most-likely / max at 90% confidence for:
   - TEF (or LEF directly),
   - Vuln (or TCap and RS percentiles),
   - PLM, broken down by the six loss forms,
   - SLEF (a probability),
   - SLM.

   Default to the highest-level factors, per O-RA's top-down guidance. Store the rationale for each estimate, which O-RA requires you to document.
2. **Monte Carlo engine.**
   - Use the event-level method: Poisson(LEF) events per year, each with a sampled PLM plus a Bernoulli(SLEF) × SLM.
   - Use beta-PERT for bounded inputs (frequencies, percentiles, probabilities). Use lognormal fitted to the 5th/95th percentiles for loss magnitudes, following riskquant.
   - Run 10k–50k iterations with a fixed seed so demos are reproducible.
   - Optionally, sample Vuln as Pr(TCap > RS).
3. **Outputs.**
   - EAL = mean annual loss.
   - VaR95 (and VaR99) = percentiles.
   - A loss exceedance curve.
   - Per-scenario and aggregated totals (sum the iteration vectors, as pyfair's `FairMetaModel` does).
   - O-RA's Fragile/Unstable flags.
   - Label "VaR" as a percentile of simulated annual loss, not a regulatory VaR.
4. **ROSI what-if.**
   - Model each control as a change to a specific factor: avoidance changes CF, deterrent changes PoA, resistive changes RS or Vuln, and responsive changes PLM, SLEF, or SLM.
   - Rerun the simulation with common random numbers, then compute ΔEAL and ΔVaR95.
   - Compute ROSI = (ΔEAL − annual control cost) / annual control cost (ENISA).
   - Rank controls by ΔEAL per dollar, which is the same logic Kovrr and SAFE market.
   - Warn when the total recommended spend exceeds about 37% of baseline expected loss (a Gordon–Loeb heuristic).
5. **Fastest path.** Wrap pyfair, or your own ~150-line NumPy engine modelled on riskquant, in FastAPI or Streamlit. Borrow the dashboard ideas from evaluator and paolocarner. Check a few scenarios against FAIR-U or the Open Group Excel tool so you can tell judges your math matches the standard.

## Caveats
- Several claims come from secondary or marketing sources and are flagged inline. These include vendor integration counts, performance percentages, "leader" rankings, and SAFE's claim that FAIR practitioners are in "over 50% of Fortune 500 companies".
- The claim that FAIR is "recognized" in ISO/IEC 27005 appears only in secondary blogs I found. I did not verify it against ISO text, so do not repeat it.
- O-RA does not name "VaR"; mapping VaR to a percentile threshold is my interpretation.
- My ENISA formula is reconstructed from text around equation images, so check it in the PDF.
- Maintenance status of GitHub repos was observed via search snippets and may be out of date. Check commit history and LICENSE files before forking. Pay particular attention to FAIR-CAM content under CC BY-NC-ND.
- Company status can change quickly. SAFE and Kovrr both announced products within the last month, so re-verify just before your demo.