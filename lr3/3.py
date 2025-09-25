import scrapy
import json


class InfiniteScrollQuotesSpider(scrapy.Spider):
    name = "quotes_infinite_scroll"
    start_urls = ["https://quotes.toscrape.com/api/quotes?page=1"]

    def parse(self, response):
        data = json.loads(response.text)

        for quote in data["quotes"]:
            yield {
                "author": quote["author"]["name"],
                "text": quote["text"],
                "tags": quote["tags"],
            }

        if data.get("has_next"):
            next_page = f'https://quotes.toscrape.com/api/quotes?page={data["page"] + 1}'
            yield scrapy.Request(next_page, callback=self.parse)
