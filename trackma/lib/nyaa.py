import requests
import urllib.parse
import time
from bs4 import BeautifulSoup


MAX_RESPONSE_BYTES = 10 * 1024 * 1024
SAFE_TAGS = {
    'a', 'b', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3',
    'h4', 'hr', 'i', 'li', 'ol', 'p', 'pre', 's', 'span', 'strong', 'u', 'ul',
}

class NyaaSearcher:
    """
    Handles searching Nyaa.si by scraping its search page.
    This provides more results than the RSS feed.
    """
    BASE_URL = "https://nyaa.si/?q={query}&c={category}&f={filter}&p={page}"

    def __init__(self, messenger=None):
        self.msg = messenger

    def _fetch(self, url, purpose):
        for attempt in range(3):
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                with requests.get(url, headers=headers, timeout=20, stream=True) as response:
                    response.raise_for_status()
                    chunks = []
                    size = 0
                    for chunk in response.iter_content(64 * 1024):
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise ValueError('response is larger than 10 MB')
                        chunks.append(chunk)
                    encoding = response.encoding or 'utf-8'
                    return b''.join(chunks).decode(encoding, errors='replace')
            except Exception as e:
                if self.msg:
                    self.msg.warn(
                        f"Nyaa: Failed to fetch {purpose} (attempt {attempt + 1}/3) - {e}")
                if attempt < 2:
                    time.sleep(1)
        return None

    @staticmethod
    def _sanitize(fragment):
        if fragment is None:
            return ''
        for tag in fragment.find_all(['script', 'style', 'iframe', 'object', 'embed']):
            tag.decompose()
        for tag in fragment.find_all(True):
            if tag.name not in SAFE_TAGS:
                tag.unwrap()
                continue
            href = tag.get('href') if tag.name == 'a' else None
            tag.attrs = {}
            if href and urllib.parse.urlparse(href).scheme in {'http', 'https', 'magnet'}:
                tag['href'] = href
        return fragment.decode_contents().strip()

    def search(self, query, category="1_0", filter="0", page=1, include_page_info=False):
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
        page_number = int(page)
        encoded_query = urllib.parse.quote(query)
        url = self.BASE_URL.format(
            query=encoded_query, category=category, filter=filter, page=page_number)
        
        if self.msg:
            self.msg.debug(f"Nyaa: Scraping search results for {query} at {url}")
            
        page_html = self._fetch(url, 'search page')
        if page_html is None:
            return {'results': [], 'has_next': False} if include_page_info else []
        soup = BeautifulSoup(page_html, 'lxml')
        results = []

        # Find the search results table
        table = soup.find('table', class_='torrent-list')
        if not table:
            return {'results': [], 'has_next': False} if include_page_info else []

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
            if "English-translated" in category_name:
                category_short = "Sub"
            elif "Raw" in category_name:
                category_short = "Raw"
            elif "Non-English" in category_name:
                category_short = "Non-Eng"

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

        has_next = False
        pagination = soup.find('ul', class_='pagination')
        if pagination:
            for link in pagination.find_all('a', href=True):
                values = urllib.parse.parse_qs(
                    urllib.parse.urlparse(link['href']).query).get('p', [])
                try:
                    if values and int(values[0]) > page_number:
                        has_next = True
                        break
                except (TypeError, ValueError):
                    continue

        if include_page_info:
            return {'results': results, 'has_next': has_next}
        return results

    def get_description(self, url):
        """
        Fetch and return all information of a torrent from its Nyaa page.
        """
        if self.msg:
            self.msg.debug(f"Nyaa: Fetching full info from {url}")

        page = self._fetch(url, 'torrent information')
        if page is None:
            return "Failed to fetch information."
        soup = BeautifulSoup(page, 'lxml')
        
        # Remove all images
        for img in soup.find_all('img'):
            img.decompose()

        # Description
        desc_div = soup.find('div', id='torrent-description')
        desc_content = self._sanitize(desc_div) if desc_div else "<p>No description available.</p>"

        # File list (HTML)
        file_list_div = soup.find('div', class_='torrent-file-list')
        file_list_html = ""
        if file_list_div:
            panel = file_list_div.find_parent('div', class_='panel')
            file_list_html = self._sanitize(panel or file_list_div)

        # Comments (HTML)
        comments_div = soup.find('div', id='comments')
        comments_html = ""
        if comments_div:
            comments_html = self._sanitize(comments_div)

        # Construct final content string
        full_content = f"{desc_content}\n\n---\n\n{file_list_html}\n\n---\n\n{comments_html}"
        
        return full_content
