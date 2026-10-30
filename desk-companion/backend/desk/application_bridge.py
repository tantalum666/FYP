"""Typed-command bridge to a real visible LibreOffice/Chromium instance.

Called through the configured executor with validated application data on stdin.
It never receives code, shell, a caller URL, credentials or an arbitrary file path.
"""

import contextlib
import fcntl
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path("/workspace")
INPUTS = Path("/inputs")
MAX_BYTES = 8_000_000


def path_under(root, relative):
    if (
        not isinstance(relative, str)
        or not relative
        or relative.startswith("/")
        or ".." in Path(relative).parts
    ):
        raise ValueError("APPLICATION_PATH_DENIED")
    path = root / relative
    if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root.parent):
        raise ValueError("APPLICATION_PATH_DENIED")
    if not path.resolve().is_relative_to(root):
        raise ValueError("APPLICATION_PATH_DENIED")
    return path


def props(**values):
    import uno

    result = []
    for name, value in values.items():
        item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        item.Name, item.Value = name, value
        result.append(item)
    return tuple(result)


def desktop():
    import uno

    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local
    )
    context = resolver.resolve("uno:pipe,name=desk-applications;urp;StarOffice.ComponentContext")
    return context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)


def capture(path):
    from PIL import ImageGrab

    ImageGrab.grab(xdisplay=os.environ.get("DISPLAY", ":99")).save(path)


def normalized(text):
    return " ".join(str(text).split())


def document_content(document):
    blocks = []
    iterator = document.Text.createEnumeration()
    while iterator.hasMoreElements():
        item = iterator.nextElement()
        if item.supportsService("com.sun.star.text.TextTable"):
            blocks.extend(
                normalized(item.getCellByName(name).String) for name in item.getCellNames()
            )
        elif item.supportsService("com.sun.star.text.Paragraph") and normalized(item.String):
            blocks.append(normalized(item.String))
    return blocks


def snapshot(document):
    properties = document.DocumentProperties.UserDefinedProperties
    try:
        operation = properties.getPropertyValue("DeskOperation")
    except Exception:
        operation = None
    result = {
        "operation_id": operation,
        "visible": document.CurrentController.Frame.ContainerWindow.isVisible(),
        "window_title": document.CurrentController.Frame.Title,
    }
    if document.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
        sheets = []
        for name in document.Sheets.getElementNames():
            sheet = document.Sheets.getByName(name)
            cursor = sheet.createCursor()
            cursor.gotoEndOfUsedArea(True)
            end = cursor.RangeAddress
            if end.EndColumn > 23 or end.EndRow > 149:
                raise ValueError("WORKBOOK_RANGE_LIMIT")
            cells = []
            for row in range(end.EndRow + 1):
                for col in range(end.EndColumn + 1):
                    cell = sheet.getCellByPosition(col, row)
                    kind = cell.Type.value
                    if kind != "EMPTY":
                        cells.append(
                            {
                                "cell": chr(65 + col) + str(row + 1),
                                "kind": kind,
                                "text": cell.String,
                                "value": cell.Value,
                                "formula": cell.Formula,
                                "error": cell.Error,
                            }
                        )
            sheets.append({"sheet": name, "cells": cells})
        result.update(application="libreoffice_calc", sheets=sheets)
    else:
        result.update(application="libreoffice_writer", content=document_content(document))
    return result


def mark(document, operation):
    properties = document.DocumentProperties.UserDefinedProperties
    if properties.PropertySetInfo.hasPropertyByName("DeskOperation"):
        properties.setPropertyValue("DeskOperation", operation)
    else:
        properties.addProperty("DeskOperation", 0, operation)
    document.DocumentProperties.Subject = "Desk Companion operation " + operation


