---
lab5_triage:
  image: ghcr.io/s189751/itsm-svcdesk@sha256:97e16eb38eb60310c17332bd56b725a70f3c27fbd819ef512f12ebff9c9bbb98
  sarif_receipt: 430
---
<!-- ai-generated: 40% - an AI assistant read the scanner logs and drafted the rows; I checked every fix against the rebuilt image -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
The shipped repository has no `.trivyignore` or `.gitleaksignore` entries: every finding below was fixed, so no ID is
suppressed and the only ignore files are the skeleton's header comments.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2026-109518 | fix | Image gate: apt 3.0.3 and libapt-pkg7.0 in the base image; pinned `python:3.13-slim@sha256:e48f59cd…` and added `apt-get update && apt-get upgrade -y` before the app layers, which installs apt 3.0.4. Re-scan of the rebuilt image is clean. |
| trivy | CVE-2026-76844 | fix | Image gate: zlib1g 1:1.3.dfsg+really1.3.1-1+b1 in the base image; the same `apt-get upgrade` moves it to 1:1.3.dfsg+really1.3.1-1+deb13u1. Gone from the rebuilt image. |
| trivy | CVE-2026-85091 | fix | Image gate: second zlib1g advisory (heap overflow in gz_vacate); fixed by the same `apt-get upgrade` to the deb13u1 revision of zlib1g. Gone from the rebuilt image. |
| trivy | GHSA-6q48-6c7w-9gw2 | fix | CRITICAL certifi advisory: httpx pulled certifi 2026.7.22; pinned `certifi==2026.10.18` in requirements.txt, the first release with the compromised emSign roots removed. Gone from the rebuilt image. |
| trivy | CVE-2026-114613 | fix | HIGH in msgpack 1.1.2 read from pip's own `pip/_vendor` bill of materials, not from my code. pip is only needed to install, so the Dockerfile now ends the install with `pip uninstall -y pip`; the vendored copy left the image. svcdesk never calls pip at run time. |
| trivy | GHSA-6v7p-g79w-8964 | fix | Second msgpack advisory in the same vendored copy; removed together with pip by `pip uninstall -y pip` in the Dockerfile. |
| trivy | CVE-2025-47273 | fix | setuptools 70.3.0 vendored inside pip; removed with pip (`pip uninstall -y pip`). Nothing in the runtime imports setuptools. |
| trivy | CVE-2026-97687 | fix | urllib3 2.7.0 vendored inside pip; removed with pip. The application's own urllib3 comes from httpx and is current. |
| trivy | CVE-2026-97689 | fix | Second urllib3 advisory in the same vendored copy; removed together with pip. |
| semgrep | dockerfile.security.missing-user.missing-user | fix | The Dockerfile ran the container as root. Added a system user `app`, chowned /data and /app, and set `USER app`; the p/default scan of the rebuilt tree reports 0 findings. |

## Bake-off

My canary set has 8 labelled defects (3 credentials, 2 vulnerable pins, 3 code defects). On that set the measured
matrix is: trivy TP 3 / FP 1 / FN 5 (precision 0.7500, recall 0.3750, F1 0.5000); gitleaks TP 2 / FP 1 / FN 6
(0.6667, 0.2500, 0.3636); grype TP 2 / FP 0 / FN 6 (1.0000, 0.2500, 0.4000); osv-scanner the same as grype; semgrep
TP 2 / FP 3 / FN 6 (0.4000, 0.2500, 0.3077). Trivy's extra true positive over grype and osv-scanner is a secret: the
deps job runs Trivy with `--scanners vuln,secret`, so it is both a dependency and a secret detector. Its one false
positive is a decoy in the set, and the same decoys explain gitleaks' 0.6667 precision and semgrep's 0.4000.

If I could keep only one dependency gate, it would be Trivy in the deps job: it found both pins and one credential,
and a false positive rate of 1 in 4 on a deliberately adversarial set is still tolerable for a blocking gate. Grype
and osv-scanner have perfect precision but exactly the same recall as Trivy on dependencies on this set, so they are
better used as corroboration in code scanning than as a second blocking gate. For credentials I would keep gitleaks
in the gate despite its 0.2500 recall: a missed secret is a different kind of failure from a missed code smell, and
its 1 FP here is a seeded decoy rather than noise on real code. I would not block on Semgrep: 3 FPs against 2 TPs is
exactly the alert-fatigue ratio Lecture 5 warns about, so I would report it and triage it, not fail the build.

The cells that surprised me were the recall values: all five detectors agree on the two vulnerable pins and the
obvious credentials, and none of them sees the three app/ defects except Semgrep's two weak-crypto hits. The
injection defects in `sla_formula.py` and the decoy-heavy modules are invisible to every scanner here, which is the
point of reading recall as an upper bound: the set was seeded with scanner-visible faults, and real bugs are not.
Every recall above is therefore optimistic; seeded defects flatter every detector, and the direction of the numbers
is not what matters - what matters is that they were produced by the published rule from the receipted SARIF.
