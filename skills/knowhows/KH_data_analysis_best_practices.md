# Best practices for data analyses

**Knowhow ID:** KH_data_analysis_best_practices
**Category:** Data Analysis
**Version:** 1.0
**Last Updated:** January 2025
**Short Description:** Best practices for data analyses with focused on user supplied data.
**Keywords:** data analysis, data validation, handling duplicates, missing data, data quality

---

### Critical: Validate Data Before Analysis

**Before any analysis, check user-supplied data for quality issues.**

When you find problems:
1. **Ask the user** how to proceed
2. **If unable to ask**: Remove problematic data and document what was removed

### Common Issues to Check

- **Duplicate columns**: Suffixes like `.1`, `.2` often indicate pandas auto-renamed duplicates - remove all
- **Mismatched IDs**: Use only samples present in both data and metadata
- **Missing values**: Remove samples with >20% missing data
- **Conflicting metadata**: Remove samples with inconsistent annotations

### Always Document Removals

Report what was cleaned:
- Number of samples/columns removed
- Reason for each removal
- Final dataset dimensions

### Data Loading Best Practices

```python
import pandas as pd

# Load data
df = pd.read_csv('data.csv')

# Check for duplicate columns
dup_cols = df.columns[df.columns.duplicated()].tolist()
if dup_cols:
    print(f"WARNING: Duplicate columns found: {dup_cols}")
    df = df.loc[:, ~df.columns.duplicated()]

# Check for missing values
missing_pct = df.isnull().sum() / len(df) * 100
high_missing = missing_pct[missing_pct > 20]
if len(high_missing) > 0:
    print(f"WARNING: Columns with >20% missing: {high_missing.index.tolist()}")

# Report final dimensions
print(f"Final dataset: {df.shape[0]} rows x {df.shape[1]} columns")
```

### Metadata Validation

```python
# Check sample ID overlap
data_samples = set(df.index)
meta_samples = set(metadata.index)

common = data_samples & meta_samples
only_data = data_samples - meta_samples
only_meta = meta_samples - data_samples

if only_data or only_meta:
    print(f"WARNING: {len(only_data)} samples only in data, {len(only_meta)} only in metadata")
    print("Using only common samples")
    df = df.loc[list(common)]
    metadata = metadata.loc[list(common)]
```
