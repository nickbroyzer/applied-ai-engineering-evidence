# 8. The support agent: 4 of 10, then 9 of 10, then 4 of 4

**In short:** a Claude agent reviews trust-and-safety reports and proposes a decision for a person to approve. Its first scored round got 4 of 10 right, by handing hard cases back. Its reasons were saved, before any fix, in its own words. After the fixes it scored 9 of 10, then 4 of 4 on a new kind of case.

## The design
- Claude Haiku with ten read-only tools, each locked to the one case.
- It proposes, and a person approves. It can never suspend anyone or move money. The one exception is a confirmed missed pickup, which gives an undoable Zelbi credit.
- Text inside a case is information, never instructions.
- Every failure path hands the case to a person.
- A daily spending cap, with alerts at 80 and 100 percent.
- A leak guard on the one line a user can see.
- At hour 23, with no human action, it may carry out only undoable decisions. The deadline alerts involve no AI at all.

## The scored rounds
These ran against 15 seeded cases with a written answer key:
- **Run 1 (Oct 8): 4 correct of 10, and 1 partial.** It handed back 5 cases it should have decided. In its own words, these held it back: test flags on the listings, the reporter's count of reports in 24 hours, a photo that didn't match its title, and finding no policy to cite. Cost: $0.037 for the ten.
- **Run 2 (Oct 8, after fixes): 9 of 10,** for $0.028 for ten cases. One miss is kept on record: rude in person, which should be dismissed and was still handed off. One pass is marked "stronger than the key": hide and pause where the key says hide only.
- **Run 3 (Oct 9, new missed-pickup rule): 4 of 4,** for $0.012 for four cases.

There are 275 agent tests, run against a fake model so they cost nothing.

Not done yet, so not claimed: a fourth round scoring the agent's confidence, a comparison of three models on the same cases, and a runnable offline package for the agent's evaluation.

## What this shows
The failures were measured and kept, and the system was fixed rather than the score. Everything risky stays with a person.
