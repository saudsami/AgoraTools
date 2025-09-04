# Agora Documentation Export Tool

A Python script that automates the conversion of multiple MDX documentation files to Markdown format using the `mdx2md.py` converter. This tool processes entire documentation repositories, handling platform-specific exports and creating organized output structures.

## Overview

The bulk export tool walks through a documentation repository, identifies MDX files, and converts them to Markdown based on platform configurations defined in the product mapping. It handles:

- Platform-specific document variations
- Automated file organization
- Error handling and reporting  
- Platform index file generation
- Bulk processing with detailed logging

## Prerequisites

- Python 3.7+
- `mdx2md.py` script in the same directory
- Required Python packages: `pyyaml`
- Access to the Agora Docs repository structure

## Usage

```bash
python bulk_export.py --docs-folder <path> [options]
```

### Required Parameters

- `--docs-folder` (required): Path to the root Docs folder containing the documentation repository (e.g., `D:/Git/AgoraDocs/Docs`)

### Optional Parameters

- `--start-folder` (optional): Subfolder within `Docs/docs` to start processing from. If not specified, processes the entire docs folder.
  - Example: `--start-folder flexible-classroom` processes only `Docs/docs/flexible-classroom/`

- `--output-dir` (optional): Base output directory for generated Markdown files. Default: `output`
  - Creates the directory structure if it doesn't exist
  - Maintains the original folder hierarchy from the source

- `--skip-platform-index` (optional): Skip creation of platform index files. When omitted, the tool creates index files that link to all platform-specific versions of documents.

- `--continue-on-error` (optional): Explicitly continue processing when individual exports fail. This is the default behavior, included for clarity.

## Examples

### Basic Usage
Convert all documentation:
```bash
python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs
```

### Process Specific Product
Convert only flexible-classroom documentation:
```bash
python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs --start-folder flexible-classroom
```

### Custom Output Directory
Export to a custom location:
```bash
python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs --output-dir converted-docs
```

### Skip Platform Indexes
Generate only platform-specific files without index pages:
```bash
python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs --skip-platform-index
```

## How It Works

1. **Product Mapping**: Reads `Docs/data/v2/products.js` to understand which platforms are available for each product
2. **File Discovery**: Walks through the documentation directory to find `.mdx` files
3. **Platform Processing**: For each file, determines available platforms and creates exports accordingly
4. **Conversion**: Calls `mdx2md.py` for each platform-specific version
5. **Index Generation**: Creates platform selection pages linking to all variants (unless skipped)
6. **Error Handling**: Continues processing even when individual files fail, collecting error details

## Output Structure

The tool maintains the original folder hierarchy:

```
output/
├── flexible-classroom/
│   ├── get-started/
│   │   ├── quickstart_android.md
│   │   ├── quickstart_ios.md
│   │   ├── quickstart_web.md
│   │   └── quickstart.md (platform index)
│   └── ...
└── video-calling/
    └── ...
```

Documents from the `docs-help` directory are exported to the `help` folder.

## Platform Handling

The tool processes files based on their frontmatter:

- **`platform_selector: true`** (default): Creates separate files for each supported platform
- **`platform_selector: false`**: Creates a single universal file
- **`excluded_platforms`**: Array of platforms to skip for this file

## Error Handling

When exports fail:
- Processing continues with remaining files
- Error details are collected and reported
- A detailed error log (`export_errors.log`) is created in the output directory
- Final summary shows success/failure statistics

## Troubleshooting

### Common Issues

1. **Missing product mapping**: Files skipped with "no product mapping" warning
   - Ensure the file path structure matches product IDs in `products.js`

2. **Export failures**: Individual files fail conversion
   - Check the error log for detailed failure reasons
   - Common causes: missing imports, invalid MDX syntax, missing assets

3. **Path issues**: Windows/Unix path separator problems
   - The tool normalizes paths automatically, but ensure no mixed separators in arguments

### Error Log

Check `export_errors.log` in the output directory for:
- Complete command that failed
- Return codes and error messages  
- File paths and platform information
- Suggested fixes for common issues

## Dependencies

The tool relies on:
- `mdx2md.py` for individual file conversion
- `products.js` for platform configuration
- Original MDX files and their imports/assets
- YAML frontmatter parsing for file metadata

## Usage examples

1. Execute the bulk export for the entire site:

    ```bash
    python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs
    ```

1. Export a specific folder:

    ```bash
    python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs --start-folder signaling/reference
    ```

1. Export the help articles:

    ```bash
    python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs --process-help 
    ```

1. Generate sitemap

    ```bash
    python sitemap_generator.py --docs-dir ./output
    ```

1. Upload the following files to the `markdown-service` repository:

    1. Copy the images folder from the output to `/public/`
    1. Copy all other folders to `/public/en/`
    1. Copy sitemap.xml to `/public/`