import requests
import urllib.parse
import re
import time
from bs4 import BeautifulSoup

class NyaaSearcher:
    """
    Handles searching Nyaa.si by scraping its search page.
    This provides more results than the RSS feed.
    """
    BASE_URL = "https://nyaa.si/?q={query}&c={category}&f={filter}&p={page}"

    def __init__(self, messenger=None):
        self.msg = messenger

    def search(self, query, category="1_0", filter="0", page=1):
        """
        Search Nyaa.si and return a list of results.
        Categories:
            0_0: All categories
            1_0: Anime (All)
            1_2: Anime - English-translated
        Filters:
            0: No filter
            1: No remakes
            2: Trusted only
        """
        encoded_query = urllib.parse.quote(query)
        url = self.BASE_URL.format(query=encoded_query, category=category, filter=filter, page=page)
        
        if self.msg:
            self.msg.debug(f"Nyaa: Scraping search results for {query} at {url}")
            
        response = None
        for attempt in range(3):
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=20)
                response.raise_for_status()
                break
            except Exception as e:
                if self.msg:
                    self.msg.warn(f"Nyaa: Failed to fetch page (attempt {attempt+1}/3) - {e}")
                if attempt == 2:
                    return []
                time.sleep(1)

        soup = BeautifulSoup(response.text, 'lxml')
        results = []

        # Find the search results table
        table = soup.find('table', class_='torrent-list')
        if not table:
            return []

        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8:
                continue

            # Category
            cat_link = cols[0].find('a')
            category_name = cat_link.get('title', 'Unknown') if cat_link else 'Unknown'
            # Simplify names: "Anime - English-translated" -> "Sub", "Anime - Raw" -> "Raw"
            category_short = "Unknown"
            if "English-translated" in category_name: category_short = "Sub"
            elif "Raw" in category_name: category_short = "Raw"
            elif "Non-English" in category_name: category_short = "Non-Eng"

            # Title and Link
            title_col = cols[1]
            links = title_col.find_all('a')
            # Usually the second link is the title if there's a comment icon, 
            # otherwise it's the first. We look for the one without a class or with 'title' class.
            title_link = title_col.find('a', class_=None) or links[-1]
            title = title_link.get('title', title_link.text).strip()
            page_url = "https://nyaa.si" + title_link.get('href')

            # Magnet Link
            magnet_link = cols[2].find_all('a')[1].get('href')

            # Metadata
            size = cols[3].text.strip()
            date = cols[4].text.strip()
            seeders = cols[5].text.strip()
            leechers = cols[6].text.strip()
            completed = cols[7].text.strip()

            results.append({
                'title': title,
                'link': magnet_link,
                'id': page_url,
                'category': category_short,
                'size': size,
                'seeders': seeders,
                'leechers': leechers,
                'completed': completed,
                'published': date
            })

        return results

    def get_description(self, url):
        """
        Fetch and return all information of a torrent from its Nyaa page.
        """
        if self.msg:
            self.msg.debug(f"Nyaa: Fetching full info from {url}")

        response = None
        for attempt in range(3):
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=20)
                response.raise_for_status()
                break
            except Exception as e:
                if self.msg:
                    self.msg.warn(f"Nyaa: Failed to fetch info (attempt {attempt+1}/3) - {e}")
                if attempt == 2:
                    return "Failed to fetch information."
                time.sleep(1)

        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove all images
        for img in soup.find_all('img'):
            img.decompose()

        # Description
        desc_div = soup.find('div', id='torrent-description')
        desc_content = desc_div.decode_contents().strip() if desc_div else "_No description available._"

        # File list (HTML)
        file_list_div = soup.find('div', class_='torrent-file-list')
        file_list_html = ""
        if file_list_div:
            panel = file_list_div.find_parent('div', class_='panel')
            file_list_html = str(panel) if panel else str(file_list_div)

        # Comments (HTML)
        comments_div = soup.find('div', id='comments')
        comments_html = ""
        if comments_div:
            comments_html = str(comments_div)

        # Construct final content string
        full_content = f"{desc_content}\n\n---\n\n{file_list_html}\n\n---\n\n{comments_html}"
        
        return full_content
