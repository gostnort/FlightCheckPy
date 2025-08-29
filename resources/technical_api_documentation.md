# Flight Data Processing System - Technical API Documentation

## Project Overview

The Flight Data Processing System is a comprehensive Python application for processing and analyzing HBPR (Hotel Booking Passenger Record) data. It utilizes a centralized in-memory database architecture for high performance and data consistency, with automatic persistence to disk. The system validates and parses records, stores them in SQLite databases, and provides a modern Streamlit-based UI for database building, record processing, airline command analysis with timeline versioning, and Excel output generation by mapping TKNE to CKIN CCRD data.

**Key Features:**
- **Centralized In-Memory Database**: High-performance architecture where the entire UI shares a single database connection, managed by a global manager.
- **Automatic Data Persistence**: Changes made in memory are automatically saved back to the source file when switching databases or modifying records.
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
- **Missing Boarding Number Detection**: Intelligent detection of discontinuous boarding numbers with automatic exclusion of deleted passengers to prevent duplicate reporting
- **Reusable UI Components**: Modular component architecture for consistent statistics display with separated calculation and presentation logic

## 🏗️ System Architecture

### Core Components

```
FlightCheckPy/
├── scripts/                    # Core processing modules
│   ├── hbpr_info_processor.py  # HBPR record processing, validation, and statistics
│   ├── hbpr_list_processor.py  # Batch processing and database creation
│   ├── excel_processor.py      # Excel-to-EMD processing via TKNE/CKIN CCRD mapping
│   ├── command_processor.py    # Airline command processing and timeline management
│   ├── general_func.py         # Utility functions and configuration
│   └── data_cleaner.py        # Data cleaning and sanitization utilities
├── ui/                         # Web UI components
│   ├── main.py                 # Main UI coordinator with Windows integration
│   ├── db_management.py        # Centralized in-memory database management and utilities
│   ├── login_page.py           # Authentication interface
│   ├── home_page.py            # System overview with real-time statistics
│   ├── database_page.py        # Database management and construction
│   ├── process_records_page.py # Record processing navigation (batch/single/simple/sort/export)
│   ├── command_analysis_page.py # Command processing, timeline view, and maintenance
│   ├── excel_processor_page.py # Excel upload and EMD export UI
│   ├── settings_page.py        # System configuration and about info
│   ├── components/             # Reusable UI components
│   │   ├── main_stats.py       # Main statistics display and UI logic
│   │   ├── deleted_stats.py    # Deleted/missing passenger calculation functions
│   │   └── home_metrics.py     # Home page metrics and debug information
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
def export_as_origin_txt(conn: sqlite3.Connection) -> str:
    """
    Export raw text format, converting literal '\\n' to newlines
    
    Args:
        conn (sqlite3.Connection): The database connection object
        
    Returns:
        str: Formatted raw text content
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

def clean_database_connection(conn: sqlite3.Connection) -> bool:
    """
    Clean all records in a database via a connection object
    
    Args:
        conn (sqlite3.Connection): Connection to the database to clean
        
    Returns:
        bool: True if the operation was successful
    """
```

**UI Integration**: Available through "Clean Database Data" button in `ui/database_page.py`

### Deleted Passenger Analytics & Missing Boarding Number Detection

The system provides comprehensive tracking and analysis of deleted passengers with automatic classification and original boarding number extraction, plus intelligent detection of missing boarding numbers with duplicate prevention.

**Locations**: 
- `scripts/hbpr_info_processor.py` - Deleted passenger identification and statistics
- `ui/components/deleted_stats.py` - Missing boarding number calculation
- `ui/components/main_stats.py` - Unified display logic

**Purpose**: Identifies and categorizes deleted passengers by XRES property, extracts their original boarding numbers from DEL command lines, and detects truly missing boarding numbers by excluding deleted passengers to prevent duplicate reporting.

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

**Missing Boarding Number Detection**:
```python
# Step 1: Find all discontinuous boarding numbers
missing_numbers = expected_range - existing_numbers

# Step 2: Exclude deleted passenger boarding numbers
deleted_boarding_numbers = xres_boarding_numbers + non_xres_boarding_numbers
truly_missing_numbers = missing_numbers - deleted_boarding_numbers

# Result: Only truly missing boarding numbers (not deleted passengers)
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

def get_missing_boarding_numbers(db) -> List[int]:
    """
    Calculate truly missing boarding numbers excluding deleted passengers
    
    Args:
        db: HbprDatabase instance
        
    Returns:
        List[int]: Truly missing boarding numbers (not including deleted passengers)
        
    Features:
        - Detects discontinuous boarding number sequences
        - Excludes deleted passenger boarding numbers to prevent duplication
        - Returns sorted list of genuinely missing numbers
        - Integrates with deleted passenger statistics
    """
```

