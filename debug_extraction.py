#!/usr/bin/env python3
"""
Debug script for code extraction.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from libreapp.utils.code_runner import CodeRunner
import re

def debug_code_extraction():
    """Debug the code extraction."""
    test_text = """
    Let me analyze your data with some calculations:
    
    ```python
    # Create sample data
    data = {'glucose': [120, 135, 110, 145, 130]}
    df = pd.DataFrame(data)
    print(f"Average glucose: {df['glucose'].mean()}")
    ```
    
    This shows the basic analysis.
    """
    
    print("Original text:")
    print(repr(test_text))
    print("\n" + "="*50 + "\n")
    
    # Test the patterns manually
    patterns = [
        r"```python\n(.*?)\n```",
        r"```py\n(.*?)\n```", 
        r"```\n(.*?)\n```"
    ]
    
    for i, pattern in enumerate(patterns):
        print(f"Pattern {i+1}: {pattern}")
        matches = re.findall(pattern, test_text, re.DOTALL)
        print(f"Matches: {len(matches)}")
        for j, match in enumerate(matches):
            print(f"  Match {j+1}: {repr(match)}")
        print()
    
    # Test the actual method
    code_blocks = CodeRunner.extract_code_blocks(test_text)
    print(f"Extracted code blocks: {len(code_blocks)}")
    for i, block in enumerate(code_blocks):
        print(f"Block {i+1}:")
        print(block)
        print("-" * 30)

if __name__ == "__main__":
    debug_code_extraction()
