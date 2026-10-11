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
