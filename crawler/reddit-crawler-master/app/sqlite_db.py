import sqlite3

def create_schema_db():
    """创建数据库表结构"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    # 创建 submissions 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            title TEXT,
            submitter TEXT,
            discussion_url TEXT,
            url TEXT,
            score INTEGER,
            num_comments INTEGER,
            created_date REAL,
            post_content TEXT,    -- 🆕 帖子正文
            content_html TEXT -- 🆕 帖子正文的HTML格式
        )
    ''')
    
    # 创建 comments 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            parent_id TEXT,
            submission_id TEXT,
            user TEXT,
            text TEXT,
            score INTEGER,
            FOREIGN KEY (submission_id) REFERENCES submissions (id)
        )
    ''')
    
    # 创建 users 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            comment_karma INTEGER,
            link_karma INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库架构创建完成")

def save_submissions(submissions):
    """保存提交数据"""
    if not submissions:
        print("❌ 没有提交数据可保存")
        return
    
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    count = 0
    
    for submission in submissions:
        try:
            # 检查字段数量，支持新旧格式
            if len(submission) == 10:  # 新格式（有内容字段）
                cursor.execute('''
                    INSERT OR REPLACE INTO submissions 
                    (id, title, submitter, discussion_url, url, score, num_comments, created_date, post_content, content_html)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', submission)
            else:  # 旧格式（8个字段）
                cursor.execute('''
                    INSERT OR REPLACE INTO submissions 
                    (id, title, submitter, discussion_url, url, score, num_comments, created_date, post_content, content_html)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', submission + ("", ""))  # 添加空的内容字段
                
            count += 1
        except Exception as e:
            print(f"❌ 保存提交失败: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ 已保存 {count}/{len(submissions)} 个提交到数据库")

def save_submissions_comments(comments):
    """保存评论数据"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    for comment in comments:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO comments 
                (comment_id, parent_id, submission_id, user, text, score)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', comment)
        except Exception as e:
            print(f"❌ 保存评论失败: {e}")
    
    conn.commit()
    conn.close()
    print("✅ 数据库架构创建完成（已添加帖子内容字段）")

def save_users(users):
    """保存用户数据"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    for user in users:
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (username, comment_karma, link_karma)
                VALUES (?, ?, ?)
            ''', user)
        except Exception as e:
            print(f"❌ 保存用户失败: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ 已保存 {len(users)} 个用户到数据库")

# import sqlite3, os

# DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))+'/db/'

# db = sqlite3.connect(DATABASE_DIR+'python_subreddit.db')

# def create_schema_db():
# /*************  ✨ Windsurf Command ⭐  *************/
    """
    Creates the database schema from the schema.sql file.

    This function reads the schema.sql file and executes the SQL commands
    to create the database schema. It then commits the changes to
    the database.

    :return: None
    """
# /*******  7af03fc7-6c06-47a4-9412-8e332eb3c1d2  *******/
#     with open(DATABASE_DIR+'schema.sql', mode='r') as schema_script:
#         db.cursor().executescript(schema_script.read())
#     db.commit()

# def save_submissions(submissions):
#     insert_submissions = 'insert or ignore into submissions(id, title, submitter, discussion_url, url, punctuation, num_comments, created_date) values(?, ?, ?, ?, ?, ?, ?, ?)'
#     db.cursor().executemany(insert_submissions, submissions)
#     db.commit()

# def get_submission_by_id(id):
#     return db.cursor().execute("select * from submissions where id = ?;", (id,)).fetchall()

# def get_submissions_by_submitter(submitter):
#     return db.cursor().execute("select * from submissions where submitter = ?;", (submitter,)).fetchall()

# def get_submissions_commented_by_user(user):
#     return db.cursor().execute("select * from submissions where id in (select submission_id from comments where user = ?);", (user,)).fetchall()

# def get_submissions(type, order_by):
#     query = "select * from submissions"

#     if type == "external":
#         query += " where url NOT LIKE 'https://www.reddit.com%'"
#     elif type == "internal":
#         query += " where url LIKE 'https://www.reddit.com%'"

#     query += " order by " + order_by + " desc limit 10;"

#     return db.cursor().execute(query).fetchall()

# def save_submissions_comments(comments):
#     insert_comments = 'insert or ignore into comments(id, parent_id, submission_id, user, text, punctuation) values(?, ?, ?, ?, ?, ?)'
#     db.cursor().executemany(insert_comments, comments)
#     db.commit()

# # setting default to top 10
# def get_top_submitters(limit=10):
#     return db.cursor().execute("select submitter from submissions group by submitter order by count(*) desc limit ?;", (limit,)).fetchall()

# # setting default to top 10
# def get_top_commenters(limit=10):
#     return db.cursor().execute("select user from comments group by user order by count(*) desc limit ?;", (limit,)).fetchall()

# def save_users(users):
#     insert_users = 'insert or ignore into users(username, comment_karma, post_karma) values(?, ?, ?)'
#     db.cursor().executemany(insert_users, users)
#     db.commit()

# def get_user_comment_karma(username):
#     return db.cursor().execute("select comment_karma from users where username=?", (username,)).fetchall()

# def get_most_valued_users():
#     return db.cursor().execute("select * from users order by comment_karma+post_karma desc limit 10;").fetchall()
