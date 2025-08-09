# EMD Processor Documentation

## Overview

The EMD (Electronic Miscellaneous Document) Processor is a Python script that replaces the original VBA functionality for processing EMD data and filling out Excel files programmatically. It provides a robust, configurable solution for handling EMD records, validating data, and generating properly formatted Excel output files.

## Features

- **Excel File Processing**: Process structured data and populate EMD sheets
- **Number to Text Conversion**: Convert amounts to spelled-out text (for RECEIPT sheets)
- **Payment Type Handling**: Support for both cash and credit payments
- **Data Validation**: Comprehensive validation of EMD data integrity
- **Configurable**: All settings and constants stored in YAML configuration
- **Error Handling**: Robust error handling and logging
- **API Interface**: Clean API functions for easy integration
- **Collection Messages**: Support for adding collection messages to SUM sheet

## File Structure

```
FlightCheckPy/
├── scripts/
│   ├── emd_processor.py          # Main EMD processor script
│   └── test_emd_processor.py     # Test script for demonstration
├── resources/
│   ├── emd_processor_config.yaml # Configuration file
│   └── emd_processor_documentation.md # This documentation
└── requirements.txt              # Updated with PyYAML dependency
```

## Installation

1. Ensure you have the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. The script requires:
   - `pandas>=2.0.0`
   - `openpyxl>=3.1.0`
   - `PyYAML>=6.0`

## Configuration

The configuration file (`resources/emd_processor_config.yaml`) contains all customizable settings:

### File Settings
- **prefix**: File name prefix (default: "EMD CA")
- **separator**: Separator between flight number and date
- **date_format**: Date format for filename generation
- **file_extension**: Output file extension

### Sheet Names
- **emd**: EMD sheet name
- **sum**: SUM sheet name
- **receipt**: RECEIPT sheet name

### Column Mappings
Defines the column positions for each field in the EMD sheet:
- EMD number, ticket number, origin/destination
- Operator, account, issue date, product, ID
- Flight number, price, cash/credit amounts

### Validation Settings
- **require_last_four_digits**: Require last 4 digits for credit payments
- **check_duplicate_emds**: Check for duplicate EMD numbers
- **min_rows_required**: Minimum rows required for processing

## API Functions

### Main Processing Function

```python
process_emd_data(emd_data_dict, template_path, output_path=None, config_path=None)
```

**Parameters:**
- `emd_data_dict`: Dictionary containing EMD data in the specified format
- `template_path`: Path to template Excel file
- `output_path`: Path for output file (optional, auto-generated if not provided)
- `config_path`: Path to configuration file (optional)

**Returns:**
- Path to the generated output file

**Example:**
```python
from scripts.emd_processor import process_emd_data

# Sample data in the new API format
sample_data = {
    "total_amount": 12345.00,
    "report_date": "2025-08-07",
    "signature": "Jun Liu",
    "collection_msg": ["Message 1", "Message 2", "Message 3"],
    "emd_list": [
        {
            "emd": "9991234567890",
            "et": "9991234567890",
            "leg": "LAX-PEK",
            "emd_count": 1,
            "operation": "issue",
            "job_number": 35008,
            "date": "2025-08-07",
            "product": "EXPC",
            "i_d": "international",
            "flight": "CA984",
            "price": 12345.00,
            "cash": 12345.00,
            "ax": 0.00,
            "other": 0.00,
            "last_4_digit": "",
            "remark": "Sample remark"
        }
    ]
}

output_file = process_emd_data(
    emd_data_dict=sample_data,
    template_path="templates/emd_template.xlsx",
    output_path="output/processed_emds.xlsx"
)
print(f"Processed file: {output_file}")
```

### Utility Functions

#### Number to Text Conversion
```python
spell_number(amount, config_path=None)
```
Converts numeric amounts to spelled-out text (e.g., 1234.56 → "ONE THOUSAND TWO HUNDRED THIRTY FOUR DOLLARS AND FIFTY SIX CENTS EXACTLY")

#### Data Validation
```python
validate_emd_data(emd_data_dict, config_path=None)
```
Validates EMD records for integrity and returns (is_valid, error_message)

