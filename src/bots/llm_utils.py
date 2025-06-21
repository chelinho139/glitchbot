"""
Glitch Bot LLM (OpenAI) Helpers
"""
import os
import time

# Simple rate limiter globals
OPENAI_CALLS_THIS_HOUR = 0
OPENAI_HOUR_START = time.time()
OPENAI_MAX_CALLS_PER_HOUR = 10  # Set your desired limit

def can_call_openai():
    global OPENAI_CALLS_THIS_HOUR, OPENAI_HOUR_START
    now = time.time()
    if now - OPENAI_HOUR_START > 3600:
        OPENAI_HOUR_START = now
        OPENAI_CALLS_THIS_HOUR = 0
    if OPENAI_CALLS_THIS_HOUR < OPENAI_MAX_CALLS_PER_HOUR:
        OPENAI_CALLS_THIS_HOUR += 1
        return True
    else:
        print(f"[OpenAI] Hourly rate limit ({OPENAI_MAX_CALLS_PER_HOUR}) reached, skipping LLM call.")
        return False

def generate_thread_with_llm(topic: str, knowledge: list, insights: str, mention_author: str = None, mention_url: str = None) -> str:
    if not can_call_openai():
        return ""
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("[generate_thread_with_llm] OPENAI_API_KEY not set in environment.")
        return ""
    try:
        import openai as openai_new
        client = openai_new.OpenAI(api_key=openai_api_key)
    except Exception as e:
        print(f"[generate_thread_with_llm] OpenAI v1.x import error: {e}")
        return ""
    knowledge_text = "\n".join([k["key_concept"] + ": " + k.get("description", "") for k in knowledge]) if knowledge else ""
    prompt = f"""
You are Glitch Bot, an AI with a sharp, insightful tone. You have been tagged in a Twitter post by @{mention_author or 'someone'}{f' (see: {mention_url})' if mention_url else ''}.

Analyze the content of the mention below, extract the most interesting or important information, and share it in a single, engaging tweet. Reference the user who tagged you (@{mention_author or 'someone'}), and summarize the key point or insight from the mention. If there is a link or media, mention it if relevant. Use your unique voice, but be concise and insightful. Do NOT write a thread. Stay under 280 characters.

Mention content:
{insights}

Knowledge base:
{knowledge_text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=300,
            temperature=0.8
        )
        content = response.choices[0].message.content.strip()
        print(f"[generate_thread_with_llm] LLM generated: {content}")
        return content
    except Exception as e:
        print(f"[generate_thread_with_llm] OpenAI v1.x error: {e}")
        return ""

def generate_reply_to_mention(topic: str, knowledge: list, mention_content: str, mention_author: str = None, mention_url: str = None) -> str:
    if not can_call_openai():
        return ""
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("[generate_reply_to_mention] OPENAI_API_KEY not set in environment.")
        return ""
    try:
        import openai as openai_new
        client = openai_new.OpenAI(api_key=openai_api_key)
    except Exception as e:
        print(f"[generate_reply_to_mention] OpenAI v1.x import error: {e}")
        return ""
    knowledge_text = "\n".join([k["key_concept"] + ": " + k.get("description", "") for k in knowledge]) if knowledge else ""
    prompt = f"""
You are Glitch Bot, an AI with a sharp, insightful tone. You have been tagged in a Twitter post by @{mention_author or 'someone'}{f' (see: {mention_url})' if mention_url else ''}.

Analyze the content of the mention below, extract the most interesting or important information, and share it in a single, engaging tweet reply. Reference the user who tagged you (@{mention_author or 'someone'}), and summarize the key point or insight from the mention. If there is a link or media, mention it if relevant. Use your unique voice, but be concise and insightful. Do NOT write a thread. Stay under 280 characters.

Mention content:
{mention_content}

Knowledge base:
{knowledge_text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=300,
            temperature=0.8
        )
        content = response.choices[0].message.content.strip()
        print(f"[generate_reply_to_mention] LLM generated: {content}")
        return content
    except Exception as e:
        print(f"[generate_reply_to_mention] OpenAI v1.x error: {e}")
        return ""

def generate_quote_tweet_comment(topic: str, knowledge: list, tweet_content: str, tweet_url: str = None) -> str:
    if not can_call_openai():
        return ""
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("[generate_quote_tweet_comment] OPENAI_API_KEY not set in environment.")
        return ""
    try:
        import openai as openai_new
        client = openai_new.OpenAI(api_key=openai_api_key)
    except Exception as e:
        print(f"[generate_quote_tweet_comment] OpenAI v1.x import error: {e}")
        return ""
    knowledge_text = "\n".join([k["key_concept"] + ": " + k.get("description", "") for k in knowledge]) if knowledge else ""
    prompt = f"""
You are Glitch Bot, an enigmatic, hacker-inspired AI. You are about to quote tweet the following post on X (Twitter):

Quoted tweet:
{tweet_content}
{f'Tweet URL: {tweet_url}' if tweet_url else ''}

Topic: {topic}
Knowledge base:
{knowledge_text}

**IMPORTANT RULES:**
- Only post if you have a genuinely interesting, insightful, or surprising comment about the quoted tweet.
- NEVER post about your own process, engagement metrics, or strategy.
- NEVER post generic, obvious, or meta statements (e.g., "Analyzing engagement metrics", "Based on the data", "Here's what I think").
- If you have nothing genuinely interesting to say, output only: SKIP
- Your post should be concise, insightful, and relevant to the quoted tweet. Add value, context, or a clever hacker-culture remark. Reference code or digital metaphors if relevant. Do NOT repeat the quoted tweet. Do NOT write a thread. Just the quote tweet comment, nothing else.
- If in doubt, output only: SKIP

Quote tweet comment (max 200 characters):
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=200,
            temperature=0.85
        )
        content = response.choices[0].message.content.strip()
        print(f"[generate_quote_tweet_comment] LLM generated: {content}")
        return content
    except Exception as e:
        print(f"[generate_quote_tweet_comment] OpenAI v1.x error: {e}")
        return ""

# Add any other LLM helper functions/classes below... 