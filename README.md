# Flight Check --- Python Edition 0.5

## Install/Update

Download this project, and extract to a new folder.

### Build an virtual environment

In the project folder(where the README.md is), run the following commands

```
python -m venv .venv

.venv/scripts/activate

pip install -r requirements.txt
```

### Update the Shortcut

1. Right click the 'Run.lnk' to open its property.

0. Change the 'target' to ``Current_folder_absolute_path\.venv\Scripts\pythonw.exe "Current_folder_absolute_path\main_window.py"``

0. Change the 'start' to ``Current_folder_absolute_path\.venv\Scripts``

0. The icon is in the 'resources' folder, if you like.

0. the '--debug' shows detail messages; the '--pr_list' shows the separated result.

## Major update

1. Add an user interface based on QT PySide6.

0. Fixed "FBA/1PC" of the baggage allowence.

## main_window.py

This is for the basic window and controls setup.

## run_button.py

Saved functions of the button of 'Run'.

## obtain_info.py

Split a single PR infomation and check mistakes.

## genaral_func.py

Saved some arguments and general functions.