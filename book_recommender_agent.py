from google.adk.agents import Agent

def recommend_book(preferences: dict) -> dict:
    """Recommends a book based on user preferences.

    Args:
        preferences (dict): A dictionary with keys like 'genre' and 'mood'.

    Returns:
        dict: A dictionary with 'status' and either a 'recommendation' or an 'error_message'.
    """
    genre = preferences.get("genre", "").lower()
    mood = preferences.get("mood", "").lower()

    # Simple hardcoded logic (can be replaced with LLM or API calls)
    if genre == "science fiction" and "adventurous" in mood:
        return {
            "status": "success",
            "recommendation": "I recommend *Project Hail Mary* by Andy Weir — it's an inventive, science-heavy adventure with emotional depth."
        }
    elif genre == "fantasy" and "escape" in mood:
        return {
            "status": "success",
            "recommendation": "Try *The Name of the Wind* by Patrick Rothfuss — an immersive fantasy with lyrical prose and a compelling underdog hero."
        }
    elif genre == "mystery":
        return {
            "status": "success",
            "recommendation": "You might enjoy *The Girl with the Dragon Tattoo* by Stieg Larsson — a gripping, gritty thriller full of twists."
        }
    else:
        return {
            "status": "error",
            "error_message": "Sorry, I couldn't find a recommendation for those preferences."
        }

root_agent = Agent(
    name="book_recommender_agent",
    model="gemini-2.0-flash",
    description="Agent that recommends books based on your preferences.",
    instruction="Ask me for a book recommendation based on genre and mood.",
    tools=[recommend_book]
)
