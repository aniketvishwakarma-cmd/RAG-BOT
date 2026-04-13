from app.ingestion.scraper import RBIScraper


if __name__ == "__main__":
    scraper = RBIScraper()
    for document in scraper.scrape_listing("https://www.rbi.org.in"):
        print(f"{document.title} -> {document.url}")