#### Integration Points
- **Statistics Caching**: Integrated with StatisticsManager for efficient retrieval
- **UI Components**: Separated calculation (deleted_stats.py) and display (main_stats.py) logic
- **Database Migration**: Automatic field creation and data population on first use
- **Cache Invalidation**: Statistics cache cleared on database modifications
- **Debug Information**: Complete boarding number lists included in debug output (home_metrics.py)
- **Unified Display**: Deleted passengers and missing boarding numbers shown together in two-column layout

### Reusable UI Components

The system implements a modular component architecture with separated calculation and presentation logic for consistent statistics display across multiple pages.

**Location**: `ui/components/`

**Purpose**: Provides reusable, maintainable UI components with clear separation of concerns - calculation functions separated from display logic for better maintainability and testability.

#### Component Structure

```
ui/components/
├── main_stats.py          # UI display logic and presentation (all display functions)
├── deleted_stats.py       # Calculation functions only (deleted/missing passenger calculations)
└── home_metrics.py        # Flight summary and comprehensive debug information
```

#### Key Functions

**main_stats.py**:
```python
def display_main_statistics(all_stats: Dict[str, Any], db: HbprDatabase = None) -> None:
    """
    Display main HBPR statistics in reusable format with unified deleted/missing passenger display
    
    Args:
        all_stats: Complete statistics dictionary
        db: Database instance for missing boarding number calculation (optional)
    
    Features:
        - Max HBNB, Missing Count, Accepted Passengers metrics
        - Unified deleted passenger and missing boarding number display in two-column layout
        - Consistent formatting across pages
        - Intelligent display logic (info message when no data, columns when data exists)
    """

def get_and_display_main_statistics(db: HbprDatabase) -> Dict[str, Any]:
    """
    Get all statistics from database and display them with missing boarding numbers
    
    Returns:
        Dict[str, Any]: Complete statistics for additional processing
        
    Features:
        - Single function call for complete statistics display
        - Integrated missing boarding number calculation and display
        - Error handling and user feedback
        - Automatic caching through database layer
    """

def display_deleted_stats(deleted_stats: Dict[str, Any]) -> None:
    """
    Display merged deleted passenger statistics
    
    Features:
        - Combined XRES and non-XRES deleted passengers in single metric
        - Intelligent boarding number list truncation (40 numbers max)
        - Consistent "Del in Records" metric display
    """

def display_missing_boarding_numbers(missing_numbers: List[int]) -> None:
    """
    Display missing boarding number statistics
    
    Features:
        - Missing boarding number count and list display
        - Intelligent truncation for large lists (40 numbers max)
        - Integration with deleted passenger exclusion logic
    """

def get_and_display_deleted_stats(db: HbprDatabase) -> None:
    """
    Get and display comprehensive deleted passenger statistics with missing boarding numbers
    
    Features:
        - Complete deleted passenger statistics retrieval and display
        - Missing boarding number calculation and display
        - Error handling for missing data
        - Integration with statistics caching
    """
```

**deleted_stats.py**:
```python
def get_missing_boarding_numbers(db: HbprDatabase) -> List[int]:
    """
    Calculate truly missing boarding numbers excluding deleted passengers (pure calculation)
    
    Args:
        db: HbprDatabase instance
        
    Returns:
        List[int]: Truly missing boarding numbers (not including deleted passengers)
        
    Features:
        - Detects discontinuous boarding number sequences
        - Excludes deleted passenger boarding numbers to prevent duplication
        - Returns sorted list of genuinely missing numbers
        - Pure calculation function with no UI dependencies
        - Integrates with deleted passenger statistics for exclusion logic
    """
```

