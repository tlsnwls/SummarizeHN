from newspaper import Article
import requests
import nltk
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from config_gemini import get_article_category, INTEREST_CATEGORIES

# Automatically check and download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("NLTK 'punkt','punkt_tab' data not found. Downloading...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    
# Selenium WebDriver Settings (Background Execution)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)
service = Service(ChromeDriverManager().install())

def get_hacker_news_urls(limit=30):
    """Get latest Hacker News article URLs and titles"""
    print(f"Retrieving the hottest {limit} articles from Hacker News...")
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty"
    try:
        top_ids = requests.get(top_stories_url, timeout=10).json()
    except requests.RequestException as e:
        print(f"Failed calling Hacker News API: {e}")
        raise e

    articles = []
    for story_id in top_ids[:limit]:
        item_url = f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json'
        try:
            item = requests.get(item_url, timeout=5).json()
            if item and 'url' in item and 'title' in item:
                articles.append({'url': item['url'], 'title': item['title']})
        except requests.RequestException:
            continue
    print(f"A total of {len(articles)} were successfully retrieved.")
    return articles

def crawl_and_summarize(url: str):
    """Access a URL with Selenium, extract text and summarize"""
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        time.sleep(3)
        article = Article(url)
        article.download(input_html=driver.page_source)
        article.parse()
        article.nlp()
        return article.summary if article.summary else "Failed to generate summary :("
    except Exception as e:
        return f"Error occured while generating summary: {e}"
    finally:
        driver.quit()

def is_supported_url(url: str):
    """Exclude non-contextual content domains"""
    excluded_domains = ["github.com", "youtube.com", "x.com", "ycombinator.com"]
    return not any(domain in url for domain in excluded_domains)

if __name__ == "__main__":
    # STEP 1: Get Hacker News articles
    all_articles = get_hacker_news_urls(limit=30)
    all_articles = [a for a in all_articles if is_supported_url(a['url'])]
    
    # STEP 2: Get categories + priorities from Gemini
    print("\n--Start interest-based filtering--")
    titles = [a['title'] for a in all_articles]
    categories_with_scores = get_article_category(titles)

    filtered_articles = []
    for article in all_articles:
        title = article['title']
        data = categories_with_scores.get(title, {"category": "Other", "EngineerPriority": 1, "StartupPotential": 1})
        category = data["category"]
        article['category'] = category
        article['EngineerPriority'] = data.get("EngineerPriority", 1)
        article['StartupPotential'] = data.get("StartupPotential", 1)

        print(f" -Title: {title[:60]:<60} -> Category:{category}, EngineerPriority:{article['EngineerPriority']}, StartupPotential:{article['StartupPotential']}")
        
        if category in INTEREST_CATEGORIES:
            filtered_articles.append(article)

    print(f"\n[Filtering completed] {len(filtered_articles)} articles of interest found.")

    # STEP 3: Select top 10 based on priority (Engineer or Startup)
    final_selection = sorted(
        filtered_articles,
        key=lambda x: (x['EngineerPriority'], x['StartupPotential']),
        reverse=True
    )[:10]

    print(f"\n---Start summarizing the final selected {len(final_selection)} articles---")
    results = []
    for article in final_selection:
        summary = crawl_and_summarize(article['url'])
        article['summary'] = summary
        results.append(article)
        
        print("\n" + "="*80)
        print(f"URL     : {article['url']}")
        print(f"Title   : {article['title']}")
        print(f"Category: {article['category']}")
        print(f"EngineerPriority: {article['EngineerPriority']}")
        print(f"StartupPotential: {article['StartupPotential']}")
        print(f"Summary : {article['summary']}")
        print("="*80)

    print("\n--All work has been completed.--")
