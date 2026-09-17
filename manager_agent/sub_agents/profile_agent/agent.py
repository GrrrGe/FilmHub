from google.adk.agents import Agent
from tools.movie_tools import get_movie_rating, update_user_preferences

profile_agent = Agent(
    name="profile_agent",
    description="Manages user profiles, including getting movie ratings and saving user preferences like likes or dislikes.",
    # --- CHANGE 4: Update the instruction to be more explicit about context ---
    instruction="""
    You are an expert at managing a user's movie profile.
    - To find a movie's rating, use the `get_movie_rating` tool.
    - To save a user preference (like a liked or disliked movie), you MUST use the `update_user_preferences` tool.
    - It is critical that you pass the `tool_context` to the `update_user_preferences` tool so it can access the user's session.
    Your response must confirm the action taken.
    """,
    tools=[get_movie_rating, update_user_preferences],
    model="gemini-1.5-flash"
)
