"""
metric_constants.py — hybrid metric weights, declared independently of outcome data.

THIS FILE MUST NEVER BE EDITED IN RESPONSE TO A RESULT.

The weights below are a design choice, not an estimate. They are fixed here, before
analysis, so that reporting a correlation against them is a genuine test rather than a
maximum over a search. If they are changed after seeing an outcome, every result computed
with them becomes a tuned result and must be reported as such.

Background: the previous implementation grid-searched (w1, w2, w3) to maximise Spearman
rho against the same outcome variable it then reported, with no held-out data. The paper's
headline rho was therefore a maximum over ~66 candidate triplets presented as a single
test. See _audit/AUDIT_REPORT.md section E.2.

Any change to FIXED_WEIGHTS must be recorded in the CHANGELOG below with a date and a
rationale that does not reference an outcome.
"""

from __future__ import annotations

from typing import NamedTuple


class HybridWeights(NamedTuple):
    """Weights for the fan-out corrected hybrid criticality metric.

    Criticality(v) = w_in * C_in(v)
                   + w_out * C_out(v) * fan_out_weight(v)
                   + w_btw * C_btw(v)

    where fan_out_weight(v) = d_out(v) / max_u d_out(u).
    """

    w_in: float
    w_out: float
    w_btw: float

    def validate(self) -> None:
        total = self.w_in + self.w_out + self.w_btw
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"weights must sum to 1.0, got {total}")
        if min(self) < 0.0:
            raise ValueError(f"weights must be non-negative, got {self}")


# ── The declared weights ──────────────────────────────────────────────────────
#
# Rationale, stated without reference to any measured outcome:
#
#   w_in = 0.4   Inbound callers lose a dependency when v fails. This is the classical
#                failure-propagation channel and is weighted equally with the outbound
#                channel below.
#   w_out = 0.4  Outbound callees are severed simultaneously when v fails. The paper's
#                whole thesis is that this channel is as important as the inbound one,
#                so it gets equal weight -- not more, which would beg the question.
#   w_btw = 0.2  Betweenness is a secondary, path-based signal and is degenerate on
#                shallow graphs (it is 0.0 for 5 of 12 Social Network services and for
#                6 of 7 Hotel Reservation services), so it carries half the weight of
#                the two degree channels.
#
# The equal in/out split is the neutral prior for the hypothesis under test. It was NOT
# selected by comparing candidate splits against measured impact.

FIXED_WEIGHTS = HybridWeights(w_in=0.4, w_out=0.4, w_btw=0.2)


# ── Tuning protocol constants ─────────────────────────────────────────────────

# The architecture weights may be tuned on, under the "cross-arch" protocol. The other
# architecture is the held-out evaluation set and must be touched exactly once.
TUNING_ARCHITECTURE = "socialnetwork"
HELDOUT_ARCHITECTURE = "hotelreservation"

# Grid resolution used by the cross-arch protocol. Recorded here so the size of the
# search space is declared up front and can be reported alongside any tuned result.
GRID_STEP = 0.05


# ── CHANGELOG ─────────────────────────────────────────────────────────────────
#
# 2026-09-23  Created. FIXED_WEIGHTS = (0.4, 0.4, 0.2), carried over from the previous
#             implementation's default. Note for honest reporting: that default was
#             itself described in centrality/compute_centrality.py as "optimised
#             empirically via hybrid_weight_optimizer.py". Its provenance is therefore
#             NOT clean. Using it as a "fixed" weight is only defensible if the paper
#             states plainly that the value originated from a search over contaminated
#             data. The clean alternatives are to justify it a priori as above, or to
#             use the cross-arch protocol. This needs a decision -- see
#             PREREGISTRATION.md, open question 1.
