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

# Rio Tinto related keywords
RIO_TINTO_KEYWORDS = [
    'Rio Tinto', 'RioTinto', 'riotinto', 'RIO TINTO', 'RIOTINTO',
    'rio tinto', 'riotinto', 'Rio tinto', '力拓', '力拓集团', 
    '力拓公司', '力拓矿业', 'RT', 'RTP', 'RIO', 'ASX:RIO', 
    'LSE:RIO', 'NYSE:RIO', 'RIO.AX', 'RioTino', 'Rio Tino', '力托'
]

def init_database():
    """Initialize database"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reddit_id TEXT UNIQUE,
            title TEXT,
            submitter TEXT,
            discussion_url TEXT,
            url TEXT,
            score INTEGER,
            num_comments INTEGER,
            created_date REAL,
            post_content TEXT,
            timezone TEXT,
            location TEXT,
            crawled_time TEXT,
            created_datetime TEXT,
            keyword_matched TEXT,
            post_year INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            comment_karma INTEGER,
            link_karma INTEGER,
            user_created REAL,
            user_timezone TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def save_submissions(submissions):
    """Save submission data"""
    if not submissions:
        return 0
        
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    count = 0
    for submission in submissions:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO submissions 
                (reddit_id, title, submitter, discussion_url, url, score, num_comments, 
                 created_date, post_content, timezone, location, crawled_time, created_datetime, keyword_matched, post_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', submission)
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
            continue
    
    conn.commit()
    conn.close()
    return count

def save_users_batch(users_batch):
    """Batch save user data to reduce requests"""
    if not users_batch:
        return 0
        
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    count = 0
    for user in users_batch:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (username, comment_karma, link_karma, user_created, user_timezone)
                VALUES (?, ?, ?, ?, ?)
            ''', user)
            if cursor.rowcount > 0:
                count += 1
        except Exception as e:
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
    delay = random.uniform(2, 4)  # Increase delay
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
        return {"data": {}}

def contains_rio_tinto_keywords(text):
    """Check if text contains Rio Tinto related keywords"""
    if not text or text == 'nan':
        return None
    
    text_lower = text.lower()
    for keyword in RIO_TINTO_KEYWORDS:
        if keyword.lower() in text_lower:
            return keyword
    return None

def get_existing_post_ids():
    """Get existing post IDs to avoid duplicates"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT reddit_id FROM submissions")
    existing_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return existing_ids

def search_with_retry(search_query, pages=5, sort_by='relevance', time_filter='all'):
    """Search function with retry"""
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
            
            new_posts_count = 0
            for s in submissions:
                sd = s.get("data", {})
                reddit_id = sd.get("id")
                
                # Check if already exists
                if reddit_id in existing_ids:
                    continue
                
                # Check if contains Rio Tinto keywords
                title = sd.get("title", "")
                matched_keyword = contains_rio_tinto_keywords(title) or contains_rio_tinto_keywords(sd.get("selftext", ""))
                
                if matched_keyword:
                    # Extract post information
                    submitter = sd.get("author")
                    created_date = sd.get("created")
                    post_year = datetime.fromtimestamp(created_date).year if created_date else None
                    
                    submission = (
                        reddit_id, title, submitter, sd.get("permalink"), sd.get("url"),
                        sd.get("score"), sd.get("num_comments"), created_date,
                        sd.get("selftext", ""), "UTC", "Unknown",
                        datetime.now().isoformat(),
                        datetime.fromtimestamp(created_date).isoformat() if created_date else "",
                        matched_keyword, post_year
                    )
                    all_new_submissions.append(submission)
                    existing_ids.add(reddit_id)
                    
                    if submitter:
                        usernames.add(submitter)
                    
                    new_posts_count += 1
            
            print(f"🎯 This page added {new_posts_count} new Rio Tinto related posts")
            
            after = data.get("after")
            if not after:
                break
            next_page = f"after={after}"
            
            # Save each page to avoid large memory usage
            if all_new_submissions:
                saved_count = save_submissions(all_new_submissions)
                print(f"💾 Saved {saved_count} new posts")
                all_new_submissions = []
                
        except Exception as e:
            print(f"❌ Search error: {e}")
            time.sleep(10)
            continue
    
    return len(existing_ids)

