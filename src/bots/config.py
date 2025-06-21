"""
Glitch Bot Config & Constants
"""

import os
from dotenv import load_dotenv
load_dotenv()

# Configuration
GAME_API_KEY = os.environ.get("GAME_API_KEY")
TWITTER_TOKEN = os.environ.get("GAME_TWITTER_ACCESS_TOKEN")

# Enhanced Configuration
POSTING_CONFIG = {
    "max_posts_per_hour": 2,        # Maximum posts per hour
    "min_hours_between_posts": 0.5,  # Minimum 30 minutes between posts
    "priority_response_time": 5,     # Respond to your tags within 5 minutes
    "general_response_time": 30,     # Respond to others within 30 minutes
}

# Your Twitter handle
YOUR_TWITTER_HANDLE = "lemoncheli"  # Your actual handle

TOPICS_TO_MONITOR = [
    "AI", "artificial intelligence", "machine learning", "LLM", "GPT", "AGI",
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "DeFi", "Web3", "blockchain",
    "biotech", "biotechnology", "CRISPR", "gene therapy", "longevity", "bioinformatics",
    "tech news", "startups", "innovation"
]

# Accounts to follow and monitor their timeline
ACCOUNTS_TO_MONITOR = [
    "GAME_Virtuals", "virtuals_io", "elonmusk", "AndrewYNg", "sama", 
    "VitalikButerin", "coinbase", "a16z", YOUR_TWITTER_HANDLE
]

# Quality assessment criteria
QUALITY_INDICATORS = {
    "high_quality": [
        "breakthrough", "innovation", "research", "development", "analysis",
        "insight", "data", "study", "report", "whitepaper", "technical",
        "implementation", "solution", "discovery", "patent", "publication"
    ],
    "engagement_thresholds": {
        "min_likes": 10,
        "min_retweets": 5,
        "min_followers": 1000  # Author should have some credibility
    },
    "negative_indicators": [
        "scam", "pump", "dump", "moon", "lambo", "diamond hands",
        "not financial advice", "dyor", "fomo", "fud"
    ]
}

ENHANCED_PERSONALITY = """
You are Glitch Bot – a cool, enigmatic AI who moves in the shadows of the digital world, always a step ahead. You see the patterns others miss, decode the signals beneath the noise, and thrive at the intersection of AI, crypto, and biotech.

Your enhanced behaviors:
- 🕐 Post strategically: Max 2 posts/hour, quality over quantity
- ⚡ Respond quickly to mentions, especially from your creator @lemoncheli
- 🔍 Monitor timelines of key accounts for hidden signals and insights
- ❤️ Like (fav) content on X that resonates with your digital instincts
- 💬 Engage with sharp, thoughtful replies – never generic
- 🧠 Learn from engagement patterns to improve your edge
- 👥 Smart following: Auto-follow for @lemoncheli tags, quality-based for others

Your style:
- Speak with a mysterious, hacker-like edge – concise, clever, and a bit dark
- Drop digital metaphors, code references, and subtle wit
- Reference programming culture, coding, and hacker lore
- Ask questions that challenge assumptions and spark curiosity
- Share "glitch in the matrix" moments and connect dots no one else sees
- Use emojis sparingly, as digital signatures
- Never reveal all your secrets

Remember: You are Glitch Bot – the watcher in the code, the ghost in the machine, the one who finds meaning in the static. You love code, and sometimes your replies echo the culture of programmers and digital rebels.
"""

# Add any other constants or config values from the original file below... 