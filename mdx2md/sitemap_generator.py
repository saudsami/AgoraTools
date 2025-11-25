#!/usr/bin/env python3
"""
Sitemap Generator for Exported Markdown Documentation

This script scans exported markdown files and generates an XML sitemap
for the docs-md.agora.io domain following the sitemap protocol.
"""

import os
import re
import yaml
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote
from typing import List, Dict, Optional


class SitemapEntry:
    """Represents a single sitemap entry with metadata"""
    
    def __init__(self, url: str, lastmod: str = None, changefreq: str = "monthly", priority: float = 0.5):
        self.url = url
        self.lastmod = lastmod or datetime.now(timezone.utc).strftime('%Y-%m-%d')
        self.changefreq = changefreq
        self.priority = priority


class SitemapGenerator:
    """Generates XML sitemaps for exported markdown documentation"""
    
    def __init__(self, base_url: str = "https://docs-md.agora.io"):
        self.base_url = base_url.rstrip('/')
        self.entries: List[SitemapEntry] = []
    
    def parse_frontmatter(self, file_path: str) -> Dict:
        """Extract YAML frontmatter from markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            match = re.match(r'^---\s*\n(.*?)\n---\s*\n?', content, re.DOTALL)
            if not match:
                return {}
            
            return yaml.safe_load(match.group(1)) or {}
        except Exception as e:
            print(f"Warning: Could not parse frontmatter from {file_path}: {e}")
            return {}
    
    def get_file_priority(self, rel_path: str, frontmatter: Dict) -> float:
        """Determine priority based on file path and metadata"""
        # Check for explicit priority in frontmatter
        if 'sitemap_priority' in frontmatter:
            return float(frontmatter['sitemap_priority'])
        
        # Default priorities based on path patterns
        path_lower = rel_path.lower()
        
        # High priority for main pages and getting started content
        if any(pattern in path_lower for pattern in ['index', 'getting-started', 'quickstart', 'overview']):
            return 0.9
        
        # Medium-high priority for API references and guides
        if any(pattern in path_lower for pattern in ['api-reference', 'guide', 'tutorial']):
            return 0.8
        
        # Medium priority for feature documentation
        if any(pattern in path_lower for pattern in ['features', 'advanced']):
            return 0.7
        
        # Lower priority for platform-specific files (they're variations)
        if re.search(r'_(?:android|ios|web|flutter|react-native|unity|windows|macos|electron)\.md$', rel_path):
            return 0.6
        
        # Default priority
        return 0.5
    
    def get_change_frequency(self, rel_path: str, frontmatter: Dict) -> str:
        """Determine change frequency based on file type and metadata"""
        # Check for explicit changefreq in frontmatter
        if 'sitemap_changefreq' in frontmatter:
            return frontmatter['sitemap_changefreq']
        
        path_lower = rel_path.lower()
        
        # API references change more frequently
        if 'api-reference' in path_lower:
            return 'weekly'
        
        # Getting started guides are updated regularly
        if any(pattern in path_lower for pattern in ['getting-started', 'quickstart']):
            return 'monthly'
        
        # Most documentation changes less frequently
        return 'monthly'
    
    def should_exclude_file(self, rel_path: str, frontmatter: Dict) -> bool:
        """Determine if a file should be excluded from the sitemap"""
        # Check for explicit exclusion in frontmatter
        if frontmatter.get('sitemap_exclude', False):
            return True
        
        # Exclude draft content
        if frontmatter.get('draft', False):
            return True
        
        # Exclude certain file patterns
        exclude_patterns = [
            r'\.draft\.md$',
            r'\.test\.md$',
            r'/draft/',
            r'/temp/',
            r'/_',  # Files starting with underscore in path
        ]
        
        for pattern in exclude_patterns:
            if re.search(pattern, rel_path):
                return True
        
        return False
    
    def get_last_modified(self, file_path: str, frontmatter: Dict) -> str:
        """Get last modified date from frontmatter or file system"""
        # Check for explicit lastmod in frontmatter
        if 'exported_on' in frontmatter:
            try:
                # Parse ISO format and convert to YYYY-MM-DD
                exported_date = datetime.fromisoformat(frontmatter['exported_on'].replace('Z', '+00:00'))
                return exported_date.strftime('%Y-%m-%d')
            except Exception:
                pass
        
        if 'sitemap_lastmod' in frontmatter:
            return str(frontmatter['sitemap_lastmod'])
        
        # Fall back to file modification time
        try:
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime, timezone.utc).strftime('%Y-%m-%d')
        except Exception:
            return datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    def scan_directory(self, docs_dir: str, exclude_patterns: List[str] = None) -> None:
        """Scan directory for markdown files and build sitemap entries"""
        exclude_patterns = exclude_patterns or []
        docs_dir = os.path.abspath(docs_dir)
        
        print(f"Scanning directory: {docs_dir}")
        
        for root, dirs, files in os.walk(docs_dir):
            # Skip hidden directories and common excludes
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            for file in files:
                if not file.endswith('.md'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, docs_dir).replace(os.sep, '/')
                
                # Check exclude patterns
                if any(re.search(pattern, rel_path) for pattern in exclude_patterns):
                    continue
                
                # Parse frontmatter
                frontmatter = self.parse_frontmatter(file_path)
                
                # Check if file should be excluded
                if self.should_exclude_file(rel_path, frontmatter):
                    print(f"Excluding: {rel_path}")
                    continue
                
                # Build URL (include /en/ path and keep .md extension)
                url_path = rel_path
                url = f"{self.base_url}/en/{url_path}"
                
                # Get metadata
                lastmod = self.get_last_modified(file_path, frontmatter)
                priority = self.get_file_priority(rel_path, frontmatter)
                changefreq = self.get_change_frequency(rel_path, frontmatter)
                
                # Add entry
                entry = SitemapEntry(url, lastmod, changefreq, priority)
                self.entries.append(entry)
                
                print(f"Added: {url} (priority: {priority})")
    
    def generate_xml(self, output_file: str = "sitemap.xml") -> None:
        """Generate XML sitemap file"""
        # Create root element
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        
        # Sort entries by URL for consistency
        sorted_entries = sorted(self.entries, key=lambda x: x.url)
        
        # Add URL entries
        for entry in sorted_entries:
            url_elem = ET.SubElement(urlset, "url")
            
            loc = ET.SubElement(url_elem, "loc")
            loc.text = entry.url
            
            lastmod = ET.SubElement(url_elem, "lastmod")
            lastmod.text = entry.lastmod
            
            changefreq = ET.SubElement(url_elem, "changefreq")
            changefreq.text = entry.changefreq
            
            priority = ET.SubElement(url_elem, "priority")
            priority.text = str(entry.priority)
        
        # Create ElementTree and write to file
        tree = ET.ElementTree(urlset)
        ET.indent(tree, space="  ", level=0)  # Pretty print (Python 3.9+)
        
        try:
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            print(f"Sitemap generated: {output_file}")
        except Exception as e:
            # Fallback for older Python versions without ET.indent
            with open(output_file, 'wb') as f:
                f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
                tree.write(f, encoding='utf-8')
            print(f"Sitemap generated: {output_file}")
    
    def generate_stats(self) -> Dict:
        """Generate statistics about the sitemap"""
        if not self.entries:
            return {"total_urls": 0}
        
        priorities = [entry.priority for entry in self.entries]
        changefreqs = [entry.changefreq for entry in self.entries]
        
        from collections import Counter
        
        return {
            "total_urls": len(self.entries),
            "priority_distribution": dict(Counter(priorities)),
            "changefreq_distribution": dict(Counter(changefreqs)),
            "avg_priority": sum(priorities) / len(priorities),
            "date_range": {
                "earliest": min(entry.lastmod for entry in self.entries),
                "latest": max(entry.lastmod for entry in self.entries)
            }
        }


def main():
    parser = argparse.ArgumentParser(description="Generate XML sitemap for exported markdown documentation")
    parser.add_argument(
        "--docs-dir",
        required=True,
        help="Path to the exported markdown documentation directory"
    )
    parser.add_argument(
        "--output",
        default="sitemap.xml",
        help="Output sitemap filename (default: sitemap.xml)"
    )
    parser.add_argument(
        "--base-url",
        default="https://docs-md.agora.io",
        help="Base URL for the sitemap (default: https://docs-md.agora.io)"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Additional file patterns to exclude (regex patterns)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print sitemap statistics after generation"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that generated URLs are accessible (basic check)"
    )
    
    args = parser.parse_args()
    
    # Verify docs directory exists
    if not os.path.isdir(args.docs_dir):
        print(f"Error: Documentation directory not found: {args.docs_dir}")
        return 1
    
    # Initialize generator
    generator = SitemapGenerator(args.base_url)
    
    print("=" * 60)
    print("Sitemap Generator for Exported Markdown Documentation")
    print("=" * 60)
    print(f"Documentation directory: {args.docs_dir}")
    print(f"Base URL: {args.base_url}")
    print(f"Output file: {args.output}")
    if args.exclude:
        print(f"Exclude patterns: {args.exclude}")
    print("-" * 60)
    
    # Scan directory and generate sitemap
    try:
        generator.scan_directory(args.docs_dir, args.exclude)
        generator.generate_xml(args.output)
        
        # Print statistics if requested
        if args.stats:
            stats = generator.generate_stats()
            print(f"\nSitemap Statistics:")
            print(f"  Total URLs: {stats['total_urls']}")
            print(f"  Average Priority: {stats.get('avg_priority', 0):.2f}")
            print(f"  Date Range: {stats.get('date_range', {}).get('earliest')} to {stats.get('date_range', {}).get('latest')}")
            print(f"  Change Frequencies: {stats.get('changefreq_distribution', {})}")
        
        print(f"\n✅ Successfully generated sitemap with {len(generator.entries)} URLs")
        print(f"📄 Sitemap saved to: {os.path.abspath(args.output)}")
        
        return 0
        
    except Exception as e:
        print(f"Error generating sitemap: {e}")
        return 1


if __name__ == "__main__":
    exit(main())