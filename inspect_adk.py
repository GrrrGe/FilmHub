# inspect_adk.py (Version 4 - Callback Finder)
import pkgutil
import importlib
import inspect
import google.adk

print("🔍 Searching for all callback-related classes in google.adk...")
print("-" * 60)

found = False
# Walk through all modules in the google.adk package
for _, modname, _ in pkgutil.walk_packages(path=google.adk.__path__, prefix=google.adk.__name__ + '.'):
    # We are interested in any module with 'callback' in its name
    if 'callback' in modname:
        try:
            module = importlib.import_module(modname)
            # Find all classes within that module
            classes = [name for name, obj in inspect.getmembers(module, inspect.isclass)]
            if classes:
                print(f"📄 Found module: {modname}")
                print(f"   └── Contains classes: {classes}\n")
                found = True
        except Exception:
            # Ignore modules that can't be imported
            pass

if not found:
    print("❌ No modules containing 'callback' with classes were found.")

print("-" * 60)
print("Search complete.")