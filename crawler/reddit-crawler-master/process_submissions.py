import sqlite3
import csv
from datetime import datetime

def export_to_csv():
    """Export data to CSV file"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    # Export post data
    cursor.execute("SELECT * FROM submissions")
    submissions = cursor.fetchall()
    
    with open('new_dataset.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 使用英文表头
        writer.writerow(['ID', 'Reddit_ID', 'Location', 'Time', 'Title-Content', 'Source'])
        
        for submission in submissions:
            # Extract required fields
            # According to table structure, assume the following field order:
            # 0: id, 1: reddit_id, 2: title, 3: submitter, 4: discussion_url, 
            # 5: url, 6: score, 7: num_comments, 8: created_date, 9: post_content,
            # 10: timezone, 11: location, 12: crawled_time, 13: created_datetime,
            # 14: keyword_matched, 15: post_year
            
            # Format creation time
            raw_time = submission[13]  # created_datetime field
            formatted_time = format_creation_time_fixed(raw_time)
            
            # Combine title and content with "-" separator
            title = str(submission[2]) if submission[2] else ""
            content = str(submission[9]) if submission[9] else ""
            title_content = f"{title}-{content}"
            
            # Clean combined text
            title_content = clean_combined_text(title_content)
            
            row_data = [
                submission[0],      # ID
                submission[1],     # Reddit_ID
                'Global',           # Location - set to Global
                formatted_time,     # Formatted time
                title_content,      # Combined title-content
                'Reddit'            # Source - set to Reddit
            ]
            writer.writerow(row_data)
    
    print(f"✅ Successfully exported {len(submissions)} posts to new_dataset.csv")
    conn.close()

def format_creation_time_fixed(time_str):
    """Format creation time to YYYY-MM format"""
    if not time_str or time_str == '':
        return "1970-01"
    
    try:
        # Directly check string format and extract
        if isinstance(time_str, str):
            # Check if it's ISO format (YYYY-MM-DDTHH:MM:SS)
            if 'T' in time_str and len(time_str) >= 10:
                # Extract date part (YYYY-MM-DD)
                date_part = time_str.split('T')[0]
                # Extract year-month part (YYYY-MM)
                if len(date_part) >= 7:
                    year_month = date_part[:7]
                    # Verify format is correct (YYYY-MM)
                    if year_month[4] == '-' and year_month[:4].isdigit() and year_month[5:7].isdigit():
                        return year_month
            
            # If not ISO format, try other formats
            elif len(time_str) >= 7 and time_str[4] == '-':
                # Directly extract first 7 characters
                year_month = time_str[:7]
                if year_month[:4].isdigit() and year_month[5:7].isdigit():
                    return year_month
        
        # If none of the above methods work, return default value
        return "1970-01"
    except Exception as e:
        print(f"⚠️ Time formatting failed: '{time_str}', Error: {e}")
        return "1970-01"

def clean_combined_text(text):
    """Clean combined text"""
    if not text or text == 'nan-nan' or text == '-':
        return "-"
    
    # Remove extra spaces and line breaks
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = ' '.join(text.split())  # Merge multiple spaces
    
    # Truncate if text is too long
    if len(text) > 10000:
        text = text[:10000] + "...[Content truncated]"
    
    return text

def check_sample_data():
    """Check sample data to ensure correct merge format"""
    conn = sqlite3.connect('reddit_data.db')
    cursor = conn.cursor()
    
    # Get some sample data
    cursor.execute("SELECT id, title, post_content FROM submissions LIMIT 5")
    samples = cursor.fetchall()
    
    print("🔍 Title-Content Merge Samples:")
    for i, (id_val, title, content) in enumerate(samples):
        title = str(title) if title else ""
        content = str(content) if content else ""
        combined = f"{title}-{content}"
        cleaned = clean_combined_text(combined)
        
        print(f"   {i+1}. ID: {id_val}")
        print(f"      Title: {title[:50]}...")
        print(f"      Content: {content[:50]}...")
        print(f"      Combined: {cleaned[:100]}...")
        print()
    
    conn.close()

if __name__ == "__main__":
    # Check sample data first
    check_sample_data()
    
    print("\n" + "=" * 60)
    
    # Export data
    export_to_csv()