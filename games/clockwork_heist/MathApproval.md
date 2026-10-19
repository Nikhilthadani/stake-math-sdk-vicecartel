Math verification
Betlevel templates
Depending on exposure and cost limits, different bet-level templates will be applied to your game. These templates define the minimum, maximum and default bet sizes for all currencies. With the standard templates, the RGS rejects a bet if either of the following conditions is true:

The total bet cost (bet amount × mode cost multiplier) exceeds $500,000 USD (or the equivalent amount in another currency)
The potential payout from a single bet (bet amount × mode maximum win multiplier) exceeds $50,000,000 USD (or the equivalent amount in another currency)
An operator can set lower limits. A bet beyond the limits returns HTTP 400 with the body {"error": "ERR_VAL", "message": "invalid amount"}.

Bet-level templates define the underlying base bet amount and range from a maximum of $1 USD to $1000 USD. The bet template assigned to your game will depend on factors such as maximum cost multiplier, maximum payout amount, and game volatility/operator risk (discussed below).

File Size Restrictions
In order to limit RGS instability caused by large file downloads:

No single events file (.jsonl.zst) can exceed 4.2GB
No game mode can contain more than 10,000,000 events
\*Every game must contain less than or equal to 20 modes (the math files must have at most 20 lookup table files, .jsonl.zst file sets etc…)
Files/modes exceeding this size will fail on publish.

Summary statistics and hit-rate tables will be analyzed to ensure the game adheres to industry standards for chance-based casino games and is not misleading.

Summary Statistics
Verify the mode cost is correctly represented in the game rules for each mode.
The calculated Return to Player (RTP) must be within 96.0%–96.70%.
Ensure the maximum win amount matches the description in the game rules for each mode.
The maximum win should be realistically obtainable (typically more frequent than 1 in 10,000,000, depending on payout amount).
For slot-type games, run 100,000–1,000,000 simulations to ensure sufficient outcome diversity and avoid repeated results in a single session.
A reasonable portion of simulations should yield paying results (e.g., 90,000 non-paying results out of 100,000 may be grounds for rejection).
The hit-rate of the most likely single simulation should not be overwhelmingly dominant if there is a visual expectation that results are sufficiently varied.
Critical Tests
Every game must pass all of the checks below before it can be submitted for review. The submission form blocks a game that fails any of them.

Test Requirement
Base mode The cheapest mode must have a 1.0× cost multiplier (conventionally the base mode).
Base volatility The standard deviation of every 1.0× mode must be ≥ 0.6.
RTP band Every mode’s RTP must sit between 96.0% and 96.7%.
Max payout multiplier No mode’s maximum win may exceed 1,000,000×.
Max cost multiplier No mode’s cost multiplier may exceed 50,000×.
Viable bet level At least one bet-level template must fit within the game’s 3-Star limits. In practice this only fails when another limit is breached, or when nearly every non-critical check fails (see below).
Non-Critical Tests
Non-critical tests control operator risk. Unlike critical tests, failing them does not block submission — instead your game’s maximum exposure and maximum bet cost are reduced. Those two caps decide the largest bet-level template your game can be assigned, so the more checks you fail, the smaller the bets your game will accept (and in the worst case, no template qualifies at all).

Every game is measured against two rating tiers, 2-Star and 3-Star. The 3-Star tier is more lenient, so a game that no longer qualifies at 2-Star may still qualify at 3-Star with a lower cap.

Limits per rating
Check 2-Star 3-Star
Maximum Exposure $15,000,000 $50,000,000
Maximum Bet Cost $100,000 $500,000
Maximum Payout Multiplier 50,000× 100,000×
Maximum Cost Multiplier 1,000× 5,000×
Maximum Std Dev (any mode) 50.0 60.0
Risk Limit — CVaR (per-stake) 700 700
Risk Limit — CVaR (absolute) 20,000 50,000
Tail Probability — P(≥ 5,000×) 0.010 0.050
Tail Probability — P(≥ 10,000×) 0.005 0.010
Tail Probability — P(≥ 25,000×) 0.002 0.005
Tail Probability — P(≥ 50,000×) 0.001 0.001
Tail Probability — P(≥ 100,000×) 0.0005 0.0005
Expected Tail Liability (> 40×) 0.8 0.9
Expected Tail Liability (> 10,000×) 0.6 0.8
Expected Tail Liability (sum) 1.3 1.5
Expected Tail Liability (absolute sum) 3,000 10,000
Maximum Exposure and Maximum Bet Cost are the starting caps, before any penalty. Every other check in the table is a check that, when failed, reduces those two caps.

