from urllib.parse import urljoin

import scrapy


class BookItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()
    amount_in_stock = scrapy.Field()
    rating = scrapy.Field()
    category = scrapy.Field()
    description = scrapy.Field()
    upc = scrapy.Field()


class BookspiderSpider(scrapy.Spider):
    name = "bookspider"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["https://books.toscrape.com"]

    def parse(self, response):
        """Parse category pages and follow links to books and next pages"""
        # Extract and follow links to all category pages
        category_links = response.css('div.side_categories ul.nav-list > li > ul > li > a')
        yield from response.follow_all(category_links, self.parse_category)

    def parse_category(self, response):
        """Parse a category page to extract book links and pagination"""
        # Get current category
        category = response.css('div.page-header h1::text').get().strip()

        # Extract and follow links to all books on the current page
        book_links = response.css('article.product_pod h3 a')
        for link in book_links:
            # Pass category as meta data to the callback
            yield response.follow(link, self.parse_book, meta={'category': category})

        # Follow link to the next page of this category, if it exists
        next_page = response.css('li.next a::attr(href)').get()
        if next_page:
            next_url = urljoin(response.url, next_page)
            yield scrapy.Request(next_url, self.parse_category)

    def parse_book(self, response):
        """Parse an individual book page to extract all required information"""
        # Extract book details
        book = BookItem()

        # Basic information from the main page
        book['title'] = response.css('div.product_main h1::text').get().strip()
        book['price'] = response.css('p.price_color::text').get().strip()

        # Extract availability/stock from text like "In stock (19 available)"
        stock_text = response.css('p.availability::text').getall()
        stock_text = ''.join([s.strip() for s in stock_text])
        if 'In stock' in stock_text:
            # Extract the number inside parentheses
            import re
            stock_match = re.search(r'\((\d+) available\)', stock_text)
            if stock_match:
                book['amount_in_stock'] = int(stock_match.group(1))
            else:
                book['amount_in_stock'] = "In stock"
        else:
            book['amount_in_stock'] = "Out of stock"

        # Extract rating (which is represented as a CSS class)
        rating_class = response.css('p.star-rating::attr(class)').get()
        if rating_class:
            # The class is like "star-rating Three" - extract the second word
            rating_text = rating_class.split()[1].lower()
            # Map text to numeric value
            rating_map = {
                'one': 1,
                'two': 2,
                'three': 3,
                'four': 4,
                'five': 5
            }
            book['rating'] = rating_map.get(rating_text, None)

        # Category is passed from the category page
        book['category'] = response.meta.get('category')

        # Description - handle case when description is empty
        description = response.css('div#product_description + p::text').get()
        book['description'] = description.strip() if description else "No description available"

        # UPC and other table data
        product_info_table = response.css('table.table-striped tr')
        for row in product_info_table:
            header = row.css('th::text').get().strip()
            value = row.css('td::text').get().strip()

            if header == 'UPC':
                book['upc'] = value

        yield book


custom_settings = {
    "FEED_FORMAT": "jsonlines",
    "FEED_URI": "books.jl"
}
