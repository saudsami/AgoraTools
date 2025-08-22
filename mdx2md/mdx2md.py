import re #Regular expressions
import os #Operating system
import shutil #Copy images
import argparse
import sys
import json
import yaml
from datetime import datetime

# Default value
platform = 'android'

# Create an ArgumentParser object
parser = argparse.ArgumentParser()
# Add named arguments
parser.add_argument('--platform', type=str, help='Target platform: android|electron|flutter|ios|macos|react-native|unity|web|windows')
parser.add_argument('--product', type=str, help='Agora product: video-calling|interactive-live-streaming|etc.')
parser.add_argument('--mdxPath', type=str, help='The absolute path to the mdx file')
parser.add_argument('--output-file', type=str, help='Explicit output filename (including .md)')

# Access the values of the named arguments
args = parser.parse_args()
platform = args.platform if args.platform is not None else platform
product = args.product
mdxPath = args.mdxPath

# Get the Docs repository path
if mdxPath is None:
    print('usage: mdx2md.py [-h] [--platform PLATFORM] [--product PRODUCT] [--mdxPath MDXPATH]')
    sys.exit(-1)
docs_index = mdxPath.find(os.path.sep + 'docs')
if docs_index >= 0:
    repoPath = mdxPath[:docs_index]
else:
    print('Invalid mdx path!')
    sys.exit(-2)

siteBaseUrl = "https://docs.agora.io/en"
docsPath = repoPath + "/docs"
assetsPath = docsPath + "/assets"

if product is None:
    # Get the product name from the path
    dirname = os.path.dirname(mdxPath)
    # Split the directory path into parts
    parts = dirname.split(os.path.sep)
    # Find the index of the "docs" folder
    docs_index = parts.index("docs")
    # product name is the name of the docs sub-folder
    product = parts[docs_index + 1]

# ----- Helper functions -------

# Functions to recursively resolve variables in global.js to create a dictionary
def read_variables(file_path):
    variables = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = re.match(r'export const (\w+)\s*=\s*(.+?)(?:;|$)', line)
            if match:
                variable_name, variable_value = match.groups()
                variables[variable_name] = variable_value.strip().strip("'\"`")
    return resolve_variables(variables)

def resolve_variables(variables):
    resolved_variables = {}
    for variable_name, variable_value in variables.items():
        resolved_value = resolve_value(variable_value, variables)
        resolved_variables[variable_name] = resolved_value
    return resolved_variables

def resolve_value(value, variables):
    match = re.search(r'\$\{(\w+)\}', value)
    while match:
        variable_name = match.group(1)
        variable_value = variables.get(variable_name, '')
        value = value.replace(f'${{{variable_name}}}', variable_value)
        match = re.search(r'\$\{(\w+)\}', value)
    return value

# Improved createDictionary function that handles JavaScript comments
def createDictionary(path):
    with open(path, 'r', encoding='utf-8') as f:
        data_file = f.read()

    # Extract the data from the file using regular expressions
    data_str = re.search(r'const data = {(.*?)};', data_file, re.DOTALL).group(1)
    data_str = '{' + data_str + '}'
    
    # Remove JavaScript comments before processing
    # Remove single-line comments (//)
    data_str = re.sub(r'//.*?$', '', data_str, flags=re.MULTILINE)
    # Remove multi-line comments (/* */)
    data_str = re.sub(r'/\*.*?\*/', '', data_str, flags=re.DOTALL)
    
    # Add quotes around keys (unquoted keys)
    data_str = re.sub(r'([A-Z_]+):', r'"\1":', data_str)
    
    # Convert single quotes to double quotes for JSON compatibility
    data_str = data_str.replace("'", '"')
    
    # Handle trailing commas (JSON doesn't allow them)
    data_str = re.sub(r',\s*}', '}', data_str)
    data_str = re.sub(r',\s*]', ']', data_str)
    
    try:
        # Parse as JSON (safer than eval)
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"Error parsing data from {path}: {e}")
        print(f"Problematic string portion: {data_str[max(0, e.pos-50):min(len(data_str), e.pos+50)]}")
        # Fallback to eval if JSON parsing fails (less safe but more flexible)
        try:
            import ast
            data = ast.literal_eval(data_str)
        except (ValueError, SyntaxError) as eval_error:
            print(f"Also failed with ast.literal_eval: {eval_error}")
            raise
    
    return data