How failures are grouped
Closely-related checks are collapsed into a single failure class, so failing several checks that measure the same underlying thing only counts once:

Class Checks it covers
Maximum Payout Multiplier maximum payout
Cost Multiplier maximum cost multiplier
Volatility (Std Dev) maximum std dev
Risk Limit (CVaR) per-stake CVaR and absolute CVaR
Expected Tail Liability ETL > 40×, ETL > 10,000×, the ETL sum, and the absolute ETL sum
Tail Probability P(≥ 5,000×), P(≥ 10,000×), P(≥ 25,000×), P(≥ 50,000×) and P(≥ 100,000×)
For example, exceeding both P(≥ 5,000×) and P(≥ 10,000×) counts as a single failure (the Tail Probability class), not two. A class counts once no matter how many modes trip it. There are six classes in total, so six is the maximum possible number of failures.

Penalty schedule
The number of failed classes sets the reduced exposure and bet-cost caps, per rating:

2-Star

Failed classes Maximum Exposure Maximum Bet Cost
0 $15,000,000 $100,000
1 $10,000,000 $100,000
2 $10,000,000 $50,000
3 $5,000,000 $50,000
4 $1,000,000 $10,000
5 $500,000 $10,000
6 $100,000 $5,000
3-Star

Failed classes Maximum Exposure Maximum Bet Cost
0 $50,000,000 $500,000
1 $25,000,000 $500,000
2 $15,000,000 $250,000
3 $10,000,000 $100,000
4 $5,000,000 $50,000
5 $1,000,000 $10,000
6 $500,000 $10,000
A bet-level template is valid for a rating only if both of the following hold against that rating’s reduced caps:

worst-case payout — maximum payout multiplier × maximum bet — stays within the Maximum Exposure cap, and
worst-case round cost — maximum cost multiplier × maximum bet — stays within the Maximum Bet Cost cap.
If no template fits — for example a very high max-win game whose smallest allowed bet already breaches the reduced exposure cap — the game shows “no valid template” for that rating.

Check definitions
Tail Probability — P(≥ 5,000×) to P(≥ 100,000×) The probability that a single round pays 5,000×, 10,000×, 25,000×, 50,000× or 100,000× the base bet or more. The worst-case (highest) value across all modes is compared against the limit. These are raw probabilities and are not scaled by cost multiplier.

Risk Limit — CVaR (Conditional Value at Risk) Also known as Expected Shortfall, this answers: “what is the expected payout to the operator when a win lands in the worst 0.1% of outcomes?” Two values are checked:

Per-stake (normalized) — CVaR ÷ cost multiplier, i.e. the expected worst-case payout relative to the bet. Limit: 700 for both ratings.
Absolute — the un-normalized expected payout amount. Limit: 20,000 (2-Star) / 50,000 (3-Star).
Expected Tail Liability (ETL) The share of a mode’s RTP that comes from heavy-tail wins, normalized by cost multiplier. ETL > 40× covers wins above 40× the cost multiplier, ETL > 10,000× covers wins above 10,000×, and the sum combines the two. The absolute sum is the same sum before dividing by the cost multiplier. An ETL of 0.5 means half of the mode’s total RTP comes from these large, infrequent wins — a sign of high tail-risk concentration for operators.

Other Considerations
The hit-rate of non-zero wins should align with industry standards (no rarer than 1 in 50 bets, or more frequent).
For base (1.0× cost) modes, the standard deviation should sit within industry norms to give reasonable volatility for slot-type games.
Zero-weight payouts should not dominate the provided simulations — list the number of non-zero-weight payouts.
Inspect win-range hit-rates for gaps where expected win amounts are unobtainable (e.g. intermediate wins should exist between small payouts and the maximum win).
With the standard templates, the maximum bet cost accepted by the RGS is $500,000 USD (or the equivalent in another currency). A bet beyond this limit returns HTTP 400 with "message": "invalid amount".

Previous
Front-end communication
