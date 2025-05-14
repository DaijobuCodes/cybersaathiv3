# CyberSaathi Unified Workflow

This document provides instructions for using the new unified workflow script `main.py` that combines all CyberSaathi functionality into a single process.

## Overview

The unified workflow automates all steps in the CyberSaathi pipeline:

1. **Scraping** cybersecurity articles from multiple sources
2. **Exporting** the scraped data to markdown format
3. **Summarizing** articles using Ollama's llama3:8b model
4. **Generating CISO tips** (Do's and Don'ts) from the summaries
5. **Storing** all data in MongoDB for future retrieval

## Requirements

- Python 3.8+
- MongoDB (local or Atlas) running and accessible
- Ollama with llama3:8b model installed and running
- Python dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```

## Quick Start

To run the complete CyberSaathi workflow with default settings:

```bash
python main.py
```

This will:
- Scrape up to 10 articles from each cybersecurity news site
- Export the articles to a markdown file
- Summarize the articles using Ollama
- Generate CISO tips based on the article content
- Store the tips in MongoDB

## Command Line Options

The main.py script supports several command-line options for customizing the workflow:

```
--limit N           : Limit the number of articles to scrape from each site (default: 10)
--skip-scrape       : Skip the scraping step (requires --input-file)
--input-file FILE   : Use this markdown file instead of scraping
--summary-file FILE : Use this summary file instead of generating new summaries
--skip-summaries    : Skip the article summarization step
--skip-tips         : Skip the CISO tips generation step
--skip-storage      : Skip storing data in MongoDB
--verbose           : Show detailed output
```

## Examples

### Using an existing markdown file

If you already have a markdown file with articles and want to process it:

```bash
python main.py --skip-scrape --input-file cybersecurity_articles.md
```

### Limited article scraping

To scrape only 5 articles from each site:

```bash
python main.py --limit 5
```

### Skip certain steps

If you want to skip summarization and work directly with tips generation:

```bash
python main.py --skip-summaries
```

### Complete workflow with existing summary file

If you have an existing summary file and want to generate tips from it:

```bash
python main.py --skip-scrape --skip-summaries --summary-file article_summaries.md
```

## Output Files

The script generates timestamped output files at each step:

- `cybersecurity_articles_TIMESTAMP.md`: Markdown file with scraped articles
- `article_summaries_TIMESTAMP.md`: Markdown file with article summaries
- `ciso_tips_TIMESTAMP.md`: Markdown file with generated CISO tips

## Querying Stored Tips

After running the workflow, you can query the stored tips using the query_tips.py script:

```bash
# List all available tips
python query_tips.py --list

# Query tips for a specific article
python query_tips.py --id article_1

# Query tips by date
python query_tips.py --date 2023-07-15
```

## Troubleshooting

- **Missing dependencies**: Make sure all required Python packages are installed
- **Ollama not running**: Start Ollama service before running the script
- **MongoDB connection issues**: Verify your MongoDB is running and accessible
- **Import errors**: Ensure all required script files are in the same directory as main.py 