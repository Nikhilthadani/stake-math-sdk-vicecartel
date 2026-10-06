The solution is not to put Wilds into the physical normal reel strips at all.
You need two separate layers.
Correct production model
REEL 1 REEL 2 REEL 3 REEL 4 REEL 5
│ │ │ │ │
▼ ▼ ▼ ▼ ▼
Wild roll Wild roll Wild roll Wild roll Wild roll
│ │ │ │ │
├─ 4.5% ├─ 4.5% ├─ 4.5% ├─ 4.5% ├─ 4.5%
│ │ │ │ │
▼ ▼ ▼ ▼ ▼
WILD NORMAL NORMAL WILD NORMAL
WWWW strip strip WWWW strip
│ │ │
▼ ▼ ▼
4 symbols 4 symbols 4 symbols

So the physical reel strip contains only normal symbols.
For example:
L1 L2 H1 L3 L4 SC H2 L1 H3 ...

Then draw_wild_board() decides:
const isWildReel = Math.random() < 0.045;

If true:
board[reel] = ["W", "W", "W", "W"];

Otherwise:
board[reel] = getFourSymbolsFromReelStrip(reel);

But there is one important issue
Your original strips have:
200 total positions
191 normal
9 W

Those 9 W positions were providing the 4.5% probability.
Once you remove W, you have:
191 normal positions

You now have two choices.
Option A, simplest and safest
Use the 191-stop W-free strips.
The Wild probability comes entirely from:
draw_wild_board() = 4.5%

This is what I recommend if your production reel engine supports arbitrary strip lengths.
The normal symbol probabilities remain:
L1 = 24/191
L2 = 32/191
L3 = 41/191
...
SC = 9/191

Option B, if production requires exactly 200 stops
Then we need to rebuild the normal strips to 200 positions.
We cannot simply add 9 symbols.
We need to preserve the intended conditional normal-symbol probability distribution:
Original conditional distribution:

L1 = 24/191
L2 = 32/191
L3 = 41/191
...

Then create a 200-stop W-free strip whose frequencies approximate those probabilities.
After that:
Wild probability = 4.5%
Normal reel = 95.5%

and the 200-stop strip contains zero W.
What I recommend for Vice Cartel
Given that this is already implemented in production:
Do not change the production strip length yet.
First check this exact production function:
getFourSymbolsFromReelStrip(reelIndex)

or whatever your equivalent is.
If it expects a conventional circular strip:
stop = random(0, reel.length - 1)

row0 = reel[stop]
row1 = reel[stop + 1]
row2 = reel[stop + 2]
row3 = reel[stop + 3]

then 191-stop W-free strips are perfectly valid.
If it assumes:
random(0, 199)

or hardcodes 200 stops, then we need the 200-stop rebuilt version.
Most important
Your production algorithm should be exactly:
SPIN
│
┌────────▼────────┐
│ draw_wild_board │
└────────┬────────┘
│
┌────────▼────────┐
│ For each reel │
└────────┬────────┘
│
┌────────┴────────┐
│ │
Wild 4.5% Normal 95.5%
│ │
▼ ▼
WWWW physical W-free strip
│
▼
4 symbols

That is the solution.
And importantly, do not modify the RTP/paytable/bonus probabilities yet. First make the reel generation match this architecture, then run 1M/10M base simulations and compare the resulting Base RTP against the calibrated 40.331%. If it moves materially, then we know the old PAR's base simulation was using the wrong reel-generation model.
