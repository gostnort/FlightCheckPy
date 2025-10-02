# Flight Data Processing System - Technical API Documentation

## Project Overview

The Flight Data Processing System is a comprehensive Python application for processing and analyzing HBPR (Hotel Booking Passenger Record) data. It utilizes a centralized in-memory database architecture for high performance and data consistency. A dedicated HTTP server manages the SQLite database in memory, with the Streamlit UI acting as a client. This client-server model, running locally, ensures that all parts of the application interact with a single, consistent data source. The system also features automatic persistence of the in-memory database to disk.

The system validates and parses records, stores them in the database, and provides a modern Streamlit-based UI for database building, record processing with integrated command functionality and timeline versioning, and Excel output generation by mapping TKNE to CKIN CCRD data.

**Key Features:**
- **Centralized In-Memory Database Server**: High-performance client-server architecture where a dedicated Python HTTP server manages the database in-memory for each user session.
- **Unified UI Client**: The entire Streamlit UI acts as a client, communicating with the database server via HTTP requests, ensuring data consistency.
- **Automatic Data Persistence**: Changes made in memory are automatically saved back to the source file by the server.
- **Modular UI Architecture**: Organized tab-based interfaces with separate sub-modules for maintainability and clean code structure.
- **Remote Database Compatibility**: Seamless pandas integration with custom RemoteSqliteConnection objects, eliminating SQLAlchemy warnings.
- Multi-source database discovery with visual location indicators (📁 Custom, 🏠 Default, 📄 Root)
- Native Windows folder picker integration (topmost) with custom folder persistence
- Centralized database selection with flight information and session persistence
- Real-time database switching without application restart
- Intelligent statistics caching with automatic invalidation on updates
- Accepted passengers tracking with infant count and class split (Business/Economy)
- Excel Processor: XLS/XLSX import, strict header validation, TKNE ↔ CKIN CCRD mapping, formatted EMD Excel export
- Command functionality integrated into Process Records page with timeline versioning
- TKNE-aware calculations and compatibility handling
- **Data Cleaning & Export Solutions**: Comprehensive data sanitization at input, storage, and export stages to prevent binary/hexadecimal character issues
- **Deleted Passenger Analytics**: Comprehensive tracking of deleted passengers with XRES property classification and original boarding number extraction
- **Missing Boarding Number Detection**: Intelligent detection of discontinuous boarding numbers with automatic exclusion of deleted passengers to prevent duplicate reporting
- **Reusable UI Components**: Modular component architecture for consistent statistics display with separated calculation and presentation logic

## 🏗️ System Architecture

The application is architected around a local client-server model. The Streamlit UI, on startup, launches a dedicated Python-based HTTP server (`remote_db/memdb_port_server.py`) on a user-specific port. This server loads a SQLite database file into memory and exposes endpoints for all database operations (querying, execution, saving, etc.).

