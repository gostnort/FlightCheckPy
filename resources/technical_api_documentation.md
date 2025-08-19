# Flight Data Processing System - Technical API Documentation

## Project Overview

The Flight Data Processing System is a comprehensive Python application for processing and analyzing HBPR (Hotel Booking Passenger Record) data. It validates and parses records, stores them in SQLite databases, and provides a modern Streamlit-based UI for database building, record processing, airline command analysis with timeline versioning, and Excel output generation by mapping TKNE to CKIN CCRD data.

**Key Features:**
- Multi-source database discovery with visual location indicators (📁 Custom, 🏠 Default, 📄 Root)
- Native Windows folder picker integration (topmost) with custom folder persistence
- Centralized database selection with flight information and session persistence
- Real-time database switching without application restart
- Intelligent statistics caching with automatic invalidation on updates
- Accepted passengers tracking with infant count and class split (Business/Economy)
- Excel Processor: XLS/XLSX import, strict header validation, TKNE ↔ CKIN CCRD mapping, formatted EMD Excel export
- Command analysis: import, manual edit, view, timeline versioning, and maintenance/migration
- TKNE-aware calculations and compatibility handling
- **Data Cleaning & Export Solutions**: Comprehensive data sanitization at input, storage, and export stages to prevent binary/hexadecimal character issues
- **Deleted Passenger Analytics**: Comprehensive tracking of deleted passengers with XRES property classification and original boarding number extraction
- **Reusable UI Components**: Modular component architecture for consistent statistics display across multiple pages

## 🏗️ System Architecture

### Core Components

```
FlightCheckPy/
├── scripts/                    # Core processing modules
│   ├── hbpr_info_processor.py  # HBPR record processing, validation, and statistics
│   ├── hbpr_list_processor.py  # Batch processing and database creation
│   ├── excel_processor.py      # Excel-to-EMD processing via TKNE/CKIN CCRD mapping
│   ├── general_func.py         # Utility functions and configuration
│   └── data_cleaner.py        # Data cleaning and sanitization utilities
├── ui/                         # Web UI components
│   ├── main.py                 # Main UI coordinator with Windows integration
│   ├── login_page.py           # Authentication interface
│   ├── home_page.py            # System overview with real-time statistics
│   ├── database_page.py        # Database management and construction
│   ├── process_records_page.py # Record processing navigation (batch/single/simple/sort/export)
│   ├── command_analysis_page.py # Command processing, timeline view, and maintenance
│   ├── excel_processor_page.py # Excel upload and EMD export UI
│   ├── settings_page.py        # System configuration and about info
│   ├── common.py               # Shared utilities with enhanced database discovery
│   ├── components/             # Reusable UI components
│   │   ├── main_stats.py       # Main statistics display component
│   │   ├── deleted_stats.py    # Deleted passenger statistics component
│   │   └── home_metrics.py     # Home page metrics and flight summary
│   └── process_records/        # Sub-modules for record processing
│       ├── process_all.py      # Batch processing functionality
│       ├── add_edit_record.py  # Single record editing
│       ├── simple_record.py    # Simple record creation
│       ├── sort_records.py     # Record viewing and filtering
│       └── export_data.py      # Data export functionality with cleaning
├── databases/                  # Default database storage directory
└── resources/                  # Documentation and resources
```

### Data Cleaning & Export Solutions

The system implements a comprehensive approach to handle problematic binary/hexadecimal characters that can cause export failures:

#### 1. Preventive Solution (Input-time Cleaning)
**Location**: `scripts/data_cleaner.py`

**Purpose**: Prevents problematic characters from entering the system by cleaning data at multiple input points.

**Key Functions**:
```python
def clean_text_for_input(text: str, aggressive: bool = False) -> str:
    """
    Clean text for input operations, removing control characters and problematic symbols
    
    Args:
        text (str): Input text to clean
        aggressive (bool): Whether to use aggressive cleaning (removes extended Unicode)
        
    Returns:
        str: Cleaned text safe for processing
    """

def clean_hbpr_record_content(text: str) -> str:
    """
    Clean HBPR record content specifically for database storage
    
    Args:
        text (str): HBPR record content to clean
        
    Returns:
        str: Cleaned HBPR content safe for database storage
    """

def validate_and_clean_file_content(file_path: str, encoding: str = 'utf-8') -> Tuple[List[str], bool]:
    """
    Read and clean file content, detecting if cleaning was needed
    
    Args:
        file_path (str): Path to file to read and clean
        encoding (str): File encoding to use
        
    Returns:
        Tuple[List[str], bool]: Cleaned lines and whether cleaning was needed
    """
```

**Integration Points**:
- **File Reading**: `scripts/hbpr_list_processor.py` - `parse_file()` method
- **Record Parsing**: `scripts/hbpr_list_processor.py` - `parse_full_record()` method  
- **Database Storage**: `scripts/hbpr_list_processor.py` and `scripts/hbpr_info_processor.py`
- **UI Input Validation**: `ui/process_records/add_edit_record.py` - `validate_full_hbpr_record()`

#### 2. Export-time Fix
**Location**: `ui/process_records/export_data.py`

**Purpose**: Provides immediate solution for exporting existing problematic data by cleaning during export operations.

**Key Functions**:
```python
def clean_text_for_export(text: str) -> str:
    """
    Clean text specifically for export operations (CSV/Excel)
    
    Args:
        text (str): Text to clean for export
        
    Returns:
        str: Text safe for CSV/Excel export
    """

def show_export_data() -> None:
    """
    Display export functionality with data cleaning
    
    Features:
    - Export all records with cleaning
    - Export accepted passengers only
    - CSV and Excel format export
    - Safe handling of problematic characters
    - Download links for cleaned data
    """
```

#### 3. Database Cleaning Utility
**Location**: `scripts/clean_database_data.py`

**Purpose**: Provides utility to clean existing problematic data directly in the database.

**Key Functions**:
```python
def clean_text_for_database(text: str) -> str:
    """
    Clean text for database storage, removing control characters
    
    Args:
        text (str): Text to clean for database
        
    Returns:
        str: Text safe for database storage
    """

def clean_database_records(db_file: str) -> Dict[str, int]:
    """
    Clean all records in specified database
    
    Args:
        db_file (str): Path to database file to clean
        
    Returns:
        Dict[str, int]: Cleaning results with counts
    """
```

**UI Integration**: Available through "Clean Database Data" button in `ui/database_page.py`

### Deleted Passenger Analytics

The system provides comprehensive tracking and analysis of deleted passengers with automatic classification and original boarding number extraction.

**Location**: `scripts/hbpr_info_processor.py`

**Purpose**: Identifies and categorizes deleted passengers by XRES property and extracts their original boarding numbers from DEL command lines.

#### Key Components

