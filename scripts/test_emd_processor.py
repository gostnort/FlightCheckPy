"""
Test Script for EMD Processor
============================

This script demonstrates how to use the EMD processor functionality.
It includes examples of all the main API functions with the new API format.
"""

import os
import sys
from datetime import datetime
from emd_processor import (
    EMDProcessor, EMDRecord, EMDData,
    process_emd_data, spell_number, 
    validate_emd_data, generate_filename
)


def test_spell_number():
    """Test the number to text conversion function"""
    print("=== Testing Number to Text Conversion ===")
    
    test_amounts = [0, 1, 1.01, 10.50, 100.00, 1234.56, 10000.00]
    
    for amount in test_amounts:
        result = spell_number(amount)
        print(f"{amount:>10.2f} -> {result}")
    
    print()


def test_emd_record():
    """Test EMDRecord class with new API format"""
    print("=== Testing EMDRecord Class (New API) ===")
    
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
    
    print(f"EMD Record: {record}")
    print()


def test_emd_data():
    """Test EMDData class"""
    print("=== Testing EMDData Class ===")
    
    emd_record = EMDRecord(
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
    
    emd_data = EMDData(
        total_amount=12345.00,
        report_date="2025-08-07",
        signature="Jun Liu",
        collection_msg=["Message 1", "Message 2", "Message 3"],
        emd_list=[emd_record]
    )
    
    print(f"EMD Data: {emd_data}")
    print(f"Collection messages: {emd_data.collection_msg}")
    print()


def test_validation():
    """Test EMD data validation with new API format"""
    print("=== Testing EMD Data Validation (New API) ===")
    
    # Create test EMD data
    test_data = {
        "total_amount": 12345.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": ["Message 1", "Message 2"],
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
    
    # Test validation
    is_valid, error_msg = validate_emd_data(test_data)
    print(f"Validation result: {is_valid}")
    if not is_valid:
        print(f"Error: {error_msg}")
    
    # Test with duplicate EMD
    test_data_duplicate = {
        "total_amount": 24690.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": ["Message 1"],
        "emd_list": [
            {
                "emd": "9991234567890",  # Duplicate EMD
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
            },
            {
                "emd": "9991234567890",  # Duplicate EMD
                "et": "9991234567891",
                "leg": "JFK-LAX",
                "emd_count": 1,
                "operation": "issue",
                "job_number": 35009,
                "date": "2025-08-07",
                "product": "EXPC",
                "i_d": "international",
                "flight": "CA985",
                "price": 12345.00,
                "cash": 0.00,
                "ax": 12345.00,
                "other": 0.00,
                "last_4_digit": "1234",
                "remark": "Credit payment"
            }
        ]
    }
    
    is_valid, error_msg = validate_emd_data(test_data_duplicate)
    print(f"Validation with duplicate EMD: {is_valid}")
    if not is_valid:
        print(f"Error: {error_msg}")
    
    # Test credit card validation - Amex without last 4 digits
    test_data_amex_no_digits = {
        "total_amount": 12345.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": ["Message 1"],
        "emd_list": [
            {
                "emd": "9991234567891",
                "et": "9991234567891",
                "leg": "LAX-PEK",
                "emd_count": 1,
                "operation": "issue",
                "job_number": 35008,
                "date": "2025-08-07",
                "product": "EXPC",
                "i_d": "international",
                "flight": "CA984",
                "price": 12345.00,
                "cash": 0.00,
                "ax": 12345.00,  # Amex payment
                "other": 0.00,
                "last_4_digit": "",  # Missing last 4 digits
                "remark": "Amex payment"
            }
        ]
    }
    
    is_valid, error_msg = validate_emd_data(test_data_amex_no_digits)
    print(f"Validation with Amex without last 4 digits: {is_valid}")
    if not is_valid:
        print(f"Error: {error_msg}")
    
    # Test credit card validation - Other credit card without last 4 digits
    test_data_other_no_digits = {
        "total_amount": 12345.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": ["Message 1"],
        "emd_list": [
            {
                "emd": "9991234567892",
                "et": "9991234567892",
                "leg": "LAX-PEK",
                "emd_count": 1,
                "operation": "issue",
                "job_number": 35008,
                "date": "2025-08-07",
                "product": "EXPC",
                "i_d": "international",
                "flight": "CA984",
                "price": 12345.00,
                "cash": 0.00,
                "ax": 0.00,
                "other": 12345.00,  # Other credit card payment
                "last_4_digit": "",  # Missing last 4 digits
                "remark": "Other credit card payment"
            }
        ]
    }
    
    is_valid, error_msg = validate_emd_data(test_data_other_no_digits)
    print(f"Validation with other credit card without last 4 digits: {is_valid}")
    if not is_valid:
        print(f"Error: {error_msg}")
    
    # Test credit card validation - Valid credit card with last 4 digits
    test_data_valid_credit = {
        "total_amount": 12345.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": ["Message 1"],
        "emd_list": [
            {
                "emd": "9991234567893",
                "et": "9991234567893",
                "leg": "LAX-PEK",
                "emd_count": 1,
                "operation": "issue",
                "job_number": 35008,
                "date": "2025-08-07",
                "product": "EXPC",
                "i_d": "international",
                "flight": "CA984",
                "price": 12345.00,
                "cash": 0.00,
                "ax": 12345.00,  # Amex payment
                "other": 0.00,
                "last_4_digit": "1234",  # Valid last 4 digits
                "remark": "Valid Amex payment"
            }
        ]
    }
    
    is_valid, error_msg = validate_emd_data(test_data_valid_credit)
    print(f"Validation with valid credit card: {is_valid}")
    if not is_valid:
        print(f"Error: {error_msg}")
    
    print()


def test_filename_generation():
    """Test filename generation with flight number"""
    print("=== Testing Filename Generation (Flight Number) ===")
    
    flight = "CA984"
    date_str = "2025-08-07"
    
    filename = generate_filename(flight, date_str)
    print(f"Flight: {flight}, Date: {date_str}")
    print(f"Generated filename: {filename}")
    
    # Test with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    filename_current = generate_filename(flight, current_date)
    print(f"With current date: {filename_current}")
    print()


def test_processor_initialization():
    """Test EMDProcessor initialization"""
    print("=== Testing EMDProcessor Initialization ===")
    
    try:
        processor = EMDProcessor()
        print("✓ EMDProcessor initialized successfully")
        print(f"✓ Configuration loaded with {len(processor.config)} sections")
        
        # Test some configuration values
        print(f"✓ File prefix: {processor.config['file_settings']['prefix']}")
        print(f"✓ EMD sheet name: {processor.config['sheets']['emd']}")
        print(f"✓ Cash payment type: {processor.config['payment_types']['cash']}")
        
    except Exception as e:
        print(f"✗ Error initializing processor: {e}")
    
    print()


def test_api_data_creation():
    """Test creating data in the new API format"""
    print("=== Testing New API Data Creation ===")
    
    # Create sample data in the new API format
    sample_data = {
        "total_amount": 24690.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": [
            "Collection message 1: All payments received",
            "Collection message 2: Documents processed",
            "Collection message 3: Ready for filing"
        ],
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
                "remark": "Cash payment for baggage"
            },
            {
                "emd": "9991234567891",
                "et": "9991234567891",
                "leg": "JFK-LAX",
                "emd_count": 1,
                "operation": "issue",
                "job_number": 35009,
                "date": "2025-08-07",
                "product": "EXPC",
                "i_d": "international",
                "flight": "CA985",
                "price": 12345.00,
                "cash": 0.00,
                "ax": 12345.00,
                "other": 0.00,
                "last_4_digit": "5678",
                "remark": "Credit card payment"
            }
        ]
    }
    
    print(f"Created sample data with {len(sample_data['emd_list'])} EMD records")
    print(f"Total amount: ${sample_data['total_amount']:.2f}")
    print(f"Report date: {sample_data['report_date']}")
    print(f"Signature: {sample_data['signature']}")
    print(f"Collection messages: {len(sample_data['collection_msg'])} messages")
    
    for i, record in enumerate(sample_data['emd_list'], 1):
        print(f"  {i}. EMD: {record['emd']}, Flight: {record['flight']}, Price: ${record['price']:.2f}")
        print(f"     Cash: ${record['cash']:.2f}, AX: ${record['ax']:.2f}")
    
    return sample_data