All core logic in `scripts/` and UI components in `ui/` interact with the database exclusively through a client layer defined in `ui/common.py` and `remote_db/`. This client layer translates function calls into HTTP requests to the local server, effectively decoupling the application logic from direct database file access.

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
│   ├── common.py               # Common utilities and DB client management
│   ├── components/
│   │   ├── main_stats.py       # Main statistics display, UI logic and calculation functions
│   │   └── home_metrics.py     # Home page metrics and debug information
│   ├── login_page.py           # Authentication interface
│   ├── home_page.py            # System overview with real-time statistics
│   ├── database_page.py        # Database management orchestrator
│   ├── process_records_page.py # Record processing navigation orchestrator
│   ├── excel_processor_page.py # Excel upload and EMD export UI
│   ├── settings_page.py        # System configuration and about info
│   ├── database/               # Database management sub-modules
│   │   ├── __init__.py
│   │   ├── hbpr.py             # HBPR operations (Create, Process, Erase, Save)
│   │   ├── commands.py         # Commands operations (Migrate, Clear)
│   │   ├── export.py           # Export operations (CSV, TXT)
│   │   ├── simple.py          # Simple records management
│   │   └── sort.py            # Record sorting and filtering
│   └── process_records/        # Record processing sub-modules
│       ├── __init__.py
│       ├── info.py            # Processing information display
│       ├── add_hbprs.py       # HBPR file upload with duplicate handling
│       ├── edit_hbpr.py       # Single HBPR record editing
│       ├── add_commands.py    # Command file import
│       ├── edit_command.py    # Single command editing
│       ├── timeline.py        # HBPR/Commands timeline with radio switcher
│       ├── process_all.py     # Batch processing functionality
│       ├── add_edit_record.py # Add or edit a record
│       ├── add_hbprs.py       # Add multiple HBPR records
│       ├── edit_command.py    # Edit a single command
│       ├── edit_hbpr.py       # Edit a single HBPR record
│       ├── export_data.py     # Export data to various formats
│       ├── info.py            # Display processing information and errors
│       ├── timeline.py        # Timeline visualization of record processing
│   ├── README.md              # UI documentation
├── start_ui.bat             # Batch script to start the UI
├── start_ui.py              # Main Streamlit application runner
├── remote_db/                  # In-memory database server and client components
│   ├── remote_sqlite_adapter.py # HTTP-to-SQLite adapter layer
│   ├── hbpr_database_client.py # Remote HbprDatabase API client
│   ├── db_port_client.py       # HTTP client for remote DB server
│   └── memdb_port_server.py   # Per-port in-memory DB HTTP server
├── databases/                  # Default database storage directory
└── resources/                  # Documentation and resources
```

### Server and Client Components

The client-server architecture consists of several key components that work together:

**Database Server** (`remote_db/memdb_port_server.py`):
A standard Python `http.server` that loads a SQLite database into memory.
```python
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # /health - Server health check
        # /databases/list - List available databases

    def do_POST(self):
        # /database/load - Load SQLite file into memory
        # /database/backup - Create timestamped backup
        # /database/save - Persist memory DB to source file
        # /query - Execute SELECT queries
        # /exec - Execute DDL/DML operations
```

**HTTP Client** (`remote_db/db_port_client.py`):
A minimal client for sending requests to the database server's endpoints.
```python
class DbPortClient:
    """Minimal HTTP client for the per-port in-memory DB server."""
    def load_database(self, path: str):  # POST /database/load
    def backup(self):                     # POST /database/backup
    def save(self):                       # POST /database/save
    def query(self, sql, params):         # POST /query
    def exec(self, sql, params):          # POST /exec
```

**SQLite Adapter** (`remote_db/remote_sqlite_adapter.py`):
A crucial compatibility layer that mimics the standard `sqlite3.Connection` and `sqlite3.Cursor` API, but routes all calls through the `DbPortClient` to the HTTP server. This allows existing code that expects a standard `sqlite3` connection object to work seamlessly with the new architecture.
```python
class RemoteSqliteConnection:
    """Minimal connection adapter that proxies SQLite calls to HTTP server."""
    def cursor(self) -> RemoteCursor:
    def execute(self, sql, params):
    def commit(self):  # No-op for compatibility
    def close(self):   # No-op for compatibility

class RemoteCursor:
    """DB-API–like cursor that proxies to HTTP server."""
    def execute(self, sql, params):
    def fetchall(self):
```

**High-Level API Client** (`remote_db/hbpr_database_client.py`):
A client that mirrors the API of the original `HbprDatabase` class, providing a convenient, high-level interface for application code to use. It uses the `RemoteSqliteConnection` internally.
```python
class HbprDatabaseClient:
    """Thin client mirroring scripts.hbpr_info_processor.HbprDatabase API."""
    def get_connection(self):  # Returns RemoteSqliteConnection
    def query_one(self, sql, params):  # Convenience method
    def query_all(self, sql, params):  # Convenience method
    def exec(self, sql, params):       # Convenience method
```

**UI Connection Management** (`ui/common.py`):
A set of functions that manage the lifecycle of the database client within the Streamlit UI, storing client instances in the session state to be shared across pages.
```python
# Key functions in ui/common.py
def ensure_memdb_server(username: str) -> Tuple[bool, int, str]:
    """
    Start per-user memdb_port_server if not running.
    Returns (started_now, port, message). If already running, returns (False, port, "User already logged in on this host").
    """

def get_db_port_client() -> Optional[DbPortClient]:
    """Get/create the low-level DbPortClient bound to 127.0.0.1 and session port."""

def get_hbpr_database_client() -> Optional[HbprDatabase]:
    """Get/create the HbprDatabase instance backed by RemoteSqliteConnection."""

def load_database(file_path: str) -> bool:
    """Instruct the server to load a database file into memory (resets caches)."""

def trigger_auto_save() -> bool:
    """Persist the in-memory database back to its source file and clear unsaved flag."""