**Database Schema Enhancement**:
- **`is_deleted` field**: INTEGER field storing original boarding numbers of deleted passengers
- **Value meanings**:
  - `0`: Not deleted (normal passenger)
  - `≥1`: Deleted passenger, value represents original boarding number

**Identification Logic**:
```python
# Deleted passengers are identified by:
boarding_number = 0 AND record_content LIKE '%DELETED%'

# Classification:
# - XRES deleted: properties LIKE '%XRES%'  
# - Non-XRES deleted: properties NOT LIKE '%XRES%' OR properties IS NULL

# Original boarding number extraction from DEL lines:
# Pattern: '\n\s+DEL\s+.*?/BN(\d+)\s'
# Example: "     DEL LAX7527 AGT47185/25JUL2316/BN89 SNR60D 60D" → boarding number 89
```

#### Functions

```python
def get_deleted_passengers_stats(self) -> Dict[str, Any]:
    """
    Get comprehensive deleted passenger statistics (cached)
    
    Returns:
        Dict[str, Any]: Statistics including:
            - total_deleted: Total number of deleted passengers
            - deleted_with_xres: Count of deleted passengers with XRES property
            - deleted_without_xres: Count of deleted passengers without XRES property
            - xres_boarding_numbers: List of original boarding numbers for XRES deleted passengers
            - original_boarding_numbers: List of original boarding numbers for non-XRES deleted passengers
    """

def add_is_deleted_field_if_not_exists(self) -> bool:
    """
    Add is_deleted field to database schema if not exists and populate with original boarding numbers
    
    Returns:
        bool: True if operation successful
        
    Features:
        - Automatic database schema migration
        - Parsing of DEL command lines for boarding number extraction
        - Handles existing databases without field
        - Automatic detection and processing of deleted records
    """

def _fetch_deleted_passengers_stats(self) -> Dict[str, Any]:
    """
    Internal method to fetch deleted passenger statistics with automatic field creation
    
    Returns:
        Dict[str, Any]: Raw deleted passenger statistics
        
    Features:
        - Ensures is_deleted field exists before processing
        - Falls back to content-based detection for compatibility
        - Extracts boarding numbers using regex pattern matching
    """
```

#### Integration Points
- **Statistics Caching**: Integrated with StatisticsManager for efficient retrieval
- **UI Components**: Displayed through reusable components in main_stats.py and deleted_stats.py
- **Database Migration**: Automatic field creation and data population on first use
- **Cache Invalidation**: Statistics cache cleared on database modifications

### Reusable UI Components

The system implements a modular component architecture for consistent statistics display across multiple pages.

**Location**: `ui/components/`

**Purpose**: Provides reusable, maintainable UI components for statistics display with consistent formatting and behavior.

#### Component Structure

```
ui/components/
├── main_stats.py          # Main statistics display component
├── deleted_stats.py       # Deleted passenger statistics component
└── home_metrics.py        # Flight summary and debug metrics
```

#### Key Functions

**main_stats.py**:
```python
def display_main_statistics(all_stats: Dict[str, Any]) -> None:
    """
    Display main HBPR statistics in reusable format
    
    Features:
        - Max HBNB, Missing Count, Accepted Passengers metrics
        - Deleted passenger statistics integration
        - Consistent formatting across pages
    """

def get_and_display_main_statistics(db: HbprDatabase) -> Dict[str, Any]:
    """
    Get all statistics from database and display them
    
    Returns:
        Dict[str, Any]: Complete statistics for additional processing
        
    Features:
        - Single function call for complete statistics display
        - Error handling and user feedback
        - Automatic caching through database layer
    """

def display_detailed_range_info(all_stats: Dict[str, Any]) -> None:
    """
    Display detailed HBNB range information for database page
    
    Features:
        - HBNB Range, Total Expected, Total Found, Missing Numbers
        - Specialized display for database management interface
    """
```

**deleted_stats.py**:
```python
def display_deleted_stats(deleted_stats: Dict[str, Any]) -> None:
    """
    Display deleted passenger statistics in reusable format
    
    Features:
        - Del w XRES and Del w/o XRES metrics
        - Boarding number lists with intelligent truncation
        - Enhanced display limits (10 XRES, 30 non-XRES boarding numbers)
    """

def get_and_display_deleted_stats(db: HbprDatabase) -> None:
    """
    Get deleted passenger statistics from database and display them
    
    Features:
        - Complete deleted passenger statistics retrieval and display
        - Error handling for missing data
        - Integration with statistics caching
    """
```

**home_metrics.py**:
```python
def get_home_summary(db_file: str) -> Dict[str, Any]:
    """
    Get flight summary data for home page display
    
    Returns:
        Dict[str, Any]: Flight summary including totals, ratios, and breakdowns
    """

def get_debug_summary(db_file: str) -> str:
    """
    Get debug information for database troubleshooting
    
    Returns:
        str: Formatted debug information
    """
```

#### Component Features
- **Consistent Display**: Identical appearance and behavior across pages
- **Intelligent Truncation**: Boarding numbers display with enhanced limits
- **Error Handling**: Graceful fallback for missing or invalid data
- **Modular Design**: Easy to add to new pages or modify existing displays
- **Performance**: Leverages existing statistics caching infrastructure

#### Usage Examples
```python
# In home page or database page
from ui.components.main_stats import get_and_display_main_statistics
all_stats = get_and_display_main_statistics(db)

# For deleted passenger statistics only
from ui.components.deleted_stats import get_and_display_deleted_stats
get_and_display_deleted_stats(db)

# For flight summary display
from ui.components.home_metrics import get_home_summary
summary = get_home_summary(db_file)
```

#### 4. Character Cleaning Strategy

**Problematic Characters Handled**:
- **Control Characters**: ASCII 0-31 (null, bell, tab, newline, etc.)
- **DEL Character**: ASCII 127
- **Extended ASCII**: Characters above 127 that may cause encoding issues
- **Binary Data**: Hex-encoded content from file reading operations

**Cleaning Methods**:
- **Replacement**: Control characters replaced with spaces
- **Filtering**: Only printable ASCII characters (32-126) and safe whitespace preserved
- **Normalization**: Multiple spaces collapsed, empty lines cleaned
- **Validation**: Detection of cleaning needs for user awareness

### Platform Requirements

**Windows-Specific Features:**
- Native folder picker dialogs using `tkinter.filedialog`
- Windows path handling and directory operations
- Topmost window management for dialog positioning

**Dependencies:**
- `streamlit` - Web UI framework
- `tkinter` - Native Windows GUI toolkit (built-in with Python)
- `sqlite3` - Database operations
- `pandas` - Data manipulation
- `openpyxl` - Excel reading/writing for XLSX
- `xlrd` - Legacy XLS support
- `glob` - File pattern matching
- `time` - Cache timing management

## 📋 Class Specifications

### 1. StatisticsManager Class - Statistics Caching