def test_data_conversion():
    """Test converting dictionary to EMDData object"""
    print("=== Testing Data Conversion ===")
    
    processor = EMDProcessor()
    
    # Test data
    test_data = {
        "total_amount": 12345.00,
        "report_date": "2025-08-07",
        "signature": "Jun Liu",
        "collection_msg": ["Message 1", "Message 2"],
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
    
    # Convert to EMDData object
    emd_data = processor.create_emd_data_from_dict(test_data)
    
    print(f"✓ Successfully converted dictionary to EMDData object")
    print(f"✓ Total amount: {emd_data.total_amount}")
    print(f"✓ Report date: {emd_data.report_date}")
    print(f"✓ Signature: {emd_data.signature}")
    print(f"✓ Collection messages: {len(emd_data.collection_msg)}")
    print(f"✓ EMD records: {len(emd_data.emd_list)}")
    
    # Test individual record conversion
    emd_record = processor.create_emd_record_from_dict(test_data['emd_list'][0])
    print(f"✓ EMD Record: {emd_record}")
    
    print()


def main():
    """Main test function"""
    print("EMD Processor Test Suite (New API Format)")
    print("=" * 60)
    print()
    
    # Run all tests
    test_spell_number()
    test_emd_record()
    test_emd_data()
    test_validation()
    test_filename_generation()
    test_processor_initialization()
    test_api_data_creation()
    test_data_conversion()
    
    print("=" * 60)
    print("Test suite completed!")
    print()
    print("To use the EMD processor with the new API format:")
    print("1. Prepare data in the specified JSON format")
    print("2. Have a template Excel file ready")
    print("3. Call: process_emd_data(emd_data_dict, template_path, output_path)")
    print()
    print("Example:")
    print("sample_data = {")
    print('    "total_amount": 12345.00,')
    print('    "report_date": "2025-08-07",')
    print('    "signature": "Jun Liu",')
    print('    "collection_msg": ["Message 1", "Message 2"],')
    print('    "emd_list": [...]')
    print("}")
    print()
    print("output_file = process_emd_data(")
    print("    emd_data_dict=sample_data,")
    print("    template_path='path/to/template.xlsx',")
    print("    output_path='path/to/output.xlsx'")
    print(")")


if __name__ == "__main__":
    main() 