def edit_workbook(document, step, cancelled, creating=False):
    # References must resolve while each formula is parsed. Create every sheet
    # first; adding a missing sheet later does not repair an unresolved name.
    for edit in step["sheets"]:
        if not document.Sheets.hasByName(edit["sheet"]):
            document.Sheets.insertNewByName(edit["sheet"], document.Sheets.Count)
    for edit in step["sheets"]:
        sheet = document.Sheets.getByName(edit["sheet"])
        for item in edit["cells"]:
            cancelled()
            cell = sheet.getCellRangeByName(item["cell"])
            if item["kind"] == "text":
                cell.String = item["value"]
            elif item["kind"] == "number":
                cell.Value = item["value"]
            else:
                cell.Formula = item["value"]
            cell.CharFontName = "Liberation Sans"
            cell.CharHeight = 11
            if item.get("format") == "heading":
                cell.CharWeight = 150
                cell.CellBackColor = 0xE8EDF4
            elif item.get("format") in {"money", "percent"}:
                import uno

                locale = uno.createUnoStruct("com.sun.star.lang.Locale")
                locale.Language, locale.Country = "en", "GB"
                code = "0.00%" if item["format"] == "percent" else "0.00"
                key = document.NumberFormats.queryKey(code, locale, True)
                if key < 0:
                    key = document.NumberFormats.addNew(code, locale)
                cell.NumberFormat = key
        used = sheet.createCursor()
        used.gotoEndOfUsedArea(True)
        address = used.RangeAddress
        columns = sheet.getCellRangeByPosition(0, 0, address.EndColumn, address.EndRow).Columns
        columns.OptimalWidth = True
        for index in range(columns.Count):
            column = columns.getByIndex(index)
            column.Width = min(6000, max(1800, column.Width))
    if (
        creating
        and document.Sheets.Count > 1
        and document.Sheets.hasByName("Sheet1")
        and all(s["sheet"] != "Sheet1" for s in step["sheets"])
    ):
        first = document.Sheets.getByName("Sheet1")
        if not first.getCellByPosition(0, 0).String:
            document.Sheets.removeByName("Sheet1")
    document.calculateAll()
    document.CurrentController.setActiveSheet(document.Sheets.getByName(step["sheets"][0]["sheet"]))


def edit_document(document, step, cancelled):
    import uno

    if step.get("mode") != "append":
        document.Text.String = ""
    styles = document.StyleFamilies.getByName("PageStyles")
    page = styles.getByName("Standard")
    for key, value in {
        "Width": 21000,
        "Height": 29700,
        "LeftMargin": 1800,
        "RightMargin": 1800,
        "TopMargin": 1700,
        "BottomMargin": 1700,
    }.items():
        page.setPropertyValue(key, value)
    cursor = document.Text.createTextCursor()
    cursor.gotoEnd(False)
    for block in step["blocks"]:
        cancelled()
        if block["kind"] == "table":
            table = document.createInstance("com.sun.star.text.TextTable")
            table.initialize(len(block["rows"]), len(block["rows"][0]))
            document.Text.insertTextContent(cursor, table, False)
            table.setPropertyValue("RepeatHeadline", True)
            for r, values in enumerate(block["rows"]):
                for c, value in enumerate(values):
                    cell = table.getCellByName(chr(65 + c) + str(r + 1))
                    cell.String = value
                    text_cursor = cell.createTextCursor()
                    text_cursor.CharFontName, text_cursor.CharHeight = "Liberation Sans", 10
                    if r == 0:
                        text_cursor.CharWeight = 150
                        cell.BackColor = 0xE8EDF4
            cursor.gotoEnd(False)
            document.Text.insertControlCharacter(cursor, 0, False)
        elif block["kind"] == "page_break":
            cursor.BreakType = uno.Enum("com.sun.star.style.BreakType", "PAGE_BEFORE")
        else:
            cursor.ParaStyleName = {
                "title": "Title",
                "heading": "Heading 1",
                "paragraph": "Text body",
            }[block["kind"]]
            cursor.CharFontName = "Liberation Sans"
            cursor.CharHeight = {"title": 22, "heading": 14, "paragraph": 11}[block["kind"]]
            document.Text.insertString(cursor, block["text"], False)
            document.Text.insertControlCharacter(cursor, 0, False)
            cursor.BreakType = uno.Enum("com.sun.star.style.BreakType", "NONE")


def office(request):
    import uno

    mode = request["mode"]
    path = path_under(ROOT, request["path"])
    engine = desktop()
    before = []
    components = engine.Components.createEnumeration()
    while components.hasMoreElements():
        before.append(components.nextElement())
    # All windows belong to the isolated executor. Dispose them before loading
    # to force a new disk read rather than reusing an already-open UNO model.
    for old in before:
        with contextlib.suppress(Exception):
            old.dispose()
    source = path_under(ROOT, request["source"]) if request.get("source") else None
    step = request.get("step", {})
    factory = (
        "private:factory/scalc" if step.get("kind") == "workbook" else "private:factory/swriter"
    )
    load = path if mode == "inspect" else source
    document = engine.loadComponentFromURL(
        load.as_uri() if load else factory,
        "_blank",
        0,
        props(
            Hidden=False,
            ReadOnly=mode == "inspect",
            MacroExecutionMode=uno.getConstantByName(
                "com.sun.star.document.MacroExecMode.NEVER_EXECUTE"
            ),
            UpdateDocMode=uno.getConstantByName("com.sun.star.document.UpdateDocMode.NO_UPDATE"),
        ),
    )
    if document is None:
        raise ValueError("APPLICATION_OPEN_FAILED")

    def cancelled():
        if request.get("cancel") and path_under(ROOT, request["cancel"]).exists():
            raise ValueError("APPLICATION_CANCELLED")

    cancelled()
    if mode == "edit":
        if step["kind"] == "workbook":
            edit_workbook(document, step, cancelled, creating=source is None)
        elif step["kind"] == "document":
            edit_document(document, step, cancelled)
        mark(document, request["operation_id"])
        cancelled()
        if step["kind"] == "pdf":
            document.storeToURL(
                path.as_uri(), props(FilterName="writer_pdf_Export", Overwrite=False)
            )
        else:
            document.storeAsURL(
                path.as_uri(),
                props(
                    FilterName="Calc MS Excel 2007 XML"
                    if step["kind"] == "workbook"
                    else "writer8",
                    Overwrite=False,
                ),
            )
    result = snapshot(document)
    if (
        mode == "edit"
        and step["kind"] == "workbook"
        and any(c["error"] for sheet in result["sheets"] for c in sheet["cells"])
    ):
        raise ValueError("APPLICATION_FORMULA_ERROR")
    document.CurrentController.Frame.ContainerWindow.toFront()
    time.sleep(0.15)
    if request.get("screenshot"):
        capture(path_under(ROOT, request["screenshot"]))
    result["office_pid"] = json.loads(Path("/tmp/desk-applications.json").read_text())["office_pid"]
    return result


