# Multi-Agent-Recommender-System-MARS

## Project Overview

The `Multi-Agent-Recommender-System-MARS` project is an intelligent chatbot designed to provide movie-related information and personalized recommendations. It leverages a multi-agent architecture where specialized AI agents collaborate and delegate tasks to fulfill user queries. This system integrates large language models (LLMs) with a custom vector database for semantic search and utilizes dynamically generated content for enhanced functionality.

## Features

* **Movie Plot Retrieval:** Get concise plot summaries for movies.
* **Movie Rating Retrieval:** Obtain IMDb ratings and vote counts for movies.
* **Personalized Movie Recommendations:** Receive movie suggestions based on a liked movie's themes and your viewing preferences.
* **User Preference Tracking:** Store and update user's liked and disliked movies for better personalization.
* **Multi-Agent Collaboration:** Intelligent routing of user queries to specialized agents.

## Architecture: High-Level Design

The system is built around a multi-agent architecture, orchestrated by a central `Manager Agent`. This manager acts as the brain, routing user requests to the most appropriate specialized "sub-agent" for processing. Each agent is powered by a large language model (LLM) and may have access to specific tools.

```
User Query
|
v
[ Root Agent (movie_chatbot_manager) ]
|  Delegates based on query type
+-------------------------------------------------+
|                 |                 |             |
v                 v                 v             v
[ Profile Agent ] [ Movie Info Agent ] [ Recommender Agent ] [ Critic Agent ]
(Manages user     (Retrieves factual    (Generates movie     (Analyzes movies
likes/dislikes)   movie data/plots)    recommendations)    for thematic summaries)
|
+-------------------+
|
v
[ Movie Tools ]
(e.g., search_movies, get_movie_rating, recommend_movies)
|
v
[ Storage ]
(e.g., IMDb data, Vector DB/FAISS Index)
```

## Low-Level Design & Key Components

The project is structured with distinct components for agents, tools, and data storage:

### 1. Agents (`sub_agents/`, `manager_agent/`)

* **`manager_agent/agent.py` (Root Agent)**:
    * **Role:** The central orchestrator. It receives user queries and, based on predefined routing logic, delegates the task to the most suitable sub-agent.
    * **Instruction:** Guides the agent to identify user intent (recommendation, factual question, preference update) and route to `recommender_agent`, `movie_info_agent`, or `profile_agent` respectively.
    * **Model:** `gemini-1.5-pro`.

* **`sub_agents/profile_agent/agent.py` (Profile Agent)**:
    * **Role:** Manages user preferences (liked/disliked movies) in the session state.
    * **Tools:** `update_user_preferences` tool.

* **`sub_agents/movie_info_agent/agent.py` (Movie Info Agent)**:
    * **Role:** Answers factual questions about movies, including plots, actors, and genres.
    * **Instruction:** Explicitly guided to use the `search_movies` tool and to **specifically extract and provide the content of the 'plot' field** when asked for a movie's plot. Also tasked with listing actors from the `Star Cast` field.
    * **Tools:** `search_movies` tool.
    * **Model:** `gemini-1.5-flash`.

* **`sub_agents/critic_agent/agent.py` (Critic Agent)**:
    * **Role:** Provides thematic analysis or summaries of a movie, which are then used as `base_query` for recommendations.
    * **Model:** `gemini-1.5-pro`.

* **`sub_agents/recommender_agent/agent.py` (Recommender Agent)**:
    * **Role:** Generates movie recommendations based on user preferences and movie themes.
    * **Instruction:** Designed to first use the `critic_agent` to get a thematic summary of a liked movie, and then use that summary as a query for the `recommend_movies` tool. **Crucially, it is explicitly instructed to only recommend ACTUAL, EXISTING MOVIES from the tool's results and ABSOLUTELY NOT to invent or alter movie titles or plots.** It must extract 'title' and 'plot' fields exactly as provided by the tool.
    * **Tools:** `critic_agent` (as an AgentTool) and `recommend_movies` tool.
    * **Model:** `gemini-1.5-pro`.

### 2. Tools (`tools/movie_tools.py`)

This module defines the callable functions that agents use to interact with data or external services.

* **`get_movie_rating(title: str)`**: Fetches IMDb rating and votes for a given movie.
* **`search_movies(query: str)`**: Performs keyword-based search across movie titles, genres, cast, and directors. This tool is responsible for retrieving movie details, including the generated plot.
* **`recommend_movies(...)`**: The core recommendation tool. It takes a `base_query` (thematic summary from critic), `liked_movies`, and `disliked_movies`, and performs a semantic search using the vector store.
* **`update_user_preferences(...)`**: Saves user's liked/disliked movies to the session state.

### 3. Storage (`storage/`)

This package manages data access and persistence.

