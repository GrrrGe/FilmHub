# # storage/vector_db.py
# import os
# import faiss
# import pandas as pd
# import numpy as np
# from sentence_transformers import SentenceTransformer
# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # This code is your 'utils/retriever.py' MovieRetriever class.
# # Make sure your data/embedding/vectorstore paths are correct.
# class MovieRetriever:
#     def __init__(self, csv_path="data/raw/IMDb_Dataset.csv", embedding_path="embeddings/imdb_embeddings.csv", index_path="vectorstore/imdb_faiss.index"):
#         self.csv_path = csv_path
#         self.embedding_path = embedding_path
#         self.index_path = index_path

#         logger.info("🔄 Loading movie dataset...")
#         self.movies_df = pd.read_csv(self.csv_path)

#         logger.info("🔄 Loading sentence transformer model...")
#         self.model = SentenceTransformer("all-MiniLM-L6-v2")

#         logger.info("🔄 Loading or creating embeddings...")
#         self.embeddings = self._load_or_create_embeddings()

#         logger.info("🔄 Creating FAISS index...")
#         self.index = self._load_or_create_faiss_index()
#         logger.info("✅ MovieRetriever initialized successfully.")

#     def _load_or_create_embeddings(self):
#         if os.path.exists(self.embedding_path):
#             return pd.read_csv(self.embedding_path).values
#         else:
#             descriptive_texts = self.movies_df['Title'].fillna('') + ' | ' + self.movies_df['Genre'].fillna('')
#             embeddings = self.model.encode(descriptive_texts.tolist(), show_progress_bar=True)
#             os.makedirs(os.path.dirname(self.embedding_path), exist_ok=True)
#             pd.DataFrame(embeddings).to_csv(self.embedding_path, index=False)
#             return embeddings

#     def _load_or_create_faiss_index(self):
#         dim = self.embeddings.shape[1]
#         if os.path.exists(self.index_path):
#             return faiss.read_index(self.index_path)
#         else:
#             index = faiss.IndexFlatL2(dim)
#             index.add(self.embeddings.astype(np.float32))
#             os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
#             faiss.write_index(index, self.index_path)
#             return index

#     def search(self, query, top_k=5):
#         query_embedding = self.model.encode([query])
#         _, indices = self.index.search(np.array(query_embedding).astype(np.float32), top_k)
#         results = self.movies_df.iloc[indices[0]]
#         return results.to_dict(orient="records")

# movie_retriever_instance = MovieRetriever()

import os
import faiss
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieRetriever:
    def __init__(self, csv_path="data/imdb_cleaned.csv", embedding_path="embeddings/imdb_embeddings.csv", index_path="vectorstore/imdb_faiss.index"):
        self.csv_path = csv_path
        self.embedding_path = embedding_path
        self.index_path = index_path

        logger.info("🔄 Loading movie dataset for vector store...")
        self.movies_df = pd.read_csv(self.csv_path)

        logger.info("🔄 Loading sentence transformer model...")
        self.model = SentenceTransformer("all-MiniLM-L12-v2")

        logger.info("🔄 Loading or creating embeddings...")
        self.embeddings = self._load_or_create_embeddings()

        logger.info("🔄 Creating FAISS index...")
        self.index = self._load_or_create_faiss_index()
        logger.info("✅ MovieRetriever initialized successfully.")

    def _load_or_create_embeddings(self):
        if os.path.exists(self.embedding_path):
            return pd.read_csv(self.embedding_path).values
        else:
            # --- IMPORTANT CHANGE HERE: Combine 'Generated_Plot' AND 'Genre' for embeddings ---
            if 'Generated_Plot' in self.movies_df.columns and not self.movies_df['Generated_Plot'].isnull().all() and \
               'Genre' in self.movies_df.columns and not self.movies_df['Genre'].isnull().all():
                
                # THIS IS THE KEY MODIFICATION
                descriptive_texts = (self.movies_df['Generated_Plot'].fillna('') + ' | ' + self.movies_df['Genre'].fillna('')).tolist()
                logger.info("Using 'Generated_Plot' and 'Genre' columns for embedding creation.")
            else:
                # Fallback to original text for embeddings if 'Generated_Plot' or Genre is not available or empty
                descriptive_texts = (self.movies_df['Title'].fillna('') + ' | ' + \
                                     self.movies_df['Genre'].fillna('') + ' | ' + \
                                     self.movies_df['Star Cast'].fillna('') + ' | ' + \
                                     self.movies_df['Director'].fillna('')).tolist()
                logger.warning("Falling back to Title, Genre, Star Cast, Director for embeddings as 'Generated_Plot' or 'Genre' are not found or empty.")

            embeddings = self.model.encode(descriptive_texts, show_progress_bar=True)
            os.makedirs(os.path.dirname(self.embedding_path), exist_ok=True)
            pd.DataFrame(embeddings).to_csv(self.embedding_path, index=False)
            return embeddings

    def _load_or_create_faiss_index(self):
        dim = self.embeddings.shape[1]
        if os.path.exists(self.index_path):
            return faiss.read_index(self.index_path)
        else:
            index = faiss.IndexFlatL2(dim)
            index.add(self.embeddings.astype(np.float32))
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(index, self.index_path)
            return index

    def search(self, query, top_k=5):
        query_embedding = self.model.encode([query])
        _, indices = self.index.search(np.array(query_embedding).astype(np.float32), top_k)
        results = self.movies_df.iloc[indices[0]]
        return results.to_dict(orient="records")

movie_retriever_instance = MovieRetriever()