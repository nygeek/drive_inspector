#!/usr/bin/env python3
import ast
import sys
import argparse

def extract_function(filename, func_name):
    with open(filename, 'r') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
        lines = source.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                start_line = node.lineno - 1
                if hasattr(node, 'end_lineno'):
                    end_line = node.end_lineno
                else:
                    # Fallback for older Python versions
                    end_line = start_line + 1
                    while end_line < len(lines) and (lines[end_line].startswith('    ') or lines[end_line].strip() == ''):
                        end_line += 1
                
                return '\n'.join(lines[start_line:end_line])
        
        return f"Function '{func_name}' not found in {filename}"
    
    except SyntaxError as e:
        return f"Syntax error in {filename}: {e}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract a function from a Python file')
    parser.add_argument('file', help='Python file to extract from')
    parser.add_argument('function', help='Function name to extract')
    
    args = parser.parse_args()
    print(extract_function(args.file, args.function))
