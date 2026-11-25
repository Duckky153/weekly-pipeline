# How it was built

What AI did at each step, and what checked it.

1. **Study.** The posting, the company's public pages and product screens, and HubSpot's public docs on deal properties, pipelines and exports were read and saved with their dates.
2. **Plan.** Four AI helpers each planned one part (the field and HubSpot, the model step, the product, the claims). Their parts were merged into one plan, which three AI reviewers, new to it each time, took apart in turn; each round's findings were fixed before the next.
3. **Sample data.** A separate AI helper wrote the practice and scored exports one deal at a time from `sample/RULES.md`, with their answer keys, and searched every owner's full name on the web. It kept the scored export outside the build until the lock.
4. **Engine and recount.** The engine was written from the definitions. A different AI helper wrote `recount.py` from the definitions alone, without seeing the engine, and listed every place it had to guess. Both ran on a test export that breaks and passes every rule once, and on practice; each disagreement was settled in the definitions, which were then locked.
5. **The page.** Built on practice data in the company's visual language, then checked twice by two AI reviewers: one against the company's own product screens, one reading every visible word for clarity and anything that reads machine-made.
6. **The notes check.** Practice rounds on practice data only; the question changes are in `prompts/CHANGELOG.md`. An AI helper wrote the keyword rules from the labeling rules without seeing any deal.
7. **A model from a different AI company** wrote 15 deals' notes and its own 40-deal sample, and labeled 20 deals' notes before the read. AI readers checked its keys, and another settled every difference from the labeling rules.
8. **Lock, read, score.** Every file that decides a number, a tag or a score was fingerprinted in `lock.json`. The scored export was then read once, read again for the repeat check, and scored by `score.py`.
9. **Final reviews.** AI reviewers each took one view (a hiring manager and a sales lead, an engineer recomputing every number, truth and privacy, a first-time visitor, the look and every click, the publish path) before it went public. What they changed is in `CHANGES.md`.