```

### Environment Configuration

```bash
# Required environment variables for remote architecture
export FCP_DB_HOST=192.168.1.100    # Database server host
export FCP_DB_PORT=8080             # Database server port (per-user)

# Or set via Streamlit session state at runtime
st.session_state.db_service_host = "192.168.1.100"
st.session_state.db_service_port = 8080
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
- `ui/components/main_stats.py` - Missing boarding number calculation and unified display logic

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
- **UI Components**: Unified calculation and display (main_stats.py) logic
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
├── main_stats.py          # Main statistics display with calculation functions
└── home_metrics.py        # Home page metrics and comprehensive debug information
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

**main_stats.py**:
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
    - Integrates with command functionality in Process Records for compartment configuration
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
from ui.common import get_hbpr_database_client

db_client = get_hbpr_database_client()
if db_client:
    all_stats = get_and_display_main_statistics(db_client)

# For deleted passenger statistics with missing boarding numbers
from ui.components.main_stats import get_and_display_deleted_stats
db_client = get_hbpr_database_client()
if db_client:
    get_and_display_deleted_stats(db_client)

# For missing boarding number calculation only (pure function)
from ui.components.main_stats import get_missing_boarding_numbers
db_client = get_hbpr_database_client()
if db_client:
    missing_numbers = get_missing_boarding_numbers(db_client)

# For flight summary display
from ui.components.home_metrics import get_home_summary
summary = get_home_summary()

# For complete debug information with full boarding number lists
from ui.components.home_metrics import get_debug_summary
debug_info = get_debug_summary()
# Contains complete deleted passenger and missing boarding number lists

# Separated calculation and display approach
from ui.components.main_stats import get_missing_boarding_numbers
from ui.components.main_stats import display_missing_boarding_numbers

db_client = get_hbpr_database_client()
if db_client:
    missing_numbers = get_missing_boarding_numbers(db_client)  # Pure calculation
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

### Remote Database Compatibility

**Location**: Multiple UI files with `execute_query_to_dataframe()` helper functions

**Purpose**: Ensures pandas compatibility with `RemoteSqliteConnection` objects used in the remote database architecture.

#### Problem Solved
The remote database architecture uses custom `RemoteSqliteConnection` and `RemoteCursor` objects that mimic sqlite3 behavior but are not recognized by pandas' `read_sql_query()` method, causing:
- `UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection`
- Compatibility issues with pandas DataFrame operations

#### Solution Implementation
```python
def execute_query_to_dataframe(db, query, params=None):
    """
    Execute SQL query using remote connection and return pandas DataFrame
    Bypasses pandas compatibility issues by using cursor directly
    """
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params or [])

    # Extract column names and data manually
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchall()

    # Create DataFrame from results
    return pd.DataFrame(rows, columns=columns) if columns and rows else pd.DataFrame()
```

#### Files Updated
- `ui/database/export.py` - Database-export display helpers and DataFrame query helper
- `ui/database/sort.py` - Record sorting UI with DataFrame query helper
- `ui/process_records/info.py` - Processing info and DataFrame query helper

#### Benefits
- ✅ Eliminates pandas SQLAlchemy warnings
- ✅ Maintains compatibility with both remote and local database architectures
- ✅ Preserves all existing functionality
- ✅ No performance degradation
- ✅ Clean error handling

### Modular UI Architecture

**Purpose**: Implements a consistent, maintainable structure for complex UI pages with multiple tabs.

#### Architecture Pattern
```
Page Orchestrator (e.g., database_page.py, process_records_page.py)
├── Tab coordination and navigation
├── Session state management
└── Sub-module imports

Individual Tab Modules (in page-specific subdirectories)
├── Separate .py files for each tab
├── Focused functionality per tab
├── Reusable helper functions
└── Clean import structure
```

#### Implementation Benefits
- **Separation of Concerns**: Each tab in its own file
- **Maintainability**: Easier to modify individual features
- **Code Organization**: Logical grouping of related functionality
- **Import Clarity**: Explicit dependencies between modules
- **Testing**: Isolated testing of individual tab functions

#### Applied To
- **Database Page**: `hbpr.py`, `commands.py`, `export.py`, `simple.py`, `sort.py`
- **Process Records Page**: `info.py`, `add_hbprs.py`, `edit_hbpr.py`, `add_commands.py`, `edit_command.py`, `timeline.py`

