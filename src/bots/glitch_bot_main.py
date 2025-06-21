"""
Glitch Bot Main Runner
"""
import sys
import os
import time
from src.bots.config import YOUR_TWITTER_HANDLE, POSTING_CONFIG, ACCOUNTS_TO_MONITOR
from src.bots.glitch_bot_db import TwitterAgentDB
from src.bots.glitch_bot_agent import enhanced_glitch_bot_v2

db = TwitterAgentDB("enhanced_glitch_bot_v2.db")

def print_db_contents():
    print("\n===== DB: monitored_content =====")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM monitored_content ORDER BY created_at DESC LIMIT 10")
        for row in cursor.fetchall():
            print(dict(row))
    print("\n===== DB: generated_threads =====")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM generated_threads ORDER BY created_at DESC LIMIT 10")
        for row in cursor.fetchall():
            print(dict(row))
    print("\n===== DB: mentions_responses =====")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mentions_responses ORDER BY created_at DESC LIMIT 10")
        for row in cursor.fetchall():
            print(dict(row))
    print("\n===== DB: priority_queue =====")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM priority_queue ORDER BY created_at DESC LIMIT 10")
            for row in cursor.fetchall():
                print(dict(row))
        except Exception as e:
            print("(priority_queue table not found)")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "printdb":
        print_db_contents()
        sys.exit(0)
    print("⚡ Starting ENHANCED GLITCH BOT V2...")
    print("🎯 NEW Smart Following Features:")
    print(f"   • Priority handling for @{YOUR_TWITTER_HANDLE}")
    print(f"   • Auto-follow when @{YOUR_TWITTER_HANDLE} tags the bot")
    print(f"   • Quality-based following for other users")
    print(f"   • Content quality assessment (15+ score threshold)")
    print(f"   • Max {POSTING_CONFIG['max_posts_per_hour']} posts/hour")
    print(f"   • Timeline monitoring of {len(ACCOUNTS_TO_MONITOR)} accounts")
    # Show current metrics
    metrics = db.get_engagement_metrics()
    print(f"\n📊 Current Database Metrics:")
    print(f"   • Content Monitored: {metrics['total_monitored_content']}")
    print(f"   • Threads Generated: {metrics['total_threads_generated']}")
    print(f"   • Threads Posted: {metrics['total_threads_posted']}")
    print(f"   • Mention Responses: {metrics['total_mention_responses']}")
    print("\n" + "="*60)
    print("🤖 Enhanced Glitch Bot V2 - Smart Following & Quality Network")
    print("="*60)
    # enhanced_glitch_bot_v2.compile()
    print("✅ Enhanced Glitch Bot V2 compiled!")
    print("🔄 Starting controlled autonomous operation with smart following...")
    print(f"⚡ Now prioritizing @{YOUR_TWITTER_HANDLE} with auto-follow...")
    print("🧠 Quality assessment active for other mentions...")
    print("🛑 Press Ctrl+C to stop")

    # Configurable delay (default 900s = 15 minutes)
    DELAY_BETWEEN_STEPS = int(os.environ.get("GLITCH_BOT_STEP_DELAY", POSTING_CONFIG.get("delay_between_steps", 900)))
    MAX_BACKOFF = 1800  # 30 minutes
    backoff = DELAY_BETWEEN_STEPS

    while True:
        try:
            agent = enhanced_glitch_bot_v2()
            agent.compile()
            while True:
                try:
                    agent.run()
                    time.sleep(DELAY_BETWEEN_STEPS)
                    backoff = DELAY_BETWEEN_STEPS
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "Too Many Requests" in err_str:
                        # Identify source
                        if "twitter" in err_str.lower():
                            print("[GlitchBot] ⚠️ Rate limited by TWITTER API (429). Backing off for", backoff, "seconds...")
                        elif "game" in err_str.lower() or "ThrottlerException" in err_str:
                            print("[GlitchBot] ⚠️ Rate limited by GAME PLATFORM (429). Backing off for", backoff, "seconds...")
                        else:
                            print("[GlitchBot] ⚠️ Rate limited (429). Backing off for", backoff, "seconds...")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                    else:
                        print("[GlitchBot] ⚠️ Error:", e)
                        time.sleep(DELAY_BETWEEN_STEPS)
        except KeyboardInterrupt:
            print("[GlitchBot] Stopped by user.")
            break
        except Exception as e:
            print("[GlitchBot] ⚠️ Fatal error:", e)
            time.sleep(DELAY_BETWEEN_STEPS)
    # To adjust the delay, set the GLITCH_BOT_STEP_DELAY environment variable or change POSTING_CONFIG['delay_between_steps']

if __name__ == "__main__":
    main()

# Add any CLI or entrypoint logic below... 