# Flight Data Processing System - Technical API Documentation

## Core Processing APIs

### HBPR Processor (`scripts/hbpr_file_processor.py`)

#### Class: `HbprProcessor`

**Constructor**
```python
HbprProcessor(conn: sqlite3.Connection)
```
- Location: Line 14
- Initializes processor with database connection
- Attributes:
  - `flight_data`: Dict[str, Dict[str, Any]] - indexed by flight_id
  - `flight_info`: Dict[str, Tuple[str, str]] - (flight_number, date)
  - `flight_id`: str - current flight ID
  - `all_simple_records`: Dict[int, str] - simple records by HBNB

**Methods**

| Method | Location | Signature | Returns |
|--------|----------|-----------|---------|
| `parse_file_content` | L37 | `(file_content: str) -> None` | Parses HBPR text, extracts records by flight |
| `parse_full_record` | L89 | `(lines: list[str], start_index: int) -> tuple[int \| None, str, int]` | Returns (hbnb_num, content, next_index) |
| `store_records` | L195 | `(flight_id: str) -> None` | Stores flight records to database with cleaning |
| `clean_duplicate_headers` | L229 | `(content: str) -> str` | Removes duplicate >HBPR: headers and +/- markers |
| `find_missing_numbers` | L162 | `(flight_id: str) -> list[int]` | Finds missing HBNB numbers in range |
| `generate_report` | L248 | `(flight_id: str) -> None` | Prints processing report |
| `process` | L277 | `(file_content: str) -> None` | Full pipeline: parse → store → report |
| `create_tables_if_not_exist` | L177 | `() -> None` | Creates database tables if missing |

**Module-Level Function**

| Function | Location | Signature | Returns |
|----------|----------|-----------|---------|
| `parse_flight_id_from_content` | L290 | `(file_content: str) -> str \| None` | Extracts flight ID without full parsing |

---

### PR Processor (`scripts/pr_processor.py`)

| Function | Location | Signature | Returns |
|----------|----------|-----------|---------|
| `split_commands` | L12 | `(content: str) -> list[dict]` | Parses PR content into command list with type 'PR' |
| `merge_pr_sections` | L67 | `(pr_content: str) -> str` | Merges multiple PR sections with same header |
| `extract_tkne_from_pr` | L37 | `(pr_content: str) -> list[str]` | Extracts TKNE ticket numbers from PR |
| `find_hbpr_header_by_tkne` | L116 | `(db, tkne_number: str) -> dict` | Returns {found: bool, hbnb_number: int, hbpr_header: str, error: str} |
| `convert_pr_to_hbpr` | L171 | `(pr_content: str, db) -> dict` | Returns {success: bool, converted_content: str, hbnb_number: int, error: str} |
| `process_mixed_commands` | L236 | `(content: str, db) -> dict` | Returns {hbpr_commands: list, failed_pr_commands: list, stats: dict} |
| `validate_pr_content` | L283 | `(pr_content: str) -> dict` | Returns {is_valid: bool, is_pr_command: bool, errors: list} |
| `display_processing_results` | L322 | `(chbpr) -> None` | Displays CHbpr processing results in Streamlit UI |

---

### UI Record Processing (`ui/process_records/add_hbprs.py`)

| Function | Location | Signature | Purpose |
|----------|----------|-----------|---------|
| `show_add_hbprs_tab` | L14 | `() -> None` | Renders file uploader and process button |
| `process_and_add_hbprs` | L28 | `(uploaded_file) -> None` | Main handler: detects file type, routes to processor |
| `process_hbpr_file` | L56 | `(file_content: str, db) -> None` | HBPR-specific: validates, parses with HbprProcessor |
| `process_pr_file` | L86 | `(file_content: str, db) -> None` | PR-specific: converts to HBPR, then processes |
| `process_records_into_database` | L144 | `(db, processor: HbprProcessor, flight_id_from_file: str) -> None` | Shared: stores records with cleaning, duplicate tracking |
| `process_updated_records` | L252 | `(db, hbnb_list: list) -> None` | Advanced: processes records with CHbpr |

---

### Common Utilities (`ui/common.py`)