**Location**: `scripts/hbpr_info_processor.py`

**Purpose**: Manages caching of database statistics with automatic invalidation and refresh capabilities.

#### Attributes
- `_cache: Dict[str, Any]` - Internal cache storage
- `_cache_timestamps: Dict[str, float]` - Cache entry timestamps
- `_cache_duration: int` - Cache validity duration in seconds (default: 300)

#### Methods

```python
def __init__(self, cache_duration: int = 300) -> None:
    """
    Initialize StatisticsManager with cache duration
    
    Args:
        cache_duration (int): Cache validity duration in seconds
    """

def get_cached_data(self, key: str) -> Optional[Any]:
    """
    Retrieve cached data if valid
    
    Args:
        key (str): Cache key
        
    Returns:
        Optional[Any]: Cached data if valid, None otherwise
    """

def set_cached_data(self, key: str, data: Any) -> None:
    """
    Store data in cache with current timestamp
    
    Args:
        key (str): Cache key
        data (Any): Data to cache
    """

def is_cache_valid(self, key: str) -> bool:
    """
    Check if cached data is still valid
    
    Args:
        key (str): Cache key
        
    Returns:
        bool: True if cache is valid, False otherwise
    """

def clear_cache(self) -> None:
    """Clear all cached data"""

def invalidate_cache(self, key: str) -> None:
    """
    Invalidate specific cache entry
    
    Args:
        key (str): Cache key to invalidate
    """
```

### 2. CHbpr Class - HBPR Record Processing

**Location**: `scripts/hbpr_info_processor.py`

**Purpose**: Processes and validates individual HBPR passenger records, extracting structured data and performing comprehensive validation.

#### Public Attributes
- `error_msg: Dict[str, List[str]]` - Error messages categorized by type
- `BoardingNumber: int` - Extracted boarding number
- `HbnbNumber: int` - HBNB record number
- `debug_msg: List[str]` - Debug messages for processing
- `PNR: str` - Passenger Name Record
- `NAME: str` - Passenger name
- `SEAT: str` - Seat assignment
- `CLASS: str` - Travel class (F/C/Y)
- `DESTINATION: str` - Flight destination
- `BAG_PIECE: int` - Number of baggage pieces
- `BAG_WEIGHT: int` - Total baggage weight
- `BAG_ALLOWANCE: int` - Baggage allowance
- `FF: str` - Frequent flyer information
- `PSPT_NAME: str` - Passport name
- `PSPT_EXP_DATE: str` - Passport expiration date
- `CKIN_MSG: List[str]` - Check-in messages
- `ASVC_MSG: List[str]` - Additional service messages
- `EXPC_PIECE: int` - Excess baggage pieces
- `EXPC_WEIGHT: int` - Excess baggage weight
- `ASVC_PIECE: int` - Additional service pieces
- `FBA_PIECE: int` - Free baggage allowance pieces
- `IFBA_PIECE: int` - Infant free baggage allowance pieces
- `FLYER_BENEFIT: int` - Frequent flyer benefits
- `INBOUND_FLIGHT: str` - Inbound flight information
- `OUTBOUND_FLIGHT: str` - Outbound flight information
- `PROPERTIES: List[str]` - Additional properties
- `IS_CA_FLYER: bool` - Is CA frequent flyer
- `TKNE: str` - TKNE field value

#### Methods

```python
def __init__(self) -> None:
    """Initialize CHbpr instance with default values"""

def run(self, HbprContent: str) -> None:
    """
    Main processing method for HBPR records
    
    Args:
        HbprContent (str): Raw HBPR record content
        
    Raises:
        Exception: If fatal error occurs during processing
    """

def is_valid(self) -> bool:
    """
    Check if the processed record is valid
    
    Returns:
        bool: True if no errors found, False otherwise
    """

def get_structured_data(self) -> Dict[str, Any]:
    """
    Get all extracted structured data as dictionary
    
    Returns:
        Dict[str, Any]: Complete structured data from HBPR record
    """
```

#### Private Methods

```python
def __GetHbnbNumber(self) -> bool:
    """Extract HBNB number from record"""

def __GetPassengerInfo(self) -> bool:
    """Extract passenger name, boarding number, seat, class, destination"""

def __ExtractStructuredData(self) -> None:
    """Extract all structured data fields including TKNE"""

def __MatchingBag(self) -> None:
    """Validate baggage allowance and weight"""

def __GetPassportExp(self) -> None:
    """Check passport expiration date"""

def __NameMatch(self) -> None:
    """Validate passenger name consistency"""

def __GetVisaInfo(self) -> None:
    """Extract visa information"""

def __GetProperties(self) -> None:
    """Extract additional properties"""

def __GetConnectingFlights(self) -> None:
    """Extract connecting flight information"""
```

### 3. HbprDatabase Class - Database Management

**Location**: `scripts/hbpr_info_processor.py`

**Purpose**: Manages all database operations for HBPR records including creation, querying, maintenance, and statistics caching.

#### Attributes
- `db_file: str` - Database file path
- `stats_manager: StatisticsManager` - Statistics caching manager

#### Methods

