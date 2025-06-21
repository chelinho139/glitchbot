"""
Glitch Bot Database Helpers
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import difflib

class TwitterAgentDB:
    def __init__(self, db_path: str = "twitter_agent.db"):
        self.db_path = db_path
        self.init_database()
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitored_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT UNIQUE,
                    content TEXT NOT NULL,
                    topic TEXT,
                    author_id TEXT,
                    engagement_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id INTEGER,
                    topic TEXT,
                    key_points TEXT,
                    sentiment TEXT,
                    importance_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (content_id) REFERENCES monitored_content (id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_content TEXT NOT NULL,
                    topic TEXT,
                    source_analysis_ids TEXT,
                    posted BOOLEAN DEFAULT FALSE,
                    tweet_id TEXT,
                    engagement_metrics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mentions_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mention_tweet_id TEXT UNIQUE,
                    mention_content TEXT,
                    response_content TEXT,
                    response_tweet_id TEXT,
                    context_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    key_concept TEXT,
                    description TEXT,
                    source_content_ids TEXT,
                    confidence_score REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT,
                    metric_value TEXT,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("✅ Database initialized successfully")
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    def store_monitored_content(self, tweet_id: str, content: str, topic: str, author_id: str = None, engagement_metrics: Dict = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO monitored_content 
                (tweet_id, content, topic, author_id, engagement_metrics)
                VALUES (?, ?, ?, ?, ?)
            """, (
                tweet_id, content, topic, author_id, 
                json.dumps(engagement_metrics) if engagement_metrics else None
            ))
            conn.commit()
            return cursor.lastrowid
    def store_analysis_result(self, content_id: int, topic: str, key_points: List[str], sentiment: str = None, importance_score: int = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analysis_results 
                (content_id, topic, key_points, sentiment, importance_score)
                VALUES (?, ?, ?, ?, ?)
            """, (content_id, topic, json.dumps(key_points), sentiment, importance_score))
            conn.commit()
            return cursor.lastrowid
    def store_generated_thread(self, thread_content: str, topic: str, source_analysis_ids: List[int] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO generated_threads 
                (thread_content, topic, source_analysis_ids)
                VALUES (?, ?, ?)
            """, (
                thread_content, topic, 
                json.dumps(source_analysis_ids) if source_analysis_ids else None
            ))
            conn.commit()
            return cursor.lastrowid
    def mark_thread_posted(self, thread_id: int, tweet_id: str, engagement_metrics: Dict = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE generated_threads 
                SET posted = TRUE, tweet_id = ?, engagement_metrics = ?
                WHERE id = ?
            """, (tweet_id, json.dumps(engagement_metrics) if engagement_metrics else None, thread_id))
            conn.commit()
    def store_mention_response(self, mention_tweet_id: str, mention_content: str, response_content: str, response_tweet_id: str, context_used: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO mentions_responses 
                (mention_tweet_id, mention_content, response_content, response_tweet_id, context_used)
                VALUES (?, ?, ?, ?, ?)
            """, (mention_tweet_id, mention_content, response_content, response_tweet_id, context_used))
            conn.commit()
    def update_knowledge_base(self, topic: str, key_concept: str, description: str, source_content_ids: List[int], confidence_score: float = 0.5):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM knowledge_base WHERE topic = ? AND key_concept = ?
            """, (topic, key_concept))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE knowledge_base 
                    SET description = ?, source_content_ids = ?, confidence_score = ?, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (description, json.dumps(source_content_ids), confidence_score, existing[0]))
            else:
                cursor.execute("""
                    INSERT INTO knowledge_base 
                    (topic, key_concept, description, source_content_ids, confidence_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (topic, key_concept, description, json.dumps(source_content_ids), confidence_score))
            conn.commit()
    def get_recent_analysis(self, topic: str = None, limit: int = 10) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT a.*, m.content, m.tweet_id 
                FROM analysis_results a
                JOIN monitored_content m ON a.content_id = m.id
            """
            params = []
            if topic:
                query += " WHERE a.topic = ?"
                params.append(topic)
            query += " ORDER BY a.created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    def get_knowledge_for_topic(self, topic: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM knowledge_base 
                WHERE topic = ?
                ORDER BY confidence_score DESC, last_updated DESC
                LIMIT 10
            """, (topic,))
            return [dict(row) for row in cursor.fetchall()]
    def get_engagement_metrics(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM monitored_content")
            total_monitored_content = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM generated_threads")
            total_threads_generated = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM generated_threads WHERE posted=1")
            total_threads_posted = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM mentions_responses")
            total_mention_responses = cursor.fetchone()[0]
        return {
            "total_monitored_content": total_monitored_content,
            "total_threads_generated": total_threads_generated,
            "total_threads_posted": total_threads_posted,
            "total_mention_responses": total_mention_responses,
        }
    def cleanup_old_data(self, days_old: int = 30):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff = datetime.now().timestamp() - days_old * 86400
            cursor.execute("DELETE FROM monitored_content WHERE created_at < ?", (cutoff,))
            cursor.execute("DELETE FROM analysis_results WHERE created_at < ?", (cutoff,))
            cursor.execute("DELETE FROM generated_threads WHERE created_at < ?", (cutoff,))
            cursor.execute("DELETE FROM mentions_responses WHERE created_at < ?", (cutoff,))
            conn.commit()
    def get_mention_response(self, mention_tweet_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM mentions_responses WHERE mention_tweet_id = ?", (mention_tweet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    def has_posted_tweet_id(self, tweet_id: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM generated_threads WHERE thread_content LIKE ? LIMIT 1", (f"%{tweet_id}%",))
            return cursor.fetchone() is not None
    def is_similar_content_posted(self, content: str, similarity_threshold: float = 0.9, days: int = 7) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT thread_content FROM generated_threads WHERE created_at >= datetime('now', ?)", (f'-{days} days',))
            for row in cursor.fetchall():
                existing = row[0]
                ratio = difflib.SequenceMatcher(None, content, existing).ratio()
                if ratio >= similarity_threshold:
                    return True
        return False
    def get_recent_monitored_content(self, limit: int = 10):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM monitored_content ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

# Add any other DB helper functions/classes below... 