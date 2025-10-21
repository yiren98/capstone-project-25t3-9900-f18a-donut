import sqlite3
import csv

def export_to_csv():
    """Export data to CSV files"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    # Export submissions data
    cursor.execute("SELECT * FROM submissions")
    submissions = cursor.fetchall()
    
    with open('submissions.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Reddit_ID', 'Title', 'Author', 'Discussion_URL', 'URL', 'Score', 'Comment_Count', 
                        'Created_Timestamp', 'Content', 'Timezone', 'Location', 'Crawled_Time', 'Created_Time', 'Keyword_Matched', 'Post_Year'])
        writer.writerows(submissions)
    
    print(f"✅ Exported {len(submissions)} posts to submissions.csv")
    
    # Export comments data (new)
    cursor.execute("SELECT * FROM comments")
    comments = cursor.fetchall()
    
    with open('comments.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Comment_ID', 'Parent_ID', 'Submission_ID', 'Author', 'Body', 'Score', 
                        'Created_UTC', 'Created_Time', 'Depth', 'Crawled_Time'])
        writer.writerows(comments)
    
    print(f"✅ Exported {len(comments)} comments to comments.csv")
    
    # Export user data
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    
    with open('users.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Username', 'Comment_Karma', 'Link_Karma', 'User_Created_Time', 'User_Timezone'])
        writer.writerows(users)
    
    print(f"✅ Exported {len(users)} users to users.csv")
    
    conn.close()

if __name__ == "__main__":
    export_to_csv()