```python
def __init__(self, db_file: str = None) -> None:
    """
    Initialize database connection with statistics manager
    
    Args:
        db_file (str, optional): Path to database file
        
    Raises:
        FileNotFoundError: If specified database file doesn't exist
    """

def find_database(self) -> str:
    """
    Find HBPR database files, prioritizing databases/ folder
    
    Returns:
        str: Path to found database file
        
    Raises:
        FileNotFoundError: If no valid database found
    """

def build_from_hbpr_list(self, input_file: str = "sample_hbpr_list.txt") -> HBPRProcessor:
    """
    Build database from HBPR list file
    
    Args:
        input_file (str): Path to input HBPR list file
        
    Returns:
        HBPRProcessor: Processor instance used for building
        
    Raises:
        FileNotFoundError: If input file doesn't exist
    """

def get_hbpr_record(self, hbnb_number: int) -> str:
    """
    Get HBPR record content by HBNB number
    
    Args:
        hbnb_number (int): HBNB number to retrieve
        
    Returns:
        str: Raw HBPR record content
        
    Raises:
        ValueError: If HBNB number not found
        Exception: If database error occurs
    """

def update_with_chbpr_results(self, chbpr_instance: CHbpr) -> bool:
    """
    Update database with CHbpr validation results and invalidate cache
    
    Args:
        chbpr_instance (CHbpr): Processed CHbpr instance
        
    Returns:
        bool: True if update successful
        
    Raises:
        ValueError: If HBNB number not found in database
        Exception: If database error occurs
    """

def get_validation_stats(self) -> Dict[str, int]:
    """
    Get validation statistics (cached)
    
    Returns:
        Dict[str, int]: Statistics including total_records, validated_records, 
                       valid_records, invalid_records
    """

def get_missing_hbnb_numbers(self) -> List[int]:
    """
    Get list of missing HBNB numbers (cached)
    
    Returns:
        List[int]: Sorted list of missing HBNB numbers
    """

def get_hbnb_range_info(self) -> Dict[str, int]:
    """
    Get HBNB number range information (cached)
    
    Returns:
        Dict[str, int]: Range info including min, max, total_expected, total_found
    """

def check_hbnb_exists(self, hbnb_number: int) -> Dict[str, bool]:
    """
    Check if HBNB number exists in database
    
    Args:
        hbnb_number (int): HBNB number to check
        
    Returns:
        Dict[str, bool]: Status including exists, full_record, simple_record
    """

def create_simple_record(self, hbnb_number: int, record_line: str) -> bool:
    """
    Create simple HBPR record and invalidate cache
    
    Args:
        hbnb_number (int): HBNB number
        record_line (str): Simple record content (automatically cleaned)
        
    Returns:
        bool: True if creation successful
        
    Features:
    - Automatic cleaning of record_line using cleanHbprRecordContent()
    - Prevention of problematic characters in database storage
    """

def create_full_record(self, hbnb_number: int, record_content: str, 
                      flight_info_match: bool = True) -> bool:
    """
    Create full HBPR record and invalidate cache
    
    Args:
        hbnb_number (int): HBNB number
        record_content (str): Full HBPR record content (automatically cleaned)
        flight_info_match (bool): Whether to validate flight info
        
    Returns:
        bool: True if creation successful
        
    Features:
    - Automatic cleaning of record_content using cleanHbprRecordContent()
    - Prevention of problematic characters in database storage
    """

def delete_simple_record(self, hbnb_number: int) -> bool:
    """
    Delete simple HBPR record and invalidate cache
    
    Args:
        hbnb_number (int): HBNB number to delete
        
    Returns:
        bool: True if deletion successful
    """

def update_missing_numbers_table(self) -> bool:
    """
    Recalculate and update missing numbers table
    
    Returns:
        bool: True if update successful
    """

def get_flight_info(self) -> Optional[Dict[str, str]]:
    """
    Get flight information from database
    
    Returns:
        Optional[Dict[str, str]]: Flight info including flight_id, flight_number, flight_date
    """

def validate_flight_info_match(self, record_content: str) -> bool:
    """
    Validate if record flight info matches database
    
    Args:
        record_content (str): HBPR record content to validate
        
    Returns:
        bool: True if flight info matches
    """

def get_record_summary(self) -> Dict[str, int]:
    """
    Get comprehensive record summary including TKNE count (cached)
    
    Returns:
        Dict[str, int]: Summary including full_records, simple_records, 
                       validated_records, accepted_pax, tkne_count, total_records
    """

def get_accepted_passengers(self, page: int = 1, page_size: int = 50, 
                          sort_by: str = 'boarding_number', 
                          sort_order: str = 'asc',
                          search_term: str = None,
                          class_filter: List[str] = None,
                          ff_level_filter: List[str] = None,
                          ckin_type_filter: List[str] = None,
                          properties_filter: List[str] = None) -> Dict[str, Any]:
    """
    Get accepted passengers with pagination and filtering (cached)
    
    Args:
        page (int): Page number (1-based)
        page_size (int): Number of records per page
        sort_by (str): Sort field ('boarding_number', 'name', 'class', etc.)
        sort_order (str): Sort order ('asc' or 'desc')
        search_term (str): Search term for name or PNR
        class_filter (List[str]): Filter by travel class
        ff_level_filter (List[str]): Filter by frequent flyer level
        ckin_type_filter (List[str]): Filter by check-in type
        properties_filter (List[str]): Filter by properties
        
    Returns:
        Dict[str, Any]: Paginated results with metadata
    """

def get_accepted_passengers_count(self) -> int:
    """
    Get total count of accepted passengers (cached)
    
    Returns:
        int: Total count of accepted passengers
    """

def get_accepted_passengers_stats(self) -> Dict[str, Any]:
    """
    Get accepted passengers statistics (cached)
    
    Returns:
        Dict[str, Any]: Statistics including total_accepted, min_boarding, 
                       max_boarding, avg_bag_piece, avg_bag_weight, total_bag_weight
    """

def get_tkne_count(self) -> int:
    """
    Get count of records with TKNE data
    
    Returns:
        int: Count of records with non-null and non-empty TKNE values
        
    Note:
        Returns 0 if TKNE column doesn't exist in database
    """

def get_all_statistics(self) -> Dict[str, Any]:
    """
    Get all statistics efficiently using caching
    
    Returns:
        Dict[str, Any]: Complete statistics including hbnb_range_info, 
                       missing_numbers, accepted_stats, record_summary, deleted_passengers_stats
    """

def get_deleted_passengers_stats(self) -> Dict[str, Any]:
    """
    Get comprehensive deleted passenger statistics (cached)
    
    Returns:
        Dict[str, Any]: Statistics including:
            - total_deleted: Total number of deleted passengers
            - deleted_with_xres: Count of deleted passengers with XRES property
            - deleted_without_xres: Count of deleted passengers without XRES property
            - xres_boarding_numbers: List of original boarding numbers for XRES deleted passengers
            - original_boarding_numbers: List of original boarding numbers for non-XRES deleted passengers
    """

def add_is_deleted_field_if_not_exists(self) -> bool:
    """
    Add is_deleted field to database schema if not exists and populate with original boarding numbers
    
    Returns:
        bool: True if operation successful
        
    Features:
        - Automatic database schema migration
        - Parsing of DEL command lines for boarding number extraction using regex pattern \\n\\s+DEL\\s+.*?/BN(\\d+)\\s
        - Handles existing databases without field
        - Automatic detection and processing of deleted records
        - Reprocessing protection for databases after rebuilds
    """

def invalidate_statistics_cache(self) -> None:
    """Invalidate all cached statistics"""

def force_refresh_statistics(self) -> None:
    """Force refresh all statistics by clearing cache"""

def _fetch_record_summary(self) -> Dict[str, int]:
    """
    Fetch record summary from database (internal method)
    
    Returns:
        Dict[str, int]: Raw record summary data
    """

def _fetch_accepted_passengers_stats(self) -> Dict[str, Any]:
    """
    Fetch accepted passengers statistics from database (internal method)
    
    Returns:
        Dict[str, Any]: Raw accepted passengers statistics
    """
```

### 4. HBPRProcessor Class - Batch Processing

**Location**: `scripts/hbpr_list_processor.py`

**Purpose**: Processes HBPR list files, extracts records, and creates flight-specific databases with integrated data cleaning.

#### Methods

