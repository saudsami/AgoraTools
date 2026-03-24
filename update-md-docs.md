Follow these steps to update the markdown docs periodically and upload the files to DocsBot AI:

1.  Delete the `mdx2md/output` and `mdx2md/output-indexed` folders

1. Export the docs to markdown

    ```bash
    cd mdx2md
    python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs
    ```

1. Export the help files to markdown

    ```bash
    python bulk_export.py --docs-folder D:/Git/AgoraDocs/Docs --process-help 
    ```

1. Rename (reindex) files

    ```bash
    python rename_md_files.py ./output
    ```

1. Upload the generated markdown files to the [markdown-service](https://github.com/AgoraIO/markdown-service/) repository.

    1. Copy the `output/images` folder to `/public/images`

    1. Copy the other product doc folders from `output` to `/public/en`

1. Zip markdown document folders for upload to DocsBot.

    ```bash
    ./zip_folders.ps1 
    ```

1. Upload each zip file to the [DocsBot AI](https://docsbot.ai/) **Agora Assist** bot under **Sources**. For each zip file:

    1. Delete the existing file
    1. Choose **New Source** > **Document**
    1. Drag the zip file
    1. Paste the Product Overview page URL for the **Source URL**
    1. Use the product name as the **Source title**
    1. Click **Add source**