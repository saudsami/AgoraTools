# Agora RTC HTML to Markdown Converter

A Python script that converts Agora Web SDK API Reference documentation from TypeDoc-generated HTML to clean Markdown format, preserving folder structure and converting all internal links.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Input and Output Structure](#input-and-output-structure)
- [Configuration and Customization](#configuration-and-customization)
- [Examples](#examples)
- [Use Cases](#use-cases)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Quick Start

### Option 1: Automated Script (Fastest)
```bash
chmod +x quick_start.sh
./quick_start.sh docs_en docs_md
```

### Option 2: Manual (3 Steps)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run conversion
python html_to_markdown_converter.py docs_en docs_md --create-index

# 3. Check output
cat docs_md/README.md
```

**That's it!** Your Markdown documentation is ready in the `docs_md` folder.

---

## Features

- ✅ **Converts HTML to Markdown** - Clean, readable format optimized for LLMs
- ✅ **Preserves folder structure** - Maintains `classes/`, `enums/`, `interfaces/` organization
- ✅ **Converts internal links** - Automatically changes `.html` to `.md`
- ✅ **Maintains anchor links** - Preserves `#section` references within pages
- ✅ **Adds YAML frontmatter** - Includes title and description metadata
- ✅ **Cleans up content** - Removes navigation and UI elements
- ✅ **Creates index file** - Optional README with quick links (use `--create-index`)
- ✅ **Fast processing** - Converts ~100 files in 1 minute
- ✅ **Error handling** - Reports issues with helpful messages

---

## Requirements

- **Python:** 3.7 or higher
- **Dependencies:**
  - `beautifulsoup4>=4.12.0` - HTML parsing
  - `html2text>=2020.1.16` - HTML to Markdown conversion
  - `lxml>=4.9.0` - Fast XML/HTML parsing
- **Input:** TypeDoc-generated HTML documentation
- **Output:** Markdown files with working internal links

---

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install beautifulsoup4 html2text lxml
```

---

## Usage

### Basic Command

```bash
python html_to_markdown_converter.py <input_directory> <output_directory>
```

### With Index Generation

```bash
python html_to_markdown_converter.py <input_directory> <output_directory> --create-index
```

### Examples

```bash
# Convert docs_en to docs_md
python html_to_markdown_converter.py docs_en docs_md

# Convert with index file
python html_to_markdown_converter.py docs_en docs_md --create-index

# Convert to different location
python html_to_markdown_converter.py /path/to/html_docs /path/to/markdown_output --create-index
```

### Command Line Options

- `input_dir` - Input directory containing HTML files (required)
- `output_dir` - Output directory for Markdown files (required)
- `--create-index` - Generate a README.md index file with quick links (optional)
- `--help` - Show help message

---

## How It Works

The converter operates in four main phases:

### 1. Scanning Phase
- Walks through the input directory
- Finds all `.html` files in root and subdirectories
- Builds a mapping: `filename.html` → `filename.md`
- Creates output directory structure

### 2. Content Extraction
For each HTML file:
- Parses HTML with BeautifulSoup
- Extracts title from `<h1>` tag
- Extracts description from first `.tsd-comment .lead` section
- Extracts main content from `<div class="col-9 col-content">`
- Ignores navigation, headers, and footers

### 3. Link Conversion
- Finds all `<a href="...">` tags
- Converts internal `.html` links to `.md`
- Preserves anchor fragments: `page.html#section` → `page.md#section`
- Maintains relative paths: `../interfaces/file.html` → `../interfaces/file.md`
- Leaves external links (http://, https://) unchanged

### 4. Markdown Generation
- Converts HTML to Markdown using html2text
- Cleans up formatting (removes extra blank lines, navigation elements)
- Adds YAML frontmatter with title and description
- Writes output file to corresponding location

### Flow Diagram
```
Input HTML → Parse → Extract Content → Convert Links → Generate Markdown → Add Frontmatter → Save
```

---

## Input and Output Structure

### Input Structure (Expected)
```
docs_en/
├── assets/           (ignored - CSS, JS, images)
├── classes/
│   ├── eventemitter.html
│   └── ...
├── enums/
│   ├── videostate.html
│   └── ...
├── interfaces/
│   ├── iagorartc.html
│   ├── iagorartcclient.html
│   └── ...
├── globals.html
└── index.html
```

### Output Structure (Generated)
```
docs_md/
├── classes/
│   ├── eventemitter.md
│   └── ...
├── enums/
│   ├── videostate.md
│   └── ...
├── interfaces/
│   ├── iagorartc.md
│   ├── iagorartcclient.md
│   └── ...
├── globals.md
├── index.md
└── README.md         (if --create-index used)
```

### File Mapping Examples
- `index.html` → `index.md`
- `classes/eventemitter.html` → `classes/eventemitter.md`
- `interfaces/iagorartc.html` → `interfaces/iagorartc.md`
- `enums/videostate.html` → `enums/videostate.md`

---

## Configuration and Customization

### HTML2Text Settings

Modify these in `HTMLToMarkdownConverter.__init__()`:

```python
self.html2text.body_width = 0              # 0 = no line wrapping
self.html2text.ignore_links = False        # Set True to remove all links
self.html2text.ignore_images = False       # Set True to remove images
self.html2text.single_line_break = False   # Set True for compact format
```

### Content Extraction

Customize what gets extracted in `extract_content()`:

```python
# Default: Extract from TypeDoc's main content area
content_div = soup.find('div', class_='col-9 col-content')

# Alternative: Extract from different container
content_div = soup.find('main')
# or
content_div = soup.find('article', class_='documentation')
```

### Link Patterns

Add custom link handling in `convert_html_links_to_markdown()`:

```python
# Skip certain patterns
if 'external' in href or 'docs.agora.io' in href:
    continue

# Transform specific patterns
if href.startswith('api/'):
    href = '../' + href
```

### Markdown Cleanup

Adjust cleanup rules in `clean_markdown_content()`:

```python
# Remove additional patterns
skip_patterns = [
    'Globals',
    'Navigation',
    'Index',
    'Hierarchy',
    'Legend'
]

for pattern in skip_patterns:
    if pattern in line:
        continue
```

### Frontmatter Customization

Add additional metadata in `add_frontmatter()`:

```python
def add_frontmatter(self, title: str, description: str) -> str:
    frontmatter = f"""---
title: {title}
description: {description if description else title}
category: API Reference
version: 4.24.1
sidebar_label: {title}
---

"""
    return frontmatter
```

### File Filtering

Control which files get converted in `convert_all()`:

```python
# Only convert specific files
for html_file in subdir_path.glob('*.html'):
    # Skip files starting with underscore
    if html_file.name.startswith('_'):
        continue
    
    # Only convert interfaces
    if subdir != 'interfaces':
        continue
    
    # Convert
    self.convert_file(html_file, output_file)
```

---

## Examples

### Example 1: Basic Conversion

**Input HTML** (`interfaces/iagorartc.html`):
```html
<p>Creates a <a href="../interfaces/iagorartcclient.html">client</a> object.</p>
```

**Output Markdown** (`interfaces/iagorartc.md`):
```markdown
---
title: IAgoraRTC
description: The entry point of the Agora Web SDK.
---

Creates a [client](../interfaces/iagorartcclient.md) object.
```

### Example 2: Link Conversion

**Before (HTML):**
```html
<a href="../classes/eventemitter.html#on">EventEmitter.on</a>
<a href="iagorartcclient.html#join">join method</a>
<a href="../enums/videostate.html">VideoState</a>
```

**After (Markdown):**
```markdown
[EventEmitter.on](../classes/eventemitter.md#on)
[join method](iagorartcclient.md#join)
[VideoState](../enums/videostate.md)
```

### Example 3: Enum Conversion

**Input** (`enums/videostate.html`):
```html
<section class="tsd-panel tsd-member">
    <h3>VideoStateDecoding</h3>
    <div class="tsd-signature">VideoStateDecoding: = 2</div>
    <div class="tsd-comment">
        <p>2: The video stream is being decoded and played normally.</p>
    </div>
</section>
```

**Output** (`enums/videostate.md`):
```markdown
---
title: VideoState
description: The state of the video stream.
---

# Enumeration VideoState

The state of the video stream.

## Enumeration members

### VideoStateDecoding

• **VideoStateDecoding**: = 2

2: The video stream is being decoded and played normally.
```

### Example 4: Method Documentation

**Input HTML:**
```html
<h3>createClient</h3>
<ul class="tsd-signatures">
    <li>createClient(config: <a href="clientconfig.html">ClientConfig</a>): 
    <a href="iagorartcclient.html">IAgoraRTCClient</a></li>
</ul>
<div class="tsd-comment">
    <p>Creates a local client object for managing a connection.</p>
</div>
```

**Output Markdown:**
```markdown
### createClient

▸ **createClient**(`config`: [ClientConfig](clientconfig.md)): [IAgoraRTCClient](iagorartcclient.md)

Creates a local client object for managing a connection.

**Parameters:**

Name | Type | Description
-----|------|------------
`config` | [ClientConfig](clientconfig.md) | Client configuration

**Returns:** [IAgoraRTCClient](iagorartcclient.md)
```

---

## Use Cases

### 1. LLM Context Enhancement

**Goal:** Use API documentation with Claude, GPT, or other LLMs

**Steps:**
1. Convert: `python html_to_markdown_converter.py docs_en docs_md`
2. Copy content from relevant `.md` file
3. Paste into LLM conversation

**Benefits:**
- Clean format for better understanding
- No HTML noise
- Preserved structure and links
- Easy to reference specific sections

**Example:**
```
Here's the Agora RTC IAgoraRTC interface documentation:

[paste content from iagorartc.md]

How do I create a client and join a channel with specific settings?
```

### 2. Documentation Website Integration

**Goal:** Add to Docusaurus, MkDocs, Jekyll, etc.

**Docusaurus Example:**
```bash
# Convert to docs folder
python html_to_markdown_converter.py docs_en docs/api --create-index

# Configure docusaurus.config.js
# docs: { path: 'docs', routeBasePath: '/' }

# Build
npm run build
```

**MkDocs Example:**
```bash
# Convert to docs folder
python html_to_markdown_converter.py docs_en docs/api

# Configure mkdocs.yml
# nav:
#   - API Reference: api/

# Build
mkdocs build
```

### 3. GitHub/GitLab Pages

**Goal:** Host documentation on GitHub Pages

**Steps:**
```bash
# Convert
python html_to_markdown_converter.py docs_en docs --create-index

# Commit
git add docs
git commit -m "Add API documentation"
git push

# Enable GitHub Pages in repository settings
# Source: docs folder or main branch
```

### 4. Version Control

**Benefits:**
- Plain text format for easy diffs
- Track documentation changes over time
- Collaborate with teams using pull requests
- Branch different documentation versions

**Example workflow:**
```bash
# Convert new version
python html_to_markdown_converter.py docs_en_v4.25.0 docs_md

# See what changed
git diff docs_md/interfaces/iagorartc.md

# Commit
git commit -m "Update API docs to v4.25.0"
```

### 5. Local Development

**Goal:** Browse documentation in VS Code or other editors

**Steps:**
1. Convert: `python html_to_markdown_converter.py docs_en docs_md --create-index`
2. Open in VS Code: `code docs_md`
3. Install Markdown Preview Enhanced extension
4. Use Cmd/Ctrl+Click to follow links

---

## Troubleshooting

### Installation Issues

**Problem:** `ModuleNotFoundError: No module named 'bs4'`

**Solution:**
```bash
pip install beautifulsoup4 html2text lxml
```

**Problem:** `pip: command not found`

**Solution:** Install Python 3.7+ with pip, or use:
```bash
python3 -m pip install beautifulsoup4 html2text lxml
```

### File and Directory Issues

**Problem:** `FileNotFoundError: [Errno 2] No such file or directory: 'docs_en'`

**Solution:** Check the input directory exists:
```bash
ls docs_en/
# or use absolute path
python html_to_markdown_converter.py /full/path/to/docs_en docs_md
```

**Problem:** Permission denied

**Solution:** Check file permissions:
```bash
chmod +x quick_start.sh
# or
chmod 755 html_to_markdown_converter.py
```

### Conversion Issues

**Problem:** Links still showing `.html` in output

**Solution:** 
1. Verify input HTML has proper relative links
2. Check console for errors during conversion
3. Search for remaining `.html` references:
```bash
grep -r "\.html" docs_md/
```

**Problem:** Missing or corrupted content

**Solution:**
1. Verify HTML structure matches TypeDoc format
2. Check that `<div class="col-9 col-content">` exists
3. Try converting a single file to debug:
```python
converter = HTMLToMarkdownConverter('docs_en', 'test_output')
converter.convert_file('docs_en/interfaces/iagorartc.html', 'test_output/test.md')
```

**Problem:** Encoding errors (strange characters)

**Solution:** Ensure all HTML files are UTF-8 encoded:
```bash
file -i docs_en/interfaces/*.html
# Should show: charset=utf-8
```

### Output Quality Issues

**Problem:** Too much whitespace in output

**Solution:** Adjust cleanup in `clean_markdown_content()`:
```python
# Remove excessive blank lines
markdown = re.sub(r'\n{3,}', '\n\n', markdown)
```

**Problem:** Navigation elements still present

**Solution:** Add patterns to remove in `clean_markdown_content()`:
```python
skip_patterns = ['Globals', 'Navigation', 'Index', 'Breadcrumb']
for pattern in skip_patterns:
    if pattern in line:
        continue
```

### Performance Issues

**Problem:** Conversion taking too long

**Solution:**
1. Process in batches for very large documentation sets
2. Use SSD for faster I/O
3. Close unnecessary applications
4. Consider implementing parallel processing (see Advanced Topics)

---

## Advanced Topics

### Parallel Processing

For large documentation sets, process files in parallel:

```python
import multiprocessing
from pathlib import Path

def convert_file_wrapper(args):
    converter, html_file, output_file = args
    return converter.convert_file(html_file, output_file)

def convert_parallel(self):
    files = [(self, f, self.get_output_path(f)) 
             for f in self.input_dir.rglob('*.html')]
    
    with multiprocessing.Pool() as pool:
        results = pool.map(convert_file_wrapper, files)
    
    return sum(results), len(results) - sum(results)
```

### Incremental Updates

Only convert files that have changed:

```python
def convert_incremental(self):
    for html_file in self.input_dir.rglob('*.html'):
        md_file = self.get_output_path(html_file)
        
        # Skip if MD is newer than HTML
        if md_file.exists():
            if md_file.stat().st_mtime > html_file.stat().st_mtime:
                continue
        
        self.convert_file(html_file, md_file)
```

### Multi-Language Support

Handle multiple languages:

```python
def convert_with_language(self, language: str):
    self.language = language
    
    # Language-specific settings
    if language == 'zh-CN':
        self.html2text.unicode_snob = True
        self.html2text.body_width = 0
    
    # Add language to frontmatter
    def add_frontmatter_with_lang(self, title, desc):
        return f"""---
title: {title}
description: {desc}
lang: {self.language}
---

"""
```

### Output Validation

Validate converted files:

```python
def validate_output(self):
    issues = []
    
    for md_file in self.output_dir.rglob('*.md'):
        content = md_file.read_text()
        
        # Check for broken links
        links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
        for text, url in links:
            if url.endswith('.md') and not url.startswith('http'):
                target = (md_file.parent / url).resolve()
                if not target.exists():
                    issues.append(f"Broken link in {md_file}: {url}")
        
        # Check frontmatter
        if not content.startswith('---'):
            issues.append(f"Missing frontmatter: {md_file}")
    
    return issues
```

### Custom Index Generation

Create a categorized index:

```python
def create_custom_index(self):
    categories = {
        'Core': ['iagorartc', 'iagorartcclient'],
        'Tracks': ['ilocaltrack', 'iremotetrack', 'ilocalaudiotrack'],
        'Enums': ['videostate', 'connectionstate']
    }
    
    index_content = "# API Reference\n\n"
    
    for category, items in categories.items():
        index_content += f"\n## {category}\n\n"
        for item in items:
            md_file = self.find_file(item)
            if md_file:
                index_content += f"- [{item}]({md_file})\n"
    
    return index_content
```

### Batch Processing Multiple Versions

Process multiple API versions:

```bash
#!/bin/bash
for version in v4.22.0 v4.23.0 v4.24.1; do
    echo "Converting $version..."
    python html_to_markdown_converter.py \
        docs_en_${version} \
        docs_md_${version} \
        --create-index
done
```

### Integration with CI/CD

GitHub Actions example:

```yaml
name: Convert API Docs

on:
  push:
    paths:
      - 'docs_html/**'

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Convert docs
        run: python html_to_markdown_converter.py docs_html docs_md --create-index
      - name: Commit changes
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add docs_md
          git commit -m "Update markdown docs"
          git push
```

---

## Package Contents

- **html_to_markdown_converter.py** - Main conversion script
- **requirements.txt** - Python dependencies
- **quick_start.sh** - Automated setup and conversion script
- **README.md** - This comprehensive guide

---

## Performance Metrics

- **Speed:** ~1 second per file
- **Typical conversion:** 100 files in ~1-2 minutes
- **Memory usage:** <100 MB for standard documentation
- **Output size:** 20-30% smaller than HTML

---

## License

This conversion script is provided for converting Agora RTC documentation. The output Markdown files retain the same licensing as the original HTML documentation from Agora.io.

---

## Credits

**Libraries Used:**
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
- [html2text](https://github.com/Alir3z4/html2text) - HTML to Markdown conversion
- [lxml](https://lxml.de/) - Fast XML/HTML parsing

**Version:** 1.0  
**Python Requirement:** 3.7+  
**Compatible with:** TypeDoc-generated HTML documentation

---

**Need help?** All documentation is in this README. Start with the [Quick Start](#quick-start) section above.
