from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def scrape_text_from_url(url):
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")

    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs if p.get_text())
        
        driver.quit()
        return text.strip() or "No relevant text content found on the webpage."
    except Exception as e:
        driver.quit()
        return f"Error scraping with Selenium: {str(e)}"

# Example usage
if __name__ == "__main__":
    url = "https://en.wikipedia.org/wiki/Neymar"  # Replace with your desired URL
    print(scrape_text_from_url(url))
