"""
LinkedIn Skill Scraper
Scrapes skills from a LinkedIn profile's skills page.
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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LinkedInSkillScraper:
    def __init__(self, headless=False, debug=False):
        """
        Initialize the LinkedIn skill scraper.
        
        Args:
            headless (bool): Run browser in headless mode (no GUI)
            debug (bool): Enable debug logging
        """
        self.driver = None
        self.headless = headless
        
        if debug:
            logger.setLevel(logging.DEBUG)

    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        logger.info("Setting up Chrome WebDriver...")
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
            logger.info("Running in headless mode")

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add user agent to avoid detection
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
        
        # Fix ChromeDriver path issue
        driver_path = ChromeDriverManager().install()

        # If the path points to THIRD_PARTY_NOTICES, find the actual chromedriver
        if 'THIRD_PARTY_NOTICES' in driver_path:
            driver_dir = os.path.dirname(driver_path)
            driver_path = os.path.join(driver_dir, 'chromedriver')

        self.driver = webdriver.Chrome(
            service=Service(driver_path),
            options=chrome_options
        )
        logger.info("WebDriver setup complete")

    def login(self, email, password):
        """
        Login to LinkedIn.
        
        Args:
            email (str): LinkedIn email
            password (str): LinkedIn password

        Raises:
            Exception: If login fails
        """
        logger.info("Logging in to LinkedIn...")
        self.driver.get('https://www.linkedin.com/login')
        
        try:
            # Wait for login form
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            password_field = self.driver.find_element(By.ID, 'password')
            
            # Enter credentials
            email_field.send_keys(email)
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            logger.info("Login successful!")

        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    def _count_skill_elements(self):
        """Count the current number of skill elements on the page."""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, '[id*="profilePagedListComponent"]')
            return len(elements)
        except:
            return 0

    def _wait_for_skills_to_load(self, timeout=60, check_interval=2):
        """
        Wait for skills to load by monitoring when the count increases.

        Args:
            timeout (int): Maximum time to wait in seconds
            check_interval (int): How often to check for changes in seconds

        Returns:
            int: Final count of skill elements
        """
        logger.info("Waiting for skills to load...")
        start_time = time.time()
        last_count = 0
        stable_count = 0

        while time.time() - start_time < timeout:
            current_count = self._count_skill_elements()

            if current_count > last_count:
                logger.info(f"Skills loaded: {current_count} (was {last_count})")
                last_count = current_count
                stable_count = 0  # Reset stability counter
            else:
                stable_count += 1

            # If count hasn't changed for 3 checks, we're probably done
            if stable_count >= 3 and current_count > 0:
                logger.info(f"Skills stable at {current_count}, continuing...")
                return current_count

            time.sleep(check_interval)

        logger.warning(f"Timeout reached. Final count: {last_count}")
        return last_count

    def scrape_skills(self, profile_url, save_html=False):
        """
        Scrape skills from a LinkedIn profile.
        
        Args:
            profile_url (str): LinkedIn profile URL or username
            save_html (bool): Whether to save the HTML for debugging

        Returns:
            list: List of skill names
        """
        # Format the URL to point to the skills page
        if not profile_url.startswith('http'):
            # Assume it's a username
            skills_url = f'https://www.linkedin.com/in/{profile_url}/details/skills/'
        elif '/details/skills/' in profile_url:
            skills_url = profile_url
        else:
            # Remove trailing slash and add skills path
            profile_url = profile_url.rstrip('/')
            skills_url = f'{profile_url}/details/skills/'
        
        logger.info(f"Navigating to: {skills_url}")
        self.driver.get(skills_url)
        
        # Wait for initial page load
        logger.info("Waiting for initial page load...")
        time.sleep(3)

        # Wait for skill components to be present and loaded
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[id*="profilePagedListComponent"]'))
            )
            logger.info("Skill components detected!")
        except Exception as e:
            logger.warning(f"Timeout waiting for skills to appear: {e}")

        # Wait dynamically for skills to fully load
        initial_count = self._wait_for_skills_to_load(timeout=30, check_interval=2)

        if initial_count == 0:
            logger.warning("No skills detected yet. Trying to scroll anyway...")

        # Scroll to load all skills (lazy loading)
        self._scroll_page()

        # Get page source and parse with BeautifulSoup
        page_source = self.driver.page_source

        # Save HTML for debugging if requested
        if save_html:
            html_file = 'skills_page.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info(f"Saved page HTML to {html_file} for debugging")

        soup = BeautifulSoup(page_source, 'html.parser')
        
        skills = self._extract_skills_from_html(soup)
        
        return skills
    
    def _scroll_page(self):
        """Scroll the page to trigger lazy loading of all skills."""
        logger.info("Scrolling to load all skills...")

        last_count = self._count_skill_elements()
        scroll_count = 0
        stable_scrolls = 0

        while stable_scrolls < 2:  # Stop after 2 scrolls with no new content
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scroll_count += 1
            logger.debug(f"Scroll {scroll_count}...")

            # Wait a moment for content to load
            time.sleep(2)

            # Check if new skills loaded
            new_count = self._count_skill_elements()

            if new_count > last_count:
                logger.info(f"New skills loaded: {new_count} (was {last_count})")
                last_count = new_count
                stable_scrolls = 0  # Reset counter
            else:
                logger.debug(f"No new skills (still {new_count})")
                stable_scrolls += 1

            # Safety limit to prevent infinite scrolling
            if scroll_count >= 20:
                logger.warning("Reached maximum scroll limit")
                break

        logger.info(f"Finished scrolling ({scroll_count} scrolls, {last_count} total skills)")

        # One final wait to ensure everything is rendered
        logger.debug("Final wait for rendering...")
        time.sleep(3)

    def _extract_skills_from_html(self, soup):
        """
        Extract skill names from the HTML.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
        Returns:
            list: List of skill names
        """
        skills = []
        skipped_count = 0

        # Find all profilePagedListComponent elements
        paged_list_components = soup.find_all('li', id=lambda x: x and 'profilePagedListComponent' in x)
        
        logger.info(f"Found {len(paged_list_components)} profilePagedListComponent elements")

        for idx, component in enumerate(paged_list_components):
            # Try multiple strategies to find the skill name
            skill_name = None
            
            # Strategy 1: Look for all span elements with aria-hidden="true"
            # The skill name is usually in the first non-empty one
            skill_spans = component.find_all('span', {'aria-hidden': 'true'})

            for span in skill_spans:
                text = span.get_text(strip=True)
                # Get clean text - skill names are typically short
                if text and 2 <= len(text) <= 100:
                    # Skip metadata patterns
                    if (not text.isdigit() and
                        not text.startswith('(') and
                        not text.endswith('endorsement') and
                        not text.endswith('endorsements') and
                        'endorsement' not in text.lower()):
                        skill_name = text
                        break

            # Strategy 2: If still not found, look for the primary text content
            if not skill_name:
                # Find the first div or span with visible text
                all_text_elements = component.find_all(['span', 'div'])
                for elem in all_text_elements:
                    text = elem.get_text(strip=True)
                    # Only direct text, not nested
                    if text and len(list(elem.children)) <= 2 and 2 <= len(text) <= 100:
                        if (not text.isdigit() and
                            not text.startswith('(') and
                            'endorsement' not in text.lower()):
                            skill_name = text
                            break
            
            if skill_name:
                if skill_name not in skills:
                    skills.append(skill_name)
                    logger.debug(f"  - {skill_name}")
            else:
                skipped_count += 1
                logger.warning(f"Skipped component {idx + 1} - could not extract skill name")
                # Debug: print first 200 chars of the component HTML
                component_html = str(component)[:200]
                logger.debug(f"HTML preview: {component_html}...")

        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} components that couldn't be parsed")

        return skills
    
    def save_skills(self, skills, filename='skills.txt'):
        """
        Save skills to a file.
        
        Args:
            skills (list): List of skill names
            filename (str): Output filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for skill in skills:
                f.write(f"{skill}\n")
        logger.info(f"Skills saved to {filename}")

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")


