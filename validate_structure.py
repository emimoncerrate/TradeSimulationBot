#!/usr/bin/env python3
"""
Project structure validation script.
Validates that all required files and directories are in place.
"""

import os
from pathlib import Path

def validate_project_structure():
    """Validate that all required files and directories exist."""
    
    required_files = [
        # Core application files
        'app.py',
        'requirements.txt',
        'template.yaml',
        'docker-compose.yml',
        'Dockerfile',
        '.env.example',
        'README.md',
        
        # Configuration
        'config/__init__.py',
        'config/settings.py',
        
        # Listeners
        'listeners/__init__.py',
        'listeners/commands.py',
        'listeners/actions.py',
        'listeners/events.py',
        
        # Other packages
        'services/__init__.py',
        'models/__init__.py',
        'ui/__init__.py',
        'utils/__init__.py',
        
        # Scripts
        'scripts/docker-build.sh',
        'scripts/deploy-lambda.sh'
    ]
    
    required_dirs = [
        'config',
        'listeners', 
        'services',
        'models',
        'ui',
        'utils',
        'scripts'
    ]
    
    print("🔍 Validating project structure...")
    print("=" * 50)
    
    # Check directories
    missing_dirs = []
    for dir_path in required_dirs:
        if not os.path.isdir(dir_path):
            missing_dirs.append(dir_path)
        else:
            print(f"✅ Directory: {dir_path}")
    
    # Check files
    missing_files = []
    for file_path in required_files:
        if not os.path.isfile(file_path):
            missing_files.append(file_path)
        else:
            print(f"✅ File: {file_path}")
    
    print("\n" + "=" * 50)
    
    if missing_dirs:
        print("❌ Missing directories:")
        for dir_path in missing_dirs:
            print(f"   - {dir_path}")
    
    if missing_files:
        print("❌ Missing files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
    
    if not missing_dirs and not missing_files:
        print("🎉 All required files and directories are present!")
        print("\n📋 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Copy .env.example to .env and configure")
        print("3. Run: python test_config.py")
        print("4. Start development: docker-compose up -d")
        return True
    else:
        print(f"❌ Project structure incomplete: {len(missing_dirs + missing_files)} items missing")
        return False

def check_file_permissions():
    """Check that script files have execute permissions."""
    script_files = [
        'scripts/docker-build.sh',
        'scripts/deploy-lambda.sh'
    ]
    
    print("\n🔐 Checking script permissions...")
    
    for script in script_files:
        if os.path.isfile(script):
            if os.access(script, os.X_OK):
                print(f"✅ Executable: {script}")
            else:
                print(f"⚠️  Not executable: {script}")
                print(f"   Run: chmod +x {script}")

def main():
    """Main validation function."""
    print("🏗️  Jain Global Slack Trading Bot - Structure Validation")
    print("=" * 60)
    
    structure_valid = validate_project_structure()
    check_file_permissions()
    
    return 0 if structure_valid else 1

if __name__ == "__main__":
    exit(main())