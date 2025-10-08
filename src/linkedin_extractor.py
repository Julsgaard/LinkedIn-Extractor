"""
LinkedIn Extractor
------------------
Extracts skills from LinkedIn profiles using Selenium and BeautifulSoup.
"""

import time
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LinkedInSkillExtractor:
    """Extracts skill data from LinkedIn profiles."""

    def __init__(self, headless=False, debug=False):
        self.driver = None
        self.headless = headless
        if debug:
            logger.setLevel(logging.DEBUG)

    def setup_driver(self):
        """Setup Chrome WebDriver."""
        logger.info("Setting up Chrome WebDriver...")
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")
            logger.info("Running in headless mode")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )

        driver_path = ChromeDriverManager().install()
        if "THIRD_PARTY_NOTICES" in driver_path:
            driver_dir = os.path.dirname(driver_path)
            driver_path = os.path.join(driver_dir, "chromedriver")

        self.driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        logger.info("WebDriver setup complete")

    def login(self, email, password):
        """Login to LinkedIn."""
        logger.info("Logging in to LinkedIn...")
        self.driver.get("https://www.linkedin.com/login")
        try:
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            email_field.send_keys(email)
            password_field.send_keys(password)
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(5)
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise

    def scrape_skills(self, profile_url, save_html=False):
        """Scrape all skills from a LinkedIn profile."""
        if not profile_url.startswith("http"):
            skills_url = f"https://www.linkedin.com/in/{profile_url}/details/skills/"
        elif "/details/skills/" in profile_url:
            skills_url = profile_url
        else:
            profile_url = profile_url.rstrip("/")
            skills_url = f"{profile_url}/details/skills/"

        logger.info(f"Navigating to: {skills_url}")
        self.driver.get(skills_url)
        time.sleep(3)

        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[id*="profilePagedListComponent"]'))
            )
            logger.info("Skill components detected!")
        except Exception as e:
            logger.warning(f"Timeout waiting for skills: {e}")

        self._scroll_until_loaded()
        page_source = self.driver.page_source

        if save_html:
            with open("skills_page.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            logger.info("Saved page HTML for debugging")

        soup = BeautifulSoup(page_source, "html.parser")
        return self._extract_skills_from_html(soup)

    def _scroll_until_loaded(self):
        """Scroll to load all skills."""
        logger.info("Scrolling to load all skills...")
        prev = 0
        stable = 0
        for i in range(20):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            current = len(self.driver.find_elements(By.CSS_SELECTOR, '[id*="profilePagedListComponent"]'))
            if current > prev:
                logger.info(f"Loaded {current} skills (was {prev})")
                prev = current
                stable = 0
            else:
                stable += 1
            if stable >= 2:
                break
        logger.info("Scrolling complete.")

    def _extract_skills_from_html(self, soup):
        """Extract skills from BeautifulSoup-parsed HTML."""
        skills = []
        elements = soup.find_all("li", id=lambda x: x and "profilePagedListComponent" in x)
        for elem in elements:
            spans = elem.find_all("span", {"aria-hidden": "true"})
            for span in spans:
                text = span.get_text(strip=True)
                if text and "endorsement" not in text.lower():
                    if text not in skills:
                        skills.append(text)
                        break
        return skills

    def save_skills(self, skills, filename="skills.txt"):
        """Save skills to a file."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(skills))
        logger.info(f"Saved {len(skills)} skills → {filename}")

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed.")


def main():
    """CLI entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract skills from a LinkedIn profile")
    parser.add_argument("profile", nargs="?", help="LinkedIn profile username (e.g., kristian-julsgaard)")
    parser.add_argument("--email", required=True, help="LinkedIn email")
    parser.add_argument("--password", required=True, help="LinkedIn password")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--output", default="skills.txt", help="Output filename")
    parser.add_argument("--save-html", action="store_true", help="Save raw HTML for debugging")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    scraper = LinkedInSkillExtractor(headless=args.headless, debug=args.debug)
    try:
        scraper.setup_driver()
        scraper.login(args.email, args.password)
        skills = scraper.scrape_skills(args.profile, save_html=args.save_html)
        scraper.save_skills(skills, args.output)
    finally:
        scraper.close()