def main():
    """Main function to run the scraper."""
    import argparse

    parser = argparse.ArgumentParser(description='Scrape skills from a LinkedIn profile')
    parser.add_argument('profile', nargs='?', help='LinkedIn profile username (e.g., kristian-julsgaard)')
    parser.add_argument('--email', help='LinkedIn email')
    parser.add_argument('--password', help='LinkedIn password')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', default='skills.txt', help='Output file (default: skills.txt)')
    parser.add_argument('--save-html', action='store_true', help='Save HTML for debugging')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    # If no arguments provided, use interactive mode
    if not args.profile:
        print("LinkedIn Skill Scraper")
        print("=" * 50)
        profile = input("Enter profile username (e.g., kristian-julsgaard): ").strip()
        email = input("Enter your LinkedIn email: ").strip()
        password = input("Enter your LinkedIn password: ").strip()
        headless = input("Run in headless mode? (y/n): ").strip().lower() == 'y'
    else:
        profile = args.profile
        email = args.email
        password = args.password
        headless = args.headless

    # Validate inputs
    if not profile:
        print("Error: Profile username is required")
        return

    if not email or not password:
        print("Error: LinkedIn credentials are required")
        return

    # Initialize scraper
    scraper = LinkedInSkillScraper(headless=headless, debug=args.debug if hasattr(args, 'debug') else False)

    try:
        # Setup driver
        scraper.setup_driver()
        
        # Login to LinkedIn
        scraper.login(email, password)

        # Scrape skills
        skills = scraper.scrape_skills(
            profile,
            save_html=args.save_html if hasattr(args, 'save_html') else False
        )

        print(f"\n{'='*50}")
        print(f"Total skills found: {len(skills)}")
        print(f"{'='*50}")
        
        if skills:
            print("\nSkills:")
            for skill in skills:
                print(f"  - {skill}")

        # Save skills to file
        output_file = args.output if hasattr(args, 'output') else 'skills.txt'
        scraper.save_skills(skills, output_file)

    except Exception as e:
        logger.error(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close browser
        scraper.close()


if __name__ == "__main__":
    main()