```python
def __init__(self, input_file: str) -> None:
    """
    Initialize HBPR processor
    
    Args:
        input_file (str): Path to input HBPR text file
    """

def parse_file(self) -> None:
    """
    Parse HBPR text file and extract all records by flight
    
    Features:
    - Integrated data cleaning using validateAndCleanFileContent()
    - Automatic detection of cleaning needs
    - Safe handling of problematic characters
    """

def parse_full_record(self, lines: List[str], start_index: int) -> Tuple[Optional[int], str, int]:
    """
    Parse complete HBPR record and extract flight info and HBNB number
    
    Args:
        lines (List[str]): Input HBPR text file lines
        start_index (int): Starting line index for parsing
        
    Returns:
        Tuple[Optional[int], str, int]: HBNB number, cleaned record content, end index
        
    Features:
    - Automatic cleaning of record_content using cleanHbprRecordContent()
    - Safe handling of binary/hexadecimal characters
    """

def find_missing_numbers(self, flight_id: str) -> List[int]:
    """
    Find missing HBNB numbers for specified flight
    
    Args:
        flight_id (str): Flight identifier
        
    Returns:
        List[int]: Sorted list of missing HBNB numbers
    """

def create_database(self, flight_id: str) -> str:
    """
    Create SQLite database for specified flight
    
    Args:
        flight_id (str): Flight identifier
        
    Returns:
        str: Path to created database file
    """

def store_records(self, flight_id: str, db_file: str) -> None:
    """
    Store records in database with data cleaning
    
    Args:
        flight_id (str): Flight identifier
        db_file (str): Database file path
        
    Features:
    - Automatic cleaning of full_records and simple_records before storage
    - Prevention of problematic characters in database
    """

def process(self) -> None:
    """Process file and create databases for all flights"""

def generate_report(self) -> str:
    """
    Generate processing report
    
    Returns:
        str: Formatted processing report
    """
```

#### Private Methods

```python
def _assign_simple_records(self) -> None:
    """Assign simple records to appropriate flights"""

def _parse_flight_info(self, flight_info: str) -> str:
    """Parse flight information and generate flight ID"""

def _parse_simple_record(self, line: str) -> Optional[int]:
    """Parse simple HBPR record to extract HBNB number"""
```

### 5. DataCleaner Class - Data Sanitization

**Location**: `scripts/data_cleaner.py`

**Purpose**: Provides comprehensive data cleaning and sanitization utilities to prevent problematic characters from entering the system and ensure safe data export.

#### Methods

```python
def clean_text_for_input(text: str, aggressive: bool = False) -> str:
    """
    Clean text for input operations, removing control characters and problematic symbols
    
    Args:
        text (str): Input text to clean
        aggressive (bool): Whether to use aggressive cleaning (removes extended Unicode)
        
    Returns:
        str: Cleaned text safe for processing
        
    Features:
    - Removes ASCII control characters (0-31, 127)
    - Configurable Unicode handling
    - Normalizes whitespace and empty lines
    """

def clean_hbpr_record_content(text: str) -> str:
    """
    Clean HBPR record content specifically for database storage
    
    Args:
        text (str): HBPR record content to clean
        
    Returns:
        str: Cleaned HBPR content safe for database storage
        
    Features:
    - Optimized for HBPR record format
    - Preserves essential formatting
    - Removes binary/hexadecimal artifacts
    """

def clean_text_for_export(text: str) -> str:
    """
    Clean text specifically for export operations (CSV/Excel)
    
    Args:
        text (str): Text to clean for export
        
    Returns:
        str: Text safe for CSV/Excel export
        
    Features:
    - Removes characters problematic for spreadsheet applications
    - Preserves data integrity
    - Safe for CSV and Excel formats
    """

def clean_text_for_database(text: str) -> str:
    """
    Clean text for database storage, removing control characters
    
    Args:
        text (str): Text to clean for database
        
    Returns:
        str: Text safe for database storage
        
    Features:
    - Database-specific cleaning rules
    - Preserves SQL-safe characters
    - Normalizes text formatting
    """

def validate_and_clean_file_content(file_path: str, encoding: str = 'utf-8') -> Tuple[List[str], bool]:
    """
    Read and clean file content, detecting if cleaning was needed
    
    Args:
        file_path (str): Path to file to read and clean
        encoding (str): File encoding to use
        
    Returns:
        Tuple[List[str], bool]: Cleaned lines and whether cleaning was needed
        
    Features:
    - Automatic file reading with encoding handling
    - Line-by-line cleaning
    - Cleaning detection for user awareness
    - Safe fallback for encoding errors
    """

def clean_database_records(db_file: str) -> Dict[str, int]:
    """
    Clean all records in specified database
    
    Args:
        db_file (str): Path to database file to clean
        
    Returns:
        Dict[str, int]: Cleaning results with counts
        
    Features:
    - Batch cleaning of existing database records
    - Progress tracking and reporting
    - Safe database operations
    - Transaction-based updates
    """
```

### 6. CArgs Class - Configuration

**Location**: `scripts/general_func.py`

**Purpose**: Provides system configuration and utility functions for flight operations.

#### Methods

```python
def SubCls2MainCls(self, Subclass: str) -> str:
    """
    Convert sub-class to main class
    
    Args:
        Subclass (str): Sub-class code (F, A, O, J, C, D, R, Z, I)
        
    Returns:
        str: Main class code (F, C, Y)
    """

def ClassBagWeight(self, MainCls: str) -> int:
    """
    Get baggage weight limit by main class
    
    Args:
        MainCls (str): Main class code (F, C, Y)
        
    Returns:
        int: Baggage weight limit in kg
    """

def InfBagWeight(self) -> int:
    """
    Get infant baggage weight allowance
    
    Returns:
        int: Infant baggage weight (23 kg)
    """

def ForeignGoldFlyerBagWeight(self) -> int:
    """
    Get foreign gold frequent flyer baggage weight
    
    Returns:
        int: Foreign gold flyer baggage weight (23 kg)
    """
```

## 🌐 UI Components

### 1. Main UI Coordinator

**Location**: `ui/main.py`

**Purpose**: Coordinates the main application UI, handles navigation, authentication, database selection, and provides native Windows folder picker functionality.

#### Dependencies
```python
import streamlit as st
import os
import tkinter as tk
from tkinter import filedialog
from ui.common import get_icon_base64, apply_global_settings, get_sorted_database_files
from ui.login_page import show_login_page
from ui.home_page import show_home_page
from ui.database_page import show_database_management
from ui.process_records_page import show_process_records
from ui.command_analysis_page import show_command_analysis
from ui.excel_processor_page import show_excel_processor
from ui.settings_page import show_settings
from scripts.hbpr_info_processor import HbprDatabase
```

#### Methods

```python
def main() -> None:
    """
    Main UI function - Application entry point
    
    Features:
    - Session state initialization
    - User authentication management
    - Centralized database selection with location indicators
    - Native Windows folder picker for custom database directories
    - Sidebar navigation with page routing
    - File cleanup on logout and page navigation
    - Visual database location indicators (📁 Custom, 🏠 Default, 📄 Root)
    """
```

