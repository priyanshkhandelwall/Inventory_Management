import sys
import sqlite3
import hashlib
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import json
import os

# Database Manager
class DatabaseManager:
    def __init__(self, db_name="inventory.db"):
        self.db_name = db_name
        self.init_database()
     
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
         
        # Users table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
         
        # Categories table
        cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT)''')
         
        # Items table
        cursor.execute('''CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER, quantity INTEGER,
            price REAL, min_stock INTEGER, supplier TEXT, date_added TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id))''')
         
        # Add default admin user
        cursor.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', ?, 'admin')", 
                      (hashlib.sha256('admin'.encode()).hexdigest(),))
         
        conn.commit()
        conn.close()

    def execute_query(self, query, params=(), fetch=False):
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall() if fetch else None
            conn.commit()
            return result
        except Exception as e:
            print(f"Database error: {e}")
            return None
        finally:
            if conn:
                conn.close()

# Modern Styled Widget Base
class StyledWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget { background-color: #f5f5f5; font-family: 'Segoe UI'; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { 
                padding: 8px; border: 2px solid #ddd; border-radius: 5px; 
                background-color: white; font-size: 14px; }
            QLineEdit:focus, QComboBox:focus { border-color: #4CAF50; }
            QPushButton { 
                padding: 10px 20px; background-color: #4CAF50; color: white; 
                border: none; border-radius: 5px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:pressed { background-color: #3d8b40; }
            QTableWidget { 
                gridline-color: #ddd; background-color: white; 
                alternate-background-color: #f9f9f9; }
            QTableWidget::item { padding: 8px; }
            QTableWidget::item:selected { background-color: #4CAF50; color: white; }
            QHeaderView::section { 
                background-color: #2196F3; color: white; padding: 10px; 
                font-weight: bold; border: none; }
            QTabWidget::pane { border: 1px solid #ddd; background-color: white; }
            QTabBar::tab { 
                background-color: #e0e0e0; padding: 10px 20px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #4CAF50; color: white; }
            QGroupBox { 
                font-weight: bold; border: 2px solid #ddd; border-radius: 5px; 
                margin: 10px; padding-top: 10px; }
        """)

# Login Dialog
class LoginDialog(QDialog, StyledWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.user_role = None
        self.setup_ui()
     
    def setup_ui(self):
        self.setWindowTitle("Inventory Management - Login")
        self.setFixedSize(400, 300)
         
        layout = QVBoxLayout()
         
        title = QLabel("INVENTORY MANAGER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3; margin: 20px;")
         
        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)
         
        btn_layout = QHBoxLayout()
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.login)
        btn_layout.addWidget(login_btn)
         
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
     
    def login(self):
        username = self.username.text()
        password = hashlib.sha256(self.password.text().encode()).hexdigest()
         
        result = self.db_manager.execute_query(
            "SELECT role FROM users WHERE username=? AND password=?", 
            (username, password), fetch=True)
         
        if result:
            self.user_role = result[0][0]
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials!")

# Chart Widget
class ChartWidget(FigureCanvas):
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 6), facecolor='white')
        super().__init__(self.figure)
        self.setParent(parent)
         
    def plot_stock_levels(self, data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
         
        if data:
            items, quantities = zip(*data)
            colors = ['red' if q < 10 else 'orange' if q < 20 else 'green' for q in quantities]
            ax.bar(range(len(items)), quantities, color=colors)
            ax.set_xticks(range(len(items)))
            ax.set_xticklabels(items, rotation=45, ha='right')
            ax.set_ylabel('Quantity')
            ax.set_title('Stock Levels')
         
        self.figure.tight_layout()
        self.draw()

# Main Application
class InventoryApp(QMainWindow, StyledWidget):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.current_user_role = None
        self.setup_ui()
         
    def setup_ui(self):
        self.setWindowTitle("Advanced Inventory Management System")
        self.setGeometry(100, 100, 1200, 800)
         
        # Login first
        login_dialog = LoginDialog(self.db_manager)
        if login_dialog.exec_() == QDialog.Accepted:
            self.current_user_role = login_dialog.user_role
        else:
            sys.exit()
         
        # Central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
         
        # Dashboard tab
        self.dashboard_widget = self.create_dashboard()
        self.tabs.addTab(self.dashboard_widget, "Dashboard")
         
        # Items management tab
        self.items_widget = self.create_items_tab()
        self.tabs.addTab(self.items_widget, "Items")
         
        # Categories tab
        self.categories_widget = self.create_categories_tab()
        self.tabs.addTab(self.categories_widget, "Categories")
         
        # Reports tab
        self.reports_widget = self.create_reports_tab()
        self.tabs.addTab(self.reports_widget, "Reports")
         
        self.create_toolbar()
        self.statusBar().showMessage("Ready")
        self.load_categories()
        self.load_items()
        self.refresh_dashboard()

    def create_toolbar(self):
        toolbar = self.addToolBar("Main")
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_all_data)
        toolbar.addAction(refresh_action)
        toolbar.addSeparator()
        export_excel_action = QAction("Export Excel", self)
        export_excel_action.triggered.connect(self.export_to_excel)
        toolbar.addAction(export_excel_action)
        export_pdf_action = QAction("Export PDF", self)
        export_pdf_action.triggered.connect(self.export_to_pdf)
        toolbar.addAction(export_pdf_action)
        toolbar.addSeparator()
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.logout)
        toolbar.addAction(logout_action)

    def create_dashboard(self):
        widget = QWidget()
        layout = QVBoxLayout()
        self.stats_layout = QHBoxLayout()
        layout.addLayout(self.stats_layout)
        self.chart_widget = ChartWidget()
        layout.addWidget(self.chart_widget)
        widget.setLayout(layout)
        return widget

    def refresh_dashboard(self):
        for i in reversed(range(self.stats_layout.count())): 
            self.stats_layout.itemAt(i).widget().setParent(None)
            
        total_items = len(self.db_manager.execute_query("SELECT * FROM items", fetch=True) or [])
        self.stats_layout.addWidget(self.create_stat_card("Total Items", str(total_items), "#2196F3"))
        
        low_stock = len(self.db_manager.execute_query("SELECT * FROM items WHERE quantity <= min_stock", fetch=True) or [])
        self.stats_layout.addWidget(self.create_stat_card("Low Stock", str(low_stock), "#f44336"))
        
        total_categories = len(self.db_manager.execute_query("SELECT * FROM categories", fetch=True) or [])
        self.stats_layout.addWidget(self.create_stat_card("Categories", str(total_categories), "#4CAF50"))
        
        items_data = self.db_manager.execute_query("SELECT name, quantity FROM items ORDER BY quantity DESC LIMIT 10", fetch=True)
        if items_data:
            self.chart_widget.plot_stock_levels(items_data)

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"background-color: {color}; border-radius: 10px; color: white; min-height: 100px;")
        layout = QVBoxLayout()
        t_label = QLabel(title)
        t_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        v_label = QLabel(value)
        v_label.setStyleSheet("font-size: 32px; font-weight: bold;")
        layout.addWidget(t_label)
        layout.addWidget(v_label)
        card.setLayout(layout)
        return card

    def create_items_tab(self):
        widget = QWidget()
        layout = QHBoxLayout()
        
        # Form
        form_group = QGroupBox("Item Details")
        form_layout = QFormLayout()
        self.item_name = QLineEdit()
        self.item_category = QComboBox()
        self.item_quantity = QSpinBox()
        self.item_quantity.setRange(0, 10000)
        self.item_price = QDoubleSpinBox()
        self.item_price.setRange(0, 1000000)
        self.item_min_stock = QSpinBox()
        self.item_min_stock.setRange(0, 1000)
        self.item_supplier = QLineEdit()
        
        form_layout.addRow("Name:", self.item_name)
        form_layout.addRow("Category:", self.item_category)
        form_layout.addRow("Quantity:", self.item_quantity)
        form_layout.addRow("Price:", self.item_price)
        form_layout.addRow("Min Stock:", self.item_min_stock)
        form_layout.addRow("Supplier:", self.item_supplier)
        
        btn_layout = QVBoxLayout()
        add_btn = QPushButton("Add Item")
        add_btn.clicked.connect(self.add_item)
        update_btn = QPushButton("Update Item")
        update_btn.clicked.connect(self.update_item)
        delete_btn = QPushButton("Delete Item")
        delete_btn.clicked.connect(self.delete_item)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(delete_btn)
        form_layout.addRow(btn_layout)
        form_group.setLayout(form_layout)
        
        # Table
        table_layout = QVBoxLayout()
        self.items_table = QTableWidget(0, 7)
        self.items_table.setHorizontalHeaderLabels(["ID", "Name", "Category", "Qty", "Price", "Min Stock", "Supplier"])
        self.items_table.itemClicked.connect(self.load_item_to_form)
        table_layout.addWidget(self.items_table)
        
        layout.addWidget(form_group, 1)
        layout.addLayout(table_layout, 2)
        widget.setLayout(layout)
        return widget

    def create_categories_tab(self):
        widget = QWidget()
        layout = QHBoxLayout()
        form_group = QGroupBox("Category Details")
        form_layout = QFormLayout()
        self.category_name = QLineEdit()
        self.category_description = QTextEdit()
        form_layout.addRow("Name:", self.category_name)
        form_layout.addRow("Description:", self.category_description)
        add_btn = QPushButton("Add Category")
        add_btn.clicked.connect(self.add_category)
        form_layout.addRow(add_btn)
        form_group.setLayout(form_layout)
        
        self.categories_list = QListWidget()
        self.categories_list.itemClicked.connect(self.load_category_details)
        
        layout.addWidget(form_group, 1)
        layout.addWidget(self.categories_list, 1)
        widget.setLayout(layout)
        return widget

    def create_reports_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        low_stock_btn = QPushButton("Low Stock Report")
        low_stock_btn.clicked.connect(self.generate_low_stock_report)
        inv_btn = QPushButton("Full Inventory Report")
        inv_btn.clicked.connect(self.generate_inventory_report)
        btn_layout.addWidget(low_stock_btn)
        btn_layout.addWidget(inv_btn)
        layout.addLayout(btn_layout)
        self.report_display = QTextEdit()
        self.report_display.setReadOnly(True)
        layout.addWidget(self.report_display)
        widget.setLayout(layout)
        return widget

    def load_categories(self):
        self.item_category.clear()
        self.categories_list.clear()
        categories = self.db_manager.execute_query("SELECT id, name FROM categories", fetch=True)
        if categories:
            for cat_id, name in categories:
                self.item_category.addItem(name, cat_id)
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, cat_id)
                self.categories_list.addItem(item)

    def load_items(self):
        self.items_table.setRowCount(0)
        items = self.db_manager.execute_query("""
            SELECT i.id, i.name, c.name, i.quantity, i.price, i.min_stock, i.supplier 
            FROM items i LEFT JOIN categories c ON i.category_id = c.id
        """, fetch=True)
        if items:
            for row_data in items:
                row = self.items_table.rowCount()
                self.items_table.insertRow(row)
                for col, data in enumerate(row_data):
                    self.items_table.setItem(row, col, QTableWidgetItem(str(data)))

    def load_item_to_form(self, item):
        row = item.row()
        self.item_name.setText(self.items_table.item(row, 1).text())
        cat_name = self.items_table.item(row, 2).text()
        index = self.item_category.findText(cat_name)
        if index >= 0: self.item_category.setCurrentIndex(index)
        self.item_quantity.setValue(int(self.items_table.item(row, 3).text()))
        self.item_price.setValue(float(self.items_table.item(row, 4).text()))
        self.item_min_stock.setValue(int(self.items_table.item(row, 5).text()))
        self.item_supplier.setText(self.items_table.item(row, 6).text())

    def add_item(self):
        self.db_manager.execute_query("""
            INSERT INTO items (name, category_id, quantity, price, min_stock, supplier, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (self.item_name.text(), self.item_category.currentData(), self.item_quantity.value(),
              self.item_price.value(), self.item_min_stock.value(), self.item_supplier.text(),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.refresh_all_data()

    def update_item(self):
        row = self.items_table.currentRow()
        if row >= 0:
            item_id = self.items_table.item(row, 0).text()
            self.db_manager.execute_query("""
                UPDATE items SET name=?, category_id=?, quantity=?, price=?, min_stock=?, supplier=?
                WHERE id=?
            """, (self.item_name.text(), self.item_category.currentData(), self.item_quantity.value(),
                  self.item_price.value(), self.item_min_stock.value(), self.item_supplier.text(), item_id))
            self.refresh_all_data()

    def delete_item(self):
        row = self.items_table.currentRow()
        if row >= 0:
            item_id = self.items_table.item(row, 0).text()
            self.db_manager.execute_query("DELETE FROM items WHERE id=?", (item_id,))
            self.refresh_all_data()

    def add_category(self):
        self.db_manager.execute_query("INSERT INTO categories (name, description) VALUES (?, ?)",
                                    (self.category_name.text(), self.category_description.toPlainText()))
        self.refresh_all_data()

    def load_category_details(self, item):
        cat_id = item.data(Qt.UserRole)
        res = self.db_manager.execute_query("SELECT name, description FROM categories WHERE id=?", (cat_id,), fetch=True)
        if res:
            self.category_name.setText(res[0][0])
            self.category_description.setPlainText(res[0][1])

    def generate_low_stock_report(self):
        items = self.db_manager.execute_query("SELECT name, quantity, min_stock FROM items WHERE quantity <= min_stock", fetch=True)
        report = "LOW STOCK REPORT\n" + "="*30 + "\n"
        for n, q, m in items: report += f"{n}: {q} (Min: {m})\n"
        self.report_display.setText(report)

    def generate_inventory_report(self):
        items = self.db_manager.execute_query("SELECT name, quantity, price FROM items", fetch=True)
        report = "INVENTORY REPORT\n" + "="*30 + "\n"
        total = 0
        for n, q, p in items:
            val = q * p
            total += val
            report += f"{n}: {q} @ ${p} = ${val}\n"
        report += f"\nTotal Value: ${total}"
        self.report_display.setText(report)

    def refresh_all_data(self):
        self.load_categories()
        self.load_items()
        self.refresh_dashboard()

    def export_to_excel(self):
        items = self.db_manager.execute_query("SELECT * FROM items", fetch=True)
        if items:
            df = pd.DataFrame(items)
            df.to_excel("inventory_export.xlsx")
            QMessageBox.information(self, "Success", "Exported to inventory_export.xlsx")

    def export_to_pdf(self):
        c = canvas.Canvas("inventory_report.pdf", pagesize=letter)
        c.drawString(100, 750, "Inventory Report")
        c.save()
        QMessageBox.information(self, "Success", "Exported to inventory_report.pdf")

    def logout(self):
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InventoryApp()
    window.show()
    sys.exit(app.exec_())
