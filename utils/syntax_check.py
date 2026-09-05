"""
utils/syntax_check.py
----------------------
Pre-flight validation for uploaded .py files, so users get a clear,
actionable error instead of a silently-dead process.
"""


def check_python_syntax(file_path: str):
    """
    Returns (ok: bool, message: str)
    message is only meaningful when ok is False.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code_content = f.read()
    except UnicodeDecodeError as e:
        return False, f"❌ Could not read file as UTF-8: {e}"
    except Exception as e:
        return False, f"❌ Error reading file: {e}"

    try:
        compile(code_content, file_path, "exec")
    except SyntaxError as e:
        line = e.text.strip() if e.text else ""
        msg = (
            f"File \"{file_path}\", line {e.lineno}\n"
            f"    {line}\n"
            f"SyntaxError: {e.msg}"
        )
        return False, msg
    except Exception as e:
        return False, f"❌ Error compiling file: {e}"

    return True, ""