* **`imdb_cleaned.csv` (data/):** The primary movie dataset. This file was initially sourced but later enriched with a `Generated_Plot` column containing LLM-generated plot summaries.
* **`storage/movie_data_access.py`**:
    * **Role:** Handles loading `imdb_cleaned.csv` into a Pandas DataFrame.
    * **Functions:** `search_movies_by_keywords` (which now correctly returns the `Generated_Plot` for factual queries) and `get_rating_by_title`.
* **`embeddings/imdb_embeddings.csv`**: Stores the numerical vector representations (embeddings) of the movies.
* **`vectorstore/imdb_faiss.index`**: The FAISS index, built from the embeddings, enabling efficient nearest-neighbor searches for recommendations.
* **`storage/vector_db.py`**:
    * **Role:** Manages the creation, loading, and searching of movie embeddings and the FAISS index.
    * **Embedding Generation:** Crucially, this module's `_load_or_create_embeddings` method was modified to use **both the `Generated_Plot` and `Genre`** of a movie to create its embedding, providing a richer semantic representation.
    * **Embedding Model:** Uses `SentenceTransformer("all-MiniLM-L12-v2")` (or similar) to generate embeddings.

## How it Works (Flows)

### Movie Plot Retrieval Flow

1.  **User Input:** "What is the plot of 'Blade Runner 2049'?"
2.  **`Manager Agent`:** Identifies the query as a factual movie question and delegates to `movie_info_agent`.
3.  **`Movie Info Agent`:** Receives the query. Its instruction guides it to use the `search_movies` tool.
4.  **`search_movies` tool:** Calls `movie_data_access.py`'s `search_movies_by_keywords` function with "Blade Runner 2049".
5.  **`movie_data_access.py`:** Searches `imdb_cleaned.csv` for the movie. Retrieves the row, including the `Generated_Plot` and `Star Cast`.
6.  **`search_movies` tool:** Returns the movie data (including 'plot') to the `Movie Info Agent`.
7.  **`Movie Info Agent`:** Based on its updated instruction, it specifically extracts the 'plot' field from the tool's results and presents it to the user.

### Movie Recommendation Flow

1.  **User Input:** "Can you recommend a movie like 'Parasite'?" (or "Since I liked 'Electric Mind'...")
2.  **`Manager Agent`:** Identifies the query as a recommendation request and delegates to `recommender_agent`.
3.  **`Recommender Agent`:**
    * Identifies the `liked_movie`/`base_query` (e.g., "Parasite" or "Electric Mind").
    * Calls the `critic_agent` with the identified movie.
4.  **`Critic Agent`:** Analyzes the movie and returns a JSON string containing a thematic `summary` (e.g., "a film about class disparity and social satire").
5.  **`Recommender Agent`:** Parses the `summary` from the critic's response. Uses this `summary` as the `base_query` for the `recommend_movies` tool.
6.  **`recommend_movies` tool:**
    * Embeds the `base_query` (thematic summary).
    * Uses `movie_retriever_instance.search` (from `vector_db.py`) to find the most semantically similar movies in the FAISS index. This search is now based on the embeddings created from `Generated_Plot` + `Genre`.
    * Retrieves the full movie data (including `Title`, `Generated_Plot`, `Genre`, `IMDb Rating`, etc.) for the top similar movies from `imdb_cleaned.csv`.
    * (Optional future step): Can apply filtering (e.g., exclude the input movie) or re-ranking (e.g., by IMDb Rating).
    * Returns a list of recommended movie dictionaries to the `Recommender Agent`.
