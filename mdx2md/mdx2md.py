import re #Regular expressions
import os #Operating system
import shutil #Copy images
import argparse
import sys
import json

# Default value
platform = 'android'

# Create an ArgumentParser object
parser = argparse.ArgumentParser()
# Add named arguments
parser.add_argument('--platform', type=str, help='Target platform: android|electron|flutter|ios|macos|react-native|unity|web|windows')
parser.add_argument('--product', type=str, help='Agora product: video-calling|interactive-live-streaming|etc.')
parser.add_argument('--mdxPath', type=str, help='The absolute path to the mdx file')

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
    """
    
    # Keep processing until no more PlatformWrapper tags are found
    while '<PlatformWrapper' in text:
        # Pattern to match PlatformWrapper tags
        pattern = re.compile(
            r'<PlatformWrapper\s+([^>]*?)>(.*?)</PlatformWrapper>',
            re.MULTILINE | re.DOTALL
        )
        
        def process_wrapper(match):
            attributes = match.group(1)
            content = match.group(2)
            
            # Check for platform attribute
            platform_match = re.search(r'platform=["\']([^"\']+)["\']', attributes)
            notallowed_match = re.search(r'notAllowed=["\']([^"\']+)["\']', attributes)
            
            if platform_match:
                # Parse comma-separated or array-like values
                platforms_str = platform_match.group(1)
                # Handle array notation if present [flutter, android] -> flutter, android
                platforms_str = platforms_str.strip('[]').replace(' ', '')
                allowed_platforms = [p.strip() for p in platforms_str.split(',')]
                
                if platform in allowed_platforms:
                    return content  # Include content without wrapper
                else:
                    return ''  # Remove everything
                    
            elif notallowed_match:
                # Parse notAllowed platforms
                excluded_str = notallowed_match.group(1)
                excluded_str = excluded_str.strip('[]').replace(' ', '')
                excluded_platforms = [p.strip() for p in excluded_str.split(',')]
                
                if platform not in excluded_platforms:
                    return content  # Include content without wrapper
                else:
                    return ''  # Remove everything
                    
            else:
                # No recognized attributes, remove the wrapper
                return ''
        
        # Apply replacements
        new_text = pattern.sub(process_wrapper, text)
        
        # If no changes were made, break to avoid infinite loop
        if new_text == text:
            # Clean up any remaining unmatched closing tags
            text = re.sub(r'</PlatformWrapper>', '', text)
            break
            
        text = new_text
    
    # Final cleanup of any orphaned closing tags
    text = re.sub(r'</PlatformWrapper>', '', text)
    
    return text

# Similar function for ProductWrapper tags
def resolve_all_product_tags(text, product):
    """
    Resolve all ProductWrapper tags in the text for the given product.
    This handles both standard and notAllowed attributes.
    """
    
    # Keep processing until no more ProductWrapper tags are found
    while '<ProductWrapper' in text:
        # Pattern to match ProductWrapper tags
        pattern = re.compile(
            r'<ProductWrapper\s+([^>]*?)>(.*?)</ProductWrapper>',
            re.MULTILINE | re.DOTALL
        )
        
        def process_wrapper(match):
            attributes = match.group(1)
            content = match.group(2)
            
            # Check for product attribute
            product_match = re.search(r'product=["\']([^"\']+)["\']', attributes)
            notallowed_match = re.search(r'notAllowed=["\']([^"\']+)["\']', attributes)
            
            if product_match:
                # Parse comma-separated or array-like values
                products_str = product_match.group(1)
                # Handle array notation if present
                products_str = products_str.strip('[]').replace(' ', '')
                allowed_products = [p.strip() for p in products_str.split(',')]
                
                if product in allowed_products:
                    return content  # Include content without wrapper
                else:
                    return ''  # Remove everything
                    
            elif notallowed_match:
                # Parse notAllowed products
                excluded_str = notallowed_match.group(1)
                excluded_str = excluded_str.strip('[]').replace(' ', '')
                excluded_products = [p.strip() for p in excluded_str.split(',')]
                
                if product not in excluded_products:
                    return content  # Include content without wrapper
                else:
                    return ''  # Remove everything
                    
            else:
                # No recognized attributes, remove the wrapper
                return ''
        
        # Apply replacements
        new_text = pattern.sub(process_wrapper, text)
        
        # If no changes were made, break to avoid infinite loop
        if new_text == text:
            # Clean up any remaining unmatched closing tags
            text = re.sub(r'</ProductWrapper>', '', text)
            break
            
        text = new_text
    
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
    # Delete import statements
    mdxFileContents = re.sub(r'import\s+\*[\s\w]*from\s+\'[a-zA-Z0-9@/]*?\';' , "", mdxFileContents)    
    mdxFileContents = re.sub(r'import\s+(\w+?)\s+from\s+\'(.+?md[x]*)\';?\n*' , "", mdxFileContents)
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

def resolve_header(text):
    regex = r"^---\ntitle:\s*'(.*)'[\s\S]*?\n---$"
    replacement = r"# \1"

    new_text = re.sub(regex, replacement, text, flags=re.MULTILINE|re.DOTALL)
    new_text = re.sub(r'export\s+const\s+toc\s*=\s*\[\s*\{\s*\}\];', '', new_text)
    return new_text

def resolve_images(text):
    # Find all matches of the image link pattern
    matches = re.findall(r'!\[.*\]\((.+)\)', text)

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
        new_url= new_url.replace('//','/')

        # Replace the link in the text
        text = text.replace(link, new_url)

    return text

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

    # Write the modified contents to a new md file
    if not os.path.exists('./output'):
        os.makedirs('./output')
    outputFilename = os.path.basename(mdxPath)
    outputFilename = os.path.splitext(outputFilename)[0] + '.md'
    with open('./output/' + outputFilename, 'w', encoding='utf-8') as file:
        file.write(mdxContents)
    
    print(f"Successfully converted {outputFilename}")
    
except Exception as e:
    print(f"Error processing file: {e}")
    sys.exit(-3)