import json
import os
from algoliasearch.search_client import SearchClient

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

DOCCARCHIVE_DATA_PATH = config["doccarchive_data_path"]
BASE_URL = config["base_url"]
PRODUCT = config["product"]
PLATFORM = config["platform"]
VERSION = config["version"]
INDEX_NAME = config["index_name"]
ALGOLIA_APP_ID = config["algolia_app_id"]
ALGOLIA_ADMIN_API_KEY = config["algolia_admin_api_key"]


def tokens_to_text(tokens):
    return "".join(t.get("text", "") for t in tokens)


def extract_abstract(abstract_nodes):
    return " ".join(
        n.get("text", "") for n in abstract_nodes if n.get("type") == "text"
    ).strip()


def extract_declaration(primary_content_sections):
    for section in primary_content_sections:
        if section.get("kind") == "declarations":
            declarations = section.get("declarations", [])
            if declarations:
                tokens = declarations[0].get("tokens", [])
                return tokens_to_text(tokens)
    return ""


def extract_parent(hierarchy):
    paths = hierarchy.get("paths", [])
    if not paths or len(paths[0]) < 1:
        return ""
    # The last element in the path is the parent — the symbol itself is not included
    parent_identifier = paths[0][-1]
    return parent_identifier.split("/")[-1]


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return None

    # Skip non-symbol and collection pages
    if data.get("kind") != "symbol":
        return None
    metadata = data.get("metadata", {})
    if metadata.get("role") == "collection":
        return None

    # Extract URL path from variants
    variants = data.get("variants", [])
    if not variants:
        return None
    url_path = variants[0].get("paths", [None])[0]
    if not url_path:
        return None

    record = {
        "objectID": url_path.lstrip("/"),
        "title": metadata.get("title", ""),
        "symbol_kind": metadata.get("symbolKind", ""),
        "role_heading": metadata.get("roleHeading", ""),
        "abstract": extract_abstract(data.get("abstract", [])),
        "declaration": extract_declaration(data.get("primaryContentSections", [])),
        "parent": extract_parent(data.get("hierarchy", {})),
        "module": metadata.get("modules", [{}])[0].get("name", ""),
        "url": f"{BASE_URL}{url_path}",
        "product": PRODUCT,
        "platform": PLATFORM,
        "version": VERSION,
    }

    return record


def main():
    records = []
    skipped = 0

    for root, dirs, files in os.walk(DOCCARCHIVE_DATA_PATH):
        for filename in files:
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(root, filename)
            record = process_file(filepath)
            if record:
                records.append(record)
            else:
                skipped += 1

    print(f"Extracted {len(records)} records, skipped {skipped} files")

    # Upload to Algolia
    client = SearchClient.create(ALGOLIA_APP_ID, ALGOLIA_ADMIN_API_KEY)
    index = client.init_index(INDEX_NAME)

    # Configure index settings
    index.set_settings({
        "searchableAttributes": [
            "unordered(title)",
            "unordered(abstract)",
            "declaration",
        ],
        "attributesForFaceting": [
            "product",
            "platform",
            "version",
            "symbol_kind",
        ],
        "attributesToSnippet": [
            "abstract:20",
            "declaration:15",
        ],
        "camelCaseAttributes": ["title", "declaration"],
    })

    # Upload in batches
    index.replace_all_objects(records)
    print(f"Uploaded {len(records)} records to index '{INDEX_NAME}'")


if __name__ == "__main__":
    main()