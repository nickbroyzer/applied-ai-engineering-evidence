# 7. Help search: fix the content first, then add vectors

**In short:** a 24-question test of the in-app help found 6 refusals and 4 answers from the wrong article. Rewriting the articles came first and got refusals down to 2. Adding meaning-based search got them to 0, with the right article first on all 24. It went live only together with cost and abuse limits.

## What the test found
In Session 463, 24 real questions were put to Ask Zelbi Help. The results:
- 6 refusals and 4 answers from the wrong article.
- Answers that pasted 1,600 to 2,000 characters.
- All 8 help articles last edited in July.
- The golden evaluation table was empty.

## Step 1: content, not models
The articles were rewritten to match the app's current rules and 4 were added. Answers can no longer come from a title-only section. The 22-case golden set was loaded and passes with 0 leaks. **Result:** 2 refusals, and answers mostly 200 to 900 characters (D536; the figures are recorded in the project backlog).

## Step 2: meaning-based search, fused with text search
Each article and each typed question becomes a vector (Voyage `voyage-3.5`). The vector ranking is fused with the existing full-text ranking by reciprocal rank:

```python
VECTOR_TOP_N = 8
RRF_K = 60
VECTOR_SIMILARITY_FLOOR = 0.45
...
fused[item.chunk_id] = fused.get(item.chunk_id, 0.0) + 1.0 / (RRF_K + rank)
```

The 0.45 floor was calibrated on 24 real and 5 off-topic questions. Any embedding failure (no key, network, rate limit) falls back to text-only search. **Result:** 0 refusals, the right article first on all 24, off-topic questions still refused, the golden set 22/22 with 0 leaks, and 114 knowledge tests passing (D537; the test count is recorded in the project backlog).

## Step 3: it can't run up the bill
Help now costs money per question, so it shipped only with limits (D538):
- Sign-in required, at 30 questions an hour per account.
- At most 1,000 embedding calls a day, counted from the query log so a restart can't reset it. Past that, help falls back to free text search and never stops answering.
- Questions capped at 300 characters.
- Abuse alerts go to the admin dashboard.

No model writes the answer. Answers are extracted from the articles and cite them.

The embedding half now has automated tests: 7 in `test_knowledge_hybrid_path.py` (commit `0cd7e3ce`). They run with Voyage never called, and cover four things:
- a meaning-only match ranks first, with the two rankings fused by reciprocal rank;
- below the floor the search refuses, and above it answers;
- an embedding failure falls back to text only;
- at the daily ceiling it uses text only, and one call below it still uses vectors.

Two limits remain, stated plainly. The 24-question before-and-after result comes from the project's decision log; the run itself was not saved as a file. And the recorded 22/22 golden evaluations ran on text-only retrieval.

## What this shows
The first fix for a retrieval problem was the documents. Vectors came second, were measured before and after, and shipped behind cost controls.
