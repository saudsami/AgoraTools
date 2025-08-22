import os
import re
import subprocess
import yaml
import argparse

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


def run_mdx2md(mdx_file, platform, output_file):
    """Run mdx2md.py for a given platform/output_file"""
    cmd = ["python", "mdx2md.py", "--mdxPath", mdx_file]
    if platform:
        cmd.extend(["--platform", platform])
    cmd.extend(["--output-file", output_file])
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


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
    args = parser.parse_args()

    docs_folder = os.path.abspath(args.docs_folder)
    output_base = os.path.abspath(args.output_dir)

    # products.js is always inside <Docs>/data/v2
    products_file = os.path.join(docs_folder, "data", "v2", "products.js")

    # start path is <Docs>/docs[/<subfolder>]
    start_path = os.path.join(docs_folder, "docs", args.start_folder)

    product_platforms = load_product_platforms(products_file)
    print(f"Loaded product → platforms mapping from {products_file}")

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
                run_mdx2md(mdx_file, None, output_file)
            else:
                # Export once per platform (except excluded)
                for p in platforms:
                    if p in excluded:
                        continue
                    output_file = os.path.join(output_dir, f"{base_name}_{p}.md")
                    run_mdx2md(mdx_file, p, output_file)


if __name__ == "__main__":
    main()