#### Directory Structure
```
ui/
├── database_page.py          # Orchestrator
├── database/                 # Sub-modules
│   ├── hbpr.py               # HBPR operations tab
│   ├── commands.py           # Commands operations tab
│   ├── export.py             # Export operations tab
│   ├── simple.py             # Simple records tab
│   └── sort.py               # Sort records tab
├── process_records_page.py   # Orchestrator
└── process_records/          # Sub-modules
    ├── info.py               # Info tab
    ├── add_hbprs.py          # Add HBPRs tab
    ├── edit_hbpr.py          # Edit HBPR tab
    ├── add_commands.py       # Add Commands tab
    ├── edit_command.py       # Edit Command tab
    ├── timeline.py           # Timeline tab
    └── [legacy files...]
```

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

### 1. UI Database Connection Management Functions

**Location**: `ui/common.py`

**Purpose**: Manages the lifecycle of the database client within the Streamlit UI, storing client instances in the session state to be shared across pages.

#### Key Functions

```python
def ensure_memdb_server(username: str) -> bool:
    """
    Starts the memdb_port_server.py process for the user session.
    Assigns a unique port based on the username to allow for multiple local users.
    """

def get_db_port_client() -> Optional[DbPortClient]:
    """
    Gets or creates the low-level DbPortClient for the current session.
    This client is responsible for direct HTTP communication with the server.
    """

def get_hbpr_database_client() -> Optional[HbprDatabaseClient]:
    """
    Gets or creates the high-level HbprDatabaseClient for the current session.
    This is the primary client used by the application logic.
    """

def load_database(file_path: str) -> bool:
    """
    Instructs the server, via the DbPortClient, to load a database file into memory.
    """

def trigger_auto_save():
    """
    Instructs the server to save the current in-memory database back to its source file.
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
from ui.common import get_icon_base64, apply_global_settings
from ui.login_page import show_login_page
from ui.home_page import show_home_page
from ui.database_page import show_database_management
from ui.process_records_page import show_process_records
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

```

### 4.1 HBPR Operations Tab

**Location**: `ui/database/hbpr.py`

```python
def show_hbpr_operations() -> None:
    """
    HBPR operations UI including:
    - Create new DB from uploaded HBPR list file
    - Process all records via CHbpr and update DB
    - Erase processing results via HbprDatabase.erase_splited_records()
    - Auto-save integration and unsaved-changes indicator
    """

def process_all_records() -> None:
    """Iterate all hbpr_full_records, run CHbpr, and update rows."""

def erase_processing_results() -> None:
    """Confirm and call db.erase_splited_records(); auto-save and rerun."""

def create_database_from_file() -> None:
    """Upload .txt HBPR list and trigger creation when confirmed."""

def create_db_from_content(file_content: str) -> None:
    """
    Parse flight ID via scripts.hbpr_list_processor.parse_flight_id_from_content,
    build DB file with HBPRProcessor, load into memory, then auto-process all.
    """
```

### 5. Process Records Page

**Location**: `ui/process_records_page.py`, `ui/process_records/`

**Purpose**: Orchestrates record processing interface with modular tab-based organization.

```python
def show_process_records() -> None:
    """
    Main orchestrator for record processing interface

    Features:
    - Tab-based navigation (Info, Add HBPRs, Edit HBPR, Add Commands, Edit Command, Timeline)
    - Modular sub-module architecture
    - Session state management for tab persistence
    """

# Sub-module functions:
def show_info_tab() -> None:
    """Display error summary and messages without processing buttons"""

def show_add_hbprs_tab() -> None:
    """Handle HBPR file upload with smart duplicate detection"""

def show_edit_hbpr_tab() -> None:
    """Single HBPR record editing interface"""

def show_add_commands_tab() -> None:
    """Command file import functionality"""

def show_edit_command_tab() -> None:
    """Single command editing interface"""

def show_timeline_tab() -> None:
    """Timeline view with radio switcher for HBPR vs Commands history"""
```

#### Process Records Sub-modules

**Location**: `ui/process_records/`

