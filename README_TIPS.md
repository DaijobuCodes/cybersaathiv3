# CyberSaathi CISO Tips System

This system uses Ollama's llama3:8b model to generate cybersecurity tips from articles and stores them in MongoDB.

## Components

1. **ciso_tips_agent.py** - Generates context-aware security do's and don'ts from cybersecurity articles
2. **store_tips.py** - Stores the tips in MongoDB organized by date
3. **query_tips.py** - Retrieves tips from MongoDB by date or article ID
4. **main.py** - Unified workflow script that includes tips generation and storage

## Usage

### Using the Unified Workflow (Recommended)

The easiest way to run the entire process:

```bash
# Run complete workflow from scraping to storage:
python main.py

# Skip scraping and use existing markdown file:
python main.py --skip-scrape --input-file cybersecurity_articles.md

# Skip summarization and use existing summary file:
python main.py --skip-scrape --skip-summaries --summary-file article_summaries.md

# Only generate tips from existing summary file (skip storage):
python main.py --skip-scrape --skip-summaries --summary-file article_summaries.md --skip-storage
```

See [Unified Workflow Documentation](README_UNIFIED.md) for more options.

### Individual Component Usage

#### Generating Tips

```bash
python ciso_tips_agent.py --input <articles_file.md> --output <tips_output.md>
```

Example:
```bash
python ciso_tips_agent.py --input cybersecurity_articles_20250320_184806.md --output ciso_tips_20250320.md
```

#### Storing Tips in MongoDB

```bash
python store_tips.py --input <tips_file.md>
```

Example:
```bash
python store_tips.py --input ciso_tips_20250320_193602.md
```

#### Querying Tips

1. List all available dates:
   ```bash
   python query_tips.py --list-dates
   ```

2. List all tips:
   ```bash
   python query_tips.py --list
   ```

3. Query tips by date:
   ```bash
   python query_tips.py --date YYYY-MM-DD
   ```
   Example:
   ```bash
   python query_tips.py --date 2025-03-20
   ```

4. Query tips by article ID:
   ```bash
   python query_tips.py --id article_ID
   ```
   Example:
   ```bash
   python query_tips.py --id article_3
   ```

5. Save query results to a file:
   ```bash
   python query_tips.py --id article_3 --output tips_article_3.txt
   ```

## MongoDB Structure

Tips are stored in collections following the naming pattern `tips_YYYY_MM_DD`, where the date is the publication date of the article.

Each tip document contains:
- Article ID
- Title
- Summary
- DO's list
- DON'Ts list
- Source
- Date
- Tags
- Index
- Creation timestamp

## Example Collection Structure

- `tips_2025_03_20`: Contains 6 articles from March 20, 2025
- `tips_2025_03_19`: Contains 2 articles from March 19, 2025
- `tips_2025_03_18`: Contains 1 article from March 18, 2025
- `tips_2025_03_12`: Contains 1 article from March 12, 2025

## Troubleshooting

1. **Command not found errors**: Make sure to prefix script names with `.\` in PowerShell
2. **Access denied errors**: You may need to set execution policy in PowerShell with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
3. **Missing files**: Double-check file paths and ensure all referenced files exist 