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
- Multi-source database discovery with visual location indicators
- Native Windows folder picker integration (topmost) with custom folder persistence
- Centralized database selection with flight information and session persistence
- Real-time database switching without application restart
- Intelligent statistics caching with automatic invalidation on updates
- Accepted passengers tracking with infant count and class split (Business/Economy)
- **Hot Database Reload**: Real-time database updates when source files are manually modified
- Excel Processor: XLS/XLSX import, strict header validation, TKNE → CKIN CCRD mapping, formatted EMD Excel export
- **Command Functionality**: Integrated into Process Records page with timeline versioning and dual SY support (departure and arrival)
- TKNE-aware calculations and compatibility handling
- **Data Cleaning & Export Solutions**: Comprehensive data sanitization at input, storage, and export stages
- **Deleted Passenger Analytics**: Comprehensive tracking of deleted passengers with XRES property classification
- **Missing Boarding Number Detection**: Intelligent detection of discontinuous boarding numbers
- **Reusable UI Components**: Modular component architecture for consistent statistics display
- **Dual SY Command Support**: System handles both departure and arrival SY commands

---

## v0.63 Major Changes

### 1. Login Page Refactoring (`ui/login_page.py`)

**Purpose**: User authentication and server lifecycle monitoring interface

**Key Changes**:
- Separated server lifecycle management from user authentication requirements
- Removed "Start All" and "Restart All" buttons (they require login anyway for port assignment)
- Kept only "Shutdown All" button for infrastructure control (no authentication required)
- Enhanced server status display showing all 3 ports (51201, 51202, 51203) with color-coded indicators
- Display logged-in users for each active port
- All imports placed at file beginning (C convention style)

**Server Control Design Principle**:
- Server startup is automatic when a user logs in and gets assigned a port
- Server shutdown is manual and requires no authentication
- Status monitoring is accessible without login

### 2. DatabaseMigrator Class (`scripts/database_migration.py`)

**Purpose**: Unified schema migration system with JSON configuration

**Key Methods**:
- `migrate_database()`: Execute all pending migrations
- `ensure_table_exists()`: Check and create tables if needed
- `add_column_if_missing()`: Automatically add missing columns from schema
- `handle_commands_table_versioning()`: Manage commands table schema versions
- `create_indexes()`: Build all required database indexes
- `create_views()`: Create VIEW-based statistics for performance

**Features**:
- JSON-based schema configuration for easy maintenance
- Automatic column addition without data loss
- Transaction support with rollback capability
- Index management for query optimization
- Error recovery and validation

### 3. SchemaUtils Class (`scripts/schema_utils.py`)

**Purpose**: Centralized SQL generation from JSON schema configuration

**Key Methods**:
- `generate_create_table_sql()`: Build CREATE TABLE statements
- `generate_column_sql()`: Generate column definitions with constraints
- `generate_indexes()`: Create INDEX statements
- `generate_views()`: Create VIEW statements for statistics

**Features**:
- Supports all SQLite data types and constraints
- Automatic primary key and foreign key generation
- Index strategy optimization
- VIEW creation for performance-critical queries

### 4. HbprDatabase Enhanced (`scripts/hbpr_database.py`)

**Features Added**:
- VIEW-based statistics calculation for better performance
- Enhanced error resilience with retry logic
- Automatic connection validation
- Improved transaction management
- Better resource cleanup

**Statistics Views**:
- Total passengers count by flight
- Class distribution (Business/Economy)
- Infant count tracking
- Deleted passenger analytics

### 5. HbprFileProcessor Enhanced (`scripts/hbpr_file_processor.py`)

**Data Cleaning Pipeline Improvements**:
- Improved binary/hexadecimal character detection and removal
- Better handling of edge cases in record parsing
- Enhanced field validation
- Consistent encoding handling (UTF-8)
- Comprehensive error logging

---

## Module Documentation

### Core Modules

#### `scripts/database_migration.py`
- Handles all schema migrations
- Manages database versioning
- Ensures schema consistency across instances

#### `scripts/hbpr_database.py`
- Main database abstraction layer
- Manages in-memory SQLite database
- Handles all CRUD operations
- Provides statistics views

#### `scripts/schema_utils.py`
- SQL generation utilities
- Schema configuration management
- Index and view creation

#### `scripts/hbpr_file_processor.py`
- File parsing and validation
- Data cleaning pipeline
- Record processing

### UI Modules

#### `ui/login_page.py` (中文: 用户身份验证和服务器生命周期监控界面)
- User authentication
- Server status monitoring
- Server shutdown management
- Session state management

#### `ui/components/main_stats.py` (中文: 主统计显示组件)
- Display flight statistics
- Show passenger counts
- Display class distribution
- Show infant counts

---

## Database Schema

The database schema is managed via JSON configuration in `scripts/database_schema.json`:

```json
{
  "tables": {
    "flights": {
      "columns": {
        "id": "INTEGER PRIMARY KEY",
        "flight_number": "TEXT NOT NULL",
        "departure_date": "TEXT NOT NULL"
      }
    },
    "passengers": {
      "columns": {
        "id": "INTEGER PRIMARY KEY",
        "flight_id": "INTEGER",
        "name": "TEXT",
        "seat": "TEXT"
      }
    }
  }
}
```

---

## API Endpoints

### Database Port Server (`remote_db/memdb_port_server.py`)

The in-memory database runs on configurable ports (default: 51201-51203):

- **GET** `/status` - Server status
- **POST** `/query` - Execute SQL query
- **POST** `/execute` - Execute SQL command
- **POST** `/shutdown` - Graceful shutdown

---

## Error Handling & Resilience

All modules implement comprehensive error handling:
- Try-catch blocks with specific exception handling
- Automatic retry logic for transient failures
- Graceful degradation when resources unavailable
- Detailed logging for debugging

---

## Performance Optimizations

1. **In-Memory Database**: All data cached in memory for fast access
2. **VIEW-Based Statistics**: Pre-calculated statistics avoid expensive queries
3. **Index Strategy**: Strategic indexes on frequently queried columns
4. **Connection Pooling**: Reuse database connections efficiently
5. **Lazy Loading**: Load data on demand, not all at once

---

## Testing & Quality

- Comprehensive error handling
- Logging at all critical points
- Validation of inputs
- Schema consistency checks
- Transaction integrity verification

---

**Documentation Last Updated**: v0.63
**Status**: Active Development
