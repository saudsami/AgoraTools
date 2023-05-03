# `mdx` to Markdown

`mdx2md.py` is a Python script that you can use to convert any `.mdx` document in the Agora docs repository to a single markdown `.md` file by resolving all its dependencies. This enables you to include the relevant Agora document as a `README.md` file in the Github code repository. 

When you run the script, it does the following:

* Loads global variables into a dictionary.
* Creates product and platform dictionaries to resolve `<Vpl>` and `<Vpd>` tags.
* Reads the `.mdx` file and recursively resolves all the import statements.
* Resolves `<PlatformWrapper>` tags to filter content for the selected platform.
* Resolves `<ProductWrapper>` tags to filter content for the selected product.
* Replaces global variables `<Vg k="KEY" />` with values.
* Replaces product `<Vpd k="KEY" />` and platform `<Vpl k="KEY" />` variables, with corresponding values.
* Processes the document header to add a document title.
* Copies images from the repository to the `./images` folder and updates image links.
* Converts `<Link></Link>` tags to markdown links.
* Updates the relative path in markdown links to Agora docs urls
* Removes extra line breaks.
* Writes the modified contents to a new `.md` file.

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

1. Open a terminal window and navigate to the `/AgoraTools/mdx2md` folder.

1. In the terminal window execute the following command:
    
    ```bash
    python mdx2md.py [--mdxPath MDXPATH] [--platform PLATFORM] [--product PRODUCT]
    ```

    * `mdxPath`: The absolute path to the `.mdx` file in the `docs` repository.
    * `platform`: The platform for which you want to generate the markdown document. Default is `android`.
    * `product`: (Optional) The product for which you want to generate the document. If omitted, the product name is automatically interpreted from the `mdxPath`.

    For example:

    ```bash
    python mdx2md.py --mdxPath C:\Git\AgoraDocsPrivate\Docs\docs\voice-calling\get-started\get-started-sdk.mdx --platform flutter
    ```

    The script creates an `output` folder in your working directory.

1. Open the `output` folder. 

    The exported markdown file has the same name as the input `.mdx` file. The `images` folder contains all the images from the repository that are used in the document.

## Reference

This section provides additional content that completes the information in this document.

### Export to PDF

You can convert the `.md` file generated using `mdx2md.py` script to a `.pdf` document using any markdown to PDF converter. If you use VS Code:

1. Install the [Markdown PDF](https://marketplace.visualstudio.com/items?itemName=yzane.markdown-pdf) extension.

2. Open the `.md` file in VS code.

2. Press `CTRL + SHIFT + p`, type "Export (pdf)" and press enter. A `.pdf` file is created in the same folder as the markdown file.

### Known Issues
The script has the following limitations:

* The script does not correctly process nested `<PlatformWrapper>` and `<ProductWrapper>` tags. `<PlatformWrapper>` tags inside `<ProductWrapper>` or visa versa are processed correctly but same type of nested tags produce unexpected results. To avoid nesting tags in the documentation, use a JSON array with multiple values. For example:

    ```xml
    <PlatformWrapper notAllowed="{['android', 'flutter']}">
    // some non-android, non-flutter stuff
    </PlatformWrapper>
    ```

* If the content inside `<PlatformWrapper>` and `<ProductWrapper>` tags is unnecessarily indented, the indenting is reproduced in the markdown file which prevents code blocks from being interpreted and properly highlighted.
