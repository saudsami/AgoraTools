import os
import re
import subprocess
import yaml
import argparse
from datetime import datetime

# ---------------------------------------------------------------------------
# Optional dependency: docs index injection
# ---------------------------------------------------------------------------
# add_docs_index.py must be in the same directory as bulk_export.py.
# If it is absent the rest of bulk_export works normally; only the
# --no-overview-index suppression flag has no effect.

try:
    from add_docs_index import add_docs_index_for_product
    _DOCS_INDEX_AVAILABLE = True
except ImportError:
    _DOCS_INDEX_AVAILABLE = False

# --- Helpers ---

def load_product_platforms(products_file):
    """Parse products.js and return { productId: [platforms...] }"""
    with open(products_file, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"id:\s*'([^']+)'.*?platforms:\s*{[^}]*latest:\s*\[([^\]]*)\]", re.DOTALL)
    mapping = {}
    for match in pattern.finditer(content):
        product_id = match.group(1)
        platforms_str = match.group(2)
        platforms = re.findall(r"'([^']+)'", platforms_str)
        mapping[product_id] = platforms
    return mapping


def parse_frontmatter(file_path):
    """Extract YAML frontmatter dict from an .mdx file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def should_skip(path):
    """Skip certain top-level folders"""
    skip_folders = {"shared", ".github", "use-cases", "assets"}
    parts = path.replace("\\", "/").split("/")
    return any(p in skip_folders for p in parts)


def run_mdx2md(mdx_file, platform, output_file, docs_folder, failed_exports):
    """Run mdx2md.py for a given platform/output_file with error handling"""
    cmd = ["python", "mdx2md.py", "--mdxPath", mdx_file]
    if platform:
        cmd.extend(["--platform", platform])
    cmd.extend(["--output-file", output_file])
    cmd.extend(["--docs-folder", docs_folder])
    
    print("Running:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        error_info = {
            'file': mdx_file,
            'platform': platform,
            'output': output_file,
            'command': ' '.join(cmd),
            'return_code': e.returncode,
            'stdout': e.stdout if e.stdout else 'No stdout',
            'stderr': e.stderr if e.stderr else 'No stderr'
        }
        failed_exports.append(error_info)
        print(f"❌ FAILED: {mdx_file} (platform: {platform or 'none'}) - Exit code: {e.returncode}")
        if e.stderr:
            print(f"   Error: {e.stderr.strip()[:200]}...")
        return False
    except Exception as e:
        error_info = {
            'file': mdx_file,
            'platform': platform,
            'output': output_file,
            'command': ' '.join(cmd),
            'return_code': 'N/A',
            'stdout': 'N/A',
            'stderr': str(e)
        }
        failed_exports.append(error_info)
        print(f"❌ FAILED: {mdx_file} (platform: {platform or 'none'}) - Exception: {e}")
        return False


def create_platform_index_file(mdx_file, platforms, output_dir, base_name, docs_folder):
    """
    Create a platform index file that links to all platform-specific versions.
    """
    try:
        fm = parse_frontmatter(mdx_file)
        title = fm.get('title', 'Documentation')
        description = fm.get('description', '')
        sidebar_position = fm.get('sidebar_position')

        exported_from = get_exported_from_url(mdx_file, docs_folder, is_help=False)

        index_frontmatter = {
            'title': title,
            'platform_selector': False,
            'exported_from': exported_from,
            'exported_on': datetime.utcnow().isoformat() + 'Z',
            'exported_file': f'{base_name}.md'
        }
        
        if description:
            index_frontmatter['description'] = description
        if sidebar_position is not None:
            index_frontmatter['sidebar_position'] = sidebar_position
        
        frontmatter_yaml = yaml.safe_dump(index_frontmatter, sort_keys=False).strip()

        # Build AI navigation directive
        path_after_en = exported_from.split("/en/", 1)[-1]
        product_slug = path_after_en.split("/")[0]
        directive = (
            f"> For a complete site index fetch https://docs.agora.io/llms.txt."
            f" For all pages in this product fetch"
            f" https://docs.agora.io/en/{product_slug}/overview/product-overview.md"
        )

        index_content = f"""---
{frontmatter_yaml}
---

{directive}

# {title}

Select your platform:

"""
        
        platform_display_names = {
            'android': 'Android',
            'ios': 'iOS', 
            'web': 'Web',
            'flutter': 'Flutter',
            'react-native': 'React Native',
            'unity': 'Unity',
            'windows': 'Windows',
            'macos': 'macOS',
            'electron': 'Electron'
        }
        
        for platform in sorted(platforms):
            display_name = platform_display_names.get(platform, platform.title())
            platform_file = f"{base_name}_{platform}.md"
            index_content += f"- [{display_name}](./{platform_file})\n"
        
        index_file_path = os.path.join(output_dir, f"{base_name}.md")
        with open(index_file_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"✅ Created platform index: {index_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating platform index for {mdx_file}: {e}")
        return False


def get_exported_from_url(mdx_file, docs_folder, is_help=False):
    """Generate the exported_from URL for the original MDX file"""
    if is_help:
        docs_path = os.path.join(docs_folder, "docs-help")
        rel_path = os.path.relpath(mdx_file, docs_path)
        normalized_path = rel_path.replace(os.sep, "/")
        if normalized_path.endswith('.mdx'):
            normalized_path = normalized_path[:-4]
        return f"https://docs.agora.io/en/help/{normalized_path}"
    else:
        docs_path = os.path.join(docs_folder, "docs")
        rel_path = os.path.relpath(mdx_file, docs_path)
        normalized_path = rel_path.replace(os.sep, "/")
        if normalized_path.endswith('.mdx'):
            normalized_path = normalized_path[:-4]
        return f"https://docs.agora.io/en/{normalized_path}"


def write_error_log(failed_exports, output_base):
    """Write detailed error log to file"""
    if not failed_exports:
        return
    
    log_file = os.path.join(output_base, "export_errors.log")
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write(f"Export Error Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, error in enumerate(failed_exports, 1):
            f.write(f"Error #{i}:\n")
            f.write(f"  File: {error['file']}\n")
            f.write(f"  Platform: {error['platform'] or 'none'}\n")
            f.write(f"  Output: {error['output']}\n")
            f.write(f"  Return Code: {error['return_code']}\n")
            f.write(f"  Command: {error['command']}\n")
            f.write(f"  STDOUT: {error['stdout']}\n")
            f.write(f"  STDERR: {error['stderr']}\n")
            f.write("-" * 40 + "\n\n")
    
    print(f"📋 Detailed error log written to: {log_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--docs-folder",
        required=True,
        help="Path to the Docs folder (e.g. D:/Git/AgoraDocs/Docs)"
    )
    parser.add_argument(
        "--start-folder",
        default="",
        help="Optional subfolder inside Docs/docs to start from (default: whole docs)"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Base output folder for generated .md files (default: output)"
    )
    parser.add_argument(
        "--skip-platform-index",
        action="store_true",
        help="Skip creating platform index files (only create platform-specific files)"
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing even when individual exports fail (default behavior)"
    )
    parser.add_argument(
        "--process-help",
        action="store_true",
        help="Process docs-help folder instead of docs folder (no platform processing)"
    )
    parser.add_argument(
        "--no-overview-index",
        action="store_true",
        help="Skip injecting a documentation index into product-overview.md files. "
             "By default, the index is injected after each product is exported."
    )
    args = parser.parse_args()

    docs_folder = os.path.abspath(args.docs_folder)
    output_base = os.path.abspath(args.output_dir)

    # Warn if index injection was requested but add_docs_index.py is missing
    inject_overview_index = not args.no_overview_index
    if inject_overview_index and not _DOCS_INDEX_AVAILABLE:
        print(
            "⚠️  add_docs_index.py not found alongside bulk_export.py — "
            "overview index injection will be skipped. "
            "Place add_docs_index.py in the same directory to enable it, "
            "or pass --no-overview-index to suppress this warning."
        )
        inject_overview_index = False

    if args.process_help:
        start_path = os.path.join(docs_folder, "docs-help", args.start_folder)
        product_platforms = {}
    else:
        start_path = os.path.join(docs_folder, "docs", args.start_folder)
        products_file = os.path.join(docs_folder, "data", "v2", "products.js")
        product_platforms = load_product_platforms(products_file)
    
    failed_exports = []

    print(f"Mode: {'Help files' if args.process_help else 'Documentation'}")
    if not args.process_help:
        print(f"Loaded product → platforms mapping from {products_file}")
    print(f"Starting export from: {start_path}")
    print(f"Output directory: {output_base}")
    print(f"Platform processing: {'Disabled' if args.process_help else 'Enabled'}")
    print(f"Platform index creation: {'Disabled' if args.skip_platform_index or args.process_help else 'Enabled'}")
    print(f"Overview index injection: {'Disabled' if not inject_overview_index else 'Enabled'}")
    print(f"Continue on error: {'Enabled' if args.continue_on_error else 'Enabled (default)'}")
    print("-" * 60)

    processed_files = 0
    successful_exports = 0
    index_files_created = 0
    overview_indexes_injected = 0

    # Group files by product so we can run index injection per product.
    # In help mode there are no products, so we process files directly.
    if args.process_help:
        # Help mode: simple processing, no products or overview index
        for root, _, files in os.walk(start_path):
            for filename in files:
                if not (filename.endswith(".mdx") or filename.endswith(".md")):
                    continue

                mdx_file = os.path.join(root, filename)
                if should_skip(mdx_file):
                    continue

                rel_path = os.path.relpath(mdx_file, os.path.join(docs_folder, "docs-help"))
                output_dir = os.path.join(output_base, "help", os.path.dirname(rel_path))
                os.makedirs(output_dir, exist_ok=True)

                base_name = os.path.splitext(os.path.basename(mdx_file))[0]
                output_file = os.path.join(output_dir, f"{base_name}.md")
                processed_files += 1
                
                if run_mdx2md(mdx_file, None, output_file, docs_folder, failed_exports):
                    successful_exports += 1

    else:
        # Docs mode: collect all product IDs first, then process per product
        # so we can run index injection after all files for a product are done.

        # Build a mapping: product_id -> list of (mdx_file, rel_path) tuples
        # We need to walk once to discover products, but we process per product
        # to keep the injection call natural.
        #
        # For simplicity we keep the original os.walk structure but track the
        # current product and flush the index injection when it changes.

        current_product_id = None
        current_output_product_dir = None
        current_platforms = []
        current_source_product_dir = None

        def flush_overview_index():
            """Inject the overview index for the product that just finished."""
            if not inject_overview_index:
                return
            if current_product_id is None:
                return
            print(f"\n📋 Injecting documentation index for: {current_product_id}")
            ok = add_docs_index_for_product(
                product_id=current_product_id,
                source_product_dir=current_source_product_dir,
                output_product_dir=current_output_product_dir,
                platforms=current_platforms,
            )
            nonlocal overview_indexes_injected
            if ok:
                overview_indexes_injected += 1

        for root, _, files in os.walk(start_path):
            for filename in files:
                if not (filename.endswith(".mdx") or filename.endswith(".md")):
                    continue

                mdx_file = os.path.join(root, filename)
                if should_skip(mdx_file):
                    continue

                rel_path = os.path.relpath(mdx_file, os.path.join(docs_folder, "docs"))
                parts = rel_path.replace("\\", "/").split("/")
                product_id = parts[0]

                if product_id not in product_platforms:
                    print(f"⚠️ Skipping {mdx_file}, no product mapping")
                    continue

                # Detect product boundary — flush index for the previous product
                if product_id != current_product_id:
                    flush_overview_index()
                    current_product_id = product_id
                    current_platforms = product_platforms[product_id]
                    current_output_product_dir = os.path.normpath(
                        os.path.join(output_base, product_id)
                    )
                    current_source_product_dir = os.path.normpath(
                        os.path.join(docs_folder, "docs", product_id)
                    )

                platforms = product_platforms[product_id]
                fm = parse_frontmatter(mdx_file)
                excluded = fm.get("excluded_platforms", [])
                platform_selector = fm.get("platform_selector", True)

                if not platforms and platform_selector:
                    platform_selector = False

                output_dir = os.path.join(output_base, os.path.dirname(rel_path))
                os.makedirs(output_dir, exist_ok=True)

                base_name = os.path.splitext(os.path.basename(mdx_file))[0]

                if not platform_selector:
                    output_file = os.path.join(output_dir, f"{base_name}.md")
                    processed_files += 1
                    if run_mdx2md(mdx_file, None, output_file, docs_folder, failed_exports):
                        successful_exports += 1
                else:
                    exported_platforms = []
                    successful_platforms = []
                    
                    for p in platforms:
                        if p in excluded:
                            print(f"  └─ Skipping {p} (excluded)")
                            continue
                        
                        output_file = os.path.join(output_dir, f"{base_name}_{p}.md")
                        processed_files += 1
                        exported_platforms.append(p)
                        
                        if run_mdx2md(mdx_file, p, output_file, docs_folder, failed_exports):
                            successful_exports += 1
                            successful_platforms.append(p)

                    if not args.skip_platform_index and len(successful_platforms) > 1:
                        if create_platform_index_file(mdx_file, successful_platforms, output_dir, base_name, docs_folder):
                            index_files_created += 1

        # Flush index for the final product after the walk completes
        flush_overview_index()

    write_error_log(failed_exports, output_base)

    print("-" * 60)
    print("📊 Export Summary:")
    print(f"   📄 Total exports attempted: {processed_files}")
    print(f"   ✅ Successful exports: {successful_exports}")
    print(f"   ❌ Failed exports: {len(failed_exports)}")
    if not args.process_help:
        print(f"   📑 Platform index files created: {index_files_created}")
        if inject_overview_index:
            print(f"   📋 Overview indexes injected: {overview_indexes_injected}")
    
    if failed_exports:
        print("\n❌ Failed Exports:")
        for error in failed_exports:
            platform_info = f" (platform: {error['platform']})" if error['platform'] else ""
            print(f"   • {os.path.basename(error['file'])}{platform_info}")
        
        print(f"\n📋 See export_errors.log in {output_base} for detailed error information")
        print("🔧 Common fixes:")
        print("   • Check if product/platform dictionaries are missing keys")
        print("   • Verify all imported .mdx files exist")
        print("   • Check for syntax errors in MDX files")
        print("   • Ensure all required assets/images are available")
    else:
        print("\n🎉 All exports completed successfully!")


if __name__ == "__main__":
    main()