# Use the product and platform dictionaries to resolve <Vpd> and <Vpl> tags
def resolve_local_variables(text, product, productDictionary, platform, platformDictionary):
    text = re.sub(r'<Vpd\s+k="(\w+)"\s*/>', lambda match: productDictionary[product].get(match.group(1), match.group(0)), text)
    text = re.sub(r'<Vpl\s+k="(\w+)"\s*/>', lambda match: platformDictionary[platform].get(match.group(1), match.group(0)), text)
    return text

# New comprehensive platform tag resolver
def resolve_all_platform_tags(text, platform):
    """
    Resolve all PlatformWrapper tags in the text for the given platform.
    This handles both standard and notAllowed attributes.
    Properly handles nested PlatformWrapper tags.
    """
    
    # Keep processing until no more PlatformWrapper tags are found
    max_iterations = 100  # Prevent infinite loops
    iteration = 0
    
    while '<PlatformWrapper' in text and iteration < max_iterations:
        iteration += 1
        
        # Find the first opening PlatformWrapper tag
        start_match = re.search(r'<PlatformWrapper\s+([^>]*?)>', text)
        if not start_match:
            break
            
        start_pos = start_match.start()
        end_pos = start_match.end()
        attributes = start_match.group(1)
        
        # Now find the matching closing tag, accounting for nested tags
        depth = 1
        search_pos = end_pos
        
        while depth > 0 and search_pos < len(text):
            # Look for the next opening or closing tag
            opening = text.find('<PlatformWrapper', search_pos)
            closing = text.find('</PlatformWrapper>', search_pos)
            
            if closing == -1:
                # No closing tag found, malformed structure
                print(f"Warning: Unclosed PlatformWrapper tag found")
                text = text[:start_pos] + text[end_pos:]
                break
            
            if opening != -1 and opening < closing:
                # Found another opening tag before the closing tag (nested)
                depth += 1
                search_pos = opening + 1
            else:
                # Found a closing tag
                depth -= 1
                if depth == 0:
                    # This is our matching closing tag
                    closing_end = closing + len('</PlatformWrapper>')
                    content = text[end_pos:closing]
                    
                    # Determine if we should include this content
                    platform_match = re.search(r'platform\s*=\s*["\']([^"\']+)["\']', attributes)
                    notallowed_match = re.search(r'notAllowed\s*=\s*["\']([^"\']+)["\']', attributes)
                    
                    include_content = False
                    
                    if platform_match:
                        platforms_str = platform_match.group(1)
                        platforms_str = platforms_str.strip('[]').replace(' ', '')
                        allowed_platforms = [p.strip() for p in platforms_str.split(',')]
                        include_content = platform in allowed_platforms
                    elif notallowed_match:
                        excluded_str = notallowed_match.group(1)
                        excluded_str = excluded_str.strip('[]').replace(' ', '')
                        excluded_platforms = [p.strip() for p in excluded_str.split(',')]
                        include_content = platform not in excluded_platforms
                    
                    # Replace the entire wrapper with content or nothing
                    if include_content:
                        # Process nested PlatformWrapper tags in the content first
                        content = resolve_all_platform_tags(content, platform)
                        text = text[:start_pos] + content + text[closing_end:]
                    else:
                        text = text[:start_pos] + text[closing_end:]
                    
                    break
                else:
                    search_pos = closing + 1
    
    # Final cleanup of any orphaned closing tags
    text = re.sub(r'</PlatformWrapper>', '', text)
    
    return text

