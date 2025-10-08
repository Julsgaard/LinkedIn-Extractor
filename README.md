# LinkedIn Skill Scraper

A Python-based tool to scrape skills from LinkedIn profile skills pages using dynamic content loading detection. The scraper intelligently waits for content to load rather than using fixed delays, making it faster and more reliable.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **Smart Content Detection** - Dynamically waits for skills to load instead of fixed delays
- 🤖 **Automated Browser Control** - Uses Selenium for reliable scraping
- 📊 **Proper Logging** - Track scraping progress with configurable logging levels
- 🛠️ **CLI & Programmatic API** - Use as command-line tool or import as library
- 💾 **Flexible Output** - Save to text files or use in your code
- 🔒 **Secure** - No hardcoded credentials, supports environment variables
- 📄 **HTML Parsing** - Can parse saved HTML files without logging in

## Installation

### Option 1: Clone Repository (Recommended for GitHub)

```bash
git clone https://github.com/yourusername/linkedin-skill-scraper.git
cd linkedin-skill-scraper
pip install -r requirements.txt
```

### Option 2: Install as Package

```bash
pip install -e .
```

This allows you to import the package from anywhere:

```python
from linkedin_skill_scraper import LinkedInSkillScraper
```

## Usage

### Command Line Interface

#### Interactive Mode

Simply run without arguments for interactive prompts:

```bash
python linkedin_skill_scraper.py
```

#### Command Line Arguments

```bash
python linkedin_skill_scraper.py <profile> --email <email> --password <password> [options]
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
python linkedin_skill_scraper.py kristian-julsgaard \
  --email your_email@example.com \
  --password your_password \
  --headless \
  --output kristian_skills.txt \
  --debug
```

### Programmatic Usage (Import as Library)

#### Basic Example

```python
from linkedin_skill_scraper import LinkedInSkillScraper

# Initialize scraper
scraper = LinkedInSkillScraper(headless=False, debug=False)

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
from linkedin_skill_scraper import LinkedInSkillScraper
import time

profiles = ["profile1", "profile2", "profile3"]
scraper = LinkedInSkillScraper(headless=True)

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

See the `examples/` directory for more usage patterns.

### Parse Saved HTML (No Login Required)

If you have saved the HTML of a LinkedIn skills page:

```bash
python scrape_from_html.py skills_page.html
```

## How It Works

### Smart Dynamic Loading

Unlike traditional scrapers that use fixed delays, this scraper:

1. **Monitors Content Loading** - Actively counts skill elements as they appear
2. **Detects Stability** - Waits until no new skills load for several checks
3. **Intelligent Scrolling** - Only scrolls when new content is detected
4. **Adaptive Timing** - Moves quickly when content loads fast, waits longer when slow

This makes it more reliable with LinkedIn's variable page load times and throttling.

### HTML Structure

The scraper identifies skills by finding `<li>` elements with IDs containing `profilePagedListComponent` and extracting text from `<span aria-hidden="true">` elements.

## API Reference

### LinkedInSkillScraper Class

#### Constructor

```python
LinkedInSkillScraper(headless=False, debug=False)
```

**Parameters:**
- `headless` (bool): Run browser without GUI
- `debug` (bool): Enable debug logging

#### Methods

**`setup_driver()`**
- Sets up Chrome WebDriver

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

## Configuration

### Using Environment Variables

For security, use environment variables instead of hardcoding credentials:

```python
import os
from linkedin_skill_scraper import LinkedInSkillScraper

email = os.getenv('LINKEDIN_EMAIL')
password = os.getenv('LINKEDIN_PASSWORD')

scraper = LinkedInSkillScraper()
scraper.setup_driver()
scraper.login(email, password)
```

Set variables:
```bash
export LINKEDIN_EMAIL="your_email@example.com"
export LINKEDIN_PASSWORD="your_password"
```

## Requirements

- Python 3.7+
- Chrome browser
- LinkedIn account

See `requirements.txt` for Python dependencies.

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
- Consider using the HTML parsing method for personal/educational use

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
- LinkedIn may require 2FA or CAPTCHA (run in non-headless mode to complete)
- Try logging in manually in the browser first

### Skills load slowly or incompletely
- The dynamic waiting should handle this automatically
- If issues persist, check your internet connection
- LinkedIn may be throttling - add longer delays

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. The authors are not responsible for misuse or any violations of LinkedIn's Terms of Service. Use at your own risk and always respect LinkedIn's policies and user privacy.

## Changelog

### v1.0.0 (2025-10-07)
- Initial release
- Dynamic content loading detection
- CLI and programmatic interfaces
- Proper logging
- Batch scraping support
- HTML parsing mode
