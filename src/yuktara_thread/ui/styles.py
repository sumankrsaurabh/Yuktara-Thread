"""Minimal, platform-native styling for the desktop shell."""

APP_STYLE = """
QWidget { font-family: 'Source Sans 3', 'Segoe UI', sans-serif; font-size: 14px; color: #202124; }
QMainWindow, QWidget#root { background: #f7f7f5; }
QFrame#sidebar { background: #f0f0ed; border-right: 1px solid #deded9; }
QLabel#brand { font-size: 18px; font-weight: 650; padding: 8px 4px 16px 4px; }
QLabel#muted { color: #6b6f73; }
QLabel#pageTitle { font-size: 24px; font-weight: 650; }
QPushButton { background: #ffffff; border: 1px solid #d7d9dc; border-radius: 7px; padding: 7px 12px; }
QPushButton:hover { background: #f2f4f6; }
QPushButton:pressed { background: #e8eaed; }
QPushButton#primary { background: #24272b; color: white; border-color: #24272b; }
QPushButton#primary:hover { background: #3b4046; }
QListWidget, QPlainTextEdit, QLineEdit { background: #ffffff; border: 1px solid #d7d9dc; border-radius: 7px; padding: 6px; }
QListWidget::item { padding: 8px; border-radius: 5px; }
QListWidget::item:selected { background: #e2e6eb; color: #17191c; }
QTabWidget::pane { border: 1px solid #deded9; border-radius: 8px; background: #ffffff; top: -1px; }
QTabBar::tab { padding: 9px 14px; color: #5e6267; }
QTabBar::tab:selected { color: #202124; border-bottom: 2px solid #343a40; }
QMessageBox, QDialog { background: #f7f7f5; }
"""