#### Key Features

##### Database Selection Enhancement
- **Multi-source discovery**: Searches custom folders, default `databases/` folder, and root directory
- **Visual indicators**: Location-based icons distinguish database sources
  - 📁 Custom folder databases
  - 🏠 Default databases folder
  - 📄 Root directory databases
- **Session persistence**: Custom folder selection persists across navigation

##### Native Windows Integration
- **Folder picker**: Uses `tkinter.filedialog.askdirectory()` for native Windows folder selection
- **Topmost dialog**: Ensures folder picker appears above Streamlit interface
- **Path persistence**: Remembers last selected custom folder location

##### Session State Management
```python
# Key session state variables
st.session_state.current_page          # Current active page
st.session_state.authenticated         # Authentication status
st.session_state.selected_database     # Currently selected database file
st.session_state.available_databases   # List of available database files
st.session_state.custom_db_folder      # Custom database folder path
st.session_state.settings             # Global application settings
st.session_state.view_results_tab     # Current tab in view results page
```

### 2. Authentication System

**Location**: `ui/login_page.py`, `ui/common.py`

```python
def show_login_page() -> None:
    """Display the login page"""

def authenticate_user(username: str) -> bool:
    """
    Authenticate user using SHA256 hashed username
    
    Args:
        username (str): Username to authenticate
        
    Returns:
        bool: True if authentication successful
    """
```

### 3. Home Page

**Location**: `ui/home_page.py`

**Purpose**: Displays system overview with simplified metrics (Max HBNB, Missing Count, Accepted Passengers with infant and class split), quick actions, and refresh.

```python
def show_home_page() -> None:
    """
    Display system overview and quick actions
    
    Features:
    - Database connection status
    - HBNB range information
    - Record counts (total, full, simple, validated)
    - Missing numbers display with pagination
    - Quick action buttons for navigation
    - Statistics refresh functionality
    """
```

### 4. Database Management

**Location**: `ui/database_page.py`

```python
def show_database_management() -> None:
    """Display database management interface"""

def build_database_ui(input_file: str) -> None:
    """
    Build database from uploaded file
    
    Args:
        input_file (str): Path to uploaded HBPR file
    """

def show_database_info() -> None:
    """Show database information and statistics"""

def show_database_maintenance() -> None:
    """
    Show database maintenance operations
    
    Features:
    - Database integrity checks
    - Record validation
    - Data cleaning operations
    - Performance optimization
    """

def show_data_cleaning() -> None:
    """
    Display data cleaning interface
    
    Features:
    - Clean existing database records
    - Remove problematic characters
    - Cleaning progress tracking
    - Results reporting
    - Integration with clean_database_data.py utility
    """
```

### 5. Process Records Page

**Location**: `ui/process_records_page.py`

**Purpose**: Provides interface for processing individual HBPR records and manual input with integrated data cleaning.

```python
def show_process_records_page() -> None:
    """
    Display record processing interface
    
    Features:
    - Database selection
    - HBPR record processing
    - Manual input for full and simple records
    - Validation results display
    - Error handling and user feedback
    - Integrated data cleaning for user input
    """

def validate_full_hbpr_record(record_content: str) -> Tuple[bool, List[str]]:
    """
    Validate full HBPR record with automatic data cleaning
    
    Args:
        record_content (str): Raw HBPR record content
        
    Returns:
        Tuple[bool, List[str]]: Validation result and error messages
        
    Features:
    - Automatic cleaning of user input using cleanHbprRecordContent()
    - Prevention of problematic characters in manual input
    - Comprehensive validation after cleaning
    """
```

### 6. View Results Page

**Location**: `ui/view_results_page.py`

**Purpose**: Displays comprehensive results with statistics, records table, accepted passengers, and export functionality.

```python
def show_view_results_page() -> None:
    """
    Display comprehensive results interface
    
    Features:
    - Statistics tab with detailed metrics
    - Records table with filtering and pagination
    - Accepted passengers tab with advanced filtering
    - Export data functionality
    - Statistics refresh capability
    """

def show_statistics() -> None:
    """
    Display comprehensive statistics
    
    Features:
    - HBNB range information
    - Record counts and validation stats
    - Accepted passengers statistics
    - TKNE count and acceptance rate
    - Missing numbers display
    - Statistics refresh button
    """

def show_records_table() -> None:
    """
    Display records table with filtering
    
    Features:
    - Paginated records display
    - Multi-column filtering
    - Search functionality
    - Export capabilities
    """

def show_accepted_passengers() -> None:
    """
    Display accepted passengers with advanced filtering
    
    Features:
    - Paginated accepted passengers display
    - Multi-criteria filtering (class, FF level, check-in type, properties)
    - Search by name or PNR
    - Sorting by various fields
    - Statistics display
    """

def show_export_data() -> None:
    """
    Display export functionality with integrated data cleaning
    
    Features:
    - Export all records with automatic cleaning
    - Export accepted passengers only with cleaning
    - CSV and Excel format export
    - Safe handling of problematic characters
    - Download links for cleaned data
    - Cleaning status reporting
    """
```

### 7. Settings Page

**Location**: `ui/settings_page.py`

```python
def show_settings() -> None:
    """Display system settings and configuration"""
```

### 8. Common Utilities

**Location**: `ui/common.py`

```python
def get_icon_base64(path: str) -> str:
    """
    Convert icon file to base64 encoding
    
    Args:
        path (str): Path to icon file
        
    Returns:
        str: Base64 encoded icon data
    """

def apply_global_settings() -> None:
    """Apply global settings from session state"""

def create_database_selectbox(label: str = "Select database:", 
                            key: str = None, 
                            default_index: int = 0, 
                            show_flight_info: bool = False,
                            custom_folder: str = None) -> Tuple[str, List[str]]:
    """
    Create database selection widget with custom folder support
    
    Args:
        label (str): Widget label
        key (str): Widget key for session state
        default_index (int): Default selection index
        show_flight_info (bool): Whether to show flight information
        custom_folder (str): Custom database folder path
        
    Returns:
        Tuple[str, List[str]]: Selected database file, all database files
    """

def get_sorted_database_files(sort_by: str = 'creation_time', 
                            reverse: bool = True,
                            custom_folder: str = None) -> List[str]:
    """
    Get sorted list of database files from multiple sources
    
    Args:
        sort_by (str): Sort criteria ('creation_time', 'modification_time', 'name')
        reverse (bool): Whether to reverse sort order
        custom_folder (str): Custom database folder path to include in search
        
    Returns:
        List[str]: Sorted list of database file paths from all sources
        
    Features:
        - Searches custom folder first (if provided)
        - Searches default databases/ folder
        - Searches root directory as fallback
        - Removes duplicates automatically
        - Supports multiple sort criteria
    """

def get_current_database() -> Optional[str]:
    """
    Get currently selected database from session state
    
    Returns:
        Optional[str]: Path to selected database file or None
    """
```

