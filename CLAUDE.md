# Project rules

- Read docs/build-spec.md before any planning or coding.
- No hard-coded outputs: every number comes from a DB row or function call.
- Provenance on every number: source, timestamp, run ID.
- Synthetic inputs, real mechanics; label which is which.
- Risk is computed per scenario and attributed downward; never sum VaR;
  EPSS is a relative rank, never a raw probability.
- Python only, no microservices. ISO/CIS: IDs and short titles only.
- Tests before dependents build on a function.
