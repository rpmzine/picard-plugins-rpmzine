# Development Notes

Architecture and implementation notes for the rpmzine Picard plugin collection.

---

## Repository Layout

Each plugin lives in its own subdirectory and is self-contained:

```
plugin_name/
├── __init__.py       # Plugin code (PLUGIN_NAME, PLUGIN_VERSION, enable(api), …)
├── _compat.py        # Compatibility shim — identical copy of root _compat.py
└── MANIFEST.toml     # Picard 3.0 metadata (uuid, api, authors, repository)
```

`_compat.py` at the repo root is the **master copy**. After editing it, copy it to all plugin directories:

```sh
for d in album_subfolder artwork_searcher audio_file_info cluster_refresh \
          grouping_tagger multidisc_tagger suffix_appender tag_filter_joiner; do
    cp _compat.py "$d/_compat.py"
done
```

---

## Picard 2.x vs Picard 3.0 API

### The key difference

Picard 3.0 introduces a V3 plugin API. Plugins receive an `api` (a `PluginApi` object) as the argument to `enable()`. Registrations go through this object, and action classes are passed as classes (not instances).

| | Picard 2.x | Picard 3.0 |
|---|---|---|
| `enable` signature | `def enable(api): ...` (same) | same |
| Registration | `register_cluster_action(instance)` | `api.register_cluster_action(MyClass)` |
| Tagger access in callbacks | `self.tagger` | `self.api.tagger` |
| Cluster object `.files` | via `tagger.get_files_from_objects(objs)` | direct `obj.files` attribute |
| Action menu label | `NAME` attribute | `TITLE` attribute (falls back to `NAME`) |

### The `enable(api)` pattern

Every plugin uses this pattern to support both V2 and V3:

```python
def enable(api):
    use_v3 = hasattr(api, 'register_cluster_action')
    if use_v3:
        api.register_cluster_action(MyAction)   # pass the CLASS
        api.register_file_action(MyAction)
    else:
        _action = MyAction()                    # V2 needs an instance
        register_cluster_action(_action)
        register_file_action(_action)
```

Detection: `hasattr(api, 'register_cluster_action')` is `True` only in V3. In V2, `api` is a stub that does not have these attributes, so the global lazy wrappers (imported from `_compat`) are used instead.

### Action class requirements

```python
class MyAction(BaseAction):
    NAME = "My Action"      # V2 menu label; also used as TITLE fallback
    TITLE = "My Action"     # V3 menu label — must match what you want in the menu

    def callback(self, objs):
        # objs: list of selected Picard objects (Cluster, Album, File, Track)
        tagger = getattr(getattr(self, 'api', None), 'tagger', None) \
                 or getattr(self, 'tagger', None)
        # V3 objects have .files directly; V2 uses get_files_from_objects
        files = []
        for obj in objs:
            if hasattr(obj, 'files'):
                files.extend(obj.files)
            elif hasattr(obj, 'filename'):
                files.append(obj)
        if not files and tagger and hasattr(tagger, 'get_files_from_objects'):
            files = list(tagger.get_files_from_objects(objs))
```

### Metadata processors and options pages

`register_track_metadata_processor` and `register_options_page` work the same in V2 and V3 — the global lazy wrappers in `_compat.py` handle both:

```python
def enable(api):
    register_options_page(MyOptionsPage)           # works in both versions
    register_track_metadata_processor(my_handler)  # works in both versions
```

---

## `_compat.py` Architecture

The shim solves two problems:
1. PyQt5 vs PyQt6 scoped enums (`Qt.AlignCenter` vs `Qt.AlignmentFlag.AlignCenter`)
2. Picard 2.x vs 3.0 import paths for `BaseAction`, `OptionsPage`, `register_*` functions

### PyQt detection

Feature-probe instead of inspecting module names (PyInstaller bundles register names differently):

```python
try:
    from PyQt6 import QtCore, QtWidgets, QtGui
    QtWidgets.QMessageBox.StandardButton.Yes   # raises AttributeError on PyQt5
    _PYQT6 = True
except (ImportError, AttributeError):
    from PyQt5 import QtCore, QtWidgets, QtGui
    _PYQT6 = False
```

### `_QtNS` proxy — universal Qt enum access

`Qt = _QtNS()` is a proxy object that lets plugin code write `Qt.AlignCenter` on both PyQt5 and PyQt6:

```python
class _QtNS:
    def __getattr__(self, name):
        raw = getattr(QtCore.Qt, name, _MISSING)
        if raw is not _MISSING:
            return raw                          # PyQt5 flat access works
        # PyQt6: search scoped enum namespaces
        for ns_name in ('AlignmentFlag', 'ItemDataRole', 'TextFormat',
                        'CheckState', 'WindowType', 'ConnectionType', ...):
            ns = getattr(QtCore.Qt, ns_name, None)
            if ns and hasattr(ns, name):
                return getattr(ns, name)
        raise AttributeError(name)
```

