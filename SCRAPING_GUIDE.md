# PheKB Scraping Quick Start

## Two-Stage Scraping Process

The scraper collects all phenotype data locally BEFORE processing with Claude. This means **no API credits** are needed for data collection!

## Stage 1: Get the List (Run Once)

```bash
fhir-eval scrape list-urls
```

**What it does:**
- Visits https://phekb.org/phenotypes
- Handles pagination to get ALL 100+ phenotypes
- Saves to `data/phekb-raw/phenotypes.json`
- Takes 2-5 minutes

**Output:**
```
============================================================
STAGE 1: Fetching all phenotype URLs from PheKB
============================================================

This will:
  1. Load the phenotypes page
  2. Handle pagination to get ALL phenotypes
  3. Save the list to data/phekb-raw/phenotypes.json

... (browser automation) ...

============================================================
✓ SUCCESS! Found 112 phenotypes
============================================================

Saved to: data/phekb-raw/phenotypes.json
```

## Stage 2: Download Details

### Test with a Few Phenotypes

```bash
# Download just the first 5 to test
fhir-eval scrape download --limit 5
```

### Download a Specific One

```bash
# If you know the phenotype ID
fhir-eval scrape download --id diabetes-mellitus-type-2
```

### Download Everything (Patient Required!)

```bash
# This downloads ALL phenotypes - takes hours!
fhir-eval scrape download
```

**What it does for each phenotype:**
- Visits the phenotype page
- Extracts the description
- Downloads PDF files
- Downloads Word documents
- **Skips** Excel files
- Saves everything to `data/phekb-raw/[phenotype-id]/`

**Example output:**
```
============================================================
STAGE 2: Downloading details for 5 phenotypes
============================================================

[1/5] Type 2 Diabetes Mellitus
  URL: https://phekb.org/phenotype/123
  ✓ Downloaded 3 files
  Saved to: data/phekb-raw/123

[2/5] Hypertension
  URL: https://phekb.org/phenotype/456
  ✓ Downloaded 2 files
  Saved to: data/phekb-raw/456

...
```

## Check Status

See what's been downloaded:

```bash
fhir-eval scrape status
```

Output:
```
============================================================
PheKB Scraping Status
============================================================

Total phenotypes: 112
Downloaded:       5 (4.5%)
Remaining:        107

Data directory: data/phekb-raw
```

## What Gets Downloaded

For each phenotype, you get a folder with:

```
data/phekb-raw/
├── phenotypes.json          # Master list (from Stage 1)
├── diabetes-type-2/
│   ├── details.json        # Metadata
│   ├── algorithm.pdf       # Downloaded files
│   ├── description.docx
│   └── ...
├── hypertension/
│   ├── details.json
│   ├── criteria.pdf
│   └── ...
```

## Important Notes

✅ **No API Credits Required** - Both stages use only web scraping
✅ **Run Stage 1 Once** - The phenotype list rarely changes
✅ **Stage 2 is Resume-able** - Can stop and restart anytime
✅ **Respectful Rate Limiting** - 2 second delay between requests
✅ **Automatic Chromedriver** - Downloads and manages automatically

⚠️ **Requires Chrome/Chromium** - Must be installed on your system
⚠️ **Takes Time** - Downloading all 100+ phenotypes takes several hours

## Next Steps

After downloading the data:

1. **Process with Claude** (requires API credits)
   - Analyze downloaded documents
   - Generate natural language prompts
   - Create FHIR queries with codes

2. **Manual Curation**
   - Review generated test cases
   - Validate code selections
   - Add test data

See [docs/phekb-scraping.md](docs/phekb-scraping.md) for details.

## Troubleshooting

### "Chrome driver failed"
- Install Chrome: https://www.google.com/chrome/
- Or install Chromium: `apt install chromium-browser`

### "No phenotypes found"
- Website structure may have changed
- Run with `--verbose` to see details
- Open an issue on GitHub

### "Phenotype list not found"
- Run Stage 1 first: `fhir-eval scrape list-urls`

### Downloads are slow
- This is intentional (respectful scraping)
- 2 second delay between requests
- Use `--limit` to download fewer phenotypes