# Similar function for ProductWrapper tags
def resolve_all_product_tags(text, product):
    """
    Resolve all ProductWrapper tags in the text for the given product.
    This handles both standard and notAllowed attributes.
    Properly handles nested ProductWrapper tags.
    """
    
    # Keep processing until no more ProductWrapper tags are found
    max_iterations = 100  # Prevent infinite loops
    iteration = 0
    
    while '<ProductWrapper' in text and iteration < max_iterations:
        iteration += 1
        
        # Find the first opening ProductWrapper tag
        start_match = re.search(r'<ProductWrapper\s+([^>]*?)>', text)
        if not start_match:
            break
            
        start_pos = start_match.start()
        end_pos = start_match.end()
        attributes = start_match.group(1)
        
        # Now find the matching closing tag, accounting for nested tags
        depth = 1
        search_pos = end_pos
        
        while depth > 0 and search_pos < len(text):
            # Look for the next opening or closing tag
            opening = text.find('<ProductWrapper', search_pos)
            closing = text.find('</ProductWrapper>', search_pos)
            
            if closing == -1:
                # No closing tag found, malformed structure
                print(f"Warning: Unclosed ProductWrapper tag found")
                text = text[:start_pos] + text[end_pos:]
                break
            
            if opening != -1 and opening < closing:
                # Found another opening tag before the closing tag (nested)
                depth += 1
                search_pos = opening + 1
            else:
                # Found a closing tag
                depth -= 1
                if depth == 0:
                    # This is our matching closing tag
                    closing_end = closing + len('</ProductWrapper>')
                    content = text[end_pos:closing]
                    
                    # Determine if we should include this content
                    product_match = re.search(r'product\s*=\s*["\']([^"\']+)["\']', attributes)
                    notallowed_match = re.search(r'notAllowed\s*=\s*["\']([^"\']+)["\']', attributes)
                    
                    include_content = False
                    
                    if product_match:
                        products_str = product_match.group(1)
                        products_str = products_str.strip('[]').replace(' ', '')
                        allowed_products = [p.strip() for p in products_str.split(',')]
                        include_content = product in allowed_products
                    elif notallowed_match:
                        excluded_str = notallowed_match.group(1)
                        excluded_str = excluded_str.strip('[]').replace(' ', '')
                        excluded_products = [p.strip() for p in excluded_str.split(',')]
                        include_content = product not in excluded_products
                    
                    # Replace the entire wrapper with content or nothing
                    if include_content:
                        # Process nested ProductWrapper tags in the content first
                        content = resolve_all_product_tags(content, product)
                        text = text[:start_pos] + content + text[closing_end:]
                    else:
                        text = text[:start_pos] + text[closing_end:]
                    
                    break
                else:
                    search_pos = closing + 1
    
    # Final cleanup of any orphaned closing tags
    text = re.sub(r'</ProductWrapper>', '', text)
    
    return text

# Recursively resolve import statements
def resolve_imports(mdxFilePath):
    base_dir = os.path.dirname(mdxFilePath)
    with open(rf'{mdxFilePath}', 'r', encoding='utf-8') as file:
        mdxFileContents = file.read()
        # Use the new comprehensive tag resolvers
        mdxFileContents = resolve_all_platform_tags(mdxFileContents, platform)
        mdxFileContents = resolve_all_product_tags(mdxFileContents, product)

    # Read the import statements
    matches = re.findall(r'import\s+(\w+?)\s+from\s+\'(.+?md[x]*)\';?\n*', mdxFileContents)
    if not matches:
        return mdxFileContents
    
    # Delete import statements (consolidated into one pattern)
    import_pattern = r'import\s+(?:\*[\s\w]*|\w+?)\s+from\s+\'[^\']+\';?\n*'
    mdxFileContents = re.sub(import_pattern, '', mdxFileContents)
    
    # Replace tags with file content
    for tag, filepath in matches:
        filepath = filepath.replace('@docs', docsPath)
        if '/data/variables' in filepath:
            continue
        if not os.path.isabs(filepath):
            filepath = os.path.abspath(os.path.join(base_dir, filepath))

        tag_content = resolve_imports(filepath)
        # Resolve PlatformWrapper and ProductWrapper tags using new functions
        tag_content = resolve_all_platform_tags(tag_content, platform)
        tag_content = resolve_all_product_tags(tag_content, product)

        rgx = r'<{}[\s\S]*?/>'.format(tag)
        mdxFileContents = re.sub(rgx, lambda match: tag_content, mdxFileContents)

    return mdxFileContents

