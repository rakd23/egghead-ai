import requests
from bs4 import BeautifulSoup
import time
import os

def scrape_page(url):
    """Scrape a single page and return clean text"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        # ... rest of code stays the same
        
        # Remove scripts, styles, navigation, footer, header
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # Get text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

# List of NEW pages to scrape (only add new ones here)
urls_to_scrape = [
    "https://admissions.ucdavis.edu/", 
      # Add your new URL here
]

print("Starting web scraping...")
print(f"Will scrape {len(urls_to_scrape)} pages")

# Find the next available file number
existing_files = [f for f in os.listdir('uc_davis_data') if f.startswith('scraped_') and f.endswith('.txt')]
if existing_files:
    # Get highest number
    numbers = [int(f.replace('scraped_', '').replace('.txt', '')) for f in existing_files]
    start_num = max(numbers) + 1
else:
    start_num = 1

print(f"Starting at scraped_{start_num}.txt")

# Scrape each page
for i, url in enumerate(urls_to_scrape, start=start_num):
    print(f"\nScraping {url}...")
    text = scrape_page(url)
    
    if text:
        # Save to file in uc_davis_data folder
        filename = f"uc_davis_data/scraped_{i}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"SOURCE: {url}\n\n{text}")
        print(f"  ✓ Saved to {filename} ({len(text)} characters)")
    else:
        print(f"  ✗ Failed to scrape")
    
    # Be polite - wait between requests
    time.sleep(2)

print("\n✓ Done scraping!")
print("Next step: Run 'python build_vectorstore_supabase.py' to upload to Supabase")