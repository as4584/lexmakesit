import importlib
import sys
sys.path.insert(0, '/app')
try:
    import ai_receptionist.app.api.business as biz
    print("Import successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