def browser_read(source_id):
    path = path_under(INPUTS, source_id)
    if path.suffix.lower() != ".html" or not path.is_file():
        raise ValueError("SOURCE_NOT_HTML")
    expected_url = "http://127.0.0.1:8765/" + quote(source_id, safe="/")
    port = int(Path("/home/desk/browser-profile/DevToolsActivePort").read_text().splitlines()[0])
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
        targets = json.load(response)
    target = next(p for p in targets if p.get("type") == "page")
    from websockets.sync.client import connect

    with connect(target["webSocketDebuggerUrl"], open_timeout=3, max_size=1000000) as socket:
        serial = 0

        def command(method, params):
            nonlocal serial
            serial += 1
            socket.send(json.dumps({"id": serial, "method": method, "params": params}))
            while True:
                message = json.loads(socket.recv(timeout=5))
                if message.get("id") == serial:
                    if "error" in message:
                        raise ValueError("BROWSER_COMMAND_FAILED")
                    return message.get("result", {})

        command("Page.navigate", {"url": expected_url})
        result = None
        until = time.monotonic() + 5
        while time.monotonic() < until:
            value = command(
                "Runtime.evaluate",
                {
                    "expression": "JSON.stringify({url:location.href,title:document.title,ready:document.readyState,text:document.body?document.body.innerText:'',tables:Array.from(document.querySelectorAll('table')).map(t=>Array.from(t.rows).map(r=>Array.from(r.cells).map(c=>c.innerText))),links:Array.from(document.querySelectorAll('a[href]')).map(a=>({text:a.innerText,href:a.getAttribute('href')}))})",
                    "returnByValue": True,
                },
            )
            text = value.get("result", {}).get("value")
            if isinstance(text, str):
                result = json.loads(text)
                if result["url"] == expected_url and result["ready"] == "complete":
                    break
            time.sleep(0.05)
        if not result or result["url"] != expected_url or result["ready"] != "complete":
            raise ValueError("SOURCE_NOT_READY")
        return {
            **result,
            "browser_pid": json.loads(Path("/tmp/desk-applications.json").read_text())[
                "browser_pid"
            ],
        }


def main():
    body = sys.stdin.buffer.read(120001)
    if len(body) > 120000:
        raise ValueError("APPLICATION_REQUEST_LIMIT")
    request = json.loads(body)
    with open("/tmp/desk-bridge.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if request["mode"] == "browser":
            result = browser_read(request["source_id"])
        elif request["mode"] in {"edit", "inspect"}:
            result = office(request)
        elif request["mode"] == "pdf_inspect":
            path = path_under(ROOT, request["path"])
            info = subprocess.run(
                ["pdfinfo", str(path)], check=True, capture_output=True, text=True
            ).stdout
            text = subprocess.run(
                ["pdftotext", "-raw", str(path), "-"], check=True, capture_output=True, text=True
            ).stdout
            result = {"info": info, "text": text, "application": "libreoffice_writer"}
        elif request["mode"] == "status":
            result = {
                "ready": True,
                **json.loads(Path("/tmp/desk-applications.json").read_text()),
                "uno_connected": desktop() is not None,
            }
        else:
            raise ValueError("APPLICATION_COMMAND_DENIED")
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            json.dumps(
                {
                    "error": str(error)[:200],
                    "error_type": type(error).__name__,
                    "where": [
                        {"function": frame.name, "line": frame.lineno}
                        for frame in traceback.extract_tb(error.__traceback__)[-5:]
                    ],
                }
            ),
            flush=True,
        )
        sys.exit(1)
