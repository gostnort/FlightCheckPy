# HBPR Processing System - Web UI

A comprehensive web-based interface for processing and validating HBPR passenger records using Streamlit.

## 🚀 Quick Start

### Installation

1. **Install Dependencies**
   ```bash
   pip install streamlit pandas openpyxl
   ```

2. **Run the Application**
   ```bash
   streamlit run hbpr_ui.py
   ```

3. **Open in Browser**
   - The application will automatically open at `http://localhost:8501`

## 📋 Features

### 🏠 Home Page
- **System Overview**: Real-time database statistics
- **Quick Actions**: Direct access to main functions
- **Usage Guide**: Step-by-step instructions

### 🗄️ Database Management
- **Build Database**: Create database from HBPR list files
- **Database Info**: View table structures and statistics
- **Maintenance**: Reset validation data or delete databases

### 🔍 Process Records
- **Single Record**: Process individual HBPR records by HBNB number
- **Batch Processing**: Process multiple records in batches
- **Manual Input**: Process HBPR content directly from text input

### 📊 View Results
- **Statistics**: Comprehensive validation and processing metrics
- **Records Table**: Browse and filter processed records
- **Export Data**: Download results in CSV or Excel format

### ⚙️ Settings
- **UI Preferences**: Theme and display options
- **Processing Settings**: Batch sizes and defaults
- **About**: System information and version details

## 🛠️ Usage Workflow

1. **Build Database**
   - Go to "Database Management" → "Build Database"
   - Upload your `sample_hbpr_list.txt` file or use the default
   - Click "Build from Default File" or "Build from Uploaded File"

2. **Process Records**
   - Go to "Process Records"
   - Choose between Single Record, Batch Process, or Manual Input
   - For single records: select HBNB number and click "Process Record"
   - For batch: set batch size and click "Start Batch Processing"

3. **View Results**
   - Go to "View Results" to see processing statistics
   - Browse the Records Table with filtering options
   - Export data in CSV or Excel format

## 📊 Data Export

The system supports exporting processed data in two formats:

- **CSV**: Comma-separated values for general use
- **Excel**: Formatted spreadsheet with all fields

Export files include:
- All CHbpr extracted fields (name, seat, class, destination, etc.)
- Validation status and error information
- Processing timestamps

## 🔧 Technical Details

### Architecture
- **Frontend**: Streamlit web framework
- **Backend**: `hbpr_info_processor.py` with `CHbpr` and `HbprDatabase` classes
- **Database**: SQLite with dynamic field addition
- **Data Processing**: Pandas for analysis and export

### Database Schema
The system adds CHbpr fields to the existing `hbpr_full_records` table:
- Validation fields: `is_validated`, `is_valid`, `error_count`, `error_messages`
- Passenger fields: `pnr`, `name`, `seat`, `class`, `destination`
- Baggage fields: `bag_piece`, `bag_weight`, `bag_allowance`
- Special fields: `ff`, `pspt_name`, `pspt_exp_date`, `ckin_msg`
- Processing timestamp: `validated_at`

## 🚨 Error Handling

The UI includes comprehensive error handling:
- Database connection errors
- File upload validation
- Processing exceptions with detailed messages
- Graceful fallbacks for missing data

## 🎯 Performance

- **Batch Processing**: Optimized for handling multiple records
- **Progress Tracking**: Real-time progress bars and status updates
- **Memory Efficient**: Streaming data processing for large datasets
- **Responsive UI**: Fast loading and interactive components

## 🔒 Data Security

- **Local Processing**: All data stays on your local machine
- **No External Connections**: Streamlit runs locally by default
- **File Validation**: Upload validation and sanitization
- **Error Isolation**: Processing errors don't affect other records

## 📝 Tips

1. **Database Management**: Build your database first before processing
2. **Batch Size**: Start with smaller batches (10-20) for testing
3. **Export Regularly**: Save your results after processing sessions
4. **Filter Data**: Use the Records Table filters to find specific records
5. **Manual Input**: Use for testing individual HBPR content snippets

## 🔄 Updates

To update the system:
1. Pull latest changes from the repository
2. Restart the Streamlit application
3. Refresh your browser

## 📞 Support

For issues or questions:
- Check the error messages in the UI
- Review the debug information in processing results
- Ensure all dependencies are installed correctly 