import sys
import time
import random
import requests
import sqlite3
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

BASE_URL = "https://www.reddit.com/"
usernames = set()

# 数据库文件名 - 统一在这里定义
DATABASE_FILE = 'rio_tinto_new.db'

# Rio Tinto related keywords
RIO_TINTO_KEYWORDS = [
    'Rio Tinto', 'RioTinto', 'riotinto', 'RIO TINTO', 'RIOTINTO',
    'rio tinto', 'riotinto', 'Rio tinto', '力拓', '力拓集团', 
    '力拓公司', '力拓矿业', 'RT', 'RTP', 'RIO', 'ASX:RIO', 
    'LSE:RIO', 'NYSE:RIO', 'RIO.AX', 'RioTino', 'Rio Tino', '力托'
]

def init_database():
    """Initialize database with new file"""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # 删除旧表（如果存在）重新创建
    cursor.execute('DROP TABLE IF EXISTS submissions')
    cursor.execute('DROP TABLE IF EXISTS comments')
    
    cursor.execute('''
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reddit_id TEXT UNIQUE,
            title TEXT,
            submitter TEXT,
            num_comments INTEGER,
            created_date REAL,
            post_content TEXT,
            location TEXT,
            created_datetime TEXT,
            keyword_matched TEXT,
            post_year INTEGER,
            is_rio_tinto_related BOOLEAN DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id TEXT UNIQUE,
            parent_id TEXT,
            submission_id TEXT,
            body TEXT,
            score INTEGER,
            created_utc REAL,
            created_datetime TEXT,
            depth INTEGER,
            is_rio_tinto_related BOOLEAN DEFAULT 0,
            FOREIGN KEY (submission_id) REFERENCES submissions (reddit_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized successfully: {DATABASE_FILE}")

def contains_rio_tinto_keywords(text):
    """Check if text contains Rio Tinto related keywords"""
    if not text or text == 'nan':
        return None
    
    text_lower = text.lower()
    for keyword in RIO_TINTO_KEYWORDS:
        if keyword.lower() in text_lower:
            return keyword
    return None

def is_rio_tinto_related_post(post_data):
    """Check if post is truly Rio Tinto related"""
    title = post_data.get("title", "")
    content = post_data.get("selftext", "")
    
    # Check both title and content for Rio Tinto keywords
    title_match = contains_rio_tinto_keywords(title)
    content_match = contains_rio_tinto_keywords(content)
    
    return title_match or content_match

def save_submissions(submissions):
    """Save submission data with Rio Tinto flag"""
    if not submissions:
        return 0
        
    conn = sqlite3.connect(DATABASE_FILE)  # 使用统一的数据库文件
    cursor = conn.cursor()
    
    count = 0
    for submission in submissions:
        try:
            reddit_id, title, submitter, num_comments, created_date, post_content, location, created_datetime, keyword_matched, post_year = submission
            
            # Determine if it's Rio Tinto related
            is_related = 1 if keyword_matched else 0
            
            cursor.execute('''
                INSERT OR IGNORE INTO submissions 
                (reddit_id, title, submitter, num_comments, created_date, post_content, 
                 location, created_datetime, keyword_matched, post_year, is_rio_tinto_related)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (reddit_id, title, submitter, num_comments, created_date, post_content, 
                  location, created_datetime, keyword_matched, post_year, is_related))
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            print(f"❌ Error saving submission {submission[0]}: {e}")
            continue
    
    conn.commit()
    conn.close()
    return count

