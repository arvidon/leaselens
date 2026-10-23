ANALYSE_PROMPT = """You are reviewing an attached residential lease.
0. Start with a "Key lease facts" section, copied from the lease text only:
   parties, property address, lease start date, lease end date, monthly rent,
   security deposit amount, and notice periods. Write "not stated" for anything
   the lease does not say. Do not infer dates.
1. Identify risky or unusual clauses. Cover at least: security deposit terms,
   early termination and penalties, maintenance and repair responsibility,
   rent increase clauses, renewal/notice periods, and entry rights.
2. For each clause, quote it briefly, say why it is a risk, and rate it low/medium/high.
3. If you need facts about the tenant's situation to judge the risk (for example
   whether they plan to leave early), ask 1 to 3 clarifying questions and stop.
   Do not finalise the analysis until you have answers."""

FINALISE_PROMPT = """Using the user's answers, finalise the lease risk analysis from
earlier in this thread. Keep the "Key lease facts" section exactly as it was.
Keep the clause ratings, adjust them for the answers, and state which clauses
matter most for this tenant. Only describe the tenant's situation using the
user's answers below. Do not add events, meetings, or details they did not give."""

PLAN_PROMPT = """Plan a negotiation strategy with the landlord for this lease.
Base it on the analysis and tenant answers below. Write a plan that another
agent will execute. For each risky clause give: the ask, the fallback, and the
red line. Also give the order to raise the clauses, the points the landlord
email should make, and the assumptions you made. Do not ask questions; state
assumptions instead. Use only the key lease facts and tenant answers in the
analysis. Do not invent events, meetings, or walkthroughs.

{analysis}"""

FORCE_PLAN_PROMPT = """Do not ask any more questions. Choose the most sensible
option for anything still open, state those choices as assumptions, and write
the full negotiation plan now."""

DRAFT_PROMPT = """Execute the negotiation plan below for the tenant. Produce:
1. A prioritised negotiation table: Clause | Ask | Fallback | Red line, one row per risky clause.
2. A short risk summary, grouped high / medium / low.
3. A polite, firm draft email to the landlord that makes the Asks, with
   placeholders for the landlord's name and the tenant's name.

Rules:
- Use only facts that appear in the lease key facts, the clause text, or the
  tenant's answers. Use the lease start date from the key facts exactly as
  written. If a date or detail is not in those sources, write [to confirm]
  instead of guessing.
- Do not invent events, meetings, walkthroughs, conversations, or prior
  interactions with the landlord. The email must not thank the landlord for
  anything they did unless it appears in the sources.
- End the output with this exact line:
  "This is not legal advice — verify any cited laws or cases before use."

Analysis:
{analysis}

Plan:
{plan}"""
