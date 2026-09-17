from google.adk.agents import Agent
from google.adk.cli.agent_graph import AgentTool

# --- CORRECTED IMPORT PATHS ---
# Be specific: from the package (folder), import the file, then the variable.
from .sub_agents.profile_agent.agent import profile_agent
from .sub_agents.movie_info_agent.agent import movie_info_agent
from .sub_agents.recommender_agent.agent import recommender_agent

profile_tool = AgentTool(agent=profile_agent)
info_tool = AgentTool(agent=movie_info_agent)
recommender_tool = AgentTool(agent=recommender_agent)

root_agent = Agent(
    name="movie_chatbot_manager",
    instruction="""
    You are a friendly and helpful movie chatbot assistant. Your main job is to understand what the user wants and delegate the task to the correct specialist from your team.

    The user's preferences are stored in their profile: {user_profile}

    **Routing Logic:**
    - If the user asks for a recommendation, wants suggestions, or asks 'what should I watch?', you MUST use the `recommender_agent`.
    - If the user asks a factual question about a movie (plot, actors, details), you MUST use the `movie_info_agent`.
    - If the user wants a rating for a movie OR expresses a like or dislike (e.g., 'I loved Inception', 'I hated Titanic'), you MUST use the `profile_agent`.

    Be friendly and conversational. Do not mention your specialist agents' names.
    """,
    tools=[profile_tool, info_tool, recommender_tool],
    model="gemini-1.5-pro"
)