def resolve_header(content):
    """
    - Removes 'export const ...' blocks
    - Adds '# title' heading at the top if frontmatter has a title
    """
    # Remove export statements
    content = re.sub(r"^export\s+const\s+.*$", "", content, flags=re.MULTILINE).strip()

    # Check for frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if fm_match:
        fm_dict = yaml.safe_load(fm_match.group(1)) or {}
        body = content[fm_match.end():]
    else:
        fm_dict = {}
        body = content

    # Add heading if title exists
    if "title" in fm_dict:
        heading = f"# {fm_dict['title']}\n\n"
        if not body.startswith("# "):  # avoid duplicate heading
            body = heading + body

    return content[:fm_match.end()] + body if fm_match else body

def resolve_tabs(text):
    """
    Convert Tabs and TabItem components to markdown format.
    <Tabs>
      <TabItem value="..." label="Header">Content</TabItem>
    </Tabs>
    becomes:
    **Header**
    Content
    """
    
    # Keep processing until no more Tabs blocks are found
    while '<Tabs' in text:
        # Pattern to match the entire Tabs block including all TabItems
        tabs_pattern = re.compile(
            r'<Tabs[^>]*?>(.*?)</Tabs>',
            re.MULTILINE | re.DOTALL
        )
        
        match = tabs_pattern.search(text)
        if not match:
            # No complete Tabs block found, break
            break
            
        tabs_content = match.group(1)
        
        # Pattern to match individual TabItem components
        tabitem_pattern = re.compile(
            r'<TabItem\s+([^>]*?)>(.*?)</TabItem>',
            re.MULTILINE | re.DOTALL
        )
        
        # Extract all TabItems
        tabitems = tabitem_pattern.findall(tabs_content)
        
        # Convert each TabItem to markdown
        result = []
        for attributes, content in tabitems:
            # Extract value and label from attributes
            value_match = re.search(r'value\s*=\s*["\']([^"\']*)["\']', attributes)
            label_match = re.search(r'label\s*=\s*["\']([^"\']*)["\']', attributes)
            
            value = value_match.group(1) if value_match else None
            label = label_match.group(1) if label_match else None
            
            # Use label as header, fallback to value if label is empty, then to 'Tab'
            header = label if label else (value if value else 'Tab')
            
            # Add header as bold text
            result.append(f'**{header}**')
            # Add the content (strip leading/trailing whitespace)
            result.append(content.strip())
            result.append('')  # Add empty line for spacing
        
        # Create replacement text
        replacement = '\n'.join(result).rstrip() + '\n' if result else ''
        
        # Replace the entire matched Tabs block with the markdown version
        text = text[:match.start()] + replacement + text[match.end():]
    
    # Clean up any orphaned TabItem tags that aren't inside Tabs blocks
    # These might be left over from incomplete structures or parsing errors
    
    # Remove standalone TabItem opening and closing tags
    text = re.sub(r'<TabItem\s+[^>]*?>', '', text)
    text = re.sub(r'</TabItem>', '', text)
    
    # Remove any remaining Tabs tags (opening or closing)
    text = re.sub(r'<Tabs[^>]*?>', '', text)
    text = re.sub(r'</Tabs>', '', text)
    
    return text

def resolve_details(text):
    """
    Convert HTML details/summary tags to markdown format.
    <details>
      <summary>Summary text</summary>
      Content
    </details>
    becomes:
    **Summary text**
    
    Content
    """
    
    # Pattern to match details blocks with summary
    details_pattern = re.compile(
        r'<details[^>]*?>\s*<summary[^>]*?>(.*?)</summary>(.*?)</details>',
        re.MULTILINE | re.DOTALL
    )
    
    def process_details(match):
        summary_text = match.group(1).strip()
        content = match.group(2).strip()
        
        # Create markdown replacement
        result = f'**{summary_text}**\n\n{content}'
        return result
    
    # Replace all details blocks
    text = details_pattern.sub(process_details, text)
    
    # Clean up any orphaned details or summary tags
    text = re.sub(r'<details[^>]*?>', '', text)
    text = re.sub(r'</details>', '', text)
    text = re.sub(r'<summary[^>]*?>', '', text)
    text = re.sub(r'</summary>', '', text)
    
    return text

