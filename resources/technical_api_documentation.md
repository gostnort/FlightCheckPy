# Flight Data Processing System - Technical API Documentation

## Project Overview

The Flight Data Processing System is a comprehensive Python application designed to process and analyze passenger records from HBPR (Hotel Booking Passenger Record) format. The system provides data validation, structured parsing, database storage, and a modern web-based UI for data management and analysis.

## 🏗️ System Architecture

### Core Components

```
FlightCheckPy/
├── scripts/                    # Core processing modules
│   ├── hbpr_info_processor.py  # HBPR record processing and validation
│   ├── hbpr_list_processor.py  # Batch processing and database creation
│   └── general_func.py         # Utility functions and configuration
├── ui/                         # Web UI components
│   ├── main.py                 # Main UI coordinator
│   ├── login_page.py           # Authentication interface
│   ├── home_page.py            # System overview
│   ├── database_page.py        # Database management
│   ├── settings_page.py        # System configuration
│   └── common.py               # Shared utilities
├── hbpr_ui.py                  # Legacy UI functions (Process Records)
└── databases/                  # Database storage directory
```

## 📋 Class Specifications

### 1. CHbpr Class - HBPR Record Processing

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
    """Extract all structured data fields"""

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

### 2. HbprDatabase Class - Database Management

**Location**: `scripts/hbpr_info_processor.py`

**Purpose**: Manages all database operations for HBPR records including creation, querying, and maintenance.

#### Methods

```python
def __init__(self, db_file: str = None) -> None:
    """
    Initialize database connection
    
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
        record_line (str): Simple record content
        
    Returns:
        bool: True if creation successful
    """

def create_full_record(self, hbnb_number: int, record_content: str, 
                      flight_info_match: bool = True) -> bool:
    """
    Create full HBPR record
    
    Args:
        hbnb_number (int): HBNB number
        record_content (str): Full HBPR record content
        flight_info_match (bool): Whether to validate flight info
        
    Returns:
        bool: True if creation successful
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
```

### 3. HBPRProcessor Class - Batch Processing

**Location**: `scripts/hbpr_list_processor.py`

**Purpose**: Processes HBPR list files, extracts records, and creates flight-specific databases.

#### Methods

```python
def __init__(self, input_file: str) -> None:
    """
    Initialize HBPR processor
    
    Args:
        input_file (str): Path to input HBPR text file
    """

def parse_file(self) -> None:
    """Parse HBPR text file and extract all records by flight"""

def parse_full_record(self, lines: List[str], start_index: int) -> Tuple[Optional[int], str, int]:
    """
    Parse complete HBPR record and extract flight info and HBNB number
    
    Args:
        lines (List[str]): Input HBPR text file lines
        start_index (int): Starting line index for parsing
        
    Returns:
        Tuple[Optional[int], str, int]: HBNB number, record content, end index
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
    Store records in database
    
    Args:
        flight_id (str): Flight identifier
        db_file (str): Database file path
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

### 4. CArgs Class - Configuration

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

```python
def main() -> None:
    """Main UI function - Application entry point"""
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

```python
def show_home_page() -> None:
    """Display system overview and quick actions"""
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
    """Show database maintenance operations"""
```

### 5. Manual Input Processing

**Location**: `hbpr_ui.py`

```python
def process_manual_input() -> None:
    """Manual HBPR input processing interface"""

def validate_full_hbpr_record(hbpr_content: str) -> Dict[str, Any]:
    """
    Validate full HBPR record content
    
    Args:
        hbpr_content (str): HBPR record content to validate
        
    Returns:
        Dict[str, Any]: Validation results and extracted data
    """

def parse_hbnb_input(hbnb_input: str) -> List[int]:
    """
    Parse HBNB number input (ranges, lists, single numbers)
    
    Args:
        hbnb_input (str): HBNB input string (e.g., "400-410,412,415-420")
        
    Returns:
        List[int]: List of parsed HBNB numbers
        
    Raises:
        ValueError: If input format is invalid
    """
```

### 6. Common Utilities

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
                            show_flight_info: bool = False) -> Tuple[str, List[str]]:
    """
    Create database selection widget
    
    Args:
        label (str): Widget label
        key (str): Widget key for session state
        default_index (int): Default selection index
        show_flight_info (bool): Whether to show flight information
        
    Returns:
        Tuple[str, List[str]]: Selected database file, all database files
    """

def get_sorted_database_files(sort_by: str = 'creation_time', 
                            reverse: bool = True) -> List[str]:
    """
    Get sorted list of database files
    
    Args:
        sort_by (str): Sort criteria ('creation_time' or 'name')
        reverse (bool): Whether to reverse sort order
        
    Returns:
        List[str]: Sorted list of database file paths
    """
```

## 🔗 Function Dependencies and Call Hierarchy

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
    └── __CaptureCkin()
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
└── update_missing_numbers_table()
```

### UI Processing Chain
```
main()
├── authenticate_user()
├── show_home_page()
├── show_database_management()
│   └── build_database_ui()
├── process_manual_input()
│   ├── parse_hbnb_input()
│   ├── validate_full_hbpr_record()
│   └── HbprDatabase operations
└── show_settings()
```

## 📊 Data Flow and Processing Pipeline

### 1. File Processing Pipeline
```
Input File → HBPRProcessor → Database Creation → CHbpr Validation → UI Display
```

### 2. Manual Input Pipeline
```
UI Input → Validation → Database Storage → Missing Numbers Update → Statistics Refresh
```

### 3. Authentication Flow
```
Login Page → SHA256 Hash → Validation → Session State → Authenticated UI
```

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
    validated_at TIMESTAMP
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

### Processing HBPR Records
```python
# Create CHbpr instance
chbpr = CHbpr()
chbpr.run(hbpr_content)

# Check validity
if chbpr.is_valid():
    print(f"Record {chbpr.HbnbNumber} is valid")
    structured_data = chbpr.get_structured_data()
```

### Database Operations
```python
# Initialize database
db = HbprDatabase()
db.find_database()

# Build from file
processor = db.build_from_hbpr_list("sample_hbpr_list.txt")

# Get statistics
stats = db.get_validation_stats()
missing = db.get_missing_hbnb_numbers()
```

### Batch Processing
```python
# Process HBPR file
processor = HBPRProcessor("input_file.txt")
processor.process()

# Generate report
report = processor.generate_report()
```

## 🔧 Error Handling

### Exception Types
- `FileNotFoundError`: Database or input file not found
- `ValueError`: Invalid HBNB number or data format
- `sqlite3.Error`: Database operation errors
- `Exception`: General processing errors

### Error Categories
- **Baggage**: Weight/piece validation errors
- **Passport**: Expiration date issues
- **Name**: Name matching inconsistencies  
- **Visa**: Visa information problems
- **Other**: General processing errors

## 🔐 Security Features

### Authentication
- SHA256-based username validation
- Session state management
- Automatic logout and cleanup

### Data Protection
- Obfuscated credentials in source code
- Secure session handling
- File cleanup on navigation/logout

This technical documentation provides comprehensive information about the system's functions, their parameters, return types, and relationships for developers working with the HBPR Processing System.