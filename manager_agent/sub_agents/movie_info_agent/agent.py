# # manager_agent/sub_agents/movie_info_agent.py
# from google.adk.agents import Agent
# from tools.movie_tools import search_movies

# movie_info_agent = Agent(
#     name="movie_info_agent",
#     description="Finds specific information about movies using its search tool.",
#     instruction="You are a movie encyclopedia. Use the `search_movies` tool to answer factual questions about movies, plots, actors, or genres. Provide detailed answers from the tool's results.",
#     tools=[search_movies],
#     model="gemini-1.5-flash"  # <-- ADD THIS LINE
# )


# In sub_agents/movie_info_agent/agent.py

from google.adk.agents import Agent
from tools.movie_tools import search_movies

movie_info_agent = Agent(
    name="movie_info_agent",
    description="Finds specific information about movies using its search tool.",
    # --- MAKE THIS EXACT CHANGE TO THE INSTRUCTION ---
    instruction="You are a movie encyclopedia. Use the `search_movies` tool to answer factual questions about movies. When asked for a movie's plot, specifically extract and provide the content of the 'plot' field from the tool's results. For other questions, provide detailed answers from the tool's results including actors, genre, etc.",
    tools=[search_movies],
    model="gemini-1.5-flash"
)