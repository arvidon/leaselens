from cominty_sdk import AsyncCominty

from leaselens.config import load_settings

# Built-in agent IDs. Source: docs.cominty.ai/guides/agents.md (fetched).
# platform.cominty.ai/agents is a sign-in page and lists no agents.
# Live-tested: all three IDs return replies via chat.start.
CHAT_AGENT = "__cominty_agents::agent.chat"
HIVE_AGENT = "__cominty_agents::agent.hive"  # does the work, reads files
PLANNER_AGENT = "__cominty_agents::agent.planner"  # plans only, no files, plan in structured_output["canvas"]


def make_client() -> AsyncCominty:
    settings = load_settings()
    kwargs = {"api_token": settings.api_key, "user_id": settings.user_id}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return AsyncCominty(**kwargs)
