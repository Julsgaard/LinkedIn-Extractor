# LinkedIn Extractor

A Python tool to extract skills from LinkedIn profile pages using smart dynamic content detection.

## Installation

```bash
pip install linkedin-extractor
```

## Quick Start

```python
from linkedin_extractor import LinkedInExtractor

scraper = LinkedInExtractor(headless=True)
try:
    scraper.setup_driver()
    scraper.login("your_email@example.com", "your_password")
    skills = scraper.scrape_skills("profile-username")
    print(f"Found {len(skills)} skills:", skills)
finally:
    scraper.close()
```

## Documentation

For full documentation, examples, and API reference, visit:

**https://github.com/Julsgaard/LinkedIn-Extractor**

## Features

- Smart dynamic content loading detection
- CLI and programmatic API
- Automated browser control with Selenium
- Anti-detection measures
- Debug and logging support

## Requirements

- Python 3.8+
- Chrome browser
- LinkedIn account

## License

MIT License