def get_user_info_safe(username):
    """Safely get user information"""
    if username in ["[deleted]", "[removed]", None]:
        return None
        
    url_params = f"user/{username}/about.json"
    try:
        info = request_reddit_data_safe(url_params).get("data", {})
        if info:
            return (
                username,
                info.get("comment_karma", 0),
                info.get("link_karma", 0),
                info.get("created_utc", 0),
                "UTC"
            )
    except Exception:
        return None
    return None

if __name__ == "__main__":
    print("🚀 Rio Tinto data crawler started")
    print("🎯 Target: Get 1000+ Rio Tinto related posts")
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
            
            # Search in specific subreddits
            ("Rio+Tinto+subreddit:jobs", "new"),
            ("Rio+Tinto+subreddit:careerguidance", "new"),
            ("Rio+Tinto+subreddit:recruiting", "new"),
            ("Rio+Tinto+subreddit:mining", "new"),
            ("Rio+Tinto+subreddit:geology", "new"),
            ("Rio+Tinto+subreddit:engineering", "new"),
            ("Rio+Tinto+subreddit:finance", "new"),
            ("Rio+Tinto+subreddit:stocks", "new"),
            ("Rio+Tinto+subreddit:investing", "new"),
            ("Rio+Tinto+subreddit:business", "new"),
            
            # More related searches
            ("Rio+Tinto+employee", "relevance"),
            ("Rio+Tinto+job", "relevance"),
            ("Rio+Tinto+career", "relevance"),
            ("Rio+Tinto+review", "relevance"),
            ("Rio+Tinto+salary", "relevance"),
            ("Rio+Tinto+interview", "relevance"),
            ("Rio+Tinto+work", "relevance"),
            ("Rio+Tinto+company", "relevance"),
        ]
        
        total_searches = len(search_combinations)
        total_posts = 0
        
        for search_index, (search_query, sort_by) in enumerate(search_combinations, 1):
            print(f"\n🔍 Search {search_index}/{total_searches}: '{search_query.replace('+', ' ')}'")
            print("=" * 50)
            
            current_posts = search_with_retry(search_query, pages=6, sort_by=sort_by)
            total_posts = current_posts
            
            print(f"📊 Current total: {total_posts} Rio Tinto related posts")
            
            # If enough data, finish early
            if total_posts >= 800:
                print("🎉 Sufficient data, completing current search...")
                break
        
        # Get user information (optional, can skip to reduce errors)
        print(f"\n🔍 Getting user information...")
        username_list = list(usernames)
        users_to_save = []
        
        for i, username in enumerate(username_list):
            if len(users_to_save) >= 100:  # Limit user count to avoid too many requests
                break
                
            user_info = get_user_info_safe(username)
            if user_info:
                users_to_save.append(user_info)
            
            if i % 10 == 0:
                print(f"  Progress: {i+1}/{min(len(username_list), 100)}")
                saved = save_users_batch(users_to_save)
                print(f"  💾 Saved {saved} users")
                users_to_save = []
                
            time.sleep(1)  # Conservative delay
        
        # Save remaining users
        if users_to_save:
            save_users_batch(users_to_save)
        
        end_time = time.time()
        
        # Final statistics
        conn = sqlite3.connect('reddit_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM submissions")
        final_post_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT submitter) FROM submissions")
        unique_authors = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(created_datetime), MAX(created_datetime) FROM submissions")
        time_range = cursor.fetchone()
        conn.close()
        
        print(f"\n🎊 Final statistics:")
        print(f"📊 Total posts: {final_post_count}")
        print(f"👥 Unique authors: {unique_authors}")
        print(f"⏰ Time range: {time_range[0]} to {time_range[1]}")
        print(f"⏱️ Total time: {(end_time - start_time)/60:.1f} minutes")
        
        if final_post_count < 500:
            print("\n💡 Suggestion: You can run the script again to get more data")
        
    except KeyboardInterrupt:
        print("\n⏹️ User interrupted crawling")
    except Exception as e:
        print(f"\n❌ Program exception: {e}")