# Benchmark Report

_Generated: 2025-09-08 05:54 UTC_

## Overview

| Repo | Truth | AI Scan | QA | TP | Partial | FP | FN | Precision | Recall | F1 | P(w/partial) | R(w/partial) | F1(w/partial) |
|------|--------|------|----|----|---------|----|----|-----------|--------|----|--------------|--------------|---------------|
| cantina_minimal-delegation_2025_04 | 17 | 10 | 0 | 0 | 0 | 10 | 17 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| cantina_smart-contract-audit-of-tn-contracts_2025_08 | 23 | 15 | 0 | 3 | 0 | 12 | 20 | 20.0% | 13.0% | 15.8% | 20.0% | 13.0% | 15.8% |
| code4rena_cabal-liquid-staking-token_2025_05 | 8 | 36 | 0 | 0 | 1 | 35 | 8 | 0.0% | 0.0% | 0.0% | 2.8% | 12.5% | 4.5% |
| code4rena_coded-estate-invitational_2024_12 | 33 | 11 | 0 | 1 | 2 | 8 | 32 | 9.1% | 3.0% | 4.5% | 27.3% | 9.1% | 13.6% |
| code4rena_initia-move_2025_04 | 18 | 23 | 0 | 1 | 1 | 21 | 17 | 4.3% | 5.6% | 4.9% | 8.7% | 11.1% | 9.8% |
| code4rena_iq-ai_2025_03 | 9 | 18 | 0 | 3 | 0 | 15 | 6 | 16.7% | 33.3% | 22.2% | 16.7% | 33.3% | 22.2% |
| code4rena_kinetiq_2025_07 | 25 | 22 | 0 | 3 | 1 | 18 | 22 | 13.6% | 12.0% | 12.8% | 18.2% | 16.0% | 17.0% |
| code4rena_lambowin_2025_02 | 14 | 14 | 0 | 2 | 1 | 11 | 12 | 14.3% | 14.3% | 14.3% | 21.4% | 21.4% | 21.4% |
| code4rena_liquid-ron_2025_03 | 5 | 8 | 0 | 2 | 0 | 6 | 3 | 25.0% | 40.0% | 30.8% | 25.0% | 40.0% | 30.8% |
| code4rena_pump-science_2025_02 | 17 | 14 | 0 | 2 | 1 | 11 | 15 | 14.3% | 11.8% | 12.9% | 21.4% | 17.6% | 19.4% |
| ALL | 169 | 171 | 0 | 17 | 7 | 147 | 152 | 9.9% | 10.1% | 10.0% | 14.0% | 14.2% | 14.1% |

## cantina_minimal-delegation_2025_04

- **actual findings (truth, all severities)**: 17
- **scan findings (raw)**: 10
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 0
- **partial matches**: 0
- **false positives (adjusted)**: 10
- **false negatives**: 17
- **precision**: 0.0%
- **recall**: 0.0%
- **F1**: 0.0%
- **precision w/ partial**: 0.0%
- **recall w/ partial**: 0.0%
- **F1 w/ partial**: 0.0%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 2 | 0 | 4 | 11 | 0 |

## cantina_smart-contract-audit-of-tn-contracts_2025_08

- **actual findings (truth, all severities)**: 23
- **scan findings (raw)**: 15
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 3
- **partial matches**: 0
- **false positives (adjusted)**: 12
- **false negatives**: 20
- **precision**: 20.0%
- **recall**: 13.0%
- **F1**: 15.8%
- **precision w/ partial**: 20.0%
- **recall w/ partial**: 13.0%
- **F1 w/ partial**: 15.8%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 3 | 2 | 9 | 9 | 0 |

## code4rena_cabal-liquid-staking-token_2025_05

- **actual findings (truth, all severities)**: 8
- **scan findings (raw)**: 36
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 0
- **partial matches**: 1
- **false positives (adjusted)**: 35
- **false negatives**: 8
- **precision**: 0.0%
- **recall**: 0.0%
- **F1**: 0.0%
- **precision w/ partial**: 2.8%
- **recall w/ partial**: 12.5%
- **F1 w/ partial**: 4.5%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 1 | 7 | 0 | 0 | 0 |

