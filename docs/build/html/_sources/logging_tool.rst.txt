Logging Tool
************

*LaME* includes a logger that records program actions, warnings, and errors.  Logger messages help you understand what’s happening behind the scenes, especially if something goes wrong.  This page discusses how you can view and customize the behavior and even use the logger to record a workflow for use in the Workflow Design Tool.

What Is Logging?
----------------

Logging is how the application communicates its internal activity. It helps track:

- Successful operations
- Warnings or unusual behavior
- Errors or crashes

This is useful if you're troubleshooting, reporting a bug, or just want to see what the program is doing.

Where to View Logs
------------------

Logs are typically displayed in a dedicated logger window or dock within the app. In some cases, they may be saved to a log file as well.

You can access the log panel from:

- The **menu bar** (e.g., *View → Show Logs*)
- A **dockable panel** at the bottom or side of the app
.. - A **popup window** triggered automatically when an error occurs

Understanding Log Messages
--------------------------

Each log message may include:

- **Tag** – Which part of the app generated the message (e.g., `UI`, `IMPORT`, `PROCESSING`).
- **Message** – Description of what happened.
- **Arguments** - inputs sent to a function, useful for debugging and workflow design.
- **Call chain** - the train of functions to track the order of internal commands.

Messages may appear in different **colors** or **icons** depending on their severity:

.. list-table::
   :header-rows: 1

   * - Level
     - Meaning
     - Color/Icon
   * - Info
     - Normal operation
     - Gray or white
   * - Warning
     - Something unusual, but not critical
     - Yellow triangle
   * - Error
     - Something went wrong and may affect results
     - Red exclamation mark
   * - Debug (if enabled)
     - Internal diagnostics for developers
     - Light blue or gray

Controlling What Is Logged
--------------------------

You may be able to filter what messages appear by:

- **Category/Tag** (e.g., only show `IMPORT` messages)
- **Severity** (e.g., hide `Info`, only show `Errors`)
- **Search** (type keywords to find relevant messages)

To do this:

1. Open the **log viewer** panel
2. Click the settings (gear) icon
3. Use the **checkboxes** to toggle categories and options
4. Use the **search box** to locate specific messages

Saving or Exporting Logs
------------------------

If you need to share logs with support or developers:

- Click **Export Logs**
- Choose a file name and location
- The app will save a `.txt` or `.log` file with all recent messages

This file helps developers understand and fix issues you report.

Common Scenarios
----------------

- **Import errors**: If a file cannot be loaded, check the logs for details like “File not found” or “Invalid format.”
- **Unexpected behavior**: If something doesn't work as expected, check for warnings or errors logged at the time.
- **Debugging**: If you're working closely with developers or testing new features, enabling debug messages may help.

Tips
----

- Keep the log viewer open while importing data or processing maps — you’ll get helpful progress updates.
- If something fails silently, check the log panel before trying again.
- When reporting bugs, send a screenshot or export of the logs to help developers understand the issue.