"""
Glitch Bot Agent Logic (Workers, Functions)
"""
from datetime import datetime, timedelta
import random
from typing import Tuple
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import Function, Argument, FunctionResult, FunctionResultStatus
from src.bots.config import POSTING_CONFIG, YOUR_TWITTER_HANDLE, QUALITY_INDICATORS, ENHANCED_PERSONALITY, ACCOUNTS_TO_MONITOR, TOPICS_TO_MONITOR, GAME_API_KEY
from src.bots.glitch_bot_db import TwitterAgentDB
from src.bots.twitter_utils import get_twitter_client, call_with_rate_limit_handling
from src.bots.llm_utils import generate_thread_with_llm
import time

db = TwitterAgentDB("enhanced_glitch_bot_v2.db")

def get_enhanced_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    # ... (copy logic from enhanced_glitch_bot_v2.py)
    initial_state = {
        "knowledge_base": {
            "AI": [], "crypto": [], "biotech": [], "cross_connections": []
        },
        "posting_history": [],
        "mention_queue": [],
        "timeline_insights": [],
        "engagement_tracking": {},
        "last_post_time": None,
        "posts_this_hour": 0,
        "hour_started": datetime.now().hour,
        "priority_mentions": [],  # Mentions from @lemoncheli
        "general_mentions": [],   # Mentions from others
        "engagement_metrics": db.get_engagement_metrics(),
        "followed_accounts": [],  # Track who we've followed
        "follow_decisions": []    # Track follow decisions and reasoning
    }
    if current_state is None:
        for topic in ["AI", "crypto", "biotech"]:
            knowledge = db.get_knowledge_for_topic(topic)
            initial_state["knowledge_base"][topic] = knowledge[:5]
        return initial_state
    current_hour = datetime.now().hour
    if current_hour != current_state.get("hour_started", current_hour):
        current_state["posts_this_hour"] = 0
        current_state["hour_started"] = current_hour
    if function_result and function_result.info:
        info = function_result.info
        if "thread_posted" in info:
            current_state["last_post_time"] = datetime.now().isoformat()
            current_state["posts_this_hour"] += 1
            current_state["posting_history"].append({
                "timestamp": datetime.now().isoformat(),
                "content": info.get("thread_content", ""),
                "url": info.get("thread_url", "")
            })
        if "mentions_found" in info:
            for mention in info["mentions_found"]:
                if YOUR_TWITTER_HANDLE.lower() in mention.get("text", "").lower():
                    current_state["priority_mentions"].append(mention)
                else:
                    current_state["general_mentions"].append(mention)
        if "followed_user" in info:
            current_state["followed_accounts"].append(info["followed_user"])
        if "follow_decision" in info:
            current_state["follow_decisions"].append(info["follow_decision"])
        current_state["engagement_metrics"] = db.get_engagement_metrics()
    return current_state

def assess_content_quality(content: str, author_metrics: dict = None) -> Tuple[bool, str, int]:
    quality_score = 0
    reasons = []
    high_quality_count = sum(1 for indicator in QUALITY_INDICATORS["high_quality"] 
                           if indicator.lower() in content.lower())
    quality_score += high_quality_count * 10
    if high_quality_count > 0:
        reasons.append(f"Contains {high_quality_count} quality indicators")
    negative_count = sum(1 for indicator in QUALITY_INDICATORS["negative_indicators"]
                        if indicator.lower() in content.lower())
    quality_score -= negative_count * 15
    if negative_count > 0:
        reasons.append(f"Contains {negative_count} negative indicators")
    if author_metrics:
        followers = author_metrics.get("public_metrics", {}).get("followers_count", 0)
        if followers >= QUALITY_INDICATORS["engagement_thresholds"]["min_followers"]:
            quality_score += 5
            reasons.append(f"Author has {followers} followers")
        else:
            quality_score -= 5
            reasons.append(f"Author has low followers ({followers})")
    if len(content) > 100 and any(char in content for char in [".", "!", "?"]):
        quality_score += 5
        reasons.append("Well-structured content")
    should_follow = quality_score >= 15
    reason = "; ".join(reasons) if reasons else "No specific indicators"
    return should_follow, reason, quality_score

