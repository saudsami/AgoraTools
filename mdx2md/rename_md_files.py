#!/usr/bin/env python3
"""
Markdown File Renamer with Sequential ID Mapping - Parallel Output Version

This script processes markdown files in a directory structure, copies them with sequential IDs
to a parallel folder structure in 'output-indexed', and maintains a JSON index mapping IDs to original URLs.

Usage: python rename_md_files.py <root_folder>
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, Any
import argparse

class MarkdownProcessor:
    def __init__(self, root_folder: str, output_folder: str = "output-indexed", index_file: str = "file_mapping.json"):
        self.root_folder = Path(root_folder)
        self.output_folder = Path(output_folder)
        self.index_file = self.output_folder / index_file
        self.mapping: Dict[str, Any] = {}
        self.path_to_id: Dict[str, str] = {}  # original_path -> id
        self.next_id = 1
        
    def ensure_output_directory(self) -> None:
        """Create output directory if it doesn't exist."""
        self.output_folder.mkdir(exist_ok=True)
        print(f"Output directory: {self.output_folder}")
        
    def load_existing_mapping(self) -> None:
        """Load existing mapping file if it exists."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.mapping = json.load(f)
                    
                # Build path-to-ID mapping and find next available ID
                max_id = 0
                for file_id, data in self.mapping.items():
                    if 'original_path' in data:
                        self.path_to_id[data['original_path']] = file_id
                    
                    # Track highest ID number for new files
                    try:
                        id_num = int(file_id)
                        max_id = max(max_id, id_num)
                    except ValueError:
                        pass
                
                self.next_id = max_id + 1
                        
                print(f"Loaded existing mapping with {len(self.mapping)} entries")
                print(f"Next ID will be: {self.next_id}")
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load existing mapping: {e}")
                print("Starting with empty mapping")
    
    def extract_frontmatter(self, file_path: Path) -> Optional[Dict[str, str]]:
        """Extract frontmatter from a markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file starts with frontmatter delimiter
            if not content.startswith('---'):
                return None
            
            # Find the end of frontmatter
            lines = content.split('\n')
            end_index = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    end_index = i
                    break
            
            if end_index == -1:
                return None
            
            # Parse frontmatter
            frontmatter_lines = lines[1:end_index]
            frontmatter = {}
            
            for line in frontmatter_lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    frontmatter[key] = value
            
            return frontmatter
            
        except (IOError, UnicodeDecodeError) as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def get_or_create_id(self, file_path: Path, url: str, title: str) -> str:
        """Get existing ID for file or create a new one."""
        relative_path = str(file_path.relative_to(self.root_folder))
        
        # Check if we already have an ID for this file path
        if relative_path in self.path_to_id:
            existing_id = self.path_to_id[relative_path]
            print(f"Found existing ID {existing_id} for {relative_path}")
            
            # Update the mapping data in case URL or title changed
            if existing_id in self.mapping:
                self.mapping[existing_id]['url'] = url
                self.mapping[existing_id]['title'] = title
            
            return existing_id
        
        # Create new sequential ID
        new_id = str(self.next_id)
        self.next_id += 1
        
        print(f"Created new ID {new_id} for {relative_path}")
        return new_id
    
    def process_file(self, file_path: Path) -> bool:
        """Process a single markdown file."""
        if file_path.suffix.lower() != '.md':
            return False
        
        # Extract frontmatter
        frontmatter = self.extract_frontmatter(file_path)
        if not frontmatter:
            print(f"Warning: No frontmatter found in {file_path}")
            return False
        
        # Get URL from frontmatter
        url = frontmatter.get('exported_from') or frontmatter.get('url') or frontmatter.get('permalink') or frontmatter.get('slug')
        if not url:
            print(f"Warning: No URL found in frontmatter of {file_path}")
            return False
        
        title = frontmatter.get('title', file_path.name)
        
        # Get or create ID
        file_id = self.get_or_create_id(file_path, url, title)
        
        # Calculate relative path from root folder
        relative_path = file_path.relative_to(self.root_folder)
        
        # Create parallel directory structure in output folder
        output_dir = self.output_folder / relative_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create new filename and full output path
        original_name = file_path.name
        new_name = f"{file_id}__{original_name}"
        output_path = output_dir / new_name
        
        # Copy file to output location
        try:
            shutil.copy2(file_path, output_path)
            print(f"Copied: {relative_path} -> {output_path.relative_to(self.output_folder)}")
            
            # Update mapping
            relative_original_path = str(relative_path)
            relative_output_path = str(output_path.relative_to(self.output_folder))
            
            self.mapping[file_id] = {
                'url': url,
                'title': title,
                'original_filename': original_name,
                'current_filename': new_name,
                'original_path': relative_original_path,
                'output_path': relative_output_path
            }
            
            # Update path-to-ID mapping
            self.path_to_id[relative_original_path] = file_id
            
            return True
            
        except (OSError, IOError) as e:
            print(f"Error copying {file_path}: {e}")
            return False
    
    def save_mapping(self) -> None:
        """Save the mapping to JSON file."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, indent=2, ensure_ascii=False)
            print(f"Saved mapping to {self.index_file}")
        except IOError as e:
            print(f"Error saving mapping: {e}")
    
    def process_directory(self) -> None:
        """Process all markdown files in the directory tree."""
        if not self.root_folder.exists():
            print(f"Error: Directory {self.root_folder} does not exist")
            return
        
        print(f"Processing source directory: {self.root_folder}")
        
        # Ensure output directory exists
        self.ensure_output_directory()
        
        # Load existing mapping
        self.load_existing_mapping()
        
        # Find all markdown files
        md_files = list(self.root_folder.rglob("*.md"))
        print(f"Found {len(md_files)} markdown files")
        
        processed_count = 0
        for md_file in md_files:
            if self.process_file(md_file):
                processed_count += 1
        
        # Save updated mapping
        self.save_mapping()
        
        print(f"\nProcessing complete:")
        print(f"- Successfully processed {processed_count} files")
        print(f"- Total entries in mapping: {len(self.mapping)}")
        print(f"- Next available ID: {self.next_id}")
        print(f"- Output directory: {self.output_folder}")
        print(f"- Mapping file: {self.index_file}")

def main():
    parser = argparse.ArgumentParser(description="Process markdown files with sequential IDs and build URL mapping in parallel output structure")
    parser.add_argument("root_folder", help="Root folder containing markdown files")
    parser.add_argument("--output-folder", default="output-indexed", 
                       help="Output folder for processed files (default: output-indexed)")
    parser.add_argument("--index-file", default="file_mapping.json", 
                       help="Name of the JSON index file (default: file_mapping.json)")
    
    args = parser.parse_args()
    
    processor = MarkdownProcessor(args.root_folder, args.output_folder, args.index_file)
    processor.process_directory()

if __name__ == "__main__":
    main()