## 🔗 Function Dependencies and Call Hierarchy

### Statistics Management Chain
```
StatisticsManager
├── get_cached_data() → Check cache validity
├── set_cached_data() → Store with timestamp
├── is_cache_valid() → Time-based validation
└── clear_cache() → Invalidate all data

HbprDatabase Statistics Integration
├── get_all_statistics() → Orchestrate all cached stats
├── get_record_summary() → Cached record summary
├── get_accepted_passengers_stats() → Cached accepted stats
├── get_hbnb_range_info() → Cached range info
├── get_missing_hbnb_numbers() → Cached missing numbers
└── Cache invalidation on database modifications
    ├── update_with_chbpr_results()
    ├── create_full_record()
    ├── create_simple_record()
    └── delete_simple_record()
```

### CHbpr Processing Chain
```
CHbpr.run()
├── __GetHbnbNumber()
├── __GetPassengerInfo()
└── __ExtractStructuredData()
    ├── __PsptName()
    ├── __RegularBags()
    ├── __GetChkBag()
    ├── __FlyerBenifit()
    ├── __CaptureCkin()
    └── TKNE extraction
```

### Database Operations Chain
```
HbprDatabase.build_from_hbpr_list()
├── HBPRProcessor.process()
│   ├── parse_file()
│   ├── parse_full_record()
│   └── create_database()
├── find_database()
├── _add_chbpr_fields()
├── StatisticsManager initialization
└── update_missing_numbers_table()
```

### UI Processing Chain
```
main()
├── Session state initialization
├── authenticate_user()
├── apply_global_settings()
├── Database discovery and selection
│   ├── get_sorted_database_files() (with custom_folder support)
│   ├── Database location indicator assignment
│   └── Session state database storage
├── Native Windows folder picker
│   ├── tk.Tk() initialization
│   ├── filedialog.askdirectory()
│   └── Custom folder path persistence
├── Page navigation and routing
│   ├── show_home_page() (real-time system overview)
│   ├── show_database_management()
│   │   └── build_database_ui()
│   ├── show_process_records_page()
│   │   ├── show_process_all_records() (batch processing)
│   │   ├── show_add_edit_record() (single record editing)
│   │   ├── show_simple_record() (simple record creation)
│   │   ├── show_sort_records() (record viewing and filtering)
│   │   └── show_export_data() (data export)
│   ├── show_command_analysis_page()
│   │   ├── import_commands() (command file processing)
│   │   ├── add_edit_command_data() (manual command entry)
│   │   ├── view_command_data() (command viewing)
│   │   └── command_statistics() (command stats)
│   └── show_settings()
└── File cleanup and logout handling
```

## 📊 Data Flow and Processing Pipeline

### 1. File Processing Pipeline
```
Input File → Data Cleaning → HBPRProcessor → Database Creation → CHbpr Validation → Statistics Caching → UI Display
```

**Data Cleaning Integration**:
- **File Reading**: `validateAndCleanFileContent()` removes problematic characters during file parsing
- **Record Processing**: `cleanHbprRecordContent()` sanitizes individual records before database storage
- **Storage**: Clean data stored in database, preventing future export issues

### 2. Manual Input Pipeline
```
UI Input → Data Cleaning → Validation → Database Storage → Cache Invalidation → Statistics Refresh → UI Update
```

**Data Cleaning Integration**:
- **User Input**: `cleanHbprRecordContent()` sanitizes manual input immediately
- **Validation**: Clean data validated before database storage
- **Storage**: Sanitized data stored, preventing future issues

### 3. Statistics Caching Pipeline
```
Database Query → StatisticsManager Cache Check → Return Cached Data or Fetch Fresh → Store in Cache → Return to UI
```

### 4. Authentication Flow
```
Login Page → SHA256 Hash → Validation → Session State → Authenticated UI
```

### 5. Database Folder Selection Flow
```
Folder Picker Button → Native Windows Dialog → Path Selection → Session Storage → Database Discovery → UI Refresh
```

### 6. Accepted Passengers Processing Pipeline
```
Database Query → Filter by boarding_number IS NOT NULL → Apply Filters → Pagination → Statistics Calculation → UI Display
```

### 7. TKNE-Based Acceptance Rate Calculation
```
Database Query → Count records with TKNE IS NOT NULL AND TKNE != '' → Count accepted passengers → Calculate rate → UI Display
```

### 8. Data Export Pipeline with Cleaning
```
Database Query → Data Extraction → Data Cleaning → Format Conversion → File Generation → Download
```

**Data Cleaning Integration**:
- **Export Preparation**: `cleanTextForExport()` sanitizes data before CSV/Excel creation
- **Format Safety**: Ensures compatibility with spreadsheet applications
- **Data Integrity**: Preserves essential information while removing problematic characters

## 🗄️ Database Schema

### Core Tables

#### hbpr_full_records
```sql
CREATE TABLE hbpr_full_records (
    hbnb_number INTEGER PRIMARY KEY,
    record_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bol_duplicate BOOLEAN DEFAULT 0,
    -- CHbpr validation fields
    is_validated BOOLEAN DEFAULT 0,
    is_valid BOOLEAN,
    boarding_number INTEGER,
    pnr TEXT,
    name TEXT,
    seat TEXT,
    class TEXT,
    destination TEXT,
    bag_piece INTEGER,
    bag_weight INTEGER,
    bag_allowance INTEGER,
    ff TEXT,
    pspt_name TEXT,
    pspt_exp_date TEXT,
    ckin_msg TEXT,
    asvc_msg TEXT,
    expc_piece INTEGER,
    expc_weight INTEGER,
    asvc_piece INTEGER,
    fba_piece INTEGER,
    ifba_piece INTEGER,
    flyer_benefit INTEGER,
    is_ca_flyer BOOLEAN,
    inbound_flight TEXT,
    outbound_flight TEXT,
    properties TEXT,
    error_count INTEGER,
    error_baggage TEXT,
    error_passport TEXT,
    error_name TEXT,
    error_visa TEXT,
    error_other TEXT,
    validated_at TIMESTAMP,
    tkne TEXT,
    is_deleted INTEGER DEFAULT 0,
    has_infant BOOLEAN DEFAULT 0
);
```

#### hbpr_simple_records
```sql
CREATE TABLE hbpr_simple_records (
    hbnb_number INTEGER PRIMARY KEY,
    record_line TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### missing_numbers
```sql
CREATE TABLE missing_numbers (
    hbnb_number INTEGER PRIMARY KEY
);
```

#### flight_info
```sql
CREATE TABLE flight_info (
    flight_id TEXT PRIMARY KEY,
    flight_number TEXT,
    flight_date TEXT
);
```

## 🚀 Usage Examples

### Statistics Management
```python
# Initialize database with statistics manager
db = HbprDatabase("my_database.db")