**home_metrics.py**:
```python
def create_or_refresh_views() -> None:
    """
    Create views used by the home page. Idempotent.
    
    Views:
    - vw_home_accepted_counts: totals for accepted pax (adults), infants, J/Y adult split
    - vw_home_flags: ID staff (SA, PAD-2, PAD-SA) counts by class, NOSHOW by class, INAD total
    
    Features:
    - Deduplication using COUNT(DISTINCT hbnb_number) to prevent duplicate counting
    - ID staff identification for SA, PAD-2, and PAD-SA properties
    - NOSHOW calculation excluding XRES and all ID staff types
    """

def get_sy_compartments() -> Optional[Tuple[int, int]]:
    """
    Find the latest SY command matching current flight in DB and parse CNF.
    
    Returns:
        Optional[Tuple[int, int]]: (j_compartment, y_compartment) if found
        
    Features:
    - Looks up flight in table flight_info
    - Finds newest matching command in table commands where command_type = 'SY' and is_latest = 1
    - Parses CNF/JxYy patterns from command text
    """

def get_home_summary() -> Dict[str, Any]:
    """
    Get flight summary data for home page display
    
    Returns:
        Dict[str, Any]: Complete flight summary including:
            - flight_number, flight_date: Flight identification
            - total_accepted, infant_count: Passenger totals
            - accepted_business, accepted_economy: Class breakdown
            - id_j, id_y: ID staff counts by class (SA, PAD-2, PAD-SA)
            - noshow_j, noshow_y: No-show counts by class
            - inad_total: INAD passenger count
            - j_cnf, y_cnf: Compartment configuration from SY commands
            - ratio: Load factor percentage
            
    Features:
    - Ensures views exist before querying
    - Deduplication logic prevents double-counting passengers with multiple ID staff properties
    - Integrates with command analysis for compartment configuration
    """

def get_debug_data() -> Dict[str, object]:
    """
    Return debug data for manual verification of statistics
    
    Returns:
        Dict[str, object]: Debug data including:
            - class_breakdown: Total counts by class with boarding number status
            - xres_counts: XRES counts by class (deduplicated)
            - id_staff_counts: ID staff counts by class (SA, PAD-2, PAD-SA, deduplicated)
            - empty_properties: Empty properties counts by class
            - xres_samples: Sample XRES records
            - id_staff_samples: Sample ID staff records
            - noshow_samples: Sample no-show records
            
    Features:
    - Consistent use of COUNT(DISTINCT hbnb_number) for accurate counts
    - Sample records for manual verification
    - Comprehensive breakdown for troubleshooting
    """

def get_debug_summary() -> str:
    """
    Get formatted debug summary string for manual verification with complete boarding number information
    
    Returns:
        str: Formatted debug information including:
            - Complete deleted passenger boarding number lists (XRES and non-XRES)
            - Complete missing boarding number lists (excluding deleted passengers)
            - Class breakdown with boarding number statistics
            - XRES, ID staff, and empty properties counts
            - Sample records for each category
            - Error handling for database issues
            
    Features:
    - Human-readable formatting with complete boarding number visibility
    - Comprehensive statistics breakdown
    - Complete boarding number lists in debug mode (no truncation)
    - Sample data for verification
    - Integration with deleted passenger and missing boarding number calculations
    - Exception handling with error reporting
    """
```

#### Component Features
- **Separation of Concerns**: Clear division between calculation logic and UI presentation
- **Consistent Display**: Identical appearance and behavior across pages
- **Intelligent Truncation**: Boarding numbers display with enhanced limits (40 numbers max in UI)
- **Complete Debug Information**: Full boarding number lists available in debug mode without truncation
- **Duplicate Prevention**: Missing boarding numbers exclude deleted passengers automatically
- **Error Handling**: Graceful fallback for missing or invalid data
- **Modular Design**: Easy to add to new pages or modify existing displays
- **Performance**: Leverages existing statistics caching infrastructure
- **Unified Layout**: Deleted passengers and missing boarding numbers displayed together in two-column format

#### Usage Examples
```python
# In home page or database page - unified display with missing boarding numbers
from ui.components.main_stats import get_and_display_main_statistics
# db_manager provides the database connection automatically
from ui.db_management import db_manager
db = db_manager.get_database()
all_stats = get_and_display_main_statistics(db)

# For deleted passenger statistics with missing boarding numbers
from ui.components.main_stats import get_and_display_deleted_stats
db = db_manager.get_database()
get_and_display_deleted_stats(db)

# For missing boarding number calculation only (pure function)
from ui.components.deleted_stats import get_missing_boarding_numbers
db = db_manager.get_database()
missing_numbers = get_missing_boarding_numbers(db)

# For flight summary display
from ui.components.home_metrics import get_home_summary
summary = get_home_summary()

# For complete debug information with full boarding number lists
from ui.components.home_metrics import get_debug_summary
debug_info = get_debug_summary()
# Contains complete deleted passenger and missing boarding number lists

# Separated calculation and display approach
from ui.components.deleted_stats import get_missing_boarding_numbers
from ui.components.main_stats import display_missing_boarding_numbers

db = db_manager.get_database()
missing_numbers = get_missing_boarding_numbers(db)  # Pure calculation
display_missing_boarding_numbers(missing_numbers)  # UI display
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

### 1. EnhancedGlobalDatabaseManager Class - Central DB Management

**Location**: `ui/db_management.py`

**Purpose**: Manages the centralized, in-memory database connection for the entire application, including automatic saving logic. This is the single entry point for all database interactions.

#### Methods

```python
def get_database(self) -> HbprDatabaseWithAutoSave:
    """
    Get the singleton instance of the in-memory database with auto-save capabilities.
    
    Returns:
        HbprDatabaseWithAutoSave: The active database instance.
    """

