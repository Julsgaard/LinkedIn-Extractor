"""
LinkedIn Extractor
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


class LinkedInExtractor:
    def __init__(self, headless=False, debug=False):
        """
        Initialize the LinkedIn skill scraper.

        Args:
            headless (bool): Run browser in headless mode (no GUI)
            debug (bool): Enable debug logging
        """
        self.driver = None
        self.headless = headless

        # Create debug output directory
        self.debug_output_dir = os.path.join(os.getcwd(), 'linkedin_debug')
        os.makedirs(self.debug_output_dir, exist_ok=True)

        if debug:
            logger.setLevel(logging.DEBUG)

    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        logger.info("Setting up Chrome WebDriver...")
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless')
            logger.info("Running in headless mode")
        else:
            logger.info("Running in GUI mode (visible browser)")

        # Essential options for Docker/headless environments
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
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
        logger.debug(f"Browser window size: {self.driver.get_window_size()}")

    def _save_debug_screenshot(self, filename_prefix="debug"):
        """Save a screenshot for debugging purposes."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{filename_prefix}_{timestamp}.png"
            screenshot_path = os.path.join(self.debug_output_dir, screenshot_filename)
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return None

    def _save_page_source(self, filename_prefix="debug"):
        """Save the page source HTML for debugging."""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            html_filename = f"{filename_prefix}_{timestamp}.html"
            html_path = os.path.join(self.debug_output_dir, html_filename)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Page source saved to: {html_path}")
            return html_path
        except Exception as e:
            logger.error(f"Failed to save page source: {e}")
            return None

    def _check_for_login_challenges(self):
        """
        Check for various LinkedIn authentication challenges with detailed type detection.

        Returns:
            tuple: (challenge_type, message) or (None, None) if no challenge detected
        """
        try:
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()

            logger.debug(f"Checking for challenges on URL: {current_url}")

            # FIRST: Check if we're already successfully logged in
            # This prevents false positives from reCAPTCHA iframes that may exist on LinkedIn pages
            if ('feed' in current_url or
                'mynetwork' in current_url or
                '/in/' in current_url or
                '/detail/' in current_url or
                'linkedin.com/learning' in current_url or
                'linkedin.com/jobs' in current_url or
                'linkedin.com/messaging' in current_url or
                'linkedin.com/notifications' in current_url):
                logger.info(f"Already on a logged-in page (URL: {current_url}) - no challenge detected")
                return (None, None)

            # Also check for common logged-in page elements
            try:
                logged_in_indicators = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    '[data-control-name="identity_welcome_message"], .global-nav, .feed-identity-module, nav.global-nav, .authentication-outlet'
                )
                if logged_in_indicators:
                    logger.info(f"Logged-in page elements detected ({len(logged_in_indicators)} indicators found) - no challenge detected")
                    return (None, None)
            except:
                pass

            # Check if we're NOT on a login/challenge page (inverse check)
            if not any(keyword in current_url for keyword in ['login', 'checkpoint', 'challenge', 'uas/login']):
                logger.info(f"Not on a login/challenge page (URL: {current_url}) - assuming successful login")
                return (None, None)

            # Get all visible text from the page for comprehensive checking
            try:
                visible_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                logger.info(f"Page visible text (first 500 chars): {visible_text[:500]}")
            except:
                visible_text = ""
                logger.warning("Could not retrieve page visible text")

            # SECOND: Check for error messages (like incorrect password)
            # This should be checked before CAPTCHA because LinkedIn often shows both
            error_selectors = [
                '.form__label--error',
                '[role="alert"]',
                '.alert',
                '.error-message',
                '[id*="error"]',
                '.artdeco-inline-feedback--error',
                '.form__input--error',
                'div[data-test-form-element-error]',
                '.error',
                'span.error',
                'p.error'
            ]

            for selector in error_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        text = elem.text.strip()
                        if text and len(text) > 0:
                            logger.warning(f"Error message found with selector '{selector}': {text}")

                            # Categorize the error
                            text_lower = text.lower()
                            if 'password' in text_lower and ('incorrect' in text_lower or 'wrong' in text_lower or "couldn't" in text_lower or "not recognize" in text_lower or "doesn't match" in text_lower):
                                return ("INCORRECT_PASSWORD", f"Incorrect password: {text}")
                            elif ('email' in text_lower or 'username' in text_lower) and ('incorrect' in text_lower or 'wrong' in text_lower or 'invalid' in text_lower or "couldn't find" in text_lower or "not found" in text_lower):
                                return ("INVALID_EMAIL", f"Invalid email/username: {text}")
                            elif 'try again' in text_lower or 'please try again' in text_lower:
                                return ("LOGIN_ATTEMPT_ERROR", f"Login attempt failed: {text}")
                            elif any(keyword in text_lower for keyword in ['error', 'failed', 'unable', 'could not']):
                                # Generic error, but still prioritize over CAPTCHA
                                return ("LOGIN_ERROR", f"Login error: {text}")
                    except:
                        continue

            # Also check the visible text for common LinkedIn error messages
            if visible_text:
                error_phrases = [
                    ("hmm, that's not the right password", "INCORRECT_PASSWORD", "Incorrect password. Please check your password and try again."),
                    ("that's not the right password", "INCORRECT_PASSWORD", "Incorrect password. Please check your password and try again."),
                    ("the password you provided doesn't match", "INCORRECT_PASSWORD", "Incorrect password. The password doesn't match our records."),
                    ("couldn't find a linkedin account", "INVALID_EMAIL", "Invalid email. No LinkedIn account found with this email address."),
                    ("we don't recognize that email", "INVALID_EMAIL", "Invalid email. LinkedIn doesn't recognize this email address."),
                    ("that email address isn't registered", "INVALID_EMAIL", "Invalid email. This email address is not registered with LinkedIn."),
                    ("incorrect email or password", "INCORRECT_PASSWORD", "Incorrect email or password. Please check your credentials."),
                    ("wrong email or password", "INCORRECT_PASSWORD", "Incorrect email or password. Please check your credentials."),
                    ("please check your username", "INVALID_EMAIL", "Invalid username. Please verify your email address."),
                    ("we couldn't find an account", "INVALID_EMAIL", "Account not found. Please check your email address."),
                ]

                for phrase, error_type, message in error_phrases:
                    if phrase in visible_text:
                        logger.warning(f"Detected error phrase in page text: '{phrase}'")
                        return (error_type, message)

            # Check for phone verification
            phone_verification_indicators = [
                'input[id*="phone"]',
                'input[name*="phone"]',
                '[id*="phoneNumber"]',
                '[name*="phoneNumber"]'
            ]

            for selector in phone_verification_indicators:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Check if it's asking for phone number input
                    if any(keyword in visible_text for keyword in ['phone', 'mobile', 'verification code', 'enter code']):
                        logger.warning(f"Phone verification detected using selector: {selector}")
                        logger.info(f"Page contains text: {visible_text[:200]}...")
                        return ("PHONE_VERIFICATION",
                               "Phone verification required. LinkedIn is asking for a code sent to your phone. "
                               "This usually happens when logging in from a new location or suspicious activity is detected.")

            # Check for email verification
            email_verification_indicators = [
                'input[id*="email-pin"]',
                'input[name*="email"]',
                '[id*="email-verification"]'
            ]

            for selector in email_verification_indicators:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    if 'email' in visible_text and any(keyword in visible_text for keyword in ['code', 'verification', 'pin']):
                        logger.warning(f"Email verification detected using selector: {selector}")
                        logger.info(f"Page contains text: {visible_text[:200]}...")
                        return ("EMAIL_VERIFICATION",
                               "Email verification required. LinkedIn sent a verification code to your email address. "
                               "Please check your email and note that automated scraping cannot complete this step.")

            # Check for reCAPTCHA (Google) - but only if no error message was found AND we're still on login page
            recaptcha_selectors = [
                'iframe[title*="recaptcha"]',
                'iframe[src*="recaptcha"]',
                '.g-recaptcha',
                '#g-recaptcha',
                '[class*="recaptcha"]'
            ]

            for selector in recaptcha_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Check if the reCAPTCHA iframe is actually visible (not hidden)
                    try:
                        is_visible = elements[0].is_displayed()
                        if not is_visible:
                            logger.info(f"reCAPTCHA iframe found but not visible - ignoring")
                            continue
                    except:
                        # If we can't determine visibility, check other factors
                        pass

                    logger.warning(f"Google reCAPTCHA detected using selector: {selector}")
                    logger.info(f"reCAPTCHA iframe found: {elements[0].get_attribute('src') if elements[0].get_attribute('src') else 'N/A'}")

                    # Check if this is JUST a CAPTCHA or if there's an underlying error
                    # If we see password-related text, prioritize that
                    password_keywords = ['password', 'incorrect', 'wrong', "couldn't", "not recognize", "doesn't match", "not the right"]
                    if any(keyword in visible_text for keyword in password_keywords):
                        logger.warning("CAPTCHA present but password error text detected - treating as password error")
                        return ("INCORRECT_PASSWORD",
                               "Incorrect password detected. LinkedIn is also showing a CAPTCHA challenge. "
                               "Please verify your password is correct and try again later when the CAPTCHA requirement may be lifted.")

                    return ("RECAPTCHA",
                           "Google reCAPTCHA detected. LinkedIn is using an image/puzzle CAPTCHA to verify you're human. "
                           "This cannot be solved automatically. This may indicate incorrect credentials or suspicious activity. "
                           "Try logging in manually through a browser first or wait before retrying.")

            # Check for generic CAPTCHA
            captcha_selectors = [
                '[id*="captcha"]',
                '[class*="captcha"]',
                'img[alt*="captcha"]',
                'img[src*="captcha"]'
            ]

            for selector in captcha_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.warning(f"Generic CAPTCHA detected using selector: {selector}")
                    element_info = elements[0].get_attribute('outerHTML')[:200]
                    logger.debug(f"CAPTCHA element: {element_info}...")
                    return ("CAPTCHA_PUZZLE",
                           "CAPTCHA puzzle detected. LinkedIn is requiring an image/text CAPTCHA challenge. "
                           "This typically happens when automated activity is detected or credentials are incorrect.")

            # Check for 2FA / PIN verification
            verification_selectors = [
                'input[id*="verification"]',
                'input[name*="pin"]',
                'input[id*="pin-verification"]',
                'input[type="tel"]',
                '[data-id*="verification"]',
                '[aria-label*="verification"]'
            ]

            for selector in verification_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.warning(f"2FA/PIN verification detected using selector: {selector}")
                    element_attrs = elements[0].get_attribute('outerHTML')[:200]
                    logger.debug(f"Verification element: {element_attrs}...")

                    # Try to determine what kind of verification
                    logger.info(f"Verification page text sample: {visible_text[:300]}...")

                    if 'authenticator' in visible_text or 'authentication app' in visible_text:
                        return ("AUTHENTICATOR_APP",
                               "Authenticator app verification required. LinkedIn is asking for a code from your authentication app "
                               "(like Google Authenticator or Microsoft Authenticator). Automated scraping cannot complete this.")
                    elif 'text' in visible_text or 'sms' in visible_text:
                        return ("SMS_VERIFICATION",
                               "SMS verification required. LinkedIn sent a code via text message to your phone. "
                               "Automated scraping cannot complete this step.")
                    else:
                        return ("TWO_FACTOR_AUTH",
                               "Two-factor authentication required. LinkedIn is asking for an additional verification code. "
                               "This security feature prevents automated access.")

            # Check for security challenge/checkpoint
            if 'checkpoint/challenge' in current_url or 'uas/challenge' in current_url:
                logger.warning(f"Security checkpoint detected in URL: {current_url}")

                # Try to get more details from the page
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, 'body').text
                    logger.info(f"Security challenge page text: {page_text[:500]}...")

                    if 'unusual activity' in page_text.lower():
                        return ("UNUSUAL_ACTIVITY_CHECKPOINT",
                               "LinkedIn security checkpoint: Unusual activity detected. "
                               "LinkedIn has flagged suspicious behavior on this account. You may need to verify your identity manually.")
                    elif 'verify' in page_text.lower():
                        return ("VERIFICATION_CHECKPOINT",
                               "LinkedIn verification checkpoint: Account verification required. "
                               "LinkedIn is asking you to verify your account through additional steps.")
                except:
                    pass

                return ("SECURITY_CHECKPOINT",
                       "LinkedIn security checkpoint encountered. This is a manual verification page that requires human interaction.")

            # Check if still on login page (important for catching silent failures)
            if 'linkedin.com/login' in current_url or 'linkedin.com/uas/login' in current_url:
                logger.warning(f"Still on login page after attempt: {current_url}")

                # Try to find the password/email input fields to confirm we're on the login form
                try:
                    password_field = self.driver.find_elements(By.ID, 'password')
                    email_field = self.driver.find_elements(By.ID, 'username')

                    if password_field and email_field:
                        logger.warning("Login form still present - login likely failed")

                        # Check page text more thoroughly for credential errors
                        body_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                        logger.info(f"Login page body text: {body_text[:300]}...")

                        if any(keyword in body_text for keyword in ['incorrect', 'wrong', 'invalid', "couldn't find", "doesn't match", "not recognize"]):
                            if 'password' in body_text:
                                return ("INCORRECT_PASSWORD",
                                       "Incorrect password. Please verify your LinkedIn password and try again.")
                            elif 'email' in body_text or 'username' in body_text:
                                return ("INVALID_EMAIL",
                                       "Invalid email address. Please verify your LinkedIn email and try again.")
                            else:
                                return ("CREDENTIALS_REJECTED",
                                       "Login credentials were rejected. Please verify your LinkedIn email and password are correct.")
                        else:
                            return ("STILL_ON_LOGIN",
                                   "Login failed - still on login page. This could indicate incorrect credentials, rate limiting, or network issues. "
                                   "Please verify your credentials are correct and try again later.")
                except Exception as e:
                    logger.debug(f"Error checking login form presence: {e}")

                return ("STILL_ON_LOGIN",
                       "Still on login page after login attempt. This could indicate incorrect credentials or a silent failure.")

            return (None, None)

        except Exception as e:
            logger.error(f"Error checking for login challenges: {e}", exc_info=True)
            return (None, None)

    def login(self, email, password):
        """
        Login to LinkedIn.

        Args:
            email (str): LinkedIn email
            password (str): LinkedIn password

        Raises:
            Exception: If login fails
        """
        logger.info("=" * 60)
        logger.info("Starting LinkedIn login process")
        logger.info("=" * 60)

        try:
            logger.info("Navigating to LinkedIn login page...")
            self.driver.get('https://www.linkedin.com/login')
            logger.debug(f"Current URL: {self.driver.current_url}")
            logger.debug(f"Page title: {self.driver.title}")

            # Wait for login form
            logger.info("Waiting for login form to load...")
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'username'))
            )
            logger.info("✓ Email field found")

            password_field = self.driver.find_element(By.ID, 'password')
            logger.info("✓ Password field found")

            # Enter credentials
            logger.info(f"Entering email: {email[:3]}***@{email.split('@')[1] if '@' in email else '***'}")
            email_field.clear()
            email_field.send_keys(email)

            logger.info("Entering password: ***")
            password_field.clear()
            password_field.send_keys(password)

            # Click login button
            logger.info("Looking for login button...")
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            logger.info("✓ Login button found")
            logger.debug(f"Login button text: {login_button.text}")

            logger.info("Clicking login button...")
            login_button.click()

            # Wait a moment for the page to start loading
            time.sleep(2)
            logger.debug(f"URL after login attempt: {self.driver.current_url}")

            # Check for immediate challenges
            challenge_type, challenge_msg = self._check_for_login_challenges()
            if challenge_type:
                logger.error(f"Login challenge detected: {challenge_type}")
                logger.error(f"Message: {challenge_msg}")
                self._save_debug_screenshot(f"login_challenge_{challenge_type}")
                self._save_page_source(f"login_challenge_{challenge_type}")
                raise Exception(f"{challenge_type}: {challenge_msg}")

            # Wait for login to complete by checking for feed or profile
            logger.info("Waiting for login to complete...")
            logger.info("Looking for indicators: feed URL, mynetwork URL, or welcome message...")

            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: 'feed' in driver.current_url or
                                   'mynetwork' in driver.current_url or
                                   driver.find_elements(By.CSS_SELECTOR, '[data-control-name="identity_welcome_message"]')
                )
                logger.info("=" * 60)
                logger.info("✓ Login successful!")
                logger.info("=" * 60)
                logger.debug(f"Final URL: {self.driver.current_url}")
                logger.debug(f"Page title: {self.driver.title}")

            except Exception as wait_error:
                logger.error("Login verification timed out")
                logger.debug(f"Current URL: {self.driver.current_url}")
                logger.debug(f"Page title: {self.driver.title}")

                # Check again for challenges
                challenge_type, challenge_msg = self._check_for_login_challenges()
                if challenge_type:
                    logger.error(f"Post-login challenge detected: {challenge_type}")
                    self._save_debug_screenshot(f"login_timeout_{challenge_type}")
                    self._save_page_source(f"login_timeout_{challenge_type}")
                    raise Exception(f"{challenge_type}: {challenge_msg}")
                else:
                    self._save_debug_screenshot("login_timeout")
                    self._save_page_source("login_timeout")
                    raise Exception(f"Login verification timeout. Unable to confirm successful login. URL: {self.driver.current_url}")

        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"Login failed: {e}")
            logger.error("=" * 60)
            logger.debug(f"Exception type: {type(e).__name__}")

            # Save debug information
            if self.driver:
                logger.info("Saving debug information...")
                self._save_debug_screenshot("login_failed")
                self._save_page_source("login_failed")

            raise

    def _count_skill_elements(self):
        """Count the current number of skill elements on the page."""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, '[id*="profilePagedListComponent"]')
            return len(elements)
        except:
            return 0

    def _wait_for_skills_to_load(self, timeout=30, check_interval=1):
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

            # If count hasn't changed for 2 checks, we're probably done (reduced from 3)
            if stable_count >= 2 and current_count > 0:
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

        # Wait for skill components to be present (removed redundant time.sleep)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[id*="profilePagedListComponent"]'))
            )
            logger.info("Skill components detected!")
        except Exception as e:
            logger.warning(f"Timeout waiting for skills to appear: {e}")

        # Wait dynamically for skills to fully load (reduced timeout and interval)
        initial_count = self._wait_for_skills_to_load(timeout=20, check_interval=1)

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

            # Wait a moment for content to load (reduced from 2 to 1 second)
            time.sleep(1)

            # Check if new skills loaded
            new_count = self._count_skill_elements()

            if new_count > last_count:
                logger.info(f"New skills loaded: {new_count} (was {last_count})")
                last_count = new_count
                stable_scrolls = 0 # Reset counter
            else:
                logger.debug(f"No new skills (still {new_count})")
                stable_scrolls += 1

            # Safety limit to prevent infinite scrolling
            if scroll_count >= 15:  # Reduced from 20
                logger.warning("Reached maximum scroll limit")
                break

        logger.info(f"Finished scrolling ({scroll_count} scrolls, {last_count} total skills)")

        # One final wait to ensure everything is rendered (reduced from 3 to 1 second)
        logger.debug("Final wait for rendering...")
        time.sleep(1)

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
                # Get clean text - skill names can be 1-100 characters (changed from 2 to support "C", "R", etc.)
                if text and 1 <= len(text) <= 100:
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
                    # Only direct text, not nested (changed from 2 to 1 to support single-char skills)
                    if text and len(list(elem.children)) <= 2 and 1 <= len(text) <= 100:
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
    scraper = LinkedInExtractor(headless=headless, debug=args.debug if hasattr(args, 'debug') else False)

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
