#!/usr/bin/env python3
"""
Script to integrate Risk Alert feature into the Slack Trading Bot.

This script updates app.py and actions.py to add risk alert functionality.
"""

import os
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def add_imports_to_app():
    """Add risk alert imports to app.py."""
    app_file = project_root / "app.py"
    
    if not app_file.exists():
        print("❌ app.py not found")
        return False
    
    content = app_file.read_text()
    
    # Check if already integrated
    if "from services.alert_monitor import" in content:
        print("✅ Risk alert imports already present in app.py")
        return True
    
    # Find the import section (after other service imports)
    import_pattern = r"(from services\.service_container import.*\n)"
    
    new_imports = """from services.alert_monitor import get_alert_monitor
from listeners.risk_alert_handlers import register_risk_alert_handlers
"""
    
    content = re.sub(import_pattern, r"\1" + new_imports, content)
    
    app_file.write_text(content)
    print("✅ Added risk alert imports to app.py")
    return True


def initialize_alert_monitor_in_app():
    """Add alert monitor initialization to app.py."""
    app_file = project_root / "app.py"
    content = app_file.read_text()
    
    # Check if already integrated
    if "alert_monitor = get_alert_monitor" in content:
        print("✅ Alert monitor already initialized in app.py")
        return True
    
    # Find where to add initialization (after service container creation)
    pattern = r"(service_container = get_container\(\)\n)"
    
    initialization = """
# Initialize alert monitor
notification_service = NotificationService()
alert_monitor = get_alert_monitor(
    db_service=service_container.get(DatabaseService),
    notification_service=notification_service,
    market_data_service=None  # Will be initialized async
)
"""
    
    content = re.sub(pattern, r"\1" + initialization, content)
    
    app_file.write_text(content)
    print("✅ Added alert monitor initialization to app.py")
    return True


def register_handlers_in_app():
    """Add risk alert handler registration to app.py."""
    app_file = project_root / "app.py"
    content = app_file.read_text()
    
    # Check if already integrated
    if "register_risk_alert_handlers" in content:
        print("✅ Risk alert handlers already registered in app.py")
        return True
    
    # Find where to add registration (after event handler registration)
    pattern = r"(logger\.info\(\"Event handlers registered successfully\"\)\n)"
    
    registration = """
    # Register risk alert handlers
    try:
        register_risk_alert_handlers(
            app=app,
            db_service=service_container.get(DatabaseService),
            auth_service=service_container.get(AuthService),
            alert_monitor=alert_monitor,
            notification_service=notification_service
        )
        logger.info("Risk alert handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to register risk alert handlers: {e}")
    
"""
    
    content = re.sub(pattern, r"\1" + registration, content)
    
    app_file.write_text(content)
    print("✅ Added risk alert handler registration to app.py")
    return True


def integrate_alert_check_in_actions():
    """Add alert checking to trade execution in actions.py."""
    actions_file = project_root / "listeners" / "actions.py"
    
    if not actions_file.exists():
        print("❌ actions.py not found")
        return False
    
    content = actions_file.read_text()
    
    # Check if already integrated
    if "check_trade_against_alerts" in content:
        print("✅ Alert checking already integrated in actions.py")
        return True
    
    # Find the trade execution success block
    pattern = r"(if execution_result\.success:\s+trade\.status = TradeStatus\.EXECUTED\s+trade\.execution_id = execution_result\.execution_id)"
    
    alert_check = r"""\1
                
                # Check trade against active risk alerts
                try:
                    await alert_monitor.check_trade_against_alerts(trade)
                    logger.info(f"Trade {trade.trade_id} checked against risk alerts")
                except Exception as e:
                    logger.error(f"Failed to check risk alerts: {e}")
                    # Don't fail trade if alert check fails"""
    
    content = re.sub(pattern, alert_check, content)
    
    actions_file.write_text(content)
    print("✅ Added alert checking to actions.py")
    return True


def create_init_imports():
    """Ensure __init__.py files are updated."""
    # Update models/__init__.py
    models_init = project_root / "models" / "__init__.py"
    if models_init.exists():
        content = models_init.read_text()
        if "risk_alert" not in content:
            content += "\nfrom models.risk_alert import RiskAlertConfig, AlertTriggerEvent, AlertStatus\n"
            models_init.write_text(content)
            print("✅ Updated models/__init__.py")
    
    # Update services/__init__.py
    services_init = project_root / "services" / "__init__.py"
    if services_init.exists():
        content = services_init.read_text()
        if "alert_monitor" not in content:
            content += "\nfrom services.alert_monitor import RiskAlertMonitor, get_alert_monitor\n"
            services_init.write_text(content)
            print("✅ Updated services/__init__.py")
    
    # Update ui/__init__.py
    ui_init = project_root / "ui" / "__init__.py"
    if ui_init.exists():
        content = ui_init.read_text()
        if "risk_alert_widget" not in content:
            content += "\nfrom ui.risk_alert_widget import create_risk_alert_modal\n"
            ui_init.write_text(content)
            print("✅ Updated ui/__init__.py")


def main():
    """Run integration."""
    print("🚀 Integrating Risk Alert Feature...")
    print("=" * 50)
    
    success = True
    
    # Step 1: Add imports
    print("\n📦 Step 1: Adding imports...")
    if not add_imports_to_app():
        success = False
    
    # Step 2: Initialize alert monitor
    print("\n🔧 Step 2: Initializing alert monitor...")
    if not initialize_alert_monitor_in_app():
        success = False
    
    # Step 3: Register handlers
    print("\n📝 Step 3: Registering handlers...")
    if not register_handlers_in_app():
        success = False
    
    # Step 4: Integrate alert checking
    print("\n🔍 Step 4: Integrating alert checking...")
    if not integrate_alert_check_in_actions():
        success = False
    
    # Step 5: Update init files
    print("\n📂 Step 5: Updating __init__.py files...")
    create_init_imports()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Risk Alert feature integrated successfully!")
        print("\n📖 Next steps:")
        print("1. Review RISK_ALERT_INTEGRATION.md for details")
        print("2. Run python3 test_config.py to verify")
        print("3. Test with /risk-alert command in Slack")
        print("4. Monitor logs for alert triggers")
    else:
        print("⚠️  Integration completed with warnings")
        print("Please review the output above and check the files manually")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

