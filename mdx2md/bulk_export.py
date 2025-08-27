import os
import re
import subprocess
import yaml
import argparse
from datetime import datetime

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


def run_mdx2md(mdx_file, platform, output_file, docs_folder):
    """Run mdx2md.py for a given platform/output_file"""
    cmd = ["python", "mdx2md.py", "--mdxPath", mdx_file]
    if platform:
        cmd.extend(["--platform", platform])
    cmd.extend(["--output-file", output_file])
    cmd.extend(["--docs-folder", docs_folder])  # Pass the docs folder
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def create_platform_index_file(mdx_file, platforms, output_dir, base_name, docs_folder):
    """
    Create a platform index file that links to all platform-specific versions.
    """
    try:
        # Parse frontmatter from original MDX file
        fm = parse_frontmatter(mdx_file)
        title = fm.get('title', 'Documentation')
        description = fm.get('description', '')
        sidebar_position = fm.get('sidebar_position')
        
        # Create frontmatter for index
        index_frontmatter = {
            'title': title,
            'platform_selector': False,
            'exported_from': get_exported_from_url(mdx_file, docs_folder),
            'exported_on': datetime.utcnow().isoformat() + 'Z',
            'exported_file': f'{base_name}.md'
        }
        
        if description:
            index_frontmatter['description'] = description
        if sidebar_position is not None:
            index_frontmatter['sidebar_position'] = sidebar_position
        
        # Create platform index content
        frontmatter_yaml = yaml.safe_dump(index_frontmatter, sort_keys=False).strip()
        
        index_content = f"""---
{frontmatter_yaml}
---

# {title}

Select your platform:

"""
        
        # Add platform links
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
        
        # Write the index file
        index_file_path = os.path.join(output_dir, f"{base_name}.md")
        with open(index_file_path, 'w', encoding='utf-8') as f:
            f.write(index_content)
        
        print(f"✅ Created platform index: {index_file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating platform index for {mdx_file}: {e}")
        return False


def get_exported_from_url(mdx_file, docs_folder):
    """Generate the exported_from URL for the original MDX file"""
    # Get relative path from docs folder
    docs_path = os.path.join(docs_folder, "docs")
    rel_path = os.path.relpath(mdx_file, docs_path)
    normalized_path = rel_path.replace(os.sep, "/")
    return f"https://docs.agora.io/en/{normalized_path}"


# --- Main ---
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
    args = parser.parse_args()

    docs_folder = os.path.abspath(args.docs_folder)
    output_base = os.path.abspath(args.output_dir)

    # products.js is always inside <Docs>/data/v2
    products_file = os.path.join(docs_folder, "data", "v2", "products.js")

    # start path is <Docs>/docs[/<subfolder>]
    start_path = os.path.join(docs_folder, "docs", args.start_folder)

    product_platforms = load_product_platforms(products_file)
    print(f"Loaded product → platforms mapping from {products_file}")
    print(f"Starting export from: {start_path}")
    print(f"Output directory: {output_base}")
    print(f"Platform index creation: {'Disabled' if args.skip_platform_index else 'Enabled'}")
    print("-" * 60)

    processed_files = 0
    index_files_created = 0

    for root, _, files in os.walk(start_path):
        for filename in files:
            if not filename.endswith(".mdx"):
                continue

            mdx_file = os.path.join(root, filename)
            if should_skip(mdx_file):
                continue

            # Derive productId from path (first folder after docs/)
            rel_path = os.path.relpath(mdx_file, os.path.join(docs_folder, "docs"))
            parts = rel_path.replace("\\", "/").split("/")
            product_id = parts[0]

            if product_id not in product_platforms:
                print(f"⚠️ Skipping {mdx_file}, no product mapping")
                continue

            platforms = product_platforms[product_id]

            # Parse frontmatter
            fm = parse_frontmatter(mdx_file)
            excluded = fm.get("excluded_platforms", [])
            platform_selector = fm.get("platform_selector", True)

            # Build output folder structure under output_base
            output_dir = os.path.join(output_base, os.path.dirname(rel_path))
            os.makedirs(output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(mdx_file))[0]

            if not platform_selector:
                # Single export only
                output_file = os.path.join(output_dir, f"{base_name}.md")
                run_mdx2md(mdx_file, None, output_file, docs_folder)
                processed_files += 1
            else:
                # Export once per platform (except excluded)
                exported_platforms = []
                for p in platforms:
                    if p in excluded:
                        print(f"  └─ Skipping {p} (excluded)")
                        continue
                    output_file = os.path.join(output_dir, f"{base_name}_{p}.md")
                    run_mdx2md(mdx_file, p, output_file, docs_folder)
                    exported_platforms.append(p)
                    processed_files += 1

                # Create platform index file if multiple platforms were exported
                if not args.skip_platform_index and len(exported_platforms) > 1:
                    if create_platform_index_file(mdx_file, exported_platforms, output_dir, base_name, docs_folder):
                        index_files_created += 1

    print("-" * 60)
    print(f"✅ Export completed!")
    print(f"   📄 Processed files: {processed_files}")
    print(f"   📑 Platform index files created: {index_files_created}")


if __name__ == "__main__":
    main()