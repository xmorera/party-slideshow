#!/usr/bin/env python3
"""
Pre-deployment check script
"""

import os
import sys

def check_deployment_readiness():
    """Check if the app is ready for deployment"""
    
    print("=== Pre-Deployment Check ===")
    
    issues = []
    
    # Check if critical files exist
    required_files = [
        'app.py',
        'requirements.txt',
        'runtime.txt',
        'templates/index.html'
    ]
    
    print("\n1. Checking required files...")
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            issues.append(f"Missing file: {file}")
    
    # Check requirements.txt content
    print("\n2. Checking requirements.txt...")
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            
        required_packages = ['Flask', 'dropbox', 'gunicorn', 'setuptools']
        for package in required_packages:
            if package.lower() in requirements.lower():
                print(f"✅ {package}")
            else:
                print(f"❌ {package} - MISSING")
                issues.append(f"Missing package in requirements.txt: {package}")
                
    except FileNotFoundError:
        issues.append("requirements.txt not found")
    
    # Check Python version specification
    print("\n3. Checking Python version...")
    if os.path.exists('runtime.txt'):
        with open('runtime.txt', 'r') as f:
            runtime = f.read().strip()
        print(f"✅ Python version specified: {runtime}")
    else:
        print("⚠️ No runtime.txt found - Render will use default Python version")
    
    # Check app.py imports
    print("\n4. Checking app.py imports...")
    try:
        # Test critical imports
        import flask
        print("✅ Flask import works")
        
        import dropbox
        print("✅ Dropbox import works")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv import works")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        issues.append(f"Import error: {e}")
    
    # Summary
    print(f"\n=== Summary ===")
    if not issues:
        print("✅ All checks passed! Ready for deployment.")
        return True
    else:
        print("❌ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease fix these issues before deploying.")
        return False

if __name__ == "__main__":
    success = check_deployment_readiness()
    if not success:
        sys.exit(1)