```
├── info.py            # Error display only (no buttons)
├── add_hbprs.py       # HBPR file upload with duplicate handling
├── edit_hbpr.py       # Single HBPR record editing
├── add_commands.py    # Command file import
├── edit_command.py    # Single command editing
├── timeline.py        # HBPR/Commands timeline with radio switcher
├── process_all.py     # Batch processing and error functions
├── add_edit_record.py # Add or edit a record
├── add_hbprs.py       # Add multiple HBPR records
├── edit_command.py    # Edit a single command
├── edit_hbpr.py       # Edit a single HBPR record
├── export_data.py     # Export data to various formats
├── info.py            # Display processing information and errors
├── simple_record.py   # Simple record management
├── sort_records.py    # Record sorting functionality
├── timeline.py        # Timeline visualization of record processing
└── export_data.py     # Data export functionality
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

def parse_hbnb_input(input_text: str) -> List[int]:
    """
    Parse HBNB input supporting single numbers, ranges, and comma-separated lists

    Args:
        input_text (str): Input text to parse

    Returns:
        List[int]: List of parsed HBNB numbers
    """
```

### 7. Database Selection Components

**Locations**:
- `ui/common.py` → `create_database_selectbox()` inline helper for main pages
- `ui/components/database_selector.py` → `render_sidebar_database_selector()` for sidebar selector

