"""Lease review pipeline on Cominty built-in agents.

Stages:
  1. Hive reads the uploaded PDF and asks clarifying questions (thread A)
  2. Hive finalises the analysis after the user answers (thread A)
  3. Planner writes a negotiation plan from text only (thread B)
  4. Hive writes the risk summary and landlord email from the plan (thread C)
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from decimal import Decimal

from cominty_sdk import Question
from cominty_sdk.events import Result

from leaselens.cominty_client import HIVE_AGENT, PLANNER_AGENT, make_client
from leaselens import prompts

ProgressFn = Callable[[str], None]


@dataclass
class Review:
    thread_id: str
    questions: list[Question] = field(default_factory=list)
    analysis: str = ""
    cost_usd: Decimal = Decimal(0)


IDLE_TIMEOUT_S = 120


async def _drain(client, run, on_progress: ProgressFn) -> Decimal:
    """Consume the progress stream. Final text is read via run.text().

    Returns the run's cost in USD, taken from the Result event. Raises if no
    event arrives for IDLE_TIMEOUT_S, after cancelling the in-flight message
    so the thread is not left busy.
    """
    cost = Decimal(0)
    events = run.__aiter__()
    try:
        while True:
            try:
                event = await asyncio.wait_for(events.__anext__(), IDLE_TIMEOUT_S)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"Cominty stream sent no event for {IDLE_TIMEOUT_S}s "
                    f"(message {run.message_id})."
                ) from None
            label = getattr(event, "name", None) or type(event).__name__
            on_progress(f"{label}")
            if isinstance(event, Result):
                cost = event.data.cost.total
    except BaseException:
        await _cancel_quietly(client, run.message_id)
        raise
    return cost


async def _cancel_quietly(client, message_id) -> None:
    """Best-effort cancel of an in-flight message. Errors are reported, not hidden."""
    try:
        await client.chat.cancel(message_id)
    except Exception as exc:  # e.g. already finished
        print(f"[pipeline] cancel of {message_id} skipped: {exc}", flush=True)


async def start_review(pdf_path: Path, on_progress: ProgressFn) -> Review:
    """Upload the lease and get Hive's first analysis or its questions."""
    async with make_client() as client:
        on_progress("Uploading lease")
        lease = await client.chat.upload_file(pdf_path)

        on_progress("Hive is reading the lease")
        run = await client.chat.start(
            agent_id=HIVE_AGENT,
            message=prompts.ANALYSE_PROMPT,
            name=f"Lease review: {pdf_path.name}",
            file_ids=[lease.id],
        )
        cost = await _drain(client, run, on_progress)

        questions = await run.questions()
        analysis = await run.text()  # raw reply, kept even when questions were asked
        return Review(
            thread_id=run.thread.id, questions=questions, analysis=analysis, cost_usd=cost
        )


async def finish_review(review: Review, answers: str, on_progress: ProgressFn) -> Review:
    """Send the user's answers back in the same thread and get the final analysis."""
    async with make_client() as client:
        on_progress("Hive is finalising the analysis")
        run = await client.chat.send(
            review.thread_id,
            agent_id=HIVE_AGENT,
            message=f"{prompts.FINALISE_PROMPT}\n\nUser answers:\n{answers}",
        )
        cost = await _drain(client, run, on_progress)
        return Review(
            thread_id=review.thread_id,
            analysis=await run.text(),
            cost_usd=review.cost_usd + cost,
        )


async def plan_and_draft(review: Review, on_progress: ProgressFn) -> dict:
    """Planner writes the strategy (no file access), then Hive drafts the email."""
    async with make_client() as client:
        on_progress("Planner is building the negotiation strategy")
        plan_run = await client.chat.start(
            agent_id=PLANNER_AGENT,
            message=prompts.PLAN_PROMPT.format(analysis=review.analysis),
            name="Negotiation plan",
        )
        cost = await _drain(client, plan_run, on_progress)
        result = await plan_run.result()
        # Planner puts the plan in structured_output["canvas"], which is None
        # when it wrote no plan (for example, it asked questions instead).
        plan = (result.structured_output or {}).get("canvas")
        if not plan:
            # Planner still asked questions. Force one plan in the same thread.
            on_progress("Planner asked questions, forcing a plan")
            follow_up = await client.chat.send(
                plan_run.thread.id, agent_id=PLANNER_AGENT, message=prompts.FORCE_PLAN_PROMPT
            )
            cost += await _drain(client, follow_up, on_progress)
            result = await follow_up.result()
            plan = (result.structured_output or {}).get("canvas")
        if not plan:
            raise RuntimeError(
                "Planner did not return a plan. Its reply was: " + result.content[:300]
            )

        on_progress("Hive is drafting the summary and email")
        draft_run = await client.chat.start(
            agent_id=HIVE_AGENT,
            message=prompts.DRAFT_PROMPT.format(analysis=review.analysis, plan=plan),
            name="Risk summary and draft email",
        )
        cost += await _drain(client, draft_run, on_progress)
        return {"plan": plan, "draft": await draft_run.text(), "cost_usd": cost}
