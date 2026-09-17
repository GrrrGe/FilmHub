# # storage/state_schema.py
# from dataclasses import dataclass, field
# from typing import List, Optional

# @dataclass
# class UserProfile:
#     """Holds all information about a user's movie preferences."""
#     name: Optional[str] = None
#     liked_movies: List[str] = field(default_factory=list)
#     disliked_movies: List[str] = field(default_factory=list)
#     preferred_genres: List[str] = field(default_factory=list)

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class UserProfile:
    """Holds all information about a user's movie preferences."""
    name: Optional[str] = None
    liked_movies: List[str] = field(default_factory=list)
    disliked_movies: List[str] = field(default_factory=list)
    preferred_genres: List[str] = field(default_factory=list)