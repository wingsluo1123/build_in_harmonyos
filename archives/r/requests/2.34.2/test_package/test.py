# Test that requests can be imported
import sys
try:
    import requests
    print(f"requests {requests.__version__} imported successfully")
    sys.exit(0)
except ImportError as e:
    print(f"FAIL: {e}")
    sys.exit(1)