7.  **`Recommender Agent`:** Based on its strict instructions, it iterates through the list of actual movies returned by the `recommend_movies` tool, extracting their `title` and `plot` (which is `Generated_Plot`) exactly as provided. It then presents these to the user with a brief explanation of why they were chosen.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/Vedant-1012/Multi-Agent-Recommender-System-MARS-.git](https://github.com/Vedant-1012/Multi-Agent-Recommender-System-MARS-.git)
    cd Multi-Agent-Recommender-System-MARS
    ```
2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    # Ensure google-generativeai, pandas, python-dotenv, faiss-cpu, sentence-transformers, uvicorn, fastapi are listed.
    # If not, install them manually:
    pip install google-generativeai pandas python-dotenv faiss-cpu sentence-transformers uvicorn fastapi
    ```
4.  **Obtain API Key:**
    * Get a Google Cloud API Key (for Gemini models).
    * Create a `.env` file in your project's root directory.
    * Add your API key to the `.env` file:
        ```
        GEMINI_API_KEY="YOUR_ACTUAL_GEMINI_API_KEY"
        ```
5.  **Prepare Data (Generate Plots):**
    * The `imdb_cleaned.csv` file should be in the `data/` directory.
    * Run the plot generation script (e.g., `generate_plots.py` from our discussions) to populate the `Generated_Plot` column in your `imdb_cleaned.csv`. This script will overwrite the file.
        ```bash
        python generate_plots.py
        ```
6.  **Generate Embeddings and FAISS Index:**
    * **Crucially**, delete the old embedding and FAISS index files to force regeneration with the updated `vector_db.py` logic:
        ```bash
        rm embeddings/imdb_embeddings.csv
        rm vectorstore/imdb_faiss.index
        ```
        (Use `del` instead of `rm` on Windows if needed).
    * The embeddings and FAISS index will be created automatically when you start the application for the first time after deletion.

7.  **Run the Application:**
    ```bash
    uvicorn main:app --reload
    ```
    The application will start, and you will see logs indicating the embedding generation process.

## Usage

Once the Uvicorn server is running (typically on `http://127.0.0.1:8000`), you can interact with your chatbot through the provided interface (e.g., a web UI if you have one, or by sending POST requests to the `/chat` endpoint).

**Example Queries:**

* "What is the plot of 'Parasite'?"
* "Who are the actors in 'The Matrix'?"
* "Can you recommend movies like 'Electric Mind'?"
* "I loved 'Inception'." (This will update your profile and could influence future recommendations).

## Challenges Faced & Solutions

This project involved several key debugging challenges:

1.  **Initial Plot Retrieval Failure:**
    * **Problem:** The chatbot couldn't provide movie plots initially.
    * **Cause:** The original `imdb_cleaned.csv` lacked a dedicated 'plot' column.
    * **Solution:** Implemented a script using an LLM to generate `Generated_Plot` summaries for all movies based on existing metadata (Title, Genre, Director, Star Cast) and added this as a new column to the dataset.

2.  **Recommendation Hallucination:**
    * **Problem:** The recommender agent was inventing movie titles and plots instead of recommending actual movies.
    * **Cause:** The LLM-powered recommender agent's instruction was too generic, allowing it to generate creative responses rather than strictly using tool output.
    * **Solution:** Drastically refined the `recommender_agent`'s instruction to explicitly command it to **only use actual movie titles and plots provided by its `recommend_movies` tool** and to "ABSOLUTELY DO NOT INVENT, ALTER, OR HALLUCINATE."

3.  **Embedding Generation Issues:**
    * **Problem:** The embedding generation process would get stuck at 0% during application startup.
    * **Cause:** This was primarily due to resource demands or potential compatibility issues with the initially chosen larger embedding model (`all-mpnet-base-v2`) on the specific system, or an internal hang during batch processing.
    * **Solution:** Switched to a different, more stable, and less resource-intensive SentenceTransformer model (`all-MiniLM-L12-v2`). Ensured old embedding and FAISS index files were deleted to force regeneration with the new content and model.

4.  **Persistent `faiss` Module Error (during development/testing):**
    * **Problem:** `ModuleNotFoundError: No module named 'faiss'` when trying to run Python code or scripts.
    * **Cause:** The `faiss-cpu` library was not correctly installed or accessible within the active Python virtual environment for the execution context.
    * **Solution:** Ensured `faiss-cpu` was installed via `pip install faiss-cpu` in the activated virtual environment.

5.  **LLM Plot Accuracy for Recommendations (Remaining Challenge):**
    * **Problem:** For some recommended movies, the chatbot's provided plot still deviated from the actual movie's plot, even when the `Generated_Plot` in the CSV was meant to be accurate.
    * **Cause:** The LLM within the `recommender_agent` might still, at times, re-synthesize or rephrase the `Generated_Plot` from the tool's output instead of presenting it verbatim, especially for obscure films where its internal knowledge might conflict or the generated plot is very generic.
    * **Partial Solution (and Future Work):** While instructions are strict, this is an inherent LLM behavior. The best current mitigation is improved `Generated_Plot` quality (official synopses) and post-retrieval filtering.

## Future Enhancements

* **Integrate Official Plot Summaries:** Implement fetching and incorporating actual, verified plot summaries from APIs like OMDb or TMDb directly into `imdb_cleaned.csv`. This is the most significant step for improving semantic accuracy.
* **Implement Post-Retrieval Ranking & Filtering:** Add logic in `movie_tools.py` to:
    * Filter out the input movie from recommendations.
    * Filter by minimum `IMDb Rating` or `MetaScore` to ensure quality recommendations.
    * Re-rank semantically similar results by popularity or rating.
* **Hybrid Recommendation System:** Explore integrating collaborative filtering techniques (like BPR) if user interaction data becomes available.
* **Advanced Embedding Models:** Experiment with even larger or task-specific embedding models if further semantic improvements are needed and resources allow.
* **Streamline Data Pipeline:** Automate the data enrichment (plot generation/fetching) and embedding generation as part of a more robust CI/CD pipeline.


## License

This project is licensed under the [MIT License](LICENSE.md).