```python
def create_database_selectbox(label: str = "💾 Select Database:", key: str = "global_db_select", custom_folder: Optional[str] = None) -> Tuple[Optional[str], List[str]]:
    """Create database selection widget, validate schema via server, and load selection."""

def render_sidebar_database_selector() -> None:
    """Sidebar selector with current DB indicator and explicit Load button."""
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
│   │   ├── show_hbpr_operations() (HBPR file processing, processing, erasing, saving)
│   │   ├── show_commands_operations() (timeline migration, command clearing)
│   │   ├── show_export_operations() (CSV and TXT export)
│   │   ├── show_simple_records() (simple record management)
│   │   └── show_sort_records() (record sorting and filtering)
│   ├── show_process_records_page()
│   │   ├── show_info_tab() (error display only)
│   │   ├── show_add_hbprs_tab() (HBPR file upload with duplicate handling)
│   │   ├── show_edit_hbpr_tab() (single HBPR record editing)
│   │   ├── show_add_commands_tab() (command file import)
│   │   ├── show_edit_command_tab() (single command editing)
│   │   └── show_timeline_tab() (HBPR/Commands timeline with radio switcher)
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

### 6. TKNE-Based Acceptance Rate Calculation (availability-aware)
```
In-Memory DB Query → Count records with TKNE IS NOT NULL AND TKNE != '' (fallback to 0 if column missing) → Count accepted passengers → Calculate rate → UI Display
```

### 7. Data Export Pipeline with Cleaning
```
In-Memory DB Query → Data Extraction → Data Cleaning/Formatting → File Generation → Download
```

**Data Cleaning Integration**:
- **Export Preparation**: `export_as_origin_txt` now handles raw export correctly.
- **Format Safety**: Ensures compatibility with spreadsheet applications
- **Data Integrity**: Preserves essential information while removing problematic characters

## Centralized Schema and Migration

The database schema is now centralized in a single JSON configuration and applied uniformly across the system.

- JSON schema: `scripts/database_schema.json`
- SQL generation utilities: `scripts/schema_utils.py`
- Unified migrator: `scripts/database_migration.py`
- UI integration: Database Management → “迁移数据库” button in `ui/database/management.py`
- Deprecated: `scripts/commands_migration.py` (functionality merged into the unified migrator)

Benefits:
- Single source of truth for all tables and indexes
- One-click migration from the UI; automatic creation of missing tables/columns
- Consistent structure across scripts (`hbpr_info_processor.py`, `hbpr_list_processor.py`, `command_processor.py`)

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
    hbnb_number INTEGER PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### flight_info
```sql
CREATE TABLE flight_info (
    flight_id TEXT PRIMARY KEY,
    flight_number TEXT NOT NULL,
    flight_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### duplicate_record
```sql
CREATE TABLE duplicate_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hbnb_number INTEGER NOT NULL,
    original_hbnb_id INTEGER NOT NULL,
    record_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_hbnb_id) REFERENCES hbpr_full_records(hbnb_number)
);
```

#### commands
```sql
CREATE TABLE commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_full TEXT NOT NULL,
    command_type TEXT,
    flight_number TEXT,
    flight_date TEXT,
    content TEXT,
    version INTEGER DEFAULT 1,
    parent_id INTEGER,
    is_latest BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Indexes
CREATE INDEX idx_commands_timeline ON commands(command_full, version);
CREATE INDEX idx_commands_parent ON commands(parent_id);
CREATE INDEX idx_commands_latest ON commands(command_full, is_latest);
```

## 🚀 Usage Examples

### Local SQLite Database Usage
```python
# Local SQLite database management
from ui.components.database_manager import db_manager, create_database_selectbox

# Load a database
success = db_manager.load_database("path/to/database.db")

# Create database selector widget
selected_file, available_files = create_database_selectbox(
    label="Select Database:",
    custom_folder="C:/MyDatabases"
)

# Get database instance for operations
db = db_manager.get_database()

# Get all statistics efficiently
all_stats = db.get_all_statistics()
record_summary = all_stats['record_summary']
accepted_stats = all_stats['accepted_stats']
```

### Remote HTTP Database Usage
```python
# Remote database management (requires running server)
import os
os.environ['FCP_DB_HOST'] = '192.168.1.100'
os.environ['FCP_DB_PORT'] = '8080'

from remote_db.database_manager import get_manager

# Get remote database manager
remote_manager = get_manager()

# Load database via HTTP
success = remote_manager.load_database("path/to/database.db")

# Get remote database instance
remote_db = remote_manager.get_database()

# Use same API as local database
all_stats = remote_db.get_all_statistics()
```

### Remote Database Server Setup
```bash
# Start remote database server for port 8080
python remote_db/memdb_port_server.py --host 0.0.0.0 --port 8080

# Or with specific host
python remote_db/memdb_port_server.py --host 192.168.1.100 --port 8080
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
from ui.components.database_manager import db_manager

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
# Note: get_sorted_database_files is now part of the database manager

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

### UI Statistics Display (Local SQLite)
```python
# In Streamlit UI components - Local SQLite
from ui.components.database_manager import db_manager

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

# Auto-save on changes
db_manager.trigger_auto_save()
```

### UI Statistics Display (Remote HTTP)
```python
# In Streamlit UI components - Remote HTTP
from remote_db.database_manager import get_manager

remote_manager = get_manager()
remote_db = remote_manager.get_database()
all_stats = remote_db.get_all_statistics()

# Same UI code works with remote database!
record_summary = all_stats['record_summary']
accepted_stats = all_stats['accepted_stats']
st.metric("Total Records", record_summary['total_records'])
st.metric("Accepted Pax", record_summary['accepted_pax'])
```

### Architecture Selection
```python
# Choose database architecture at runtime
import os

# Check if remote server is available
remote_host = os.environ.get('FCP_DB_HOST')
remote_port = os.environ.get('FCP_DB_PORT')

if remote_host and remote_port:
    # Use remote architecture
    from remote_db.database_manager import get_manager
    db_manager = get_manager()
    st.info("📡 Using remote database server")
else:
    # Use local architecture (remote-style API via per-port server)
    from ui.common import get_hbpr_database_client
    st.info("💻 Using local per-port in-memory database")

# Same API works for both architectures (via HbprDatabase/HbprDatabaseClient-compatible interface)
db = get_hbpr_database_client()
stats = db.get_all_statistics() if db else {}
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

This technical documentation provides comprehensive information about the HBPR Processing System's dual architecture approach with enhanced modular UI design:

## 🏗️ Architecture Summary

### Local SQLite Architecture (Default)
- **Best for**: Single-user applications, development, offline usage
- **Features**: Direct file access, immediate persistence, no network setup
- **Location**: `ui/components/database_manager.py`
- **Performance**: Highest performance for local operations

### Remote HTTP Architecture (Alternative)
- **Best for**: Multi-user environments, LAN deployments, centralized management
- **Features**: Network-based access, user isolation, scalable deployment, pandas compatibility
- **Location**: `remote_db/` directory
- **Performance**: Network latency overhead, suitable for distributed systems

### Unified API
Both architectures provide identical APIs, allowing seamless switching between local and remote database operations without code changes. The system automatically detects available architecture and provides transparent operation.

### Enhanced Features (Version 0.63)
- **Modular UI Architecture**: Organized tab-based interfaces with separate sub-modules for maintainability
- **Remote Database Compatibility**: Seamless pandas integration with custom connection objects
- **Streamlined Navigation**: Consolidated Process Records page with integrated command functionality
- **Automatic Persistence**: Changes saved to disk automatically
- **Data Cleaning**: Comprehensive sanitization at input, storage, and export
- **Statistics Caching**: Efficient data retrieval with automatic invalidation
- **UI Components**: Reusable, modular interface components
- **Error Handling**: Robust exception management across all layers
- **Cross-Platform**: Windows-native folder picker and path handling

The system is designed for flexibility, allowing deployment in both traditional single-user environments and modern distributed, multi-user architectures with a clean, maintainable codebase structure.