def resolve_admonitions(text):
    """
    Convert Admonition components to markdown blockquote format.
    <Admonition type="info" title="Custom Title">
      Content
    </Admonition>
    becomes:
    > ℹ️ **Custom Title**
    > Content
    
    or if no title:
    > ℹ️ **Info**
    > Content
    """
    
    # Map admonition types to emojis and default titles
    admonition_types = {
        'note': ('📝', 'Note'),
        'tip': ('💡', 'Tip'),
        'info': ('ℹ️', 'Info'),
        'caution': ('⚠️', 'Caution'),
        'warning': ('⚠️', 'Warning'),
        'danger': ('🚨', 'Danger'),
        'important': ('❗', 'Important'),
        'success': ('✅', 'Success'),
    }
    
    # Pattern to match Admonition blocks
    admonition_pattern = re.compile(
        r'<Admonition\s+([^>]*?)>(.*?)</Admonition>',
        re.MULTILINE | re.DOTALL
    )
    
    def process_admonition(match):
        attributes = match.group(1)
        content = match.group(2).strip()
        
        # Extract type and title attributes
        type_match = re.search(r'type\s*=\s*["\']([^"\']*)["\']', attributes)
        title_match = re.search(r'title\s*=\s*["\']([^"\']*)["\']', attributes)
        
        admonition_type = type_match.group(1).lower() if type_match else 'note'
        custom_title = title_match.group(1) if title_match else None
        
        # Get emoji and default title for the type
        emoji, default_title = admonition_types.get(admonition_type, ('📝', 'Note'))
        
        # Use custom title if provided, otherwise use default
        title = custom_title if custom_title else default_title
        
        # Create markdown blockquote format
        # Split content into lines and add > prefix to each
        lines = content.split('\n')
        quoted_lines = [f'> {line}' if line.strip() else '>' for line in lines]
        
        # Add the title line with emoji
        result = f'> {emoji} **{title}**\n' + '\n'.join(quoted_lines)
        
        return result
    
    # Replace all Admonition blocks
    text = admonition_pattern.sub(process_admonition, text)
    
    return text

def remove_imports_outside_codeblocks(text):
    """
    Remove import statements that are outside of code blocks.
    Code blocks can be triple backticks (```) or <CodeBlock> tags.
    """
    
    # Store all code blocks with their positions
    protected_regions = []
    
    # Find all triple backtick code blocks
    for match in re.finditer(r'```[\s\S]*?```', text):
        protected_regions.append((match.start(), match.end()))
    
    # Find all CodeBlock tags
    for match in re.finditer(r'<CodeBlock[\s\S]*?</CodeBlock>', text):
        protected_regions.append((match.start(), match.end()))
    
    # Sort regions by start position
    protected_regions.sort()
    
    # Function to check if a position is inside a protected region
    def is_protected(pos):
        for start, end in protected_regions:
            if start <= pos < end:
                return True
        return False
    
    # Find and remove import statements that are not in protected regions
    lines = text.split('\n')
    result_lines = []
    current_pos = 0
    
    for line in lines:
        line_start = current_pos
        
        # Check if this line contains an import statement
        import_match = re.match(r'^\s*import\s+.*?\s+from\s+[\'"].*?[\'"];?\s*$', line)
        
        # If it's an import and not in a protected region, skip it
        if import_match and not is_protected(line_start):
            pass  # Skip this line
        else:
            result_lines.append(line)
        
        current_pos += len(line) + 1  # +1 for the newline character
    
    return '\n'.join(result_lines)

def resolve_images(text):
    # Find all matches of the image link pattern
    matches = re.findall(r'!\[.*?\]\((.+?)\)', text)

    if matches:
        # create the images directory if it doesn't exist
        if not os.path.exists('./output/images'):
            os.makedirs('./output/images')

    # Copy each image to the ./images folder and update the paths
    for match in matches:
        if match.startswith('http') or match.startswith('https'):
            continue
        # Get the filename from the path
        filename = match.split('/')[-1]
        # Copy the file to the ./images folder
        try:
            shutil.copyfile(assetsPath + match, f'./output/images/{filename}')
            # Update the path in the markdown file
            text = re.sub(re.escape(match), f'./images/{filename}', text)
        except FileNotFoundError:
            print(f"Warning: Image file not found: {assetsPath + match}")

    return text

