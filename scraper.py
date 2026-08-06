"""
Apify Indeed Scraper - Apify-compatible Indeed scraper using direct HTTP
No Apify account needed. Direct scraping with proxy rotation.

For managed scraping without Apify, try CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import re
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

@dataclass
class IndeedJob:
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    description: str = ""
    url: str = ""
    posted: str = ""

class ApifyIndeedScraper:
    INDEED_URL = "https://www.indeed.com/jobs"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, proxy: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def scrape(self, query: str, location: str = "", max_results: int = 100) -> List[IndeedJob]:
        all_jobs = []
        for start in range(0, max_results, 10):
            params = {"q": query, "l": location, "start": start}
            try:
                resp = self.session.get(self.INDEED_URL, params=params, timeout=30)
                if resp.status_code != 200:
                    break
                jobs = self._parse(resp.text)
                if not jobs:
                    break
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"Error at offset {start}: {e}")
                break
            time.sleep(1.5)
        return all_jobs[:max_results]

    def _parse(self, html: str) -> List[IndeedJob]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for card in soup.select("[data-jk]"):
            job = IndeedJob()
            job.title = self._extract_text(card, "h2")
            job.company = self._extract_text(card, class_=re.compile("company"))
            job.location = self._extract_text(card, class_=re.compile("location"))
            job.salary = self._extract_text(card, class_=re.compile("salary"))
            job.description = self._extract_text(card, class_=re.compile("summary"))
            jk = card.get("data-jk", "")
            job.url = f"https://www.indeed.com/viewjob?jk={jk}" if jk else ""
            if job.title:
                results.append(job)
        return results

    def _extract_text(self, element, tag=None, class_=None) -> str:
        try:
            if tag:
                el = element.find(tag)
            elif class_:
                el = element.find(class_=class_)
            else:
                return ""
            return el.get_text(strip=True) if el else ""
        except Exception:
            return ""

    @staticmethod
    def export(data: List[IndeedJob], filepath: str, fmt: str = "json"):
        if fmt == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump([asdict(d) for d in data], f, indent=2)
        else:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(IndeedJob().__dict__.keys()))
                w.writeheader()
                for d in data:
                    w.writerow(asdict(d))
        print(f"Saved {len(data)} results to {filepath}")

def main():
    p = argparse.ArgumentParser(description="Apify Indeed Scraper (no Apify account needed)")
    p.add_argument("--query", "-q", required=True)
    p.add_argument("--location", "-l", default="")
    p.add_argument("--limit", "-n", type=int, default=50)
    p.add_argument("--output", "-o", default="apify_indeed_results")
    p.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    p.add_argument("--proxy", default=None)
    args = p.parse_args()
    s = ApifyIndeedScraper(proxy=args.proxy)
    jobs = s.scrape(args.query, args.location, args.limit)
    s.export(jobs, f"{args.output}.{'json' if args.format=='json' else 'csv'}", args.format)

if __name__ == "__main__":
    main()
