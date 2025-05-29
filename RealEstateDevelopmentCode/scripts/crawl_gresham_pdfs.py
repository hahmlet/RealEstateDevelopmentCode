#!/usr/bin/env python3
"""
Gresham PDF Crawler - Downloads PDFs from https://greshamoregon.gov/Development-Code/
Based on crawler log evidence from May 21, 2025
"""

import os
import sys
import requests
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
import time
from datetime import datetime
import json

# Setup logging
def setup_logging():
    """Setup logging to match the archive log format"""
    log_dir = Path("/workspace/RealEstateDevelopmentCode/archive/logs/crawler")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "gresham.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

class GreshamPDFCrawler:
    def __init__(self, base_url="https://greshamoregon.gov/Development-Code/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Municipal Document Crawler/1.1)'
        })
        self.logger = setup_logging()
        
        # Setup download directory
        self.download_dir = Path("/workspace/RealEstateDevelopmentCode/production_pdfs/Oregon/gresham")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        self.downloaded_count = 0
        self.errors = []
        
    def is_pdf_url(self, url):
        """Check if URL points to a PDF file"""
        return url.lower().endswith('.pdf') or 'pdf' in url.lower()
    
    def sanitize_filename(self, filename):
        """Sanitize filename for filesystem"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Ensure it ends with .pdf
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
            
        return filename
    
    def download_pdf(self, pdf_url, filename=None):
        """Download a single PDF file"""
        try:
            if not filename:
                filename = os.path.basename(urlparse(pdf_url).path)
                if not filename or not filename.endswith('.pdf'):
                    filename = f"document_{self.downloaded_count + 1}.pdf"
            
            filename = self.sanitize_filename(filename)
            filepath = self.download_dir / filename
            
            # Skip if already exists
            if filepath.exists():
                self.logger.info(f"Skipping existing file: {filename}")
                return True
            
            self.logger.info(f"Downloading: {pdf_url} -> {filename}")
            
            response = self.session.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Verify it's actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
                self.logger.warning(f"URL may not be PDF: {pdf_url} (content-type: {content_type})")
            
            # Write file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = filepath.stat().st_size
            self.logger.info(f"Downloaded {filename} ({file_size:,} bytes)")
            self.downloaded_count += 1
            
            return True
            
        except Exception as e:
            error_msg = f"Error downloading {pdf_url}: {str(e)}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def crawl_page(self, url, max_depth=2, current_depth=0):
        """Crawl a page looking for PDF links"""
        if current_depth > max_depth:
            return []
        
        pdf_urls = []
        
        try:
            self.logger.info(f"Crawling page (depth {current_depth}): {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                full_url = urljoin(url, href)
                
                # Check if it's a PDF
                if self.is_pdf_url(full_url):
                    pdf_urls.append(full_url)
                    self.logger.info(f"Found PDF: {full_url}")
                
                # If not max depth, crawl sub-pages that might contain PDFs
                elif (current_depth < max_depth and 
                      full_url.startswith(self.base_url) and 
                      full_url not in pdf_urls and
                      not any(ext in full_url.lower() for ext in ['.jpg', '.png', '.gif', '.css', '.js'])):
                    
                    # Look for development code related pages
                    if any(keyword in href.lower() for keyword in ['development', 'code', 'zoning', 'planning', 'ordinance']):
                        sub_pdfs = self.crawl_page(full_url, max_depth, current_depth + 1)
                        pdf_urls.extend(sub_pdfs)
            
            # Also look for any direct PDF links in the page content
            pdf_pattern_links = soup.find_all('a', href=lambda x: x and '.pdf' in x.lower())
            for link in pdf_pattern_links:
                href = link['href']
                full_url = urljoin(url, href)
                if full_url not in pdf_urls:
                    pdf_urls.append(full_url)
                    self.logger.info(f"Found PDF (pattern): {full_url}")
            
        except Exception as e:
            error_msg = f"Error crawling {url}: {str(e)}"
            self.logger.error(error_msg)
            self.errors.append(error_msg)
        
        return pdf_urls
    
    def run_crawl(self):
        """Run the complete crawl process"""
        start_time = datetime.now()
        self.logger.info(f"Starting Gresham PDF crawl at {start_time}")
        self.logger.info(f"Base URL: {self.base_url}")
        self.logger.info(f"Download directory: {self.download_dir}")
        
        try:
            # Crawl for PDF URLs
            pdf_urls = self.crawl_page(self.base_url)
            
            # Remove duplicates while preserving order
            unique_pdfs = []
            seen = set()
            for url in pdf_urls:
                if url not in seen:
                    unique_pdfs.append(url)
                    seen.add(url)
            
            self.logger.info(f"Found {len(unique_pdfs)} unique PDF URLs")
            
            # Download all PDFs
            for pdf_url in unique_pdfs:
                self.download_pdf(pdf_url)
                time.sleep(1)  # Be respectful to the server
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Summary
            self.logger.info(f"Crawl completed in {duration}")
            self.logger.info(f"Downloaded: {self.downloaded_count} PDFs")
            self.logger.info(f"Errors: {len(self.errors)}")
            
            if self.errors:
                self.logger.error("Error summary:")
                for error in self.errors:
                    self.logger.error(f"  - {error}")
            
            # Save summary
            summary = {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'base_url': self.base_url,
                'pdfs_found': len(unique_pdfs),
                'pdfs_downloaded': self.downloaded_count,
                'errors': self.errors,
                'download_directory': str(self.download_dir)
            }
            
            summary_file = self.download_dir / 'crawl_summary.json'
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Fatal error during crawl: {str(e)}")
            raise

def main():
    """Main entry point"""
    crawler = GreshamPDFCrawler()
    
    try:
        summary = crawler.run_crawl()
        print(f"\nCrawl Summary:")
        print(f"  PDFs Downloaded: {summary['pdfs_downloaded']}")
        print(f"  Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"  Download Dir: {summary['download_directory']}")
        
        if summary['errors']:
            print(f"  Errors: {len(summary['errors'])}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nCrawl interrupted by user")
        return 1
    except Exception as e:
        print(f"\nCrawl failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