Write `Qt.AlignCenter`, `Qt.UserRole`, `Qt.Checked`, etc. in plugin code — the proxy resolves the correct enum value for whichever Qt version is loaded.

### `BaseAction` lookup

```python
try:
    from picard.plugin3.api import BaseAction   # Picard 3.0 V3
except ImportError:
    try:
        from picard.ui.itemviews import BaseAction  # Picard 2.x
    except ImportError:
        BaseAction = object                          # safe no-op fallback
```

### `exec_` compatibility on dialogs

PyQt6 removed `QDialog.exec_()` (renamed to `exec()`). The shim provides real Python wrappers — not class-level aliases (which fail due to SIP slot restrictions):

```python
class _CompatDialog(QtWidgets.QDialog):
    def exec_(self):
        return super().exec()   # real method, not an alias
```

### Lazy `register_*` wrappers

Global registration functions are looked up in `sys.modules` at call time, not at import time. This ensures the correct Picard module is targeted regardless of import order:

```python
def _lazy(module_path, fn_name):
    def wrapper(*args, **kwargs):
        mod = sys.modules.get(module_path)
        fn = getattr(mod, fn_name, None) if mod else None
        if fn:
            return fn(*args, **kwargs)
    return wrapper

register_cluster_action = _lazy('picard.ui.itemviews', 'register_cluster_action')
register_options_page   = _lazy('picard.ui.options',   'register_options_page')
# … etc
```

---

## Adding a New Plugin

1. Create `new_plugin/` with `__init__.py` and copy `_compat.py` into it.

2. Write the `MANIFEST.toml`:

   ```toml
   uuid = "<generate a new UUID>"
   name = "My Plugin"
   description = "One-line description."
   api = ["3.0"]
   authors = ["rpmzine"]
   license = "MIT"
   license_url = "https://opensource.org/licenses/MIT"
   repository = "https://github.com/rpmzine/picard-plugins-rpmzine"
   ```

3. In `__init__.py`, follow this skeleton:

   ```python
   PLUGIN_NAME = "My Plugin"
   PLUGIN_AUTHOR = "rpmzine"
   PLUGIN_DESCRIPTION = "Does X."
   PLUGIN_VERSION = "1.0.0"
   PLUGIN_API_VERSIONS = ["2.10", "2.11", "2.12", "2.13", "3.0"]
   PLUGIN_LICENSE = "MIT"
   PLUGIN_LICENSE_URL = "https://opensource.org/licenses/MIT"

   from picard import log
   from ._compat import BaseAction, register_cluster_action, register_file_action

   class MyAction(BaseAction):
       NAME = "My Action"
       TITLE = "My Action"

       def callback(self, objs):
           tagger = getattr(getattr(self, 'api', None), 'tagger', None) \
                    or getattr(self, 'tagger', None)
           # … your logic here

   def enable(api):
       if hasattr(api, 'register_cluster_action'):
           api.register_cluster_action(MyAction)
       else:
           register_cluster_action(MyAction())
       log.info("My Plugin: loaded")
   ```

4. Add the plugin to the root `MANIFEST.toml` description field and to `README.md`.

---

## Common Pitfalls

### "name 'Qt' is not defined"

The `_compat.py` exports `Qt = _QtNS()` as the proxy. If you forget to import it:

```python
from ._compat import Qt, QtCore, QtWidgets   # Qt must be listed explicitly
```

### V3 registration takes a CLASS, not an instance

```python
# Wrong (V3):
api.register_cluster_action(MyAction())   # instance — will error or silently fail

# Right (V3):
api.register_cluster_action(MyAction)     # class
```

### V2 registration takes an instance, not a class

The global lazy wrappers expect an instance. Create one inline in the V2 branch rather than keeping a module-level singleton — module-level instances can interfere when Picard reloads plugins.

### `exec_` vs `exec`

Never write `QDialog.exec_ = QDialog.exec` at class level — SIP slot aliasing fails. Use a real method wrapper (`def exec_(self): return super().exec()`), which `_compat.py` provides via `_CompatDialog`.

### Picard 3.0 callback objects

In V3, `callback(self, objs)` receives `picard.plugin3.api.Cluster` / `Album` objects. These expose a `.files` attribute directly. `tagger.get_files_from_objects(objs)` is V2-only and will return nothing (or error) on V3 objects — always check `.files` first:

```python
files = []
for obj in objs:
    if hasattr(obj, 'files'):
        files.extend(obj.files)
    elif hasattr(obj, 'filename'):
        files.append(obj)
if not files and tagger and hasattr(tagger, 'get_files_from_objects'):
    files = list(tagger.get_files_from_objects(objs))
```

---

## Building Distribution ZIPs

```sh
bash install_plugins.sh
```

Per-plugin ZIPs are written to `dist/`. These are the files to attach to GitHub Releases or install via Picard's "Install Plugin" dialog.

---

## Tested Environment

- MusicBrainz Picard 3.0 (macOS, PyQt6)
- MusicBrainz Picard 2.12/2.13 (macOS, PyQt5)
- Python 3.11+
