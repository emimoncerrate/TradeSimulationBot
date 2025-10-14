# 🚀 Quick Reference Card

## 📁 **Where to Find Things**

| What you need             | Where to find it          |
| ------------------------- | ------------------------- |
| **🚀 Setup Instructions** | `docs/setup/SETUP_LOG.md` |
| **🗂️ Project Structure**  | `PROJECT_STRUCTURE.md`    |
| **🔧 View Database**      | `tools/view_database.py`  |
| **🧪 Run Tests**          | `tests/` folder           |
| **📊 Fix Documentation**  | `docs/fixes/`             |
| **📖 Guides**             | `docs/guides/`            |
| **⚙️ Configuration**      | `.env` file               |
| **🚀 Start Bot**          | `python app.py`           |

## 🎯 **Common Commands**

```bash
# Start the bot
python app.py

# View database
python tools/view_database.py

# Setup DynamoDB
./scripts/setup_local_dynamodb.sh

# Create tables
python scripts/create_dynamodb_tables.py --local

# Run tests
pytest tests/

# Check Docker
docker ps | grep dynamodb
```

## 📋 **File Organization**

- **Root**: Only essential files (app.py, .env, README.md, etc.)
- **docs/**: All documentation organized by type
- **tests/**: All test files moved here
- **tools/**: Utility scripts and helpers
- **logs/**: Log files (auto-created)
- **Core folders**: services/, models/, listeners/, etc. (unchanged)

## 🎉 **Benefits of New Structure**

✅ **Clean root directory** - Only essential files visible  
✅ **Organized documentation** - Easy to find guides and fixes  
✅ **Separated tests** - All tests in one place  
✅ **Utility tools** - Development helpers organized  
✅ **Better navigation** - Logical folder structure  
✅ **Professional appearance** - Production-ready organization

## 🔍 **Quick Navigation**

- **Need help setting up?** → `docs/setup/SETUP_LOG.md`
- **Want to understand the code?** → `PROJECT_STRUCTURE.md`
- **Need to debug?** → `tools/view_database.py`
- **Want to test?** → `tests/`
- **Looking for a specific fix?** → `docs/fixes/`