| Function | Location | Signature | Returns |
|----------|----------|-----------|---------|
| `detect_file_type` | L530 | `(content: str) -> str` | 'HBPR', 'PR', or 'UNKNOWN' |
| `parse_hbnb_input` | L497 | `(input_text: str) -> list[int]` | Parses "400-410,412,415-420" format |
| `get_hbpr_database_client` | L144 | `() -> HbprDatabase \| None` | Gets/creates database client from session |
| `get_db_port_client` | L133 | `() -> DbPortClient \| None` | Gets database port client |
| `load_database` | L287 | `(path: str) -> bool` | Loads database file into memory |
| `trigger_auto_save` | L180 | `() -> bool` | Saves in-memory database to disk |
| `reload_database_from_disk` | L198 | `() -> bool` | Reloads database from disk |
| `is_db_available` | L157 | `() -> bool` | Checks if database is loaded |
| `get_database_name` | L169 | `() -> str` | Gets current database name |
| `authenticate_user` | L28 | `(username: str) -> bool` | Validates user via SHA256 hash |
| `ensure_memdb_server` | L67 | `(username: str) -> tuple[bool, int, str]` | Ensures server running, returns (ok, port, message) |
| `create_database_selectbox` | L315 | `(label: str, key: str, custom_folder: str \| None) -> tuple[str, list]` | Creates DB selector widget |

---

### Edit Record Processing (`ui/process_records/edit_hbpr.py`)

| Function | Location | Signature | Purpose |
|----------|----------|-----------|---------|
| `_handle_record_input` | - | `(db, content: str, is_duplicate: bool = False) -> dict` | Handles PR/HBPR validation, cleaning, saving |

---

### Data Cleaner (`scripts/data_cleaner.py`)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `clean_hbpr_record_content` | `(content: str, hbnb_num: int) -> str` | Removes binary/hex artifacts |
| `clean_text_for_input` | `(text: str) -> str` | Normalizes input text |

---

## Database Layer (`scripts/hbpr_database.py`)

### Class: `HbprDatabase`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `check_hbnb_exists` | `(hbnb_number: int) -> dict` | Returns {full_record: bool, simple_record: bool} |
| `create_full_record` | `(hbnb_number: int, record_content: str) -> bool` | Inserts/replaces full record |
| `create_simple_record` | `(hbnb_number: int, record_line: str) -> bool` | Inserts simple record |
| `create_duplicate_record_with_time` | `(hbnb_num: int, hbnb_dup: int, content: str, created_at: str) -> bool` | Creates timestamped duplicate |
| `get_hbpr_record` | `(hbnb_number: int) -> str` | Retrieves full record content |
| `delete_simple_record` | `(hbnb_number: int) -> None` | Deletes simple record |
| `get_original_record_info` | `(hbnb_number: int) -> dict` | Returns {record_content, created_at} |
| `update_with_chbpr_results` | `(chbpr) -> bool` | Stores CHbpr processing results |
| `get_flight_info` | `() -> dict` | Returns {flight_id, flight_number, flight_date} |
| `get_connection` | `() -> sqlite3.Connection` | Returns database connection |

---

## Data Flow

### HBPR Import Flow
```
uploaded_file → process_and_add_hbprs()
  → detect_file_type() = 'HBPR'
  → process_hbpr_file()
    → parse_flight_id_from_content()
    → HbprProcessor.parse_file_content()
    → process_records_into_database()
      → processor.clean_duplicate_headers()
      → clean_hbpr_record_content()
      → db.check_hbnb_exists()
      → db.create_full_record() or create_duplicate_record_with_time()
    → process_updated_records()
      → CHbpr.run()
      → db.update_with_chbpr_results()
  → trigger_auto_save()
```

### PR Import Flow
```
uploaded_file → process_and_add_hbprs()
  → detect_file_type() = 'PR'
  → process_pr_file()
    → process_mixed_commands()
      → split_commands()
      → merge_pr_sections()
      → for each command:
        → extract_tkne_from_pr()
        → convert_pr_to_hbpr()
          → find_hbpr_header_by_tkne()
          → combine header + body
    → HbprProcessor.parse_file_content() on converted HBPR
    → process_records_into_database() [same as HBPR flow]
```

---

## Database Schema

**Key Tables:**
- `flight_info` - Flight metadata
- `hbpr_full_records` - Complete HBPR records
- `hbpr_simple_records` - Simple HBPR records
- `commands` - Command history
- `deleted_passengers` - Deleted passenger tracking

---

**Documentation Last Updated**: v0.63
**Status**: Production
