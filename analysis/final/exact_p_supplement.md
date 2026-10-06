# Exact permutation p-values: supplementary refinement

**SUPPLEMENTARY. Not a re-analysis, not a locked output, not a new test.** Produced by `analysis/final/exact_p_supplement.py`. Full table: `exact_p_supplement.csv`.

The Social Network tests in the locked confirmatory family used 10,000 Monte-Carlo permutations because 11! = 39,916,800 exceeded the enumeration limit. Permuting the rank vector with more ties enumerates the identical null distribution from far fewer distinct arrangements, so those p-values can be made exact after the fact. Hotel Reservation tests were already exact (7! = 5,040) and are unchanged.

## Primary test

| quantity | value |
|---|---|
| test | Social Network, ancestor_count vs ancestor_affected_count, kill faults |
| Spearman rho | 0.785118891023205 (unchanged; recomputed 0.785119) |
| raw p, locked (10,000 Monte-Carlo) | **0.007999200079992** |
| raw p, exact enumeration | **0.00692641** = 64/9,240 |
| enumeration | exact enumeration of 9,240 distinct arrangements (39,916,800 permutations) |
| BH-adjusted p, locked | **0.3450512091647978** |
| BH-adjusted p, exact primary substituted | **0.304762** |
| BH-adjusted p, all available exact substituted | **0.304762** |
| significant at q = 0.05 | **False -> False** |

## Family-level effect

| quantity | value |
|---|---|
| tests in family | 44 |
| tests with a defined p | 44 |
| tests refined to an exact p | 43 |
| tests whose raw p changed at all | 37 |
| significant after BH-FDR, locked | **0** |
| significant after BH-FDR, with exact p | **0** |

**The BH-adjusted verdict is unchanged: 0 of 44 confirmatory tests are significant at q = 0.05, before and after this refinement.** The primary test's adjusted p moves by a fraction of a percent and remains roughly an order of magnitude above the threshold.

## Correction to an earlier figure

An earlier supplementary note (`blind_recompute.md`) reported **0.006883** for this test from 2,000,000 Monte-Carlo pairings and described it as high-resolution. It is a Monte-Carlo estimate, not an exact value. The exact value is **0.00692641** (64 of 9,240 arrangements). The difference, 4.3e-05, is within Monte-Carlo error for 2,000,000 resamples and changes nothing, but the exact value is the one that should be cited.
