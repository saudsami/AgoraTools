#!/usr/bin/env python3
"""
Agora RTC Web API Reference HTML to Markdown Converter

This script converts the TypeDoc-generated HTML API reference to Markdown format
while preserving the folder structure and converting internal links.
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, Set, Tuple
import html2text
import argparse


class HTMLToMarkdownConverter:
    """Converts HTML API reference documentation to Markdown."""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.ignore_emphasis = False
        self.html2text.body_width = 0  # No wrapping
        self.html2text.single_line_break = False
        
        # Track all files for link conversion
        self.file_map: Dict[str, str] = {}  # maps HTML path to MD path
        
    def setup_output_directories(self):
        """Create output directory structure."""
        directories = ['classes', 'enums', 'interfaces']
        
        for directory in directories:
            output_path = self.output_dir / directory
            output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Created output directories in: {self.output_dir}")
    
    def scan_files(self):
        """Scan all HTML files and build file mapping."""
        print("Scanning HTML files...")
        
        # Scan root level
        for html_file in self.input_dir.glob('*.html'):
            relative_path = html_file.relative_to(self.input_dir)
            md_path = self.output_dir / relative_path.with_suffix('.md')
            self.file_map[str(relative_path)] = str(md_path.relative_to(self.output_dir))
        
        # Scan subdirectories
        for subdir in ['classes', 'enums', 'interfaces']:
            subdir_path = self.input_dir / subdir
            if subdir_path.exists():
                for html_file in subdir_path.glob('*.html'):
                    relative_path = html_file.relative_to(self.input_dir)
                    md_path = self.output_dir / relative_path.with_suffix('.md')
                    self.file_map[str(relative_path)] = str(md_path.relative_to(self.output_dir))
        
        print(f"Found {len(self.file_map)} HTML files to convert")
    
    def extract_content(self, soup: BeautifulSoup) -> Tuple[str, str, str]:
        """
        Extract relevant content from HTML.
        
        Returns:
            Tuple of (title, description, main_content)
        """
        # Extract title
        title = ""
        title_element = soup.find('h1')
        if title_element:
            title = title_element.get_text(strip=True)
        
        # Extract description (from first tsd-comment section)
        description = ""
        comment_section = soup.find('section', class_='tsd-panel tsd-comment')
        if comment_section:
            lead = comment_section.find('div', class_='lead')
            if lead:
                description = lead.get_text(strip=True)
        
        # Extract main content (col-9 col-content)
        main_content = ""
        content_div = soup.find('div', class_='col-9 col-content')
        if content_div:
            main_content = str(content_div)
        
        return title, description, main_content
    
    def convert_html_links_to_markdown(self, html_content: str, source_file: Path) -> str:
        """
        Convert HTML links to proper Markdown links.
        
        Args:
            html_content: HTML content string
            source_file: Path to the source HTML file (for relative path calculation)
            
        Returns:
            HTML content with converted links
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all anchor tags
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip external links and anchors
            if href.startswith('http://') or href.startswith('https://') or href.startswith('#'):
                continue
            
            # Skip special links
            if href.startswith('/') or href in ['', '#']:
                continue
            
            # Convert .html to .md
            if '.html' in href:
                # Split href into file and anchor parts
                if '#' in href:
                    file_part, anchor_part = href.split('#', 1)
                    new_href = file_part.replace('.html', '.md') + '#' + anchor_part
                else:
                    new_href = href.replace('.html', '.md')
                
                link['href'] = new_href
        
        return str(soup)
    
    def clean_markdown_content(self, markdown: str) -> str:
        """Clean up markdown content to improve readability."""
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Clean up navigation and breadcrumbs (remove them)
        lines = markdown.split('\n')
        cleaned_lines = []
        skip_next = False
        
        for line in lines:
            # Skip navigation elements
            if any(x in line for x in ['Globals', 'tsd-navigation', 'tsd-breadcrumb', '##  Globals']):
                continue
            
            # Skip empty headers
            if re.match(r'^#{1,6}\s*$', line):
                continue
            
            cleaned_lines.append(line)
        
        markdown = '\n'.join(cleaned_lines)
        
        # Fix multiple spaces
        markdown = re.sub(r' {2,}', ' ', markdown)
        
        return markdown.strip()
    
    def add_frontmatter(self, title: str, description: str) -> str:
        """Add YAML frontmatter to markdown file."""
        frontmatter = f"""---
title: {title}
description: {description if description else title}
---

"""
        return frontmatter
    
    def convert_file(self, html_file: Path, output_file: Path):
        """Convert a single HTML file to Markdown."""
        print(f"Converting: {html_file.name}")
        
        try:
            # Read HTML file
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract content
            title, description, main_content = self.extract_content(soup)
            
            # Convert HTML links to markdown-compatible links
            main_content = self.convert_html_links_to_markdown(main_content, html_file)
            
            # Convert to markdown
            markdown_content = self.html2text.handle(main_content)
            
            # Clean up markdown
            markdown_content = self.clean_markdown_content(markdown_content)
            
            # Add frontmatter
            final_content = self.add_frontmatter(title, description) + markdown_content
            
            # Write output
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            return True
            
        except Exception as e:
            print(f"Error converting {html_file.name}: {str(e)}")
            return False
    
    def convert_all(self):
        """Convert all HTML files to Markdown."""
        print("\n" + "="*60)
        print("Starting conversion process...")
        print("="*60 + "\n")
        
        # Setup directories
        self.setup_output_directories()
        
        # Scan all files
        self.scan_files()
        
        # Convert files
        success_count = 0
        fail_count = 0
        
        # Convert root level files
        print("\nConverting root level files...")
        for html_file in self.input_dir.glob('*.html'):
            output_file = self.output_dir / html_file.with_suffix('.md').name
            if self.convert_file(html_file, output_file):
                success_count += 1
            else:
                fail_count += 1
        
        # Convert subdirectory files
        for subdir in ['classes', 'enums', 'interfaces']:
            subdir_path = self.input_dir / subdir
            if not subdir_path.exists():
                continue
            
            print(f"\nConverting {subdir}/ files...")
            for html_file in subdir_path.glob('*.html'):
                output_file = self.output_dir / subdir / html_file.with_suffix('.md').name
                if self.convert_file(html_file, output_file):
                    success_count += 1
                else:
                    fail_count += 1
        
        # Summary
        print("\n" + "="*60)
        print("Conversion Summary")
        print("="*60)
        print(f"Successfully converted: {success_count} files")
        print(f"Failed: {fail_count} files")
        print(f"Output directory: {self.output_dir}")
        print("="*60 + "\n")
        
        return success_count, fail_count
    
    def create_index(self):
        """Create an index file listing all converted files."""
        index_content = """# Agora Web SDK API Reference

This is the Markdown version of the Agora Web SDK API Reference documentation.

## Structure

- [Globals](globals.md) - Global types and exports
- [Classes](classes/) - Class definitions
- [Enums](enums/) - Enumeration types
- [Interfaces](interfaces/) - Interface definitions

## Quick Links

### Main Interface
- [IAgoraRTC](interfaces/iagorartc.md) - Main entry point for the SDK

### Client
- [IAgoraRTCClient](interfaces/iagorartcclient.md) - Client interface for managing connections

### Tracks
- [ILocalTrack](interfaces/ilocaltrack.md) - Local track interface
- [ILocalAudioTrack](interfaces/ilocalaudiotrack.md) - Local audio track
- [ILocalVideoTrack](interfaces/ilocalvideotrack.md) - Local video track
- [IRemoteTrack](interfaces/iremotetrack.md) - Remote track interface
- [IRemoteAudioTrack](interfaces/iremoteaudiotrack.md) - Remote audio track
- [IRemoteVideoTrack](interfaces/iremotevideotrack.md) - Remote video track

## Navigation

Browse the documentation by folder:
- **classes/** - Class implementations
- **enums/** - Enumeration definitions  
- **interfaces/** - Interface definitions

All internal links have been converted to work with the Markdown structure.
"""
        
        index_file = self.output_dir / 'README.md'
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"Created index file: {index_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert Agora RTC HTML API Reference to Markdown'
    )
    parser.add_argument(
        'input_dir',
        help='Input directory containing HTML files (e.g., docs_en)'
    )
    parser.add_argument(
        'output_dir',
        help='Output directory for Markdown files (e.g., docs_md)'
    )
    parser.add_argument(
        '--create-index',
        action='store_true',
        help='Create an index README.md file'
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists():
        print(f"Error: Input directory '{args.input_dir}' does not exist")
        return 1
    
    # Create converter
    converter = HTMLToMarkdownConverter(args.input_dir, args.output_dir)
    
    # Convert all files
    success, failed = converter.convert_all()
    
    # Create index if requested
    if args.create_index:
        converter.create_index()
    
    # Return exit code
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    exit(main())
