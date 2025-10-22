"""
Quick Start Script - Start the Library System
"""
import subprocess
import webbrowser
import time
import os

print("=" * 60)
print("🚀 Starting Library System...")
print("=" * 60)
print()

# Check if we're in the right directory
if not os.path.exists('manage.py'):
    print("❌ Error: manage.py not found!")
    print("Please run this script from the ProjectMicrosoft directory.")
    input("Press Enter to exit...")
    exit(1)

print("✓ Starting Django development server...")
print("✓ Server will run at: http://localhost:8000/")
print()
print("📚 Student Interface: http://localhost:8000/")
print("⚙️  Admin Panel: http://localhost:8000/admin/")
print()
print("Press Ctrl+C to stop the server")
print("=" * 60)
print()

# Give user a moment to read
time.sleep(2)

# Open browser after a short delay
def open_browser():
    time.sleep(3)
    print("\n🌐 Opening browser...")
    webbrowser.open('http://localhost:8000/')

# Start browser opener in background
import threading
browser_thread = threading.Thread(target=open_browser)
browser_thread.daemon = True
browser_thread.start()

# Start Django server
try:
    subprocess.run(['python', 'manage.py', 'runserver'], check=True)
except KeyboardInterrupt:
    print("\n\n👋 Server stopped. Goodbye!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nMake sure Django is installed:")
    print("  pip install django django-import-export")
    input("\nPress Enter to exit...")