# Get all statistics efficiently (cached)
all_stats = db.get_all_statistics()
record_summary = all_stats['record_summary']
accepted_stats = all_stats['accepted_stats']

# Force refresh statistics
db.force_refresh_statistics()

# Invalidate specific cache
db.invalidate_statistics_cache()
```

### Processing HBPR Records
```python
# Create CHbpr instance
chbpr = CHbpr()
chbpr.run(hbpr_content)

# Check validity
if chbpr.is_valid():
    print(f"Record {chbpr.HbnbNumber} is valid")
    structured_data = chbpr.get_structured_data()
    
# Update database (automatically invalidates cache)
db.update_with_chbpr_results(chbpr)
```

### Database Operations with Caching
```python
# Initialize database
db = HbprDatabase()
db.find_database()

# Build from file
processor = db.build_from_hbpr_list("sample_hbpr_list.txt")

# Get cached statistics
stats = db.get_validation_stats()
missing = db.get_missing_hbnb_numbers()
record_summary = db.get_record_summary()

# Get TKNE count
tkne_count = db.get_tkne_count()
```

### Accepted Passengers Operations
```python
# Get accepted passengers with filtering
accepted_data = db.get_accepted_passengers(
    page=1,
    page_size=50,
    sort_by='boarding_number',
    sort_order='asc',
    search_term='John',
    class_filter=['F', 'C'],
    ff_level_filter=['GOLD'],
    ckin_type_filter=['ONLINE'],
    properties_filter=['VIP']
)

# Get accepted passengers statistics
accepted_stats = db.get_accepted_passengers_stats()
print(f"Total accepted: {accepted_stats['total_accepted']}")
print(f"Boarding range: {accepted_stats['min_boarding']} - {accepted_stats['max_boarding']}")
```

### Batch Processing
```python
# Process HBPR file
processor = HBPRProcessor("input_file.txt")
processor.process()

# Generate report
report = processor.generate_report()
```

### Data Cleaning Operations
```python
# Import data cleaning utilities
from scripts.data_cleaner import clean_hbpr_record_content, validate_and_clean_file_content

# Clean individual HBPR record
cleaned_content = clean_hbpr_record_content(raw_hbpr_content)

# Clean file content with validation
cleaned_lines, needs_cleaning = validate_and_clean_file_content("input_file.txt")
if needs_cleaning:
    print("File was cleaned during processing")

# Clean text for export
export_safe_text = clean_text_for_export(database_content)
```

### Enhanced Database Discovery
```python
# Get databases from multiple sources
from ui.common import get_sorted_database_files

# Include custom folder in search
custom_folder = "C:/MyDatabases"
db_files = get_sorted_database_files(
    sort_by='creation_time', 
    reverse=True, 
    custom_folder=custom_folder
)

# Create database selectbox with custom folder support
selected_db, all_dbs = create_database_selectbox(
    label="Select Database:",
    show_flight_info=True,
    custom_folder=custom_folder
)
```

### Native Windows Folder Picker Integration
```python
# Example of folder picker functionality (from main.py)
import tkinter as tk
from tkinter import filedialog

# Create hidden root window
root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)

# Open native Windows folder dialog
folder_path = filedialog.askdirectory(
    title="Select Database Folder",
    initialdir=os.getcwd()
)

# Cleanup
root.destroy()

# Store in session state
if folder_path:
    st.session_state.custom_db_folder = folder_path
```

### UI Statistics Display
```python
# In Streamlit UI components
all_stats = db.get_all_statistics()
record_summary = all_stats['record_summary']
accepted_stats = all_stats['accepted_stats']

# Display metrics
st.metric("Total Records", record_summary['total_records'])
st.metric("Accepted Pax", record_summary['accepted_pax'])

# Calculate and display acceptance rate (TKNE-based)
if record_summary['tkne_count'] > 0:
    acceptance_rate = (record_summary['accepted_pax'] / record_summary['tkne_count']) * 100
    st.metric("Acceptance Rate", f"{acceptance_rate:.1f}%")
else:
    st.metric("Acceptance Rate", "0.0%")

# Refresh statistics button
if st.button("🔄 Refresh Statistics"):
    db.invalidate_statistics_cache()
    st.rerun()
```

## 🔧 Error Handling

### Exception Types
- `FileNotFoundError`: Database or input file not found
- `ValueError`: Invalid HBNB number or data format
- `sqlite3.Error`: Database operation errors
- `sqlite3.OperationalError`: Column not found (for TKNE compatibility)
- `Exception`: General processing errors
- `UnicodeDecodeError`: File encoding issues during reading
- `DataCleaningError`: Data cleaning operation failures

### Error Categories
- **Baggage**: Weight/piece validation errors
- **Passport**: Expiration date issues
- **Name**: Name matching inconsistencies  
- **Visa**: Visa information problems
- **Other**: General processing errors
- **Data Cleaning**: Character encoding and sanitization issues
- **Export**: Format compatibility problems

### TKNE Compatibility Handling
```python
# Example of TKNE column existence check
try:
    cursor.execute("SELECT COUNT(*) FROM hbpr_full_records WHERE tkne IS NOT NULL AND tkne != ''")
    tkne_count = cursor.fetchone()[0]
except sqlite3.OperationalError:
    # TKNE column doesn't exist in this database
    tkne_count = 0
```

## 🔐 Security Features

### Authentication
- SHA256-based username validation
- Session state management
- Automatic logout and cleanup

### Data Protection
- Obfuscated credentials in source code
- Secure session handling
- File cleanup on navigation/logout

## 📈 Performance Optimizations

### Statistics Caching
- **Time-based cache**: 5-minute cache duration for statistics
- **Automatic invalidation**: Cache cleared on database modifications
- **Efficient queries**: Optimized SQL queries for statistics
- **Memory management**: Cache size controlled by time expiration

### Database Operations
- **Connection pooling**: Efficient database connection management
- **Indexed queries**: Proper indexing for performance
- **Batch operations**: Bulk operations where possible

### UI Responsiveness
- **Lazy loading**: Statistics loaded on demand
- **Pagination**: Large datasets displayed in manageable chunks
- **Background processing**: Heavy operations don't block UI

### Data Cleaning Performance
- **Efficient regex patterns**: Optimized character replacement operations
- **Batch processing**: Database cleaning operations use transactions
- **Memory management**: Line-by-line processing for large files
- **Caching**: Cleaning results cached where appropriate

This technical documentation provides comprehensive information about the system's functions, their parameters, return types, and relationships for developers working with the HBPR Processing System, including all recent enhancements for statistics management, accepted passengers tracking, TKNE-based calculations, and comprehensive data cleaning solutions for preventing and resolving binary/hexadecimal character issues.