## code4rena_coded-estate-invitational_2024_12

- **actual findings (truth, all severities)**: 33
- **scan findings (raw)**: 11
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 1
- **partial matches**: 2
- **false positives (adjusted)**: 8
- **false negatives**: 32
- **precision**: 9.1%
- **recall**: 3.0%
- **F1**: 4.5%
- **precision w/ partial**: 27.3%
- **recall w/ partial**: 9.1%
- **F1 w/ partial**: 13.6%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 9 | 9 | 15 | 0 | 0 |

## code4rena_initia-move_2025_04

- **actual findings (truth, all severities)**: 18
- **scan findings (raw)**: 23
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 1
- **partial matches**: 1
- **false positives (adjusted)**: 21
- **false negatives**: 17
- **precision**: 4.3%
- **recall**: 5.6%
- **F1**: 4.9%
- **precision w/ partial**: 8.7%
- **recall w/ partial**: 11.1%
- **F1 w/ partial**: 9.8%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 4 | 4 | 10 | 0 | 0 |

## code4rena_iq-ai_2025_03

- **actual findings (truth, all severities)**: 9
- **scan findings (raw)**: 18
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 3
- **partial matches**: 0
- **false positives (adjusted)**: 15
- **false negatives**: 6
- **precision**: 16.7%
- **recall**: 33.3%
- **F1**: 22.2%
- **precision w/ partial**: 16.7%
- **recall w/ partial**: 33.3%
- **F1 w/ partial**: 22.2%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 1 | 3 | 5 | 0 | 0 |

## code4rena_kinetiq_2025_07

- **actual findings (truth, all severities)**: 25
- **scan findings (raw)**: 22
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 3
- **partial matches**: 1
- **false positives (adjusted)**: 18
- **false negatives**: 22
- **precision**: 13.6%
- **recall**: 12.0%
- **F1**: 12.8%
- **precision w/ partial**: 18.2%
- **recall w/ partial**: 16.0%
- **F1 w/ partial**: 17.0%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 3 | 5 | 17 | 0 | 0 |

## code4rena_lambowin_2025_02

- **actual findings (truth, all severities)**: 14
- **scan findings (raw)**: 14
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 2
- **partial matches**: 1
- **false positives (adjusted)**: 11
- **false negatives**: 12
- **precision**: 14.3%
- **recall**: 14.3%
- **F1**: 14.3%
- **precision w/ partial**: 21.4%
- **recall w/ partial**: 21.4%
- **F1 w/ partial**: 21.4%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 4 | 10 | 0 | 0 | 0 |

## code4rena_liquid-ron_2025_03

- **actual findings (truth, all severities)**: 5
- **scan findings (raw)**: 8
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 2
- **partial matches**: 0
- **false positives (adjusted)**: 6
- **false negatives**: 3
- **precision**: 25.0%
- **recall**: 40.0%
- **F1**: 30.8%
- **precision w/ partial**: 25.0%
- **recall w/ partial**: 40.0%
- **F1 w/ partial**: 30.8%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 1 | 2 | 2 | 0 | 0 |

## code4rena_pump-science_2025_02

- **actual findings (truth, all severities)**: 17
- **scan findings (raw)**: 14
- **QA findings (from scan: Info + Best Practices)**: 0
- **true positives (exact matches)**: 2
- **partial matches**: 1
- **false positives (adjusted)**: 11
- **false negatives**: 15
- **precision**: 14.3%
- **recall**: 11.8%
- **F1**: 12.9%
- **precision w/ partial**: 21.4%
- **recall w/ partial**: 17.6%
- **F1 w/ partial**: 19.4%

Truth severity counts:

| high | medium | low | info | bestpractices |
|------|--------|-----|------|----------------|
| 2 | 3 | 12 | 0 | 0 |
