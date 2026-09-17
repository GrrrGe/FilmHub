import pandas as pd
import google.generativeai as genai
import os
import time
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure the Gemini API key
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    logging.info("Gemini model configured successfully.")
except Exception as e:
    logging.error(f"Failed to configure Gemini model: {e}. "
                  "Please ensure GEMINI_API_KEY environment variable is set correctly.")
    exit()

# --- IMPORTANT CHANGE HERE ---
# The script will now read from and overwrite this file.
DATA_FILE_PATH = "data/imdb_cleaned.csv" 

# Load your existing data
try:
    df = pd.read_csv(DATA_FILE_PATH)
    logging.info(f"Loaded {len(df)} movies from {DATA_FILE_PATH}")
except FileNotFoundError:
    logging.error(f"Error: {DATA_FILE_PATH} not found. Please check the path.")
    exit()

# Add a new 'Generated_Plot' column if it doesn't exist, initialized to None
# If it exists, existing plots will be overwritten for movies that don't have a valid plot.
if 'Generated_Plot' not in df.columns:
    df['Generated_Plot'] = None
    logging.info("Added 'Generated_Plot' column to DataFrame.")
else:
    logging.info("'Generated_Plot' column already exists. Checking for missing/error plots to re-generate.")


# --- Function to generate plot for a single movie ---
def generate_movie_plot(title, year, genre, director, star_cast):
    """
    Generates a concise plot summary using the Gemini LLM.
    """
    prompt = (
        f"Generate a concise, engaging plot summary (around 3-5 sentences) for a movie with the following details:\n"
        f"Title: {title}\n"
        f"Year: {year}\n"
        f"Genre: {genre}\n"
        f"Director: {director}\n"
        f"Star Cast: {star_cast}\n"
        f"Ensure the plot captures the main premise and avoids excessive detail. Do not include release year or cast names in the plot."
    )

    try:
        response = model.generate_content(prompt)
        generated_plot = response.text
        if generated_plot:
            return generated_plot.strip()
        else:
            return "No plot generated."
    except Exception as e:
        logging.error(f"Error during Gemini API call for '{title}': {e}")
        return "Error generating plot."

# --- Iterate through each movie and generate/update plot ---
logging.info("Starting plot generation process...")
for index, row in df.iterrows():
    title = row['Title']
    year = row.get('Year', 'N/A')
    genre = row.get('Genre', 'N/A')
    director = row.get('Director', 'N/A')
    star_cast = row.get('Star Cast', 'N/A')
    
    # Get the current value of 'Generated_Plot' for this row
    current_plot = row.get('Generated_Plot')

    if pd.isna(title):
        logging.warning(f"Skipping row {index}: Missing title.")
        continue
    
    # Generate plot only if it's missing or marked as an error from a previous run
    if pd.isna(current_plot) or current_plot == "No plot generated." or current_plot == "Error generating plot.":
        logging.info(f"Generating plot for: {title}...")
        plot = generate_movie_plot(title, year, genre, director, star_cast)
        df.at[index, 'Generated_Plot'] = plot
        # Add a delay to respect API rate limits
        time.sleep(0.5) # Adjust this delay if you face rate limit errors
    else:
        logging.debug(f"Plot already exists and is valid for: {title}. Skipping generation.")

# --- Save the updated DataFrame back to the original CSV ---
try:
    df.to_csv(DATA_FILE_PATH, index=False)
    logging.info(f"\n✅ Updated data with generated plots saved successfully to {DATA_FILE_PATH}")
except Exception as e:
    logging.error(f"❌ Failed to save updated data to {DATA_FILE_PATH}: {e}")