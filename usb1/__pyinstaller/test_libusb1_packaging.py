"""
PyTest testcases for the pyinstaller hook

Instructions to run these tests:

- Install PyInstaller with the hook_testing extra requirements:
  > pip install pyinstaller[hook_testing]

- Run the tests using the provided utility by pyinstaller:
  > python -m PyInstaller.utils.run_tests --include_only usb1

"""
import subprocess
from PyInstaller import __main__ as pyi_main


def test_pyi_hooksample(tmp_path):
    app_name = "userapp"
    workpath = tmp_path / "build"
    distpath = tmp_path / "dist"
    app = tmp_path / (app_name + ".py")
    app.write_text("\n".join([
        "import usb1",
        "print(usb1.getVersion())"
    ]))
    args = [
        # Place all generated files in ``tmp_path``.
        '--workpath', str(workpath),
        '--distpath', str(distpath),
        '--specpath', str(tmp_path),
        str(app),
    ]
    pyi_main.run(args)
    subprocess.run([str(distpath / app_name / app_name)], check=True)