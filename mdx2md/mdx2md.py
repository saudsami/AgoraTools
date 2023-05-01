import re #Regular expressions
import os #Operating system
import shutil #Copy images

platform = 'android'
product = 'video-calling'
# Relative to the 'docs' directory
inputRelPath = '/video-calling/get-started/get-started-sdk.mdx' 

#repoPath = 'C:/Users/saud/Git/AgoraDocsPrivate/Docs'
repoPath = 'C:/Git/AgoraDocs/PrivateDocs/Docs'
siteBaseUrl = "https://docs.agora.io/en"
docsPath = repoPath + "/docs"
assetsPath = docsPath + "/assets"
inputPath = docsPath + inputRelPath
inputDocDir = os.path.dirname(inputRelPath)

# '/video-calling/get-started/get-started-sdk.mdx'
# '/video-calling/develop/ensure-channel-quality.mdx' 
# '/shared/video-sdk/develop/ensure-channel-quality/project-implementation/android.mdx'
# '/shared/video-sdk/_get-started-sdk.mdx'
# '/shared/video-sdk/get-started/get-started-sdk/project-implementation/index.mdx'
# '/shared/video-sdk/get-started/get-started-sdk/project-implementation/android.mdx'

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

# Load the product/platform variables dictionary
def createDictionary(path):
    with open(path, 'r', encoding='utf-8') as f:
        data_file = f.read()

    # Extract the data from the file using regular expressions
    data_str = re.search(r'const data = {(.*?)};', data_file, re.DOTALL).group(1)
    data_str = '{' + data_str + '}'
    data_str = re.sub(r'([A-Z_]+):', r'"\1":', data_str)

    # Convert the data string to a dictionary
    data = eval(data_str)
    return data

# Use the product and platform dictionaries to resolve <Vpd> and <Vpl> tags
def resolve_local_variables(text, product, productDictionary, platform, platformDictionary):
    text = re.sub(r'<Vpd\s+k="(\w+)"\s*/>', lambda match: productDictionary[product].get(match.group(1), match.group(0)), text)
    text = re.sub(r'<Vpl\s+k="(\w+)"\s*/>', lambda match: platformDictionary[platform].get(match.group(1), match.group(0)), text)
    return text

# Recursively resolve import statements
def resolve_imports(mdxFilePath):
    base_dir = os.path.dirname(mdxFilePath)
    with open(rf'{mdxFilePath}', 'r', encoding='utf-8') as file:
        mdxFileContents = file.read()
        mdxFileContents = resolve_tags(mdxFileContents, 'PlatformWrapper', platform)
        mdxFileContents = resolve_tags(mdxFileContents, 'ProductWrapper', product)

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
        # Resolve PlatformWrapper and ProductWrapper tags
        tag_content = resolve_tags(tag_content, 'PlatformWrapper', platform)
        tag_content = resolve_tags(tag_content, 'ProductWrapper', product)

        rgx = r'<{}[\s\S]*?/>'.format(tag)
        mdxFileContents = re.sub(rgx, lambda match: tag_content, mdxFileContents)

    return mdxFileContents

# Resolves all ProductWrapper and PlatformWrapper tags keeps contents where 
# the attribute value is present in the opening tag and discards irrelevant content.
def resolve_tags(text, tagName, attributeValue):
    # pattern to match the <PlatformWrapper> block
    regex = r'^.*\<{}\s([\s\S]*?)>\n*([\s\S]*?)</{}>'.format(tagName, tagName)
    pattern = re.compile(regex, re.MULTILINE)

    # replace the matches based on platform value
    text = pattern.sub(lambda m: m.group(2) if attributeValue in m.group(1) else '', text)
    return text

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
        shutil.copyfile(assetsPath + match, f'./output/images/{filename}')
        # Update the path in the markdown file
        text = re.sub(match, f'./images/{filename}', text)

    return text

def resolve_link_tags(text):
    # Resolve <Link to="">name</Link> tags
    pattern = re.compile(r'<Link\s+to=\"\{\{(?:[Gg]lobal?|GLOBAL)\.*([^\"]+)}}([^\"]*)\"\s*>(.*?)</Link>')
    def replace(match):
        url_key = match.group(1)
        url = globalVariables.get(url_key)
        if url is None:
            raise ValueError(f"Unknown URL key: {url_key}")
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

        # Replace the link in the text
        text = text.replace(link, new_url)

    return text


# -----Main------

# Read the input file
with open(inputPath, 'r', encoding='utf-8') as file:
    contents = file.read()

# Load global variables into a dictionary
file_path = docsPath + '/shared/variables/global.js'
globalVariables = read_variables(file_path)

# Create product and platform dictionaries to resolve <Vpl> and <Vpd> tags
productDict = createDictionary(docsPath + '/shared/variables/product.js')
platformDict = createDictionary(docsPath + '/shared/variables/platform.js')

# Resolve import statements 
# Also resolves PlatformWrapper and ProductWrapper tags
mdxContents = resolve_imports(inputPath)

# Replace global variables <Vg k="KEY" /> using the dictionary
regex_pattern = r'<Vg\s+k\s*=\s*"(\w+)"\s*\/?>'
mdxContents = re.sub(regex_pattern, lambda match: globalVariables.get(match.group(1), match.group(0)), mdxContents)

# Replace product and platform variables <Vpd k="KEY" />, <Vpl k="KEY" />
mdxContents = resolve_local_variables(mdxContents, product, productDict, platform, platformDict)

# Process document header and add title
mdxContents = resolve_header(mdxContents)

# Remove extra line breaks
mdxContents = re.sub(r'\n([\s\t]*\n){3,}', r'\n\n', mdxContents)

# Copy images and update image links
mdxContents = resolve_images(mdxContents)

# Update hyperlinks
mdxContents = resolve_link_tags(mdxContents)
docFolder = os.path.dirname(inputPath)
mdxContents = resolve_hyperlinks(mdxContents, docFolder, siteBaseUrl)

# Write the modified contents to a new md file
if not os.path.exists('./output'):
    os.makedirs('./output')
outputFilename = os.path.basename(inputPath)
outputFilename = os.path.splitext(outputFilename)[0] + '.md'
with open('./output/' + outputFilename, 'w', encoding='utf-8') as file:
    file.write(mdxContents)
    