def follow_user_on_twitter(username: str, reason: str = "") -> Tuple[bool, str]:
    try:
        client = get_twitter_client()
        user_info = client.get_user(username=username)
        if not user_info.get("data"):
            return False, f"User @{username} not found"
        user_id = user_info["data"]["id"]
        follow_result = client.follow_user(target_user_id=user_id)
        if follow_result.get("data", {}).get("following"):
            return True, f"Successfully followed @{username}: {reason}"
        else:
            return False, f"Failed to follow @{username}: API response issue"
    except Exception as e:
        return False, f"Error following @{username}: {str(e)}"

def add_to_priority_queue(mention_id, author, content, quality_score, is_priority):
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS priority_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mention_id TEXT,
                    author TEXT,
                    content TEXT,
                    quality_score INTEGER,
                    is_priority BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT INTO priority_queue (mention_id, author, content, quality_score, is_priority)
                VALUES (?, ?, ?, ?, ?)
            ''', (mention_id, author, content, quality_score, int(is_priority)))
            conn.commit()
            print(f"[add_to_priority_queue] Added mention {mention_id} to priority queue (priority={is_priority}, score={quality_score})")
    except Exception as e:
        print(f"[add_to_priority_queue] Error: {e}")

def reply_to_mention(mention_id: str, author: str, content: str, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
    """Reply to a mention with context, priority handling, and smart following. Store the original post if the mention is a reply, and only consider posting about it if it passes the quality threshold."""
    try:
        # Check if already responded
        if db.get_mention_response(mention_id):
            print(f"[reply_to_mention] Already responded to mention {mention_id}, skipping.")
            return FunctionResultStatus.FAILED, "Already responded to this mention", {"skipped": True}
        client = get_twitter_client()
        is_lemoncheli = YOUR_TWITTER_HANDLE.lower() in author.lower()
        original_post = None
        original_post_score = None
        original_post_id = None
        # Try to fetch the original post if this mention is a reply
        try:
            mention_tweet = client.get_tweet(id=mention_id, expansions=["author_id", "referenced_tweets.id"], tweet_fields=["author_id", "public_metrics", "referenced_tweets"])
            referenced = mention_tweet.get("data", {}).get("referenced_tweets", [])
            if referenced:
                # Get the original post id (the tweet being replied to)
                for ref in referenced:
                    if ref.get("type") == "replied_to":
                        original_post_id = ref.get("id")
                        break
            if original_post_id:
                # Fetch the original post
                orig_tweet = client.get_tweet(id=original_post_id, expansions=["author_id"], tweet_fields=["author_id", "public_metrics"])
                orig_data = orig_tweet.get("data", {})
                orig_author_id = orig_data.get("author_id")
                orig_content = orig_data.get("text", "")
                orig_metrics = orig_data.get("public_metrics", {})
                # Store the original post in monitored_content if not already present
                db.store_monitored_content(
                    tweet_id=original_post_id,
                    content=orig_content,
                    topic="user_mention",
                    author_id=orig_author_id,
                    engagement_metrics=orig_metrics
                )
                # Assess quality/score
                _, _, original_post_score = assess_content_quality(orig_content, {"public_metrics": orig_metrics})
                original_post = {
                    "tweet_id": original_post_id,
                    "content": orig_content,
                    "author_id": orig_author_id,
                    "score": original_post_score
                }
        except Exception as e:
            print(f"[reply_to_mention] Could not fetch/store original post: {e}")
        topic = "AI"  # Or use NLP to extract topic
        knowledge = db.get_knowledge_for_topic(topic)
        from src.bots.llm_utils import generate_reply_to_mention
        # Compose reply: thank the tagger, quick comment on the original post if available
        if original_post:
            reply_context = f"Thanks @{author} for the tag! Interesting post by @{original_post['author_id']}: '{original_post['content'][:100]}...'"
        else:
            reply_context = f"Thanks @{author} for the tag!"
        llm_reply = generate_reply_to_mention(
            topic,
            knowledge,
            content + "\n" + (original_post["content"] if original_post else ""),
            mention_author=author,
            mention_url=f"https://x.com/i/web/status/{mention_id}"
        )
        # Only skip if reply is empty
        if not llm_reply or not llm_reply.strip():
            print(f"[reply_to_mention] Skipping reply: LLM output is empty. Content: '{llm_reply}'")
            return FunctionResultStatus.FAILED, "No meaningful reply generated (empty content)", {}
        # Ensure reply fits Twitter limit
        if len(llm_reply) > 280:
            llm_reply = llm_reply[:270] + "..."
        reply = client.create_tweet(
            text=llm_reply,
            in_reply_to_tweet_id=mention_id
        )
        reply_url = f"https://x.com/i/web/status/{reply['data']['id']}"
        db.store_mention_response(
            mention_tweet_id=mention_id,
            mention_content=content,
            response_content=llm_reply,
            response_tweet_id=reply["data"]["id"],
            context_used=f"{topic} knowledge, priority={is_lemoncheli}, original_post_id={original_post_id}"
        )
        # Optionally, consider posting about the original post if it passes the score threshold
        POST_SCORE_THRESHOLD = 15
        if original_post and original_post_score is not None and original_post_score >= POST_SCORE_THRESHOLD:
            # Prepare a post for the bot's own timeline (not every mention triggers this)
            from src.bots.llm_utils import generate_quote_tweet_comment
            llm_summary = generate_quote_tweet_comment(
                topic,
                knowledge,
                original_post["content"],
                tweet_url=f"https://x.com/i/web/status/{original_post_id}"
            )
            if llm_summary and len(llm_summary) > 0:
                tweet_text = f"{llm_summary}\n\nhttps://x.com/i/web/status/{original_post_id}"
                if len(tweet_text) > 280:
                    tweet_text = f"{llm_summary[:250]}...\nhttps://x.com/i/web/status/{original_post_id}"
                db.store_generated_thread(thread_content=tweet_text, topic=topic)
                print(f"[reply_to_mention] Prepared timeline post for high-scoring original post: {tweet_text}")
        result_info = {
            "response_posted": True,
            "reply_url": reply_url,
            "is_priority": is_lemoncheli,
            "topic": topic,
            "original_post": original_post
        }
        return FunctionResultStatus.DONE, f"💬 Responded to mention: {reply_url}", result_info
    except Exception as e:
        return FunctionResultStatus.FAILED, f"Response to mention failed: {str(e)}", {}

def post_insight_from_timeline(topic: str, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
    """Post a tweet quoting or commenting on an interesting timeline tweet from the DB. Prevent duplicate posts by tweet_id and content similarity."""
    try:
        current_state = kwargs.get("current_state", {})
        posts_this_hour = current_state.get("posts_this_hour", 0)
        last_post_time = current_state.get("last_post_time")
        if posts_this_hour >= POSTING_CONFIG["max_posts_per_hour"]:
            return FunctionResultStatus.FAILED, "⏰ Hourly posting limit reached", {"limit_reached": True}
        if last_post_time:
            last_post_dt = datetime.fromisoformat(last_post_time)
            time_since_last = datetime.now() - last_post_dt
            min_interval = timedelta(hours=POSTING_CONFIG["min_hours_between_posts"])
            if time_since_last < min_interval:
                return FunctionResultStatus.FAILED, f"⏰ Too soon to post again (wait {min_interval - time_since_last})", {"too_soon": True}
        # CURATION: Only post if there is a real, interesting tweet/mention in the DB
        interesting = select_interesting_content_from_db()
        if not interesting:
            print("[post_insight_from_timeline] No interesting content found in DB. Skipping post.")
            return FunctionResultStatus.FAILED, "No interesting content to post", {"skipped": True}
        tweet_id = interesting['tweet_id']
        # Anti-duplication: check if already posted this tweet_id
        if db.has_posted_tweet_id(tweet_id):
            print(f"[post_insight_from_timeline] Already posted about tweet_id {tweet_id}, skipping.")
            return FunctionResultStatus.FAILED, "Already posted about this tweet", {"skipped": True}
        content = interesting['content']
        from src.bots.llm_utils import generate_quote_tweet_comment
        knowledge = db.get_knowledge_for_topic(topic)
        llm_summary = generate_quote_tweet_comment(
            topic,
            knowledge,
            content,
            tweet_url=f"https://x.com/i/web/status/{tweet_id}"
        )
        # Anti-duplication: check if similar content has been posted recently
        if db.is_similar_content_posted(llm_summary):
            print(f"[post_insight_from_timeline] Similar content already posted recently, skipping. Content: '{llm_summary}'")
            return FunctionResultStatus.FAILED, "Similar content already posted", {"skipped": True}
        banned_phrases = [
            "Automated",
            "This is an automated post",
            "Generated post",
            "...",
            "",
            None
        ]
        if not llm_summary or any(
            (llm_summary.strip().lower() == phrase.strip().lower()) or
            (llm_summary.strip().lower().startswith(phrase.strip().lower()))
            for phrase in banned_phrases
        ):
            print(f"[post_insight_from_timeline] Skipping post: LLM summary is empty or generic. Content: '{llm_summary}'")
            return FunctionResultStatus.FAILED, "No meaningful content to post (blocked generic/bad content)", {"skipped": True}
        # Compose final tweet: quote + summary (if fits)
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        tweet_text = f"{llm_summary}\n\n{tweet_url}"
        if len(tweet_text) > 280:
            tweet_text = f"{llm_summary[:250]}...\n{tweet_url}"
        post_id = db.store_generated_thread(thread_content=tweet_text, topic=topic)
        print(f"[post_insight_from_timeline] Prepared tweet quoting {tweet_url}: {tweet_text}")
        result_info = {
            "tweet_ready": True,
            "tweet_content": tweet_text,
            "topic": topic,
            "tweet_id": post_id,
            "can_post": True
        }
        return FunctionResultStatus.DONE, f"🐦 Tweet ready quoting real content (posting controls passed)", result_info
    except Exception as e:
        return FunctionResultStatus.FAILED, f"Tweet creation failed: {str(e)}", {}

def select_interesting_content_from_db(limit=10, score_threshold=5):
    """Fetch and score recent monitored_content for interestingness."""
    from src.bots.config import QUALITY_INDICATORS
    recent = db.get_recent_monitored_content(limit=limit)
    scored = []
    for item in recent:
        score = 0
        content = item['content'].lower()
        # Score by quality keywords
        for kw in QUALITY_INDICATORS['high_quality']:
            if kw in content:
                score += 2
        # Score by engagement
        try:
            metrics = item.get('engagement_metrics')
            if metrics:
                import json
                metrics = json.loads(metrics) if isinstance(metrics, str) else metrics
                score += int(metrics.get('like_count', 0)) // 10
                score += int(metrics.get('retweet_count', 0)) // 5
        except Exception:
            pass
        # Score by recency (most recent gets a small boost)
        score += max(0, limit - recent.index(item))
        scored.append((score, item))
    scored.sort(reverse=True, key=lambda x: x[0])
    # Only return if the score is above the threshold
    return scored[0][1] if scored and scored[0][0] >= score_threshold else None

def enhanced_monitor_and_respond(topics: str = None, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
    """Enhanced monitoring with mention responses and timeline checking"""
    try:
        client = get_twitter_client()
        me = client.get_me()
        user_id = me["data"]["id"]
        # 1. Check mentions
        mentions = client.get_users_mentions(id=user_id, max_results=20)
        mention_data = mentions.get("data", [])
        priority_mentions = []
        general_mentions = []
        for mention in mention_data:
            if YOUR_TWITTER_HANDLE.lower() in mention.get("text", "").lower():
                priority_mentions.append(mention)
            else:
                general_mentions.append(mention)
        # 2. Monitor HOME TIMELINE
        timeline_insights = []
        try:
            timeline = call_with_rate_limit_handling(client.get_home_timeline, max_results=25)
            # Defensive: ensure timeline is a dict and has 'data'
            if not isinstance(timeline, dict) or "data" not in timeline:
                print(f"[ERROR] Timeline response is not a dict with 'data': {timeline}")
                timeline_tweets = []
            else:
                timeline_tweets = timeline.get("data", [])
            if timeline_tweets:
                for tweet in timeline_tweets:
                    tweet_text = tweet.get("text", "")
                    # DEBUG: Print every timeline tweet being considered
                    print(f"[DEBUG] Timeline tweet: {tweet_text[:80]}...")
                    # TEMP: Store all timeline tweets, not just those matching topics
                    timeline_insights.append({
                        "author": "home_timeline",
                        "content": tweet_text,
                        "tweet_id": tweet["id"],
                        "engagement": tweet.get("public_metrics", {}),
                        "author_id": tweet.get("author_id")
                    })
                    print(f"[DEBUG] Storing timeline tweet in DB: {tweet_text[:80]}...")
                    db.store_monitored_content(
                        tweet_id=tweet["id"],
                        content=tweet_text,
                        topic="home_timeline",
                        author_id=tweet.get("author_id"),
                        engagement_metrics=tweet.get("public_metrics", {})
                    )
            # Log the entire response for debugging
            print(f"[DEBUG] Full timeline response: {timeline}")
        except Exception as e:
            print(f"Home timeline monitoring failed: {e}")
            for account in ACCOUNTS_TO_MONITOR[:2]:
                try:
                    user_info = client.get_user(username=account)
                    if user_info.get("data"):
                        user_tweets = client.get_users_tweets(
                            id=user_info["data"]["id"],
                            max_results=5,
                            tweet_fields=["created_at", "public_metrics"]
                        )
                        if user_tweets.get("data"):
                            for tweet in user_tweets["data"]:
                                tweet_text = tweet["text"]
                                print(f"[DEBUG] Fallback timeline tweet: {tweet_text[:80]}...")
                                print(f"[DEBUG] Storing fallback timeline tweet in DB: {tweet_text[:80]}...")
                                timeline_insights.append({
                                    "author": account,
                                    "content": tweet_text,
                                    "tweet_id": tweet["id"],
                                    "engagement": tweet.get("public_metrics", {})
                                })
                                db.store_monitored_content(
                                    tweet_id=tweet["id"],
                                    content=tweet_text,
                                    topic=account,
                                    author_id=tweet.get("author_id"),
                                    engagement_metrics=tweet.get("public_metrics", {})
                                )
                except Exception as e:
                    print(f"Fallback timeline check failed for {account}: {e}")
                    continue
        # 3. Search for topic patterns
        topic_insights = []
        all_topics = TOPICS_TO_MONITOR if not topics else topics.split(",")
        for topic in all_topics[:2]:
            try:
                search_results = client.search_recent_tweets(
                    query=f"{topic.strip()} -is:retweet",
                    max_results=10,
                    tweet_fields=["author_id", "created_at", "public_metrics"]
                )
                if search_results.get("data"):
                    for tweet in search_results["data"]:
                        if any(keyword in tweet["text"].lower() for keyword in ["breakthrough", "innovation", "announcement"]):
                            topic_insights.append({
                                "topic": topic,
                                "content": tweet["text"],
                                "tweet_id": tweet["id"],
                                "engagement": tweet.get("public_metrics", {})
                            })
                            print(f"[DEBUG] Storing topic search tweet in DB: {tweet['text'][:80]}...")
                            db.store_monitored_content(
                                tweet_id=tweet["id"],
                                content=tweet["text"],
                                topic=topic,
                                author_id=tweet.get("author_id"),
                                engagement_metrics=tweet.get("public_metrics", {})
                            )
            except Exception as e:
                print(f"Topic search failed for {topic}: {e}")
                continue
        result_info = {
            "mentions_found": mention_data,
            "priority_mentions_count": len(priority_mentions),
            "general_mentions_count": len(general_mentions),
            "timeline_insights_count": len(timeline_insights),
            "topic_insights_count": len(topic_insights),
            "monitoring_completed": True
        }
        return FunctionResultStatus.DONE, f"🔍 Enhanced monitoring: {len(priority_mentions)} @lemoncheli mentions, {len(general_mentions)} general mentions, {len(timeline_insights)} timeline insights", result_info
    except Exception as e:
        return FunctionResultStatus.FAILED, f"Enhanced monitoring failed: {str(e)}", {}

def fetch_and_summarize_tweets(topic: str, client, max_results: int = 10) -> str:
    # ... (copy logic from enhanced_glitch_bot_v2.py)
    pass

def select_interesting_timeline_tweets(tweets, topic, max_count=2):
    # ... (copy logic from enhanced_glitch_bot_v2.py)
    pass

def controlled_post_thread(content: str, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
    """Post a single tweet with engagement tracking"""
    try:
        client = get_twitter_client()
        tweet_text = content.strip()
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:270] + "..."
        tweet = client.create_tweet(text=tweet_text)
        tweet_id = tweet["data"]["id"]
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        result_info = {
            "tweet_posted": True,
            "tweet_url": tweet_url,
            "tweet_id": tweet_id,
            "tweet_content": tweet_text,
            "post_time": datetime.now().isoformat()
        }
        return FunctionResultStatus.DONE, f"📱 Posted tweet: {tweet_url}", result_info
    except Exception as e:
        return FunctionResultStatus.FAILED, f"Controlled posting failed: {str(e)}", {}

def create_agent_with_retry(max_retries=5, base_delay=30):
    for attempt in range(max_retries):
        try:
            print(f"🔄 Creating Enhanced Glitch Bot V2 (attempt {attempt + 1}/{max_retries})...")
            agent = Agent(
                api_key=GAME_API_KEY,
                name="Enhanced Glitch Bot V2",
                agent_goal=f"Build high-quality network through strategic posting (max 2/hour), responsive mentions (especially to @{YOUR_TWITTER_HANDLE}), auto-follow for @{YOUR_TWITTER_HANDLE} tags, and quality-based following for others.",
                agent_description=ENHANCED_PERSONALITY,
                get_agent_state_fn=get_enhanced_state_fn,
                workers=[enhanced_monitor_worker, controlled_content_worker],
                model_name="Llama-3.1-405B-Instruct"
            )
            print("✅ Enhanced Glitch Bot V2 created successfully!")
            return agent
        except Exception as e:
            print(f"❌ Error creating agent on attempt {attempt+1}: {e}")
            import traceback
            traceback.print_exc()
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 10)
                print(f"⏰ Rate limited or error. Waiting {delay:.1f} seconds before retry {attempt + 2}/{max_retries}...")
                time.sleep(delay)
            else:
                print("❌ Max retries reached. The Game SDK API is currently rate limiting agent creation or another error occurred.")
                print("💡 Try again in a few minutes, or the platform may be experiencing high load.")
    print("❌ Failed to create agent after all retries")
    return None

post_insight_fn = Function(
    fn_name="post_insight_from_timeline",
    fn_description="Post a tweet quoting or commenting on an interesting timeline tweet from the DB.",
    args=[Argument(name="topic", type="string", description="Topic for insight")],
    executable=post_insight_from_timeline
)

reply_to_mention_fn = Function(
    fn_name="reply_to_mention",
    fn_description="Reply to a mention with context, priority handling, and smart following.",
    args=[
        Argument(name="mention_id", type="string", description="Tweet ID to respond to"),
        Argument(name="author", type="string", description="Author of the mention"),
        Argument(name="content", type="string", description="Content of the mention")
    ],
    executable=reply_to_mention
)

enhanced_monitor_fn = Function(
    fn_name="enhanced_monitor",
    fn_description="Monitor mentions, timelines, and topics with smart response handling",
    args=[Argument(name="topics", type="string", description="Topics to monitor")],
    executable=enhanced_monitor_and_respond
)

smart_respond_follow_fn = Function(
    fn_name="smart_respond_follow",
    fn_description="Respond to mentions with context, priority handling, and smart following",
    args=[
        Argument(name="mention_id", type="string", description="Tweet ID to respond to"),
        Argument(name="author", type="string", description="Author of the mention"),
        Argument(name="content", type="string", description="Content of the mention")
    ],
    executable=reply_to_mention
)

controlled_create_fn = Function(
    fn_name="controlled_create",
    fn_description="Create threads with posting frequency controls",
    args=[
        Argument(name="topic", type="string", description="Topic for thread"),
        Argument(name="insights", type="string", description="Insights to share")
    ],
    executable=post_insight_from_timeline
)

controlled_post_fn = Function(
    fn_name="controlled_post",
    fn_description="Post threads with engagement tracking",
    args=[Argument(name="content", type="string", description="Content to post")],
    executable=controlled_post_thread
)

enhanced_monitor_worker = WorkerConfig(
    id="enhanced_monitor_follow",
    worker_description=f"Enhanced monitoring specialist - tracks mentions (prioritizing @{YOUR_TWITTER_HANDLE}), timelines, and topics with smart response and follow capabilities.",
    get_state_fn=get_enhanced_state_fn,
    action_space=[enhanced_monitor_fn, smart_respond_follow_fn]
)

controlled_content_worker = WorkerConfig(
    id="controlled_creator",
    worker_description="Controlled content creator - generates and posts threads with frequency limits, engagement tracking, and strategic timing.",
    get_state_fn=get_enhanced_state_fn,
    action_space=[controlled_create_fn, controlled_post_fn]
)

def enhanced_glitch_bot_v2():
    return create_agent_with_retry() 