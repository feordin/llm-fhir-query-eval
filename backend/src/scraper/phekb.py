"""PheKB phenotype scraper

Two-stage scraper:
1. Stage 1: Collect all phenotype URLs (with pagination)
2. Stage 2: Download details and files for each phenotype

Uses Selenium to handle JavaScript-rendered content.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


@dataclass
class Phenotype:
    """PheKB phenotype metadata"""
    id: str
    name: str
    url: str
    description: Optional[str] = None
    category: Optional[str] = None
    files_downloaded: Optional[List[str]] = None


class PheKBScraper:
    """Two-stage scraper for PheKB phenotype definitions

    Stage 1: Collect all phenotype URLs (list_all_phenotypes)
    Stage 2: Download details for each phenotype (download_phenotype_details)
    """

    BASE_URL = "https://phekb.org"
    PHENOTYPES_URL = f"{BASE_URL}/phenotypes"

    def __init__(
        self,
        delay: float = 2.0,
        headless: bool = True,
        data_dir: str = "data/phekb-raw"
    ):
        """Initialize scraper

        Args:
            delay: Delay between requests in seconds (be respectful)
            headless: Run browser in headless mode
            data_dir: Directory to store downloaded data
        """
        self.delay = delay
        self.headless = headless
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "FHIR-Query-Eval-Bot/0.1.0 (Research Project)"
        })

    def _get_driver(self):
        """Create a Selenium WebDriver instance"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--user-agent=FHIR-Query-Eval-Bot/0.1.0 (Research Project)")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            logger.info("Make sure Chrome/Chromium is installed")
            raise

    # ==================== STAGE 1: List Phenotypes ====================

    def list_all_phenotypes(self, save: bool = True) -> List[Phenotype]:
        """List ALL public phenotypes from PheKB (handles pagination)

        Args:
            save: Save the list to phenotypes.json

        Returns:
            List of phenotype metadata
        """
        logger.info(f"Fetching phenotypes from {self.PHENOTYPES_URL}")
        logger.info("Handling pagination to get all phenotypes...")

        driver = None
        all_phenotypes = []
        seen_urls = set()

        try:
            driver = self._get_driver()
            driver.get(self.PHENOTYPES_URL)

            # Wait for Angular app to load and render
            logger.info("Waiting for Angular app to load...")
            logger.info(f"Page title: {driver.title}")
            logger.info(f"Page URL: {driver.current_url}")

            # Wait for Angular app-root to be populated
            # The page has <app-root></app-root> that Angular fills with content
            try:
                wait = WebDriverWait(driver, 30)

                # Wait for app-root to have child elements (Angular has rendered)
                logger.info("Waiting for app-root to be populated...")
                wait.until(lambda d: len(d.find_element(By.TAG_NAME, "app-root").find_elements(By.XPATH, ".//*")) > 0)
                logger.info("Angular app has rendered content")

                # Additional wait for phenotype links specifically
                # Try to wait for links containing '/phenotype/' or '/node/'
                logger.info("Waiting for phenotype links to appear...")
                time.sleep(5)  # Give Angular time to fully render the table

            except TimeoutException:
                logger.warning("Timeout waiting for Angular app to render")

            # Save page source for debugging if no phenotypes found
            debug_html = self.data_dir / "debug_page_source.html"
            with open(debug_html, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info(f"Saved page source to: {debug_html}")

            # Try to save screenshot
            try:
                screenshot_path = self.data_dir / "debug_screenshot.png"
                driver.save_screenshot(str(screenshot_path))
                logger.info(f"Saved screenshot to: {screenshot_path}")
            except:
                pass

            page_num = 1
            while True:
                logger.info(f"Processing page {page_num}...")

                # Get phenotypes on current page
                phenotypes = self._extract_phenotypes_from_page(driver, seen_urls)
                all_phenotypes.extend(phenotypes)
                logger.info(f"Found {len(phenotypes)} new phenotypes on page {page_num} (total: {len(all_phenotypes)})")

                # Check if we got no phenotypes (might indicate an issue)
                if not phenotypes and page_num == 1:
                    logger.warning("No phenotypes found on first page - check selectors")
                    break

                # Try to find and click "Next" button
                if not self._click_next_page(driver):
                    logger.info("No more pages to load")
                    break

                # Wait for next page to load (longer wait for Angular to re-render)
                logger.debug("Waiting for next page to load...")
                time.sleep(3)  # Increased wait time for Angular DataTable
                
                # Wait for table to update (check if content changed)
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table a, tbody a")) > 0
                    )
                except TimeoutException:
                    logger.warning("Timeout waiting for next page content")
                
                page_num += 1
                
                # Safety limit to prevent infinite loops
                if page_num > 10:
                    logger.warning("Reached page limit of 10, stopping")
                    break

            logger.info(f"Finished! Found {len(all_phenotypes)} total phenotypes")

            if save:
                self.save_phenotype_list(all_phenotypes)

            return all_phenotypes

        except Exception as e:
            logger.error(f"Failed to fetch phenotypes: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def _extract_phenotypes_from_page(self, driver, seen_urls: set) -> List[Phenotype]:
        """Extract phenotype links from current page (Angular-rendered content)
        
        PheKB uses PrimeNG DataTable. Each row has a title link in the first column.
        """
        phenotypes = []

        # First, log what we're seeing
        try:
            app_root = driver.find_element(By.TAG_NAME, "app-root")
            app_root_html = app_root.get_attribute("innerHTML")
            if len(app_root_html) < 100:
                logger.warning(f"app-root appears empty (only {len(app_root_html)} chars)")
        except NoSuchElementException:
            logger.warning("No app-root element found")

        # For PrimeNG table, the phenotype title links are in the first TD of each row
        # Pattern: <tr><td><a href="/phenotype/xxx">Title</a></td>...
        try:
            # Most specific: First TD in each table row (excludes other columns)
            rows = driver.find_elements(By.CSS_SELECTOR, "tbody.p-datatable-tbody tr")
            logger.info(f"Found {len(rows)} table rows")
            
            for row in rows:
                try:
                    # Get first TD which contains the phenotype title link
                    first_td = row.find_element(By.CSS_SELECTOR, "td:first-child")
                    link = first_td.find_element(By.TAG_NAME, "a")
                    
                    href = link.get_attribute("href")
                    if not href or href in seen_urls:
                        continue
                    
                    # Must be a phenotype URL
                    if "/phenotype/" not in href:
                        continue
                    
                    seen_urls.add(href)
                    
                    # Extract ID from URL
                    phenotype_id = href.rstrip("/").split("/")[-1]
                    phenotype_name = link.text.strip() or phenotype_id
                    
                    phenotypes.append(Phenotype(
                        id=phenotype_id,
                        name=phenotype_name,
                        url=href
                    ))
                    logger.debug(f"  Found: {phenotype_name} -> {href}")
                    
                except Exception as e:
                    logger.debug(f"Error processing row: {e}")
                    continue
                    
            if phenotypes:
                return phenotypes
                
        except Exception as e:
            logger.warning(f"Could not extract from table rows: {e}")

        # Fallback: Original logic
        logger.info("Using fallback extraction method")
        
        # Get ALL links for debugging
        all_links = driver.find_elements(By.TAG_NAME, "a")
        logger.info(f"Total links on page: {len(all_links)}")

        # Filter for phenotype URLs
        phenotype_links = [link for link in all_links
                          if link.get_attribute("href") and
                          "/phenotype/" in link.get_attribute("href")]

        logger.info(f"Found {len(phenotype_links)} phenotype links in page")

        for link in phenotype_links:
            try:
                href = link.get_attribute("href")
                if not href or href in seen_urls:
                    continue

                seen_urls.add(href)

                # Extract ID from URL
                phenotype_id = href.rstrip("/").split("/")[-1]
                phenotype_name = link.text.strip() or phenotype_id

                phenotypes.append(Phenotype(
                    id=phenotype_id,
                    name=phenotype_name,
                    url=href
                ))
            except Exception as e:
                logger.debug(f"Error processing link: {e}")
                continue

        return phenotypes

    def _click_next_page(self, driver) -> bool:
        """Try to click the next page button. Returns True if successful."""
        # PrimeNG p-paginator selectors (used by PheKB)
        next_selectors = [
            # PrimeNG next button (not disabled)
            "button.p-paginator-next:not(.p-disabled)",
            ".p-paginator-next:not(.p-disabled)",
            # Try parent container
            "p-paginator button.p-paginator-next:not(.p-disabled)",
        ]

        for selector in next_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                
                # Double-check it's not disabled
                classes = element.get_attribute("class") or ""
                disabled_attr = element.get_attribute("disabled")
                
                if "p-disabled" in classes or disabled_attr:
                    logger.debug(f"Next button is disabled - no more pages")
                    return False
                    
                if element.is_displayed():
                    # Scroll into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    time.sleep(0.5)
                    # Use JavaScript click for reliability with Angular
                    driver.execute_script("arguments[0].click();", element)
                    logger.debug(f"Clicked Next with selector: {selector}")
                    return True
            except (NoSuchElementException, Exception) as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        # Fallback: Find all paginator buttons and look for next
        try:
            paginator = driver.find_element(By.CSS_SELECTOR, "p-paginator, .p-paginator")
            buttons = paginator.find_elements(By.TAG_NAME, "button")
            
            for btn in buttons:
                classes = btn.get_attribute("class") or ""
                disabled = btn.get_attribute("disabled")
                
                # Look for next button (has right arrow icon or is labeled next)
                if "p-paginator-next" in classes:
                    if "p-disabled" in classes or disabled:
                        logger.debug("Next button is disabled - no more pages")
                        return False
                    
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    logger.debug("Clicked Next button via fallback")
                    return True
        except Exception as e:
            logger.debug(f"Error in fallback next button search: {e}")

        logger.debug("Could not find Next button")
        return False

    def save_phenotype_list(self, phenotypes: List[Phenotype]) -> None:
        """Save phenotype list to JSON file"""
        output_file = self.data_dir / "phenotypes.json"

        data = {
            "total_count": len(phenotypes),
            "phenotypes": [asdict(p) for p in phenotypes]
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(phenotypes)} phenotypes to {output_file}")

    def load_phenotype_list(self) -> List[Phenotype]:
        """Load phenotype list from JSON file"""
        list_file = self.data_dir / "phenotypes.json"

        if not list_file.exists():
            raise FileNotFoundError(f"Phenotype list not found: {list_file}")

        with open(list_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        phenotypes = [Phenotype(**p) for p in data["phenotypes"]]
        logger.info(f"Loaded {len(phenotypes)} phenotypes from {list_file}")
        return phenotypes

    # ==================== STAGE 2: Download Details ====================

    def download_phenotype_details(self, phenotype: Phenotype) -> Dict:
        """Download detailed information for a single phenotype

        Args:
            phenotype: Phenotype metadata with URL

        Returns:
            Dictionary with phenotype details and file paths
        """
        logger.info(f"Downloading details for: {phenotype.name}")

        # Create phenotype directory
        phenotype_dir = self.data_dir / phenotype.id
        phenotype_dir.mkdir(parents=True, exist_ok=True)

        # Respect rate limiting
        time.sleep(self.delay)

        driver = None
        try:
            driver = self._get_driver()
            driver.get(phenotype.url)
            time.sleep(2)

            # Extract description
            description = self._extract_description(driver)

            # Save description to separate text file
            description_file = phenotype_dir / "description.txt"
            with open(description_file, "w", encoding="utf-8") as f:
                f.write(f"Phenotype: {phenotype.name}\n")
                f.write(f"URL: {phenotype.url}\n")
                f.write("=" * 80 + "\n\n")
                f.write(description)
            logger.info(f"Saved description to {description_file}")

            # Find and download files
            downloaded_files = self._download_files(driver, phenotype_dir)

            # Save metadata
            details = {
                "id": phenotype.id,
                "name": phenotype.name,
                "url": phenotype.url,
                "description": description,
                "downloaded_files": downloaded_files,
                "phenotype_dir": str(phenotype_dir)
            }

            # Save details JSON
            details_file = phenotype_dir / "details.json"
            with open(details_file, "w", encoding="utf-8") as f:
                json.dump(details, f, indent=2)

            logger.info(f"Saved details to {details_file}")
            logger.info(f"Downloaded {len(downloaded_files)} files")

            return details

        except Exception as e:
            logger.error(f"Failed to download details for {phenotype.id}: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def _extract_description(self, driver) -> str:
        """Extract phenotype description from page
        
        Tries multiple strategies to find the summary/description text:
        1. Angular-rendered content areas
        2. Standard Drupal content fields
        3. Main content paragraphs
        """
        # Wait a bit more for Angular content to load
        time.sleep(1)
        
        # Try Angular-specific selectors first
        angular_selectors = [
            "app-root .description",
            "app-root .summary",
            "app-root .phenotype-description",
            "app-root article p",
            "app-root .content p"
        ]
        
        for selector in angular_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    # Combine first few paragraphs
                    paragraphs = [el.text.strip() for el in elements[:5] if el.text.strip() and len(el.text.strip()) > 30]
                    if paragraphs:
                        description = "\n\n".join(paragraphs)
                        logger.debug(f"Found description with Angular selector: {selector}")
                        return description
            except:
                continue
        
        # Try standard Drupal/HTML selectors
        drupal_selectors = [
            ".field-name-body",
            ".field-type-text-with-summary",
            "article .content",
            ".node-content .field-item",
            "#description",
            ".phenotype-body"
        ]

        for selector in drupal_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                description = element.text.strip()
                if description and len(description) > 50:
                    logger.debug(f"Found description with Drupal selector: {selector}")
                    return description
            except:
                continue

        # Fallback 1: Try to find any substantial paragraphs in main/article
        try:
            content_areas = driver.find_elements(By.CSS_SELECTOR, "main, article, app-root")
            for area in content_areas:
                paragraphs = area.find_elements(By.TAG_NAME, "p")
                # Filter for substantial paragraphs (>30 chars)
                good_paragraphs = [p.text.strip() for p in paragraphs if p.text.strip() and len(p.text.strip()) > 30]
                if len(good_paragraphs) >= 2:
                    # Take first few paragraphs
                    description = "\n\n".join(good_paragraphs[:5])
                    logger.debug("Found description from main content paragraphs")
                    return description
        except:
            pass
        
        # Fallback 2: Get visible text from main content area
        try:
            for selector in ["main", "article", "app-root"]:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if text and len(text) > 100:
                        # Truncate if too long
                        if len(text) > 2000:
                            text = text[:2000] + "..."
                        logger.debug(f"Found description from {selector} text content")
                        return text
                except:
                    continue
        except:
            pass

        logger.warning("Could not extract description - no suitable content found")
        return "No description found"

    def _download_files(self, driver, phenotype_dir: Path) -> List[str]:
        """Find and download PDF and Word documents (skip Excel)
        
        Returns list of downloaded filenames with metadata
        """
        downloaded_files = []
        seen_urls = set()

        # Find all file links
        try:
            file_links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            logger.info(f"Scanning {len(file_links)} links for downloadable files...")

            for link in file_links:
                try:
                    href = link.get_attribute("href")
                    if not href or href in seen_urls:
                        continue

                    # Only download PDFs and Word docs
                    if not any(ext in href.lower() for ext in [".pdf", ".doc", ".docx"]):
                        continue

                    # Skip Excel files
                    if any(ext in href.lower() for ext in [".xls", ".xlsx", ".csv"]):
                        logger.debug(f"Skipping Excel file: {href}")
                        continue

                    seen_urls.add(href)
                    
                    # Get link text for better logging
                    link_text = link.text.strip() or "Unnamed file"
                    logger.info(f"Downloading: {link_text} ({href})")

                    # Download the file
                    filename = self._download_file(href, phenotype_dir)
                    if filename:
                        downloaded_files.append({
                            "filename": filename,
                            "url": href,
                            "link_text": link_text
                        })
                        logger.info(f"  ✓ Saved as: {filename}")

                except Exception as e:
                    logger.debug(f"Error downloading file: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error finding files: {e}")

        logger.info(f"Successfully downloaded {len(downloaded_files)} files")
        return downloaded_files

    def _download_file(self, url: str, output_dir: Path) -> Optional[str]:
        """Download a single file
        
        Args:
            url: File URL (can be relative or absolute)
            output_dir: Directory to save the file
            
        Returns:
            Filename if successful, None otherwise
        """
        try:
            # Make URL absolute
            if not url.startswith("http"):
                url = self.BASE_URL + url

            # Respect rate limiting
            time.sleep(self.delay)

            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            # Get filename from URL or Content-Disposition header
            filename = None
            if "Content-Disposition" in response.headers:
                content_disp = response.headers["Content-Disposition"]
                if "filename=" in content_disp:
                    filename = content_disp.split("filename=")[-1].strip('"\'')
            
            if not filename:
                filename = url.split("/")[-1].split("?")[0]
            
            if not filename or filename == "download":
                filename = "document"

            # Ensure proper extension based on Content-Type
            if not any(filename.endswith(ext) for ext in [".pdf", ".doc", ".docx"]):
                content_type = response.headers.get("Content-Type", "").lower()
                if "pdf" in content_type:
                    filename += ".pdf"
                elif "word" in content_type or "msword" in content_type:
                    filename += ".docx"
                elif "document" in content_type:
                    filename += ".docx"

            # Clean filename (remove invalid characters)
            filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            filename = filename.strip()

            output_path = output_dir / filename
            
            # Avoid overwriting - add number if file exists
            counter = 1
            while output_path.exists():
                name, ext = os.path.splitext(filename)
                output_path = output_dir / f"{name}_{counter}{ext}"
                counter += 1

            with open(output_path, "wb") as f:
                f.write(response.content)

            # Log file size
            file_size = len(response.content)
            size_str = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
            logger.debug(f"Downloaded {size_str}: {filename}")

            return output_path.name

        except Exception as e:
            logger.error(f"Failed to download file from {url}: {e}")
            return None

    def download_all_phenotype_details(self, phenotypes: Optional[List[Phenotype]] = None) -> List[Dict]:
        """Download details for all phenotypes

        Args:
            phenotypes: List of phenotypes (if None, loads from saved list)

        Returns:
            List of detail dictionaries
        """
        if phenotypes is None:
            phenotypes = self.load_phenotype_list()

        results = []
        for i, phenotype in enumerate(phenotypes, 1):
            logger.info(f"Processing {i}/{len(phenotypes)}: {phenotype.name}")

            try:
                details = self.download_phenotype_details(phenotype)
                results.append(details)
            except Exception as e:
                logger.error(f"Failed to download {phenotype.id}: {e}")
                continue

        logger.info(f"Successfully downloaded details for {len(results)}/{len(phenotypes)} phenotypes")
        return results
