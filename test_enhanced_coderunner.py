#!/usr/bin/env python3
"""
Test script for the enhanced CodeRunner functionality.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from libreapp.utils.code_runner import CodeRunner
import pandas as pd
import numpy as np

def test_automatic_code_detection():
    """Test automatic LLM code detection."""
    print("Testing automatic LLM code detection...")
    
    # Test with code
    response_with_code = """
    Let me analyze your data with some calculations:
    
    ```python
    # Create sample data
    data = {'glucose': [120, 135, 110, 145, 130]}
    df = pd.DataFrame(data)
    print(f"Average glucose: {df['glucose'].mean()}")
    ```
    
    This shows the basic analysis.
    """
    
    has_code = CodeRunner.detect_llm_code(response_with_code)
    print(f"Response with code detected: {has_code}")
    
    # Test without code
    response_without_code = """
    This is just a regular text response without any code blocks.
    It explains concepts but doesn't include executable code.
    """
    
    has_code = CodeRunner.detect_llm_code(response_without_code)
    print(f"Response without code detected: {has_code}")

def test_enhanced_execution():
    """Test enhanced code execution with multiple data types."""
    print("\nTesting enhanced code execution...")
    
    llm_response = """
    Let me create some sample data and visualizations:
    
    ```python
    import pandas as pd
    import numpy as np
    import plotly.express as px
    import matplotlib.pyplot as plt
    
    # Create sample glucose data
    glucose_data = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
        'glucose_level': np.random.normal(120, 20, 100)
    }
    df = pd.DataFrame(glucose_data)
    print(f"Created DataFrame with {len(df)} records")
    df.head()
    ```
    
    ```python
    # Create a Plotly visualization
    fig = px.line(df, x='timestamp', y='glucose_level', 
                  title='Glucose Levels Over Time')
    fig.show()
    ```
    
    ```python
    # Create a pandas Series
    avg_glucose_by_hour = df.set_index('timestamp').resample('H')['glucose_level'].mean()
    avg_glucose_by_hour.head()
    ```
    
    ```python
    # Create a NumPy array
    glucose_array = df['glucose_level'].values
    print(f"Array shape: {glucose_array.shape}")
    glucose_array[:5]
    ```
    
    ```python
    # Create a matplotlib figure
    plt.figure(figsize=(10, 6))
    plt.hist(df['glucose_level'], bins=20, alpha=0.7)
    plt.title('Glucose Level Distribution')
    plt.xlabel('Glucose Level')
    plt.ylabel('Frequency')
    plt.show()
    ```
    """
    
    # Execute the code
    results = CodeRunner.run_llm_code_blocks(llm_response, {})
    
    print(f"Execution results:")
    print(f"- Has code: {results.get('has_code', False)}")
    print(f"- Blocks executed: {len(results.get('executed_blocks', []))}")
    print(f"- DataFrames: {len(results.get('dataframes', []))}")
    print(f"- Plotly figures: {len(results.get('figures', []))}")
    print(f"- Matplotlib figures: {len(results.get('matplotlib_figures', []))}")
    print(f"- Series: {len(results.get('series', []))}")
    print(f"- Arrays: {len(results.get('arrays', []))}")
    
    # Check individual blocks
    for i, block in enumerate(results.get('executed_blocks', [])):
        print(f"\nBlock {i+1}:")
        print(f"  - Success: {block['success']}")
        print(f"  - Is DataFrame: {block.get('is_dataframe', False)}")
        print(f"  - Is Figure: {block.get('is_figure', False)}")
        print(f"  - Is Matplotlib Figure: {block.get('is_matplotlib_figure', False)}")
        print(f"  - Is Series: {block.get('is_series', False)}")
        print(f"  - Is Array: {block.get('is_array', False)}")
        if not block['success']:
            print(f"  - Error: {block['output']}")

def test_auto_execute():
    """Test the auto_execute_llm_response method."""
    print("\nTesting auto_execute_llm_response...")
    
    simple_response = """
    Here's a quick analysis:
    
    ```python
    # Simple calculation
    glucose_readings = [110, 120, 135, 125, 115]
    average = sum(glucose_readings) / len(glucose_readings)
    print(f"Average glucose: {average} mg/dL")
    ```
    """
    
    results = CodeRunner.auto_execute_llm_response(simple_response, {})
    print(f"Auto-execution results: {results.get('has_code', False)}")
    
    if results.get('has_code'):
        print(f"Executed {len(results['executed_blocks'])} code blocks")

if __name__ == "__main__":
    print("Enhanced CodeRunner Test Suite")
    print("=" * 50)
    
    try:
        test_automatic_code_detection()
        test_enhanced_execution()
        test_auto_execute()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
