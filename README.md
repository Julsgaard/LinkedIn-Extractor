# LinkedIn Extractor

A Python-based tool to extract skills from LinkedIn profile pages using dynamic content loading detection. The scraper intelligently waits for content to load rather than using fixed delays, making it faster and more reliable.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **Smart Content Detection** - Dynamically waits for skills to load instead of fixed delays
- 🤖 **Automated Browser Control** - Uses Selenium for reliable scraping
- 📊 **Proper Logging** - Track scraping progress with configurable logging levels
- 🛠️ **CLI & Programmatic API** - Use as command-line tool or import as library
- 💾 **Flexible Output** - Save to text files or use in your code
- 🔒 **Secure** - No hardcoded credentials, supports environment variables

## Installation

### Option 1: Install as Package (Recommended)

```bash
pip install -e .
```

This installs the package and provides a CLI command:

```bash
linkedin-extractor --help
```

You can also import the package from anywhere:

```python
from linkedin_extractor import LinkedInExtractor
```

### Option 2: Clone and Install Dependencies

```bash
git clone https://github.com/yourusername/linkedin-extractor.git
cd linkedin-extractor
pip install -r requirements.txt
```

## Usage

### Command Line Interface

#### Interactive Mode

Simply run without arguments for interactive prompts:

```bash
linkedin-extractor
```

Or if running from source:

```bash
python src/linkedin_extractor.py
```

#### Command Line Arguments

```bash
linkedin-extractor <profile> --email <email> --password <password> [options]
```

**Arguments:**
- `profile` - LinkedIn profile username (e.g., `kristian-julsgaard`)
- `--email` - Your LinkedIn email
- `--password` - Your LinkedIn password
- `--headless` - Run browser in headless mode (no GUI)
- `--output` - Output filename (default: `skills.txt`)
- `--save-html` - Save HTML for debugging
- `--debug` - Enable debug logging

**Example:**

```bash
linkedin-extractor kristian-julsgaard \
  --email your_email@example.com \
  --password your_password \
  --headless \
  --output kristian_skills.txt \
  --debug
```

### Programmatic Usage (Import as Library)

#### Basic Example

```python
from linkedin_extractor import LinkedInExtractor

# Initialize scraper
scraper = LinkedInExtractor(headless=False, debug=False)

try:
    # Setup and login
    scraper.setup_driver()
    scraper.login("your_email@example.com", "your_password")
    
    # Scrape skills
    skills = scraper.scrape_skills("kristian-julsgaard")
    
    # Use the skills list
    print(f"Found {len(skills)} skills:")
    for skill in skills:
        print(f"  - {skill}")
    
    # Save to file
    scraper.save_skills(skills, "output.txt")
    
finally:
    scraper.close()
```

#### Batch Scraping Multiple Profiles

```python
from linkedin_extractor import LinkedInExtractor
import time

profiles = ["profile1", "profile2", "profile3"]
scraper = LinkedInExtractor(headless=True)

try:
    scraper.setup_driver()
    scraper.login(email, password)
    
    all_skills = {}
    for profile in profiles:
        skills = scraper.scrape_skills(profile)
        all_skills[profile] = skills
        time.sleep(5)  # Be respectful to LinkedIn servers
        
finally:
    scraper.close()
```

#### Using Environment Variables for Credentials

```python
import os
from linkedin_extractor import LinkedInExtractor

email = os.getenv('LINKEDIN_EMAIL')
password = os.getenv('LINKEDIN_PASSWORD')

scraper = LinkedInExtractor()
try:
    scraper.setup_driver()
    scraper.login(email, password)
    skills = scraper.scrape_skills("profile-username")
    scraper.save_skills(skills, "skills.txt")
finally:
    scraper.close()
```

Set environment variables:
```bash
export LINKEDIN_EMAIL="your_email@example.com"
export LINKEDIN_PASSWORD="your_password"
```

## How It Works

### HTML Structure

The scraper identifies skills by finding `<li>` elements with IDs containing `profilePagedListComponent` and extracting text from `<span aria-hidden="true">` elements.

## API Reference

### LinkedInExtractor Class

#### Constructor

```python
LinkedInExtractor(headless=False, debug=False)
```

**Parameters:**
- `headless` (bool): Run browser without GUI
- `debug` (bool): Enable debug logging

#### Methods

**`setup_driver()`**
- Sets up Chrome WebDriver with anti-detection measures

**`login(email, password)`**
- Login to LinkedIn
- Raises `Exception` if login fails

**`scrape_skills(profile_url, save_html=False)`**
- Scrapes skills from a profile
- `profile_url`: Username or full URL
- `save_html`: Save page HTML for debugging
- Returns: List of skill names

**`save_skills(skills, filename='skills.txt')`**
- Saves skills to a text file
- `skills`: List of skill names
- `filename`: Output file path

**`close()`**
- Closes the browser (always call in finally block)

## Requirements

- Python 3.8+
- Chrome browser
- LinkedIn account

Python dependencies (installed automatically):
- `selenium>=4.0.0`
- `beautifulsoup4>=4.9.0`
- `webdriver-manager>=3.8.0`

## Output Format

Skills are saved as plain text, one per line:

```
Python
JavaScript
React
Machine Learning
Data Analysis
```

## Important Considerations

⚠️ **LinkedIn Terms of Service**: Automated scraping may violate LinkedIn's Terms of Service. Use responsibly:
- Only scrape public profiles or those you have permission to access
- Add delays between requests (use `time.sleep()` in batch operations)
- Respect LinkedIn's rate limits
- This tool is for educational and personal use only

⚠️ **Rate Limiting**: LinkedIn may throttle or block repeated automated requests. The scraper includes:
- User-agent spoofing
- Automation detection avoidance
- Smart waiting (less suspicious than fixed delays)

⚠️ **Privacy**: Be respectful of privacy and only scrape publicly available information.

## Troubleshooting

### "No skills found"
- Ensure the profile has public skills
- Check that you're logged in successfully
- Try running with `--save-html` to inspect the HTML
- Enable debug mode with `--debug`

### ChromeDriver issues
- The scraper auto-downloads ChromeDriver via `webdriver-manager`
- Ensure Chrome browser is installed
- Check Chrome and ChromeDriver versions match

### Login fails
- Verify credentials are correct
- LinkedIn may require 2FA or CAPTCHA (run in non-headless mode to complete manually)
- Try logging in manually in the browser first

### Skills load slowly or incompletely
- The dynamic waiting should handle this automatically
- If issues persist, check your internet connection
- LinkedIn may be throttling - add longer delays

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. The authors are not responsible for misuse or any violations of LinkedIn's Terms of Service. Use at your own risk and always respect LinkedIn's policies and user privacy.

## Changelog

### v0.1.4 (Current)
- Improved scrolling and content detection
- Reduced wait times for faster scraping
- Better support for single-character skills (e.g., "C", "R")
- Enhanced anti-detection measures
- Fixed ChromeDriver path issues