def save_comments(comments, is_rio_tinto_related=False):
    """Save comments data with Rio Tinto flag"""
    if not comments:
        return 0
        
    conn = sqlite3.connect(DATABASE_FILE)  # 使用统一的数据库文件
    cursor = conn.cursor()
    
    count = 0
    for comment in comments:
        try:
            # Add the Rio Tinto related flag to comment data
            comment_with_flag = (*comment, 1 if is_rio_tinto_related else 0)
            
            cursor.execute('''
                INSERT OR IGNORE INTO comments 
                (comment_id, parent_id, submission_id, body, score, created_utc, 
                 created_datetime, depth, is_rio_tinto_related)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', comment_with_flag)
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            print(f"❌ Error saving comment {comment[0]}: {e}")
            continue
    
    conn.commit()
    conn.close()
    return count

# Create conservative session strategy
session = requests.Session()
retry_strategy = Retry(
    total=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    backoff_factor=2
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
session.mount("http://", adapter)
session.mount("https://", adapter)

def request_reddit_data_safe(url, timeout=20):
    """Safe request function to avoid 429 errors"""
    delay = random.uniform(2, 4)
    time.sleep(delay)
    
    headers = {
        "User-agent": f"riotinto_research_{random.randint(1000,9999)}",
        "Accept": "application/json"
    }
    
    try:
        response = session.get(BASE_URL + url, headers=headers, timeout=timeout)
        
        # Check if rate limited
        remaining_requests = response.headers.get('x-ratelimit-remaining', 1)
        if float(remaining_requests) < 2:
            wait_time = int(response.headers.get('x-ratelimit-reset', 60))
            print(f"⚠️ Approaching request limit, waiting {wait_time} seconds...")
            time.sleep(wait_time + 5)
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if hasattr(e, 'response') and e.response.status_code == 429:
            wait_time = 60
            print(f"🚫 Request limited, waiting {wait_time} seconds...")
            time.sleep(wait_time)
            return request_reddit_data_safe(url, timeout)
        return {"data": {}}
    except Exception as e:
        print(f"❌ Request error: {e}")
        return {"data": {}}

def get_existing_post_ids():
    """Get existing post IDs to avoid duplicates"""
    conn = sqlite3.connect(DATABASE_FILE)  # 使用统一的数据库文件
    cursor = conn.cursor()
    cursor.execute("SELECT reddit_id FROM submissions")
    existing_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return existing_ids

def get_existing_comment_ids():
    """Get existing comment IDs to avoid duplicates"""
    conn = sqlite3.connect(DATABASE_FILE)  # 使用统一的数据库文件
    cursor = conn.cursor()
    cursor.execute("SELECT comment_id FROM comments")
    existing_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return existing_ids

def extract_comments_from_post(submission_id, comments_url, max_depth=0):
    """Extract comments only from Rio Tinto related posts"""
    all_comments = []
    existing_comment_ids = get_existing_comment_ids()
    
    try:
        # Fetch comments data
        data = request_reddit_data_safe(f"{comments_url}.json")
        if not data or len(data) < 2:
            return all_comments
        
        # The second item in the list contains the comments
        comments_data = data[1]["data"]["children"]
        
        def process_comment_tree(comments, depth=0):
            """Process comments and their replies"""
            if depth > max_depth:
                return
                
            for comment in comments:
                comment_data = comment.get("data", {})
                
                # Skip deleted or removed comments
                if comment_data.get("author") in ["[deleted]", "[removed]"]:
                    continue
                
                comment_id = comment_data.get("id")
                if not comment_id or comment_id in existing_comment_ids:
                    continue
                
                # Extract comment information
                comment_info = (
                    comment_id,
                    comment_data.get("parent_id", ""),
                    submission_id,
                    comment_data.get("body", ""),
                    comment_data.get("score", 0),
                    comment_data.get("created_utc", 0),
                    datetime.fromtimestamp(comment_data.get("created_utc", 0)).isoformat() if comment_data.get("created_utc") else "",
                    depth
                )
                all_comments.append(comment_info)
                existing_comment_ids.add(comment_id)
                
                # Add author to usernames set
                if comment_data.get("author"):
                    usernames.add(comment_data.get("author"))
                
                # Process replies recursively
                replies = comment_data.get("replies", {})
                if isinstance(replies, dict) and "data" in replies:
                    child_comments = replies["data"].get("children", [])
                    if child_comments:
                        process_comment_tree(child_comments, depth + 1)
        
        # Start processing from top-level comments
        process_comment_tree(comments_data)
        
        print(f"💬 Extracted {len(all_comments)} comments from Rio Tinto post {submission_id}")
        
    except Exception as e:
        print(f"❌ Error extracting comments from {submission_id}: {e}")
    
    return all_comments

def search_with_retry(search_query, pages=5, sort_by='relevance', time_filter='all'):
    """Search function that only processes truly Rio Tinto related posts"""
    all_new_submissions = []
    existing_ids = get_existing_post_ids()
    
    next_page = ""
    for page_num in range(pages):
        try:
            # Build search URL
            search_url = f"search.json?q={search_query}&type=link&t={time_filter}&sort={sort_by}&limit=100"
            if next_page:
                search_url += f"&{next_page}"
            
            data = request_reddit_data_safe(search_url).get("data", {})
            if not data:
                print("❌ Failed to get data, skipping this page")
                break
            
            submissions = data.get("children", [])
            print(f"📝 Page {page_num + 1} found {len(submissions)} posts")
            
            new_rio_tinto_posts = 0
            total_comments_extracted = 0
            
            for s in submissions:
                sd = s.get("data", {})
                reddit_id = sd.get("id")
                
                # Check if already exists
                if reddit_id in existing_ids:
                    continue
                
                # STRICT CHECK: Only process posts that are truly Rio Tinto related
                matched_keyword = contains_rio_tinto_keywords(sd.get("title", "")) or contains_rio_tinto_keywords(sd.get("selftext", ""))
                
                if matched_keyword:
                    # Extract post information
                    submitter = sd.get("author")
                    created_date = sd.get("created")
                    post_year = datetime.fromtimestamp(created_date).year if created_date else None
                    
                    submission = (
                        reddit_id, 
                        sd.get("title", ""), 
                        submitter, 
                        sd.get("num_comments"), 
                        created_date,
                        sd.get("selftext", ""), 
                        "Unknown",
                        datetime.fromtimestamp(created_date).isoformat() if created_date else "",
                        matched_keyword, 
                        post_year
                    )
                    all_new_submissions.append(submission)
                    existing_ids.add(reddit_id)
                    
                    if submitter:
                        usernames.add(submitter)
                    
                    new_rio_tinto_posts += 1
                    
                    # Extract comments ONLY for confirmed Rio Tinto posts
                    discussion_url = sd.get("permalink", "")
                    if discussion_url:
                        comments = extract_comments_from_post(reddit_id, discussion_url)
                        if comments:
                            saved_comments = save_comments(comments, is_rio_tinto_related=True)
                            total_comments_extracted += saved_comments
                            print(f"   💾 Saved {saved_comments} comments for Rio Tinto post {reddit_id}")
                else:
                    # Skip posts that don't actually contain Rio Tinto keywords
                    print(f"   ⏭️  Skipped non-Rio Tinto post: {sd.get('title', '')[:50]}...")
            
            print(f"🎯 This page added {new_rio_tinto_posts} confirmed Rio Tinto related posts")
            print(f"💬 Total comments extracted: {total_comments_extracted}")
            
            after = data.get("after")
            if not after:
                break
            next_page = f"after={after}"
            
            # Save each page to avoid large memory usage
            if all_new_submissions:
                saved_count = save_submissions(all_new_submissions)
                print(f"💾 Saved {saved_count} new Rio Tinto posts")
                all_new_submissions = []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            time.sleep(10)
            continue
    
    return len(existing_ids)

if __name__ == "__main__":
    print("🚀 Rio Tinto data crawler started")
    print("🎯 Target: Get confirmed Rio Tinto related posts with comments")
    print("🔍 Strict filtering: Only process posts that actually contain Rio Tinto keywords")
    print(f"📁 Using new database: {DATABASE_FILE}")
    
    init_database()
    
    try:
        start_time = time.time()
        
        # Extended search combinations
        search_combinations = [
            # Basic keywords
            ("Rio+Tinto", "relevance"),
            ("力拓", "relevance"), 
            ("RIO", "relevance"),
            ("RioTinto", "relevance"),
        ]
        
        total_searches = len(search_combinations)
        total_posts = 0
        total_comments = 0
        
        for search_index, (search_query, sort_by) in enumerate(search_combinations, 1):
            print(f"\n🔍 Search {search_index}/{total_searches}: '{search_query.replace('+', ' ')}'")
            print("=" * 50)
            
            current_posts = search_with_retry(search_query, pages=6, sort_by=sort_by)
            total_posts = current_posts
            
            # Get current comment count
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM comments WHERE is_rio_tinto_related = 1")
            total_comments = cursor.fetchone()[0]
            conn.close()
            
            print(f"📊 Current total: {total_posts} confirmed Rio Tinto related posts")
            print(f"💬 Current total: {total_comments} Rio Tinto related comments")
            
            # If enough data, finish early
            if total_posts >= 500:
                print("🎉 Sufficient data, completing current search...")
                break
        
        end_time = time.time()
        
        # Final statistics
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM submissions WHERE is_rio_tinto_related = 1")
        final_rio_tinto_post_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM comments WHERE is_rio_tinto_related = 1")
        final_rio_tinto_comment_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT submitter) FROM submissions WHERE is_rio_tinto_related = 1")
        unique_rio_tinto_authors = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(created_datetime), MAX(created_datetime) FROM submissions WHERE is_rio_tinto_related = 1")
        time_range = cursor.fetchone()
        conn.close()
        
        print(f"\n🎊 Final statistics (Rio Tinto related only):")
        print(f"📊 Total Rio Tinto posts: {final_rio_tinto_post_count}")
        print(f"💬 Total Rio Tinto comments: {final_rio_tinto_comment_count}")
        print(f"👥 Unique Rio Tinto post authors: {unique_rio_tinto_authors}")
        print(f"⏰ Time range: {time_range[0]} to {time_range[1]}")
        print(f"⏱️ Total time: {(end_time - start_time)/60:.1f} minutes")
        print(f"💾 Data saved to: {DATABASE_FILE}")
        
        if final_rio_tinto_post_count < 300:
            print("\n💡 Suggestion: You can run the script again to get more data")
        
    except KeyboardInterrupt:
        print("\n⏹️ User interrupted crawling")
    except Exception as e:
        print(f"\n❌ Program exception: {e}")