#### Filename Generation
```python
generate_filename(flight, date_str, config_path=None)
```
Generates output filename based on flight number and date

## Classes

### EMDRecord
Represents a single EMD record with all its properties:

```python
record = EMDRecord(
    emd="9991234567890",
    et="9991234567890",
    leg="LAX-PEK",
    emd_count=1,
    operation="issue",
    job_number=35008,
    date="2025-08-07",
    product="EXPC",
    i_d="international",
    flight="CA984",
    price=12345.00,
    cash=12345.00,
    ax=0.00,
    other=0.00,
    last_4_digit="",
    remark="Sample remark"
)
```

### EMDData
Represents the complete EMD data structure:

```python
emd_data = EMDData(
    total_amount=12345.00,
    report_date="2025-08-07",
    signature="Jun Liu",
    collection_msg=["Message 1", "Message 2", "Message 3"],
    emd_list=[emd_record]
)
```

### EMDProcessor
Main class for processing EMD data:

```python
processor = EMDProcessor(config_path="resources/emd_processor_config.yaml")
```

## Input Data Format

The input data should be provided as a dictionary with the following structure:

```json
{
    "total_amount": 0.0,
    "report_date": "2025-08-07",
    "signature": "Jun Liu",
    "collection_msg": ["msg1", "msg2"],
    "emd_list": [
        {
            "emd": "9991234567890",
            "et": "9991234567890",
            "leg": "LAX-PEK",
            "emd_count": 1,
            "operation": "issue",
            "job_number": 35008,
            "date": "2025-08-07",
            "product": "EXPC",
            "i_d": "international",
            "flight": "CA984",
            "price": 12345.00,
            "cash": 12345.00,
            "ax": 12345.00,
            "other": 12345.00,
            "last_4_digit": 1234,
            "remark": "aaaa"
        }
    ]
}
```

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `total_amount` | float | Total amount for all EMDs | 12345.00 |
| `report_date` | string | Report date (YYYY-MM-DD) | "2025-08-07" |
| `signature` | string | Signature of the processor | "Jun Liu" |
| `collection_msg` | array | Collection messages for SUM sheet | ["msg1", "msg2"] |
| `emd_list` | array | Array of EMD records | [...] |

### EMD Record Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `emd` | string | EMD number | "9991234567890" |
| `et` | string | E-ticket number | "9991234567890" |
| `leg` | string | Route (origin-destination) | "LAX-PEK" |
| `emd_count` | integer | Quantity of EMDs | 1 |
| `operation` | string | Operation type | "issue" |
| `job_number` | integer | Job/account number | 35008 |
| `date` | string | Issue date | "2025-08-07" |
| `product` | string | Product code | "EXPC" |
| `i_d` | string | ID type | "international" |
| `flight` | string | Flight number | "CA984" |
| `price` | float | Total price | 12345.00 |
| `cash` | float | Cash amount | 12345.00 |
| `ax` | float | American Express card amount | 0.00 |
| `other` | float | Other credit card amount (Visa, MasterCard, etc.) | 0.00 |
| `last_4_digit` | string | Last 4 digits of credit card | "1234" |
| `remark` | string | Additional remarks | "Sample remark" |

## Usage Examples

### Basic Usage
```python
from scripts.emd_processor import process_emd_data

# Process EMD data
output_file = process_emd_data(
    emd_data_dict=sample_data,
    template_path="template.xlsx"
)
```

### Advanced Usage with Custom Configuration
```python
from scripts.emd_processor import EMDProcessor

# Initialize with custom config
processor = EMDProcessor("custom_config.yaml")

# Convert dictionary to EMDData object
emd_data = processor.create_emd_data_from_dict(sample_data)

# Validate data
is_valid, error_msg = processor.validate_emd_data(emd_data)
if not is_valid:
    print(f"Validation failed: {error_msg}")
    return

# Process data
workbook = load_workbook("template.xlsx")
processor.fill_emd_sheet(workbook, emd_data)
processor.fill_sum_sheet(workbook, emd_data)
workbook.save("output.xlsx")
```

