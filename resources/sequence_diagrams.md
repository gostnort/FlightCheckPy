# Flight Data Processing System - Sequence Diagrams

This document contains sequence diagrams illustrating the key workflows and interactions within the HBPR Processing System.

## 1. Complete System Workflow

The main sequence diagram above shows the overall system workflow including authentication, database building, record processing, and manual input.

## 2. Detailed Component Interactions

### Authentication Flow Detail

```mermaid
sequenceDiagram
    participant U as User
    participant LP as Login Page
    participant CM as Common Utils
    participant SS as Session State

    U->>LP: Enter Username
    LP->>CM: authenticate_user(username)
    CM->>CM: hashlib.sha256(username)
    CM->>CM: Check against valid_usernames
    alt Authentication Success
        CM-->>LP: True
        LP->>SS: Set authenticated=True
        LP->>SS: Set username=username
        LP->>U: Success Message & Redirect
    else Authentication Failure
        CM-->>LP: False
        LP->>U: Error Message
    end
```

### Database Building Process Detail

```mermaid
sequenceDiagram
    participant UI as Database UI
    participant HD as HbprDatabase
    participant PR as HBPRProcessor
    participant DB as SQLite Database
    participant FS as File System

    UI->>HD: build_from_hbpr_list(input_file)
    HD->>FS: Check file exists
    HD->>PR: HBPRProcessor(input_file)
    PR->>FS: Read file content
    PR->>PR: parse_file()
    
    loop For each line
        PR->>PR: Check if ">HBPR:" line
        alt Full Record
            PR->>PR: parse_full_record()
            PR->>PR: Extract flight_info
            PR->>PR: Extract hbnb_number
        else Simple Record
            PR->>PR: _parse_simple_record()
        end
    end
    
    PR->>PR: _assign_simple_records()
    PR->>FS: Create databases/ folder
    PR->>PR: create_database(flight_id)
    PR->>DB: CREATE TABLE flight_info
    PR->>DB: CREATE TABLE hbpr_full_records
    PR->>DB: CREATE TABLE hbpr_simple_records
    PR->>PR: store_records()
    PR-->>HD: Processing Complete
    
    HD->>HD: find_database()
    HD->>HD: _add_chbpr_fields()
    HD->>DB: ALTER TABLE ADD COLUMN (CHbpr fields)
    HD->>HD: update_missing_numbers_table()
    HD->>DB: CREATE/UPDATE missing_numbers table
    HD-->>UI: Database Built Successfully
```

### CHbpr Record Processing Detail

```mermaid
sequenceDiagram
    participant UI as Process UI
    participant CH as CHbpr
    participant CA as CArgs
    participant HD as HbprDatabase

    UI->>CH: CHbpr()
    UI->>CH: run(hbpr_content)
    
    CH->>CH: Initialize variables
    CH->>CH: __GetHbnbNumber()
    CH->>CH: Extract using regex pattern
    
    alt HBNB Found
        CH->>CH: __GetPassengerInfo()
        CH->>CH: Extract name, boarding_number
        CH->>CH: Extract seat, class
        CH->>CA: SubCls2MainCls(sub_class)
        CA-->>CH: Main class
        CH->>CH: Extract destination
        
        CH->>CH: __ExtractStructuredData()
        CH->>CH: Extract PNR, passport info
        CH->>CH: __GetChkBag()
        CH->>CH: __FlyerBenifit()
        
        alt Has Boarding Number
            CH->>CH: __MatchingBag()
            CH->>CA: ClassBagWeight(class)
            CA-->>CH: Weight limit
            CH->>CH: Validate baggage
            
            CH->>CH: __GetPassportExp()
            CH->>CH: __NameMatch()
            CH->>CH: __GetVisaInfo()
            CH->>CH: __GetProperties()
            CH->>CH: __GetConnectingFlights()
        end
    end
    
    CH-->>UI: Processing Complete
    UI->>CH: is_valid()
    CH-->>UI: Validation Result
    UI->>CH: get_structured_data()
    CH-->>UI: Structured Data
    
    UI->>HD: update_with_chbpr_results(chbpr)
    HD->>HD: Update database with results
    HD-->>UI: Update Success
```

### Manual Input Processing Detail

```mermaid
sequenceDiagram
    participant U as User
    participant PI as Process Input UI
    participant HD as HbprDatabase
    participant PR as HBPRProcessor
    participant CH as CHbpr

    U->>PI: Select Database
    PI->>HD: HbprDatabase(selected_db)
    PI->>HD: get_flight_info()
    HD-->>PI: Flight Information

    alt Full HBPR Record Input
        U->>PI: Enter Full HBPR Content
        U->>PI: Click "Replace Record" or "Create Duplicate"
        PI->>PI: validate_full_hbpr_record()
        PI->>PR: parse_full_record([content], 0)
        PR-->>PI: hbnb_number, content, index
        
        PI->>HD: validate_flight_info_match(content)
        HD-->>PI: Validation Result
        
        alt Flight Info Matches
            alt Replace Record
                PI->>HD: check_hbnb_exists(hbnb_number)
                HD-->>PI: Existence Info
                PI->>HD: create_full_record(hbnb, content)
                alt Simple Record Exists
                    HD->>HD: delete_simple_record(hbnb)
                end
            else Create Duplicate
                PI->>HD: create_duplicate_record(hbnb, content)
            end
            
            HD->>HD: update_missing_numbers_table()
            HD-->>PI: Success
            PI->>U: Show Success Message
        else Flight Info Mismatch
            PI->>U: Show Warning/Error
        end
        
    else Simple HBNB Record Input
        U->>PI: Enter HBNB Numbers
        PI->>PI: parse_hbnb_input(input)
        PI-->>U: Parsed Numbers List
        
        U->>PI: Click "Create Simple Records"
        
        loop For each HBNB number
            PI->>HD: check_hbnb_exists(hbnb)
            HD-->>PI: Existence Status
            
            alt HBNB Available
                PI->>HD: create_simple_record(hbnb, line)
                HD-->>PI: Creation Success
            else HBNB Exists
                Note over PI: Skip (already exists)
            end
        end
        
        PI->>HD: update_missing_numbers_table()
        HD-->>PI: Update Complete
        PI->>U: Show Processing Summary
    end
```

