Math Distribution & Summary
Version 3
Statistics Validation
Valid
Constraint
2 Star
Max template 50max_1cent
3 Star
Max template 200max_1cent

Max Exposure
1,250,000
/ 5,000,000
5,000,000
/ 15,000,000

Max Payout Multiplier
25,000
/ 50,000
25,000
/ 100,000

Max Bet Cost
50,000
/ 50,000
200,000
/ 250,000

Cost Multiplier
1,000
/ 1,000
1,000
/ 5,000

Base Volatility (Std Dev)
14.10
/ 50.0
14.10
/ 60.0

Tail Probability (5,000x)
0.0385
/ 0.0100
0.0385
/ 0.0500
What it is: How likely a single round is to pay 5,000x or more. Bet size and cost multiplier don't change it.

How to fix: Make payouts of 5,000x or more happen less often in the distribution.

Failing in 2 Star: golden_case

Tail Probability (10,000x)
0.0385
/ 0.0050
0.0385
/ 0.0100
What it is: How likely a single round is to pay 10,000x or more. Bet size and cost multiplier don't change it.

How to fix: Make payouts of 10,000x or more happen less often in the distribution.

Failing in 2 Star: golden_case

Failing in 3 Star: golden_case

Tail Probability (25,000x)
0.0385
/ 0.0020
0.0385
/ 0.0050
What it is: How likely a single round is to pay 25,000x or more. Bet size and cost multiplier don't change it.

How to fix: Make payouts of 25,000x or more happen less often in the distribution.

Failing in 2 Star: golden_case

Failing in 3 Star: golden_case

Tail Probability (50,000x)
0
/ 0.0010
0
/ 0.0010

Tail Probability (100,000x)
0
/ 5.0e-4
0
/ 5.0e-4

Risk Limit (CVaR, per-stake)
156.7
/ 700.0
156.7
/ 700.0

Risk Limit (CVaR, absolute)
25000.0
/ 20000.0
25000.0
/ 50000.0
What it is: The same worst-0.1% expected payout, but in raw base-bet multiples (not divided by cost). It bounds absolute operator liability, so a high-cost mode can't hide a large tail behind its stake.

How to fix: Lower the size of the most extreme wins.

Failing in 2 Star: golden_case

Expected Tail Liability (40x)
0.683
/ 0.800
0.683
/ 0.900

Expected Tail Liability (10,000x)
0.963
/ 0.600
0.963
/ 0.800
What it is: The cumulative RTP share that comes from wins above 10,000x.

How to fix: Move RTP away from the biggest wins (above 10,000x) toward smaller ones.

Failing in 2 Star: golden_case

Failing in 3 Star: golden_case

Expected Tail Liability (Sum)
0.963
/ 1.300
0.963
/ 1.500

Expected Tail Liability (Absolute)
963
/ 3,000
963
/ 10,000
2 Star — Caps Reduced
3 failing checks
Max Exposure
Reduced to 5,000,000
From 15,000,000
Max Bet Cost
Reduced to 50,000
From 100,000
Due to:
Risk Limit (CVaR)
Expected Tail Liability
Tail Probability
3 Star — Caps Reduced
2 failing checks
Max Exposure
Reduced to 15,000,000
From 50,000,000
Max Bet Cost
Reduced to 250,000
From 500,000
Due to:
Expected Tail Liability
Tail Probability
Game Modes

base
1x
MEDIUM
RTP
96.30%
HIT
97.18%
MAX
25,000x
B/E
0.9%

golden_case
1000x
LOW
RTP
96.30%
HIT
3.85%
MAX
25,000x
B/E
3.9%

extra_chance_3x
3x
MEDIUM
RTP
96.30%
HIT
99.09%
MAX
25,000x
B/E
1.4%

extra_chance_5x
5x
LOW
RTP
96.30%
HIT
99.62%
MAX
25,000x
B/E
3.0%

min2wild_200x
200x
LOW
RTP
96.30%
HIT
99.99%
MAX
25,000x
B/E
25.0%

min2wild_250x
250x
LOW
RTP
96.30%
HIT
100.00%
MAX
25,000x
B/E
20.1%
Detailed Metrics
Volatility
14.10
MEDIUM
Outcomes
1,000,000
Zero Rate
2.82%
Mean
0.96x
Win Hit-Rate
1.03
Std Dev
14.1008
Min
0.00x
Outcome Breakdown
Dead 2.8%
Sub-bet 96.2%
Win 0.9%
Avg Spins Between Any Win
1 spins
Expected consecutive zero win streak
Worst-Case Zero Streak
2 spins
1-in-1000 chance consecutive zero wins
Avg spins between profit
107 spins
Expected consecutive spins before profitable outcome
Worst-Case Loss Streak
739 spins
1-in-1000 chance of consecutive losing spins
Compliance per mode (base)
6/6
Base Mode Cost
The smallest-cost mode must be the 1.0x base game
Expected: = 1.00x
→
Result: 1.00x
Base Mode STD
The standard deviation for the base mode must we within limits
Expected: = 0.60x
→
Result: 14.10x
Bet Level Validator
A valid three-star bet-level template must exist
Expected: valid template
→
Result: 200max_1cent
RTP Range
Return to Player must sit within the allowed band
Expected: 96.0% – 96.70%
→
Result: 96.30%
Cost Multiplier
A mode's cost multiplier must stay within the cap
Expected: ≤ 50,000x
→
Result: 1x
Max Payout Multiplier
The biggest win multiplier must stay within the cap
Expected: ≤ 1,000,000x
→
Result: 25,000x
Hit Rate Distribution: base
Hit-Rate Ranges Distribution Counts Effective Hit-Rate Total RTP Contribution
( 0, 0.1 ) 5 8.37 0.58%
( 0.1, 1 ) 89 1.15 25.38%
( 1, 2 ) 100 70206.01 0.00%
( 2, 5 ) 259 24070.45 0.01%
( 5, 10 ) 371 12748.44 0.06%
( 10, 20 ) 548 5117.89 0.30%
( 20, 50 ) 782 422.87 10.42%
( 50, 100 ) 357 180.42 43.15%
( 100, 200 ) 169 1081.37 12.03%
( 200, 500 ) 96 7239.56 3.03%
( 500, 1000 ) 36 931278.07 0.08%
( 1000, 2000 ) 25 1301565.30 0.10%
( 2000, 5000 ) 24 1440165.47 0.21%
( 5000, 10000 ) 17 2008806.18 0.38%
( 10000, 20000 ) 9 3764458.81 0.40%
( 20000, 50000 ) 2 15695215.02 0.16%
Mode Statistics: base
Property Value
Bet Cost 1
Return to Player (%) 96.3000
Maximum Payout Multiplier 25000
Minimum Payout Multiplier 0
Average Win 0.9630
Standard Deviation 14.1008
Simulation Count 1000000
Zero Payout Count 405604
Non-Zero Weight Count 1000000
Number of Unique Payout Values 2889
Most Probable Simulation Hit-Rate (%) 3173.2869
Max Win Hit-Rate 28822135.9474
Probability of Zero Win (%) 2.8201
Probability of Payout less than Bet 99.0697