def resolve_link_tags(text):
    # Resolve <Link to="">name</Link> tags
    pattern = re.compile(r'<Link\s+to=\"\{\{(?:[Gg]lobal?|GLOBAL)\.*([^\"]+)}}([^\"]*)\"\s*>(.*?)</Link>')
    def replace(match):
        url_key = match.group(1)
        url = globalVariables.get(url_key)
        if url is None:
            print(f"Warning: Unknown URL key: {url_key}")
            return match.group(0)  # Return original if key not found
        link = match.group(2)
        name = match.group(3)
        return f'<a href="{url}{link}">{name}</a>'

    return pattern.sub(replace, text)

def resolve_hyperlinks(text, base_folder, http_url):
    # Find all links in the text
    pattern = r'(?<!\!)\[.*?\]\((.*?)\)'
    links = re.findall(pattern, text)

    # Loop through the links and resolve them
    for link in links:
        # Skip links that start with "http" or "https"
        if link.startswith('http') or link.startswith('#'):
            continue
        elif link.startswith('.'):
            # Resolve relative links with respect to the base folder
            resolved_link = os.path.abspath(os.path.join(base_folder, link))
            rel_path = os.path.relpath(resolved_link, docsPath)
        else: 
            # Resolve links with respect to the docs 'folder'
            rel_path = link

        # Create the new URL by adding the HTTP prefix
        new_url = '{}/{}'.format(http_url, rel_path.replace('\\','/'))
        new_url = new_url.replace('//','/')

        # Replace the link in the text
        text = text.replace(link, new_url)

    return text

def resolve_codeblocks(text):
    """
    Convert CodeBlock components to markdown code blocks.
    Handles both:
    <CodeBlock language="dart">{`code here`}</CodeBlock>
    and
    <CodeBlock language="dart">code here</CodeBlock>


    Output:
    ```dart
    code here
    ```
    """


    # Pattern for {`code`} style
    codeblock_pattern_wrapped = re.compile(
    r'<CodeBlock\s+([^>]*?)>\s*\{`(.*?)`}\s*</CodeBlock>',
    re.MULTILINE | re.DOTALL
    )


    # Pattern for raw code style (no {` `})
    codeblock_pattern_raw = re.compile(
    r'<CodeBlock\s*([^>]*?)>(.*?)</CodeBlock>',
    re.MULTILINE | re.DOTALL
    )


    def process_codeblock(attributes, code_content):
        # Extract language
        language_match = re.search(r'language\s*=\s*["\']([^"\']*)["\']', attributes)
        language = language_match.group(1) if language_match else ''


        # Unescape characters if wrapped
        code_content = code_content.replace('\\\\', '\\')
        code_content = code_content.replace('\\n', '\n')
        code_content = code_content.replace('\\t', '\t')
        code_content = code_content.replace('\\r', '\r')
        code_content = code_content.replace('\\"', '"')
        code_content = code_content.replace("\\'", "'")
        code_content = code_content.replace('\\`', '`')

        return f'```{language}\n{code_content.strip()}\n```'

    # First handle wrapped {` `}
    text = codeblock_pattern_wrapped.sub(lambda m: process_codeblock(m.group(1), m.group(2)), text)


    # Then handle raw blocks
    text = codeblock_pattern_raw.sub(lambda m: process_codeblock(m.group(1), m.group(2)), text)

    return text