### Number to Text Conversion
```python
from scripts.emd_processor import spell_number

# Convert amounts to text
amounts = [0, 1, 1.01, 10.50, 100.00, 1234.56]
for amount in amounts:
    text = spell_number(amount)
    print(f"{amount:>10.2f} -> {text}")
```

## Template File Requirements

The template Excel file should contain:
1. **EMD Sheet**: With proper column headers and formatting starting from row 8
2. **SUM Sheet**: With space for collection messages in column C starting from row 15
3. **RECEIPT Sheet**: For amount text conversion

## Excel Sheet Population

### EMD Sheet (Starting from Row 8)
- **Column A**: EMD Number (`emd`)
- **Column B**: Ticket Number (`et`) - with quote prefix
- **Column C**: Origin/Destination (`leg`)
- **Column D**: Quantity (`emd_count`)
- **Column E**: Operation (`operation`)
- **Column F**: Job Number (`job_number`)
- **Column G**: Issue Date (`date`)
- **Column H**: Product (`product`)
- **Column I**: ID (`i_d`)
- **Column J**: Flight Number (`flight`)
- **Column K**: Price (`price`)
- **Column L**: Cash Amount (`cash`)
- **Column M**: American Express Amount (`ax`)
- **Column N**: Other Credit Card Amount (`other`)
- **Column O**: Last 4 Digits (`last_4_digit`) - for credit payments

### SUM Sheet (Starting from Row 15)
- **Column C**: Collection messages from `collection_msg` array
  - First message at C15
  - Second message at C16
  - Third message at C17
  - And so on...

## Error Handling

The script includes comprehensive error handling:

- **File Not Found**: Clear error messages for missing files
- **Invalid Data**: Validation errors with specific messages
- **Configuration Errors**: YAML parsing and validation errors
- **Excel Errors**: OpenPyXL errors with context

**Error Output Format:**
The validation functions return error messages in a list format for debugging purposes, not the same structure as input data.

## Logging

The script uses Python's logging module with INFO level by default. Log messages include:
- Configuration loading status
- File processing progress
- Validation results
- Error details

## Testing

Run the test script to verify functionality:

```bash
cd scripts
python test_emd_processor.py
```

The test script demonstrates:
- Number to text conversion
- EMD record creation with new API format
- Data validation
- Filename generation
- Processor initialization
- Data conversion from dictionary format

## Migration from VBA

This Python script replaces the following VBA functionality:

### VBA Functions Replaced:
- `SpellNumber()` → `spell_number()`
- `GetHundreds()`, `GetTens()`, `GetDigit()` → Internal methods in `EMDProcessor`
- `Button_Open_Click()` → `fill_emd_sheet()` and `fill_sum_sheet()`
- `Bottom_Save_Click()` → `generate_filename()` and file saving
- `Button_Print_Click()` → Can be implemented using openpyxl print settings

### Key Improvements:
- **Type Safety**: Strong typing with Python type hints
- **Configuration**: External YAML configuration instead of hardcoded values
- **Error Handling**: Comprehensive error handling and logging
- **Modularity**: Clean separation of concerns with classes and functions
- **Testing**: Built-in test suite for validation
- **Documentation**: Comprehensive documentation and examples
- **API Flexibility**: Support for structured data input instead of Excel file reading

## Troubleshooting

### Common Issues:

1. **Configuration File Not Found**
   - Ensure `emd_processor_config.yaml` exists in the resources directory
   - Check file path in the script

2. **Excel File Errors**
   - Verify template file has required sheets and cells
   - Check column mappings in configuration

3. **Validation Errors**
   - Ensure EMD numbers are unique
   - Check credit payments have last 4 digits
   - Verify all required fields are present

4. **Import Errors**
   - Install required dependencies: `pip install -r requirements.txt`
   - Check Python path and module imports

### Debug Mode:
Enable debug logging by modifying the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential improvements for future versions:
- Support for additional payment types
- Enhanced receipt sheet customization
- Batch processing capabilities
- Web interface integration
- Additional validation rules
- Export to different formats
- Support for additional Excel sheet types

## Support

For issues or questions:
1. Check the test script for usage examples
2. Review the configuration file for settings
3. Enable debug logging for detailed error information
4. Verify data format matches expected structure
5. Check template file requirements 