### File Cleanup Process

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Main UI
    participant SS as Session State
    participant FS as File System

    Note over U,FS: Navigation-Based Cleanup
    U->>UI: Navigate Away from Database Page
    UI->>SS: Check previous_page == "Database"
    UI->>SS: Check uploaded_file_path exists
    
    alt File Cleanup Needed
        UI->>FS: os.path.exists(file_path)
        FS-->>UI: True
        UI->>FS: os.remove(file_path)
        UI->>SS: Set uploaded_file_path = None
    end

    Note over U,FS: Logout Cleanup
    U->>UI: Click Logout
    UI->>SS: Check uploaded_file_path exists
    
    alt File Cleanup Needed
        UI->>FS: os.remove(file_path)
    end
    
    UI->>SS: Set authenticated = False
    UI->>SS: Set username = None
    UI->>SS: Set uploaded_file_path = None
    UI->>U: Redirect to Login
```

### Database Query Operations

```mermaid
sequenceDiagram
    participant UI as UI Component
    participant HD as HbprDatabase
    participant DB as SQLite Database

    Note over UI,DB: Statistics Retrieval
    UI->>HD: get_validation_stats()
    HD->>DB: SELECT COUNT(*) FROM hbpr_full_records
    DB-->>HD: total_records
    HD->>DB: SELECT COUNT(*) WHERE is_validated = 1
    DB-->>HD: validated_records
    HD->>DB: SELECT COUNT(*) WHERE is_valid = 1
    DB-->>HD: valid_records
    HD-->>UI: Statistics Dictionary

    Note over UI,DB: Missing Numbers Calculation
    UI->>HD: update_missing_numbers_table()
    HD->>DB: SELECT hbnb_number FROM hbpr_full_records
    DB-->>HD: Full Records List
    HD->>DB: SELECT hbnb_number FROM hbpr_simple_records
    DB-->>HD: Simple Records List
    HD->>HD: Calculate range(min, max+1) - existing
    HD->>DB: DELETE FROM missing_numbers
    HD->>DB: INSERT missing numbers
    HD-->>UI: Update Complete

    Note over UI,DB: Record Existence Check
    UI->>HD: check_hbnb_exists(hbnb_number)
    HD->>DB: SELECT 1 FROM hbpr_full_records WHERE hbnb_number = ?
    DB-->>HD: Full Record Exists
    HD->>DB: SELECT 1 FROM hbpr_simple_records WHERE hbnb_number = ?
    DB-->>HD: Simple Record Exists
    HD-->>UI: Existence Status Dictionary
```

## 3. Error Handling Flows

### Database Error Handling

```mermaid
sequenceDiagram
    participant UI as UI Component
    participant HD as HbprDatabase
    participant DB as SQLite Database

    UI->>HD: Database Operation
    HD->>DB: SQL Query
    
    alt Database Error
        DB-->>HD: sqlite3.Error
        HD->>HD: Log error details
        HD-->>UI: Exception("Database error: details")
        UI->>U: Show Error Message
    else File Not Found
        HD->>HD: Check file existence
        HD-->>UI: FileNotFoundError("Database file not found")
        UI->>U: Show File Not Found Error
    else Success
        DB-->>HD: Query Result
        HD-->>UI: Successful Response
        UI->>U: Show Success/Results
    end
```

### CHbpr Processing Error Handling

```mermaid
sequenceDiagram
    participant UI as Process UI
    participant CH as CHbpr

    UI->>CH: run(hbpr_content)
    
    alt Processing Error
        CH->>CH: Exception during processing
        CH->>CH: Add to error_msg["Other"]
        CH->>CH: Set HbnbNumber = ERROR_NUMBER
    else Missing HBNB
        CH->>CH: __GetHbnbNumber() fails
        CH->>CH: Add to error_msg["Other"]
        CH-->>UI: Return with errors
    else Missing Passenger Info
        CH->>CH: __GetPassengerInfo() fails
        CH->>CH: Add to error_msg["Other"]
        CH-->>UI: Return with errors
    else Validation Errors
        CH->>CH: __MatchingBag() finds issues
        CH->>CH: Add to error_msg["Baggage"]
        CH->>CH: Continue processing
        CH-->>UI: Return with validation errors
    end
    
    UI->>CH: is_valid()
    alt Has Errors
        CH-->>UI: False
        UI->>U: Show Error Details
    else No Errors
        CH-->>UI: True
        UI->>U: Show Success
    end
```

These sequence diagrams provide a comprehensive view of the system's workflows, showing how different components interact during various operations including authentication, database management, record processing, and error handling.