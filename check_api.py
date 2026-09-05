import sys
sys.path.insert(0, r'X:\second-brain-kb')
import api
import inspect

print('=== api.py endpoints ===')
for name, obj in inspect.getmembers(api):
    if hasattr(obj, '__call__') and hasattr(obj, '__name__'):
        if not name.startswith('_'):
            try:
                sig = inspect.signature(obj)
                print(f'  {name}: {sig}')
            except:
                print(f'  {name}: (no signature)')

print()
print('=== FastAPI routes ===')
for route in api.app.routes:
    if hasattr(route, 'methods'):
        print(f'  {" ".join(route.methods)} {route.path}')
    else:
        print(f'  {route.path}')