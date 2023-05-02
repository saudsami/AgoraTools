# `mdx` to Markdown

`mdx2md.py` is a Python script that converts an mdx document in the Agora docs repository to a single markdown `.md` file by resolving all its dependencies. When you run the script, it does the following:

* Loads global variables into a dictionary
* Creates product and platform dictionaries to resolve `<Vpl>` and `<Vpd>` tags
* Reads the mdx file and recursively resolves all the import statements 
* Resolves `<PlatformWrapper>` tags to filter content for the selected platform
* Resolves `<ProductWrapper>` tags to filter content for the selected product
* Replaces global variables `<Vg k="KEY" />` with values 
* Replaces product `<Vpd k="KEY" />` and platform `<Vpl k="KEY" />` variables, with corresponding values
* Processes the document header to add the document title
* Removes extra line breaks
* Copies images from the repository to the `./images` folder and updates image links
* Converts `<Link></Link>` tags to markdown links
* Updates the relative path in markdown links to Agora docs urls
* Writes the modified contents to a new `.md` file

## Prerequisites
To run the `mdx2md` Python script you must have: 

* Installed [Python](https://www.python.org/downloads/)
* Cloned the [Agora Docs Github repository](https://github.com/AgoraIO/Docs) and its submodules


## Setup

Execute the following command to clone the AgoraTools repository:

```bash
git clone https://github.com/saudsami/AgoraTools
```

## Run the script

Take the following steps:

1. Update the `repoPath` to point to the `Docs` directory in the cloned repository. 
    For example, 
    
    ```
    repoPath = 'C:/Users/saud/Git/AgoraDocsPrivate/Docs'
    ```

1. Open the output folder. The markdown file has the same name as the input `.mdx` file with a `.md` extension. The `images` folder contains copies of all the images from the repository that are included in the document.

## Reference

This section provides additional content that completes the information in this document.

### Known Issues
The script has the following limitations:

* The script does not correctly process nested `<PlatformWrapper>` and `<ProductWrapper>` tags. One type of tag inside the other is fine but same type of tags should not be nested. To avoid nesting use multiple attribute values in the same tag for example:

    ```xml
    <PlatformWrapper notAllowed ="{['android', 'flutter']}">
    // some non-android, non-flutter stuff
    </PlatformWrapper>
    ```

* If the content inside `<PlatformWrapper>` and `<ProductWrapper>` tags is unnecessarily indented, the indenting is reproduced in the markdown file which prevents code blocks from being recognized and properly highlighted.