def is_available(self) -> bool:
    """
    Check if a database is currently loaded into memory.
    
    Returns:
        bool: True if a database is available, False otherwise.
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

**Purpose**: Manages all database operations for HBPR records including creation, querying, and maintenance. Operates on a provided database connection.

#### Attributes
- `conn: sqlite3.Connection` - The active database connection.

#### Methods

```python
def __init__(self, conn: sqlite3.Connection) -> None:
    """
    Initialize with a database connection.
    
    Args:
        conn (sqlite3.Connection): An active sqlite3 connection object.
        
    Raises:
        ValueError: If the connection object is not provided.
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
    Update database with CHbpr validation results
    
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
    Get validation statistics
    
    Returns:
        Dict[str, int]: Statistics including total_records, validated_records, 
                       valid_records, invalid_records
    """

def get_missing_hbnb_numbers(self) -> List[int]:
    """
    Get list of missing HBNB numbers
    
    Returns:
        List[int]: Sorted list of missing HBNB numbers
    """

def get_hbnb_range_info(self) -> Dict[str, int]:
    """
    Get HBNB number range information
    
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
    Create simple HBPR record
    
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
    Create full HBPR record
    
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
    Delete simple HBPR record
    
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
    Get comprehensive record summary including TKNE count
    
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
    Get accepted passengers with pagination and filtering
    
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
    Get total count of accepted passengers
    
    Returns:
        int: Total count of accepted passengers
    """

def get_accepted_passengers_stats(self) -> Dict[str, Any]:
    """
    Get accepted passengers statistics
    
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
    Get all statistics efficiently
    
    Returns:
        Dict[str, Any]: Complete statistics including hbnb_range_info, 
                       missing_numbers, accepted_stats, record_summary, deleted_passengers_stats
    """

def get_deleted_passengers_stats(self) -> Dict[str, Any]:
    """
    Get comprehensive deleted passenger statistics
    
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
```

### 4. HBPRProcessor Class - Batch Processing

**Location**: `scripts/hbpr_list_processor.py`

**Purpose**: Processes HBPR list files, extracts records, and populates a database via a connection, with integrated data cleaning.

#### Methods

```python
def __init__(self, conn: sqlite3.Connection) -> None:
    """
    Initialize HBPR processor
    
    Args:
        conn (sqlite3.Connection): An active database connection object.
    """

def process(self, file_content: str) -> None:
    """Process file content and populate the database."""

def parse_file_content(self, file_content: str) -> None:
    """
    Parse HBPR text file content and extract all records by flight
    
    Features:
    - Integrated data cleaning
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

def create_tables_if_not_exist(self) -> None:
    """Create the necessary SQLite tables if they do not exist."""

def store_records(self, flight_id: str) -> None:
    """
    Store records in database with data cleaning
    
    Args:
        flight_id (str): Flight identifier
        
    Features:
    - Automatic cleaning of full_records and simple_records before storage
    - Prevention of problematic characters in database
    """

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

def clean_database_connection(conn: sqlite3.Connection) -> bool:
    """
    Clean all records in specified database via a connection
    
    Args:
        conn (sqlite3.Connection): Connection to the database to clean
        
    Returns:
        bool: True if the operation was successful
        
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

## 📋 Data Filtering & Configuration System

### Filter Configuration

**Location**: `resources/filter_config.json`

**Purpose**: Centralized configuration for controlling data filtering in the UI layer, managing which CKIN types and Properties are displayed in filtering interfaces.

#### Configuration Structure

The filter configuration uses a simplified two-tier approach:

```json
{
  "description": "数据过滤配置文件 - 控制CKIN类型和Properties在筛选界面中的显示",
  "description_en": "Data filter configuration - Controls display of CKIN types and Properties in filtering interface",
  "excluded_ckin_types": [
    "FABS", "BRND", "LKCK", "CCQT", "CCAX", "CCVI"
  ],
  "excluded_properties": [
    "ADV", "IDOCS", "PEK", "LAX", "ASR", "RES", "OSR", "ABP", "M1/0", "F1/0", "API", "AQQ"
  ],
  "excluded_property_patterns": [
    "ESTA*", "TKNE*", "FBA*", "IFBA*", "BAG*", "FOID/*", "TMC*"
  ]
}
```

#### Configuration Components

1. **`excluded_ckin_types`**: List of CKIN types to hide from filtering interfaces
   - Contains system/administrative CKIN types not relevant for user filtering
   - Examples: `FABS`, `BRND`, `LKCK`

2. **`excluded_properties`**: List of specific properties to exclude from filtering
   - Contains system-specific properties, destination codes, gender markers, etc.
   - Examples: `PEK`, `LAX`, `M1/0`, `F1/0`, `API`

3. **`excluded_property_patterns`**: Pattern-based exclusion rules using wildcards
   - Uses `*` wildcard for prefix matching
   - Examples: `ESTA*` (excludes all ESTA-prefixed properties), `TKNE*`, `BAG*`

#### Integration Points

**UI Layer Processing**: `ui/process_records/sort_records.py`

```python
def load_filter_config():
    """Load filtering configuration from resources/filter_config.json"""
    config_path = os.path.join('resources', 'filter_config.json')
    # Returns: excluded_ckin_types, excluded_properties, excluded_patterns

def should_exclude_property(prop, excluded_props, excluded_patterns):
    """Check if property should be excluded from UI filtering"""
    # Handles single-character filtering, exact matching, and pattern matching
```

**Data Layer Processing**: `scripts/hbpr_info_processor.py`

The core data processor handles only essential business logic filtering:
- `FF/` and `FR/` attributes (frequent flyer information with member number removal)
- `R` attributes (seat information)
- `SNR` attributes (special seat requests)

#### Filtering Logic

1. **Single Character Exclusion**: Automatically excludes single-character properties (cabin classes)
2. **Exact Match**: Properties in `excluded_properties` list are filtered out
3. **Pattern Matching**: Properties matching `excluded_property_patterns` wildcards are excluded
4. **Property Normalization**: Properties are standardized (e.g., `INF1/0` → `INF`) before filtering

#### Benefits

- **Separation of Concerns**: Core processing vs. UI filtering logic separated
- **User Experience**: Only meaningful, user-relevant properties displayed in filters
- **Maintainability**: Centralized configuration easy to modify
- **Performance**: Reduced UI complexity with fewer filter options

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
from ui.db_management import get_icon_base64, apply_global_settings, create_database_selectbox, enhanced_database_status_widget
from ui.login_page import show_login_page
from ui.home_page import show_home_page
from ui.database_page import show_database_management
from ui.process_records_page import show_process_records
from ui.command_analysis_page import show_command_analysis
from ui.excel_processor_page import show_excel_processor
from ui.settings_page import show_settings
```

#### Methods

```python
def main() -> None:
    """
    Main UI function - Application entry point
    
    Features:
    - Session state initialization
    - User authentication management
    - Centralized database selection with location indicators and in-memory loading
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
st.session_state.current_memory_db     # Identifier for the in-memory database connection
st.session_state.current_db_name       # Filename of the currently loaded database
st.session_state.custom_db_folder      # Custom database folder path
st.session_state.settings             # Global application settings
st.session_state.view_results_tab     # Current tab in view results page
```

### 2. Authentication System

**Location**: `ui/login_page.py`, `ui/db_management.py`

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

### 6. Common Utilities

**Location**: `ui/db_management.py`

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
HbprDatabase Statistics Integration
├── get_all_statistics() → Orchestrate all stats
├── get_record_summary() → Record summary
├── get_accepted_passengers_stats() → Accepted pax stats
├── get_hbnb_range_info() → Range info
├── get_missing_hbnb_numbers() → Missing numbers
└── Automatic data refresh on DB change
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
db_manager.get_database()
├── HbprDatabase instance
│   ├── get_hbpr_record()
│   └── update_with_chbpr_results()
└── HBPRProcessor.process()
    ├── parse_file_content()
    └── store_records()
```

### UI Processing Chain
```
main()
├── Session state initialization
├── authenticate_user()
├── apply_global_settings()
├── Database discovery and selection (loads to memory)
│   ├── get_sorted_database_files() (with custom_folder support)
│   ├── create_database_selectbox() (triggers in-memory load)
│   └── Session state database storage
├── Native Windows folder picker
│   ├── tk.Tk() initialization
│   ├── filedialog.askdirectory()
│   └── Custom folder path persistence
├── Page navigation and routing
│   ├── show_home_page() (real-time system overview)
│   ├── show_database_management()
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
Input File → Data Cleaning → HBPRProcessor → In-Memory Database Population → CHbpr Validation → UI Display
```

**Data Cleaning Integration**:
- **File Reading**: `validateAndCleanFileContent()` removes problematic characters during file parsing
- **Record Processing**: `cleanHbprRecordContent()` sanitizes individual records before database storage
- **Storage**: Clean data stored in database, preventing future export issues

### 2. Manual Input Pipeline
```
UI Input → Data Cleaning → Validation → In-Memory Database Update → Auto-Save → UI Update
```

**Data Cleaning Integration**:
- **User Input**: `cleanHbprRecordContent()` sanitizes manual input immediately
- **Validation**: Clean data validated before database storage
- **Storage**: Sanitized data stored, preventing future issues

### 3. Authentication Flow
```
Login Page → SHA256 Hash → Validation → Session State → Authenticated UI
```

### 4. Database Folder Selection Flow
```
Folder Picker Button → Native Windows Dialog → Path Selection → Session Storage → Database Discovery → UI Refresh
```

### 5. Accepted Passengers Processing Pipeline
```
In-Memory DB Query → Filter by boarding_number IS NOT NULL → Apply Filters → Pagination → Statistics Calculation → UI Display
```

### 6. TKNE-Based Acceptance Rate Calculation
```
In-Memory DB Query → Count records with TKNE IS NOT NULL AND TKNE != '' → Count accepted passengers → Calculate rate → UI Display
```

### 7. Data Export Pipeline with Cleaning
```
In-Memory DB Query → Data Extraction → Data Cleaning/Formatting → File Generation → Download
```

**Data Cleaning Integration**:
- **Export Preparation**: `export_as_origin_txt` now handles raw export correctly.
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
# All database access is now through the global manager
from ui.db_management import db_manager

# Get the database instance (assuming one is loaded in the UI)
db = db_manager.get_database()

# Get all statistics efficiently
all_stats = db.get_all_statistics()
record_summary = all_stats['record_summary']
accepted_stats = all_stats['accepted_stats']

# Statistics are managed automatically, manual refresh is done via UI
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
    
# Update database (triggers auto-save)
db = db_manager.get_database()
db.update_with_chbpr_results(chbpr)
```

### Database Operations
```python
from ui.db_management import db_manager

# Get the database instance
db = db_manager.get_database()

# Get statistics
stats = db.get_validation_stats()
missing = db.get_missing_hbnb_numbers()
record_summary = db.get_record_summary()

# Get TKNE count
tkne_count = db.get_tkne_count()
```

### Accepted Passengers Operations
```python
# Get accepted passengers with filtering
db = db_manager.get_database()
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
# Batch processing is now handled within the UI
# See ui/database_page.py for building a database from a file,
# which uses HBPRProcessor internally.
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
```

### Enhanced Database Discovery
```python
# Get databases from multiple sources
from ui.db_management import get_sorted_database_files

# Include custom folder in search
custom_folder = "C:/MyDatabases"
db_files = get_sorted_database_files(
    sort_by='creation_time', 
    reverse=True, 
    custom_folder=custom_folder
)

# Create database selectbox with custom folder support
# This is handled within ui/main.py
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
db = db_manager.get_database()
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
    # Invalidation is handled by db modifications, refresh is st.rerun()
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

### In-Memory Database
- The application now runs entirely on an in-memory database, minimizing disk I/O for all operations.
- **Automatic Persistence**: A robust auto-save mechanism ensures data is written back to the original file upon modification or when switching databases, preventing data loss.

### UI Responsiveness
- **Lazy loading**: Statistics loaded on demand
- **Pagination**: Large datasets displayed in manageable chunks

### Data Cleaning Performance
- **Efficient regex patterns**: Optimized character replacement operations
- **Batch processing**: Database cleaning operations use transactions
- **Memory management**: Line-by-line processing for large files

This technical documentation provides comprehensive information about the system's functions, their parameters, return types, and relationships for developers working with the HBPR Processing System, including all recent enhancements for the in-memory database architecture, automatic persistence, and comprehensive data cleaning solutions.