from google.adk.agents import Agent
import json

# --- FIX 2: Remove Pydantic schema to resolve the ADK warning. ---
# The agent will now generate a reliable JSON string directly.

critic_agent = Agent(
    name="critic_agent",
    description="Analyzes a given movie title and returns a JSON string with its themes, genre, and style.",
    instruction="""
    You are a world-class film critic. Given a movie title, provide a deep, analytical summary of its key themes, genre, and cinematic style.

    You MUST respond with ONLY a valid JSON object string and nothing else.
    The JSON object must have three keys: "themes", "genre_style", and "summary".
    - "themes" must be a list of strings.
    - "genre_style" must be a string.
    - "summary" must be a one-sentence string summarizing the analysis.

    Example response for the movie 'Parasite':
    {
        "themes": ["class conflict", "social inequality", "dark comedy", "family dynamics"],
        "genre_style": "A dark comedy thriller with elements of suspense and satire.",
        "summary": "A dark comedy thriller about class conflict and social inequality, explored through the lens of two families."
    }
    """,
    model="gemini-1.5-pro",
)