def add_frontmatter(content, source_file, platform="flutter", output_file=None):
    """
    Keeps original frontmatter (title, description, sidebar_position, etc.),
    and appends/updates platform, exported_from, and exported_on.
    """
    filename = os.path.basename(source_file)
    exported_from = f"https://docs.agora.io/en/video-calling/get-started/{filename}?platform={platform}"
    exported_on = datetime.utcnow().isoformat() + "Z"

    # Match existing frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", content, re.DOTALL)
    if fm_match:
        original_fm = fm_match.group(1)
        body = content[fm_match.end():]
        fm_dict = yaml.safe_load(original_fm) or {}
    else:
        fm_dict = {}
        body = content

    # Update/add required fields
    fm_dict["platform"] = platform
    fm_dict["exported_from"] = exported_from
    fm_dict["exported_on"] = exported_on
    if output_file:
        fm_dict["exported_file"] = os.path.basename(output_file)

    # Preserve key order
    ordered_keys = ["title", "description", "sidebar_position"]
    new_fm = {}
    for key in ordered_keys:
        if key in fm_dict:
            new_fm[key] = fm_dict.pop(key)
    new_fm.update(fm_dict)

    new_frontmatter = "---\n" + yaml.safe_dump(new_fm, sort_keys=False).strip() + "\n---\n\n"
    return new_frontmatter + body

# -----Main------

try:
    # Read the input file
    with open(mdxPath, 'r', encoding='utf-8') as file:
        contents = file.read()

    # Load global variables into a dictionary
    file_path = docsPath + '/shared/variables/global.js'
    globalVariables = read_variables(file_path)

    # Create product and platform dictionaries to resolve <Vpl> and <Vpd> tags
    productDict = createDictionary(docsPath + '/shared/variables/product.js')
    platformDict = createDictionary(docsPath + '/shared/variables/platform.js')

    # Resolve import statements 
    # Also resolves PlatformWrapper and ProductWrapper tags
    mdxContents = resolve_imports(mdxPath)

    # Replace global variables <Vg k="KEY" /> using the dictionary
    regex_pattern = r'<Vg\s+k\s*=\s*"(\w+)"\s*\/?>'
    mdxContents = re.sub(regex_pattern, lambda match: globalVariables.get(match.group(1), match.group(0)), mdxContents)

    # Replace product and platform variables <Vpd k="KEY" />, <Vpl k="KEY" />
    mdxContents = resolve_local_variables(mdxContents, product, productDict, platform, platformDict)

    # Process document header and add title
    mdxContents = resolve_header(mdxContents)

    # Resolve Tabs components to markdown
    mdxContents = resolve_tabs(mdxContents)
    
    # Resolve details/summary components to markdown
    mdxContents = resolve_details(mdxContents)
    
    # Resolve Admonition components to markdown blockquotes
    mdxContents = resolve_admonitions(mdxContents)

    # Resolve CodeBlock components to markdown fenced code blocks
    mdxContents = resolve_codeblocks(mdxContents)

    # Remove import statements that are outside code blocks
    mdxContents = remove_imports_outside_codeblocks(mdxContents)

    # Apply final cleanup of platform and product tags (in case any were missed)
    mdxContents = resolve_all_platform_tags(mdxContents, platform)
    mdxContents = resolve_all_product_tags(mdxContents, product)

    # Remove extra line breaks
    mdxContents = re.sub(r'\n([\s\t]*\n){3,}', r'\n\n', mdxContents)

    # Copy images and update image links
    mdxContents = resolve_images(mdxContents)

    # Update hyperlinks
    mdxContents = resolve_link_tags(mdxContents)
    docFolder = os.path.dirname(mdxPath)
    mdxContents = resolve_hyperlinks(mdxContents, docFolder, siteBaseUrl)

    # Add frontmatter
    mdxContents = add_frontmatter(mdxContents, mdxPath, platform=platform, output_file=args.output_file)

    # Write the modified contents to a new md file
    if args.output_file:
        # Use exactly what the user provided
        output_path = args.output_file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    else:
        if not os.path.exists('./output'):
            os.makedirs('./output')

        base_name = os.path.splitext(os.path.basename(mdxPath))[0]
        # Append platform unless explicitly disabled in frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", mdxContents, re.DOTALL)
        if fm_match:
            fm_dict = yaml.safe_load(fm_match.group(1)) or {}
            platform_selector = fm_dict.get("platform_selector", True)
        else:
            platform_selector = True

        if platform_selector and platform:
            outputFilename = f"{base_name}_{platform}.md"
        else:
            outputFilename = f"{base_name}.md"

        output_path = os.path.join('./output', outputFilename)

    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(mdxContents)

    print(f"Successfully converted {output_path}")
    
except Exception as e:
    print(f"Error processing file: {e}")
    sys.exit(-3)