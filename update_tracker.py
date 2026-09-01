import feedparser
import requests
import datetime
import pytz
import os

FEEDS = {
    "ArXiv (cs.AI)": "http://export.arxiv.org/rss/cs.AI",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "KDnuggets": "https://www.kdnuggets.com/feed",
}

def fetch_feed_entries(url, limit=5):
    try:
        feed = feedparser.parse(url)
        return feed.entries[:limit]
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def get_hacker_news_ai(limit=5):
    url = "https://hn.algolia.com/api/v1/search_by_date?query=Artificial%20Intelligence&tags=story&hitsPerPage=" + str(limit)
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        entries = []
        for hit in data.get('hits', []):
            entries.append({
                'title': hit.get('title'),
                'link': hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            })
        return entries
    except Exception as e:
        print(f"Error fetching HN: {e}")
        return []

def generate_markdown():
    tz = pytz.timezone('UTC')
    today = datetime.datetime.now(tz).strftime('%Y-%m-%d')
    
    md_content = f"# Awesome AI Tracker\n\n"
    md_content += f"Welcome to the Automated Awesome AI Tracker! This repository tracks the most important and up-to-date Artificial Intelligence information.\n\n"
    md_content += f"> Last Updated: {today} (UTC)\n\n"
    
    md_content += f"## 📰 Latest AI News & Discussions\n\n"
    
    # Hacker News
    md_content += f"### Hacker News (Latest AI Discussions)\n"
    hn_entries = get_hacker_news_ai(5)
    for entry in hn_entries:
        md_content += f"- [{entry['title']}]({entry['link']})\n"
    md_content += "\n"
    
    # RSS Feeds
    for source_name, url in FEEDS.items():
        md_content += f"### {source_name}\n"
        entries = fetch_feed_entries(url, 5)
        for entry in entries:
            title = entry.get('title', 'No Title')
            link = entry.get('link', '#')
            md_content += f"- [{title}]({link})\n"
        md_content += "\n"

    md_content += "---\n"
    md_content += "*This repository is automatically updated daily via GitHub Actions.*"
    
    return md_content

def main():
    print("Fetching AI data...")
    md_content = generate_markdown()
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    print("Updated README.md successfully.")

if __name__ == "__main__":
    main()
