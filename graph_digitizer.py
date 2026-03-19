#!/usr/bin/env python3
"""
Graph Digitizer Tool
A Python application for digitizing data points from graph images.

Features:
- Load PNG images of graphs
- Calibrate axes by clicking on known points
- Digitize data points by clicking on the graph
- Export data as CSV
- Save/load digitization sessions
- Zoom and pan functionality
"""

import sys
import os
import json
import csv
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
        QWidget, QPushButton, QLabel, QFileDialog, QMessageBox,
        QSpinBox, QDoubleSpinBox, QLineEdit, QGroupBox, QGridLayout,
        QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
        QMenuBar, QMenu, QStatusBar, QProgressBar, QCheckBox,
        QComboBox, QTextEdit, QScrollArea, QFrame, QInputDialog
    )
    from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QTimer
    from PyQt6.QtGui import (
        QPixmap, QPainter, QPen, QBrush, QColor, QFont, QPalette,
        QAction, QIcon, QMouseEvent, QWheelEvent, QKeyEvent
    )
    from PyQt6.QtCore import QSize
except ImportError:
    print("PyQt6 not found. Installing...")
    os.system("pip install PyQt6")
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *

try:
    from PIL import Image
except ImportError:
    print("Pillow not found. Installing...")
    os.system("pip install Pillow")
    from PIL import Image

# Version tracking for the application
# __version__ = "2025.1"  # new program, program settings persist, image scaling works
# __version__ = "2025.2"  # fixed image scaling issue, added more buttons
__version__ = "2026.1"  # added dark fusion theme


class GraphDigitizer(QMainWindow):
    """Main application window for graph digitization."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Graph Digitizer Tool v.%s" % __version__ + " by pjohnson@ccom.unh.edu - UNH/CCOM-JHC ")
        self.setGeometry(100, 100, 1400, 900)
        
        # Open in full screen by default
        self.showMaximized()
        
        # Data storage
        self.image_path = None
        self.original_pixmap = None
        self.current_pixmap = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Session persistence
        self.settings_file = "graph_digitizer_settings.json"
        self.last_image_dir = ""
        self.last_session_dir = ""
        self.last_export_dir = ""
        
        # Calibration data
        self.calibration_points = []  # [(pixel_x, pixel_y, real_x, real_y), ...]
        self.calibrated = False
        self.x_axis_range = (0, 1)
        self.y_axis_range = (0, 1)
        
        # Digitized points
        self.digitized_points = []  # [(pixel_x, pixel_y, real_x, real_y), ...]
        
        # UI setup
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Load settings
        self.load_settings()
        
        # Mouse tracking
        self.last_mouse_pos = None
        self.dragging = False
        
    def setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Controls
        left_panel = self.create_control_panel()
        left_panel.setMaximumWidth(500)  # Prevent left panel from expanding
        splitter.addWidget(left_panel)
        
        # Right panel - Image display
        right_panel = self.create_image_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 1000])
        
    def create_control_panel(self):
        """Create the left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout(file_group)
        
        self.load_btn = QPushButton("Load Image")
        self.load_btn.clicked.connect(self.load_image)
        file_layout.addWidget(self.load_btn)
        
        self.save_session_btn = QPushButton("Save Session")
        self.save_session_btn.clicked.connect(self.save_session)
        file_layout.addWidget(self.save_session_btn)
        
        self.load_session_btn = QPushButton("Load Session")
        self.load_session_btn.clicked.connect(self.load_session)
        file_layout.addWidget(self.load_session_btn)
        
        layout.addWidget(file_group)
        
        # Calibration
        calib_group = QGroupBox("Axis Calibration")
        calib_layout = QGridLayout(calib_group)
        
        calib_layout.addWidget(QLabel("X-axis range:"), 0, 0)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-999999, 999999)
        self.x_min_spin.setValue(0)
        self.x_min_spin.valueChanged.connect(self.axis_range_changed)
        calib_layout.addWidget(self.x_min_spin, 0, 1)
        
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-999999, 999999)
        self.x_max_spin.setValue(1)
        self.x_max_spin.valueChanged.connect(self.axis_range_changed)
        calib_layout.addWidget(self.x_max_spin, 0, 2)
        
        calib_layout.addWidget(QLabel("Y-axis range:"), 1, 0)
        self.y_min_spin = QDoubleSpinBox()
        self.y_min_spin.setRange(-999999, 999999)
        self.y_min_spin.setValue(0)
        self.y_min_spin.valueChanged.connect(self.axis_range_changed)
        calib_layout.addWidget(self.y_min_spin, 1, 1)
        
        self.y_max_spin = QDoubleSpinBox()
        self.y_max_spin.setRange(-999999, 999999)
        self.y_max_spin.setValue(1)
        self.y_max_spin.valueChanged.connect(self.axis_range_changed)
        calib_layout.addWidget(self.y_max_spin, 1, 2)
        
        self.calibrate_btn = QPushButton("Start Calibration")
        self.calibrate_btn.clicked.connect(self.start_calibration)
        calib_layout.addWidget(self.calibrate_btn, 2, 0, 1, 3)
        
        layout.addWidget(calib_group)
        
        # Digitization
        digit_group = QGroupBox("Data Digitization")
        digit_layout = QVBoxLayout(digit_group)
        
        self.digitize_btn = QPushButton("Start Digitizing")
        self.digitize_btn.clicked.connect(self.start_digitizing)
        self.digitize_btn.setEnabled(False)
        digit_layout.addWidget(self.digitize_btn)
        
        self.clear_points_btn = QPushButton("Clear All Points")
        self.clear_points_btn.clicked.connect(self.clear_points)
        digit_layout.addWidget(self.clear_points_btn)
        
        self.undo_btn = QPushButton("Undo Last Point")
        self.undo_btn.clicked.connect(self.undo_last_point)
        digit_layout.addWidget(self.undo_btn)
        
        layout.addWidget(digit_group)
        
        # Export
        export_group = QGroupBox("Export Data")
        export_layout = QVBoxLayout(export_group)
        
        self.export_csv_btn = QPushButton("Export to CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        export_layout.addWidget(self.export_csv_btn)
        
        self.export_txt_btn = QPushButton("Export to TXT")
        self.export_txt_btn.clicked.connect(self.export_txt)
        export_layout.addWidget(self.export_txt_btn)
        
        # Swath Multiplier input
        swath_mult_layout = QHBoxLayout()
        swath_mult_layout.addWidget(QLabel("Swath Multiplier:"))
        self.swath_multiplier_spin = QDoubleSpinBox()
        self.swath_multiplier_spin.setRange(0.01, 1000.0)
        self.swath_multiplier_spin.setValue(1.0)
        self.swath_multiplier_spin.setDecimals(3)
        swath_mult_layout.addWidget(self.swath_multiplier_spin)
        export_layout.addLayout(swath_mult_layout)
        
        self.export_swath_btn = QPushButton("Export to Swath Coverage Curve")
        self.export_swath_btn.clicked.connect(self.export_swath_coverage_curve)
        export_layout.addWidget(self.export_swath_btn)
        
        self.export_all_btn = QPushButton("Export All")
        self.export_all_btn.clicked.connect(self.export_all_formats)
        export_layout.addWidget(self.export_all_btn)
        
        layout.addWidget(export_group)
        
        # Data table
        data_group = QGroupBox("Digitized Points")
        data_layout = QVBoxLayout(data_group)
        
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(["X (Real)", "Y (Real)", "X (Pixel)", "Y (Pixel)"])
        self.points_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Keep table edits in sync with the exported data.
        self.points_table.itemChanged.connect(self.points_table_item_changed)
        data_layout.addWidget(self.points_table)
        
        layout.addWidget(data_group)
        
        # Navigation
        nav_group = QGroupBox("Navigation")
        nav_layout = QVBoxLayout(nav_group)
        
        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        nav_layout.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = QPushButton("Zoom Out")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        nav_layout.addWidget(self.zoom_out_btn)
        
        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.clicked.connect(self.reset_view)
        nav_layout.addWidget(self.reset_view_btn)
        
        layout.addWidget(nav_group)
        
        # Instructions text area
        instructions_text = QTextEdit()
        instructions_text.setPlainText("Zoom with the mouse wheel and pan with the middle button")
        instructions_text.setMaximumHeight(60)
        instructions_text.setReadOnly(True)
        layout.addWidget(instructions_text)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        return panel
        
    def create_image_panel(self):
        """Create the right panel for image display."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        # Keep this consistent with the global dark theme.
        self.image_label.setStyleSheet(
            "border: 1px solid #5a5a5a; background-color: #2b2b2b; color: #dcdcdc;"
        )
        self.image_label.setText("Load an image to begin digitization")
        
        # Enable mouse tracking
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.image_mouse_press
        self.image_label.mouseMoveEvent = self.image_mouse_move
        self.image_label.mouseReleaseEvent = self.image_mouse_release
        self.image_label.wheelEvent = self.image_wheel_event
        
        layout.addWidget(self.image_label)
        
        return panel
        
    def setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        load_action = QAction('Load Image', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.load_image)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        save_session_action = QAction('Save Session', self)
        save_session_action.setShortcut('Ctrl+S')
        save_session_action.triggered.connect(self.save_session)
        file_menu.addAction(save_session_action)
        
        load_session_action = QAction('Load Session', self)
        load_session_action.setShortcut('Ctrl+L')
        load_session_action.triggered.connect(self.load_session)
        file_menu.addAction(load_session_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        
        undo_action = QAction('Undo Last Point', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo_last_point)
        edit_menu.addAction(undo_action)
        
        clear_action = QAction('Clear All Points', self)
        clear_action.setShortcut('Ctrl+Shift+C')
        clear_action.triggered.connect(self.clear_points)
        edit_menu.addAction(clear_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.setShortcut('Ctrl+=')
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.setShortcut('Ctrl+-')
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_view_action = QAction('Reset View', self)
        reset_view_action.setShortcut('Ctrl+0')
        reset_view_action.triggered.connect(self.reset_view)
        view_menu.addAction(reset_view_action)
        
        view_menu.addSeparator()
        
        fullscreen_action = QAction('Toggle Fullscreen', self)
        fullscreen_action.setShortcut('F11')
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # Export menu
        export_menu = menubar.addMenu('Export')
        
        export_csv_action = QAction('Export to CSV', self)
        export_csv_action.setShortcut('Ctrl+E')
        export_csv_action.triggered.connect(self.export_csv)
        export_menu.addAction(export_csv_action)
        
        export_txt_action = QAction('Export to TXT', self)
        export_txt_action.triggered.connect(self.export_txt)
        export_menu.addAction(export_txt_action)
        
    def setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def load_image(self):
        """Load an image file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", self.last_image_dir, 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.gif)"
        )
        
        if file_path:
            try:
                # Save the directory for next time
                self.last_image_dir = os.path.dirname(file_path)
                self.save_settings()
                
                # Load image
                self.image_path = file_path
                self.original_pixmap = QPixmap(file_path)
                self.current_pixmap = self.original_pixmap
                
                # Reset view
                self.scale_factor = 1.0
                self.offset_x = 0
                self.offset_y = 0
                
                # Clear previous data
                self.calibration_points = []
                self.digitized_points = []
                self.calibrated = False
                
                # Update UI
                self.update_image_display()
                self.update_points_table()
                self.update_buttons()
                
                self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
                
    def update_image_display(self):
        """Update the image display with current zoom and pan."""
        if self.current_pixmap is None:
            return
            
        # Scale the pixmap
        scaled_pixmap = self.current_pixmap.scaled(
            self.current_pixmap.size() * self.scale_factor,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Create a new pixmap for display with overlays
        display_pixmap = QPixmap(scaled_pixmap.size())
        display_pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(display_pixmap)
        painter.drawPixmap(0, 0, scaled_pixmap)
        
        # Draw calibration points
        if self.calibration_points:
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            for point in self.calibration_points:
                # Convert image coordinates to display coordinates
                x = point[0] * self.scale_factor
                y = point[1] * self.scale_factor
                painter.drawEllipse(int(x - 5), int(y - 5), 10, 10)
                painter.drawText(int(x + 10), int(y - 10), f"({point[2]:.2f}, {point[3]:.2f})")
        
        # Draw digitized points
        if self.digitized_points:
            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.setBrush(QBrush(QColor(0, 255, 0)))
            for i, point in enumerate(self.digitized_points):
                # Convert image coordinates to display coordinates (same as calibration points)
                # point structure: (screen_x, screen_y, img_x, img_y, real_x, real_y)
                x = point[2] * self.scale_factor  # img_x * current_scale
                y = point[3] * self.scale_factor  # img_y * current_scale
                painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)
                painter.drawText(int(x + 8), int(y - 8), f"{i+1}")
        
        painter.end()
        
        # Apply offset to the entire display
        if self.offset_x != 0 or self.offset_y != 0:
            offset_pixmap = QPixmap(display_pixmap.size())
            offset_pixmap.fill(Qt.GlobalColor.white)
            offset_painter = QPainter(offset_pixmap)
            offset_painter.drawPixmap(self.offset_x, self.offset_y, display_pixmap)
            offset_painter.end()
            display_pixmap = offset_pixmap
        
        self.image_label.setPixmap(display_pixmap)
        
    def image_mouse_press(self, event: QMouseEvent):
        """Handle mouse press on image."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Handle calibration or digitization
            if hasattr(self, 'calibration_mode') and self.calibration_mode:
                self.add_calibration_point(event.pos())
                return
            elif hasattr(self, 'digitizing_mode') and self.digitizing_mode:
                self.add_digitized_point(event.pos())
                return
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Middle button for panning
            self.last_mouse_pos = event.pos()
            self.dragging = True
        elif event.button() == Qt.MouseButton.RightButton:
            # Right-click to stop digitizing
            if hasattr(self, 'digitizing_mode') and self.digitizing_mode:
                self.digitizing_mode = False
                # Return to normal cursor
                self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
                self.digitize_btn.setText("Start Digitizing")
                self.status_bar.showMessage("Digitizing stopped. Click 'Start Digitizing' to continue.")
                
    def image_mouse_move(self, event: QMouseEvent):
        """Handle mouse move on image."""
        if self.dragging and self.last_mouse_pos:
            # Pan the image
            delta = event.pos() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update_image_display()
            
    def image_mouse_release(self, event: QMouseEvent):
        """Handle mouse release on image."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.dragging = False
            
    def image_wheel_event(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()
            
    def start_calibration(self):
        """Start/stop calibration process (single button control)."""
        if self.original_pixmap is None:
            QMessageBox.warning(self, "Warning", "Please load an image first.")
            return

        # If already calibrating, clicking the button stops calibration.
        if hasattr(self, "calibration_mode") and self.calibration_mode:
            point_count = len(self.calibration_points)

            self.calibration_mode = False
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)

            # If only one point was selected, revert to "Start Calibration".
            if point_count < 2:
                self.calibrated = False
                self.calibration_points = []
                self.calibrate_btn.setText("Start Calibration")
                self.status_bar.showMessage("Calibration stopped after selecting one point. Start Calibration to try again.")
            else:
                self.calibrated = True
                self.calibrate_btn.setText("Re-Do Calibration")
                self.status_bar.showMessage("Calibration complete. Ready to digitize.")

            self.update_buttons()
            return

        # Not calibrating: start fresh calibration.
        self.calibration_mode = True
        self.calibration_points = []
        self.calibrated = False

        # Set crosshair cursor for precise calibration
        self.image_label.setCursor(Qt.CursorShape.CrossCursor)
        self.calibrate_btn.setText("Calibrating.  Click to Stop")
        self.update_buttons()
        self.status_bar.showMessage(
            "Calibration started. Click two points (first = origin, second = max). Click this button again to stop."
        )

    def axis_range_changed(self):
        """
        Recalculate real-coordinate values when axis ranges change.

        - Updates stored calibration real values (origin/max) when present.
        - Recomputes digitized_points' real_x/real_y from the pixel/image coordinates.
        """
        # Only meaningful once we have a full calibration (two points define mapping).
        if not (self.calibrated and len(self.calibration_points) >= 2):
            # Still keep the overlay labels for calibration points somewhat consistent.
            if len(self.calibration_points) >= 1:
                x1 = self.x_min_spin.value()
                y1 = self.y_min_spin.value()
                p1 = self.calibration_points[0]
                self.calibration_points[0] = (p1[0], p1[1], x1, y1)
                self.update_image_display()
            return

        # Update calibration real values (origin and max) to match spin boxes.
        p1 = self.calibration_points[0]  # origin
        p2 = self.calibration_points[1]  # max
        self.calibration_points[0] = (p1[0], p1[1], self.x_min_spin.value(), self.y_min_spin.value())
        self.calibration_points[1] = (p2[0], p2[1], self.x_max_spin.value(), self.y_max_spin.value())

        # Recompute digitized points real coordinates using updated calibration.
        new_digitized = []
        for point in self.digitized_points:
            # point structure: (screen_x, screen_y, img_x, img_y, real_x, real_y)
            screen_x, screen_y, img_x, img_y, _, _ = point
            real_x, real_y = self.pixel_to_real_coords(img_x, img_y)
            new_digitized.append((screen_x, screen_y, img_x, img_y, real_x, real_y))
        self.digitized_points = new_digitized

        self.update_points_table()
        self.update_image_display()
        self.update_buttons()
        self.status_bar.showMessage("Axis ranges updated; recalculated real coordinates.")

    def add_calibration_point(self, pos: QPoint):
        """Add a calibration point."""
        if len(self.calibration_points) >= 2:
            return
            
        # Convert screen coordinates to image coordinates
        # We need to account for the QLabel's centering behavior
        if self.image_label.pixmap():
            pixmap = self.image_label.pixmap()
            label_width = self.image_label.width()
            label_height = self.image_label.height()
            pixmap_width = pixmap.width()
            pixmap_height = pixmap.height()
            
            # Calculate the offset due to centering
            center_offset_x = (label_width - pixmap_width) / 2
            center_offset_y = (label_height - pixmap_height) / 2
            
            # Adjust screen coordinates for centering
            adjusted_x = pos.x() - center_offset_x
            adjusted_y = pos.y() - center_offset_y
            
            # Convert to image coordinates
            img_x = (adjusted_x - self.offset_x) / self.scale_factor
            img_y = (adjusted_y - self.offset_y) / self.scale_factor
        else:
            # Fallback if no pixmap
            img_x = (pos.x() - self.offset_x) / self.scale_factor
            img_y = (pos.y() - self.offset_y) / self.scale_factor
        
        if len(self.calibration_points) == 0:
            # First point - origin
            real_x = self.x_min_spin.value()
            real_y = self.y_min_spin.value()
            self.calibration_points.append((img_x, img_y, real_x, real_y))
            self.status_bar.showMessage("First point set. Click on a point with known maximum values.")
        else:
            # Second point - max values
            real_x = self.x_max_spin.value()
            real_y = self.y_max_spin.value()
            self.calibration_points.append((img_x, img_y, real_x, real_y))

            # Selecting the second point completes calibration automatically.
            self.calibration_mode = False
            self.calibrated = True
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
            self.calibrate_btn.setText("Re-Do Calibration")
            self.update_buttons()
            self.status_bar.showMessage("Calibration complete. Ready to digitize.")
            
        self.update_image_display()
        
    def finish_calibration(self):
        """Finish the calibration process (legacy helper)."""
        if len(self.calibration_points) < 2:
            # Treat as a canceled/incomplete calibration.
            self.calibration_mode = False
            self.calibrated = False
            self.calibration_points = []
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
            self.calibrate_btn.setText("Start Calibration")
            self.update_buttons()
            QMessageBox.warning(self, "Warning", "Please set at least 2 calibration points.")
            return

        self.calibration_mode = False
        self.calibrated = True
        self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
        self.calibrate_btn.setText("Re-Do Calibration")
        self.update_buttons()
        self.status_bar.showMessage("Calibration complete. Ready to digitize.")
        
    def start_digitizing(self):
        """Start the digitization process."""
        if not self.calibrated:
            QMessageBox.warning(self, "Warning", "Please calibrate the axes first.")
            return

        # Toggle behavior: clicking the button again stops digitizing.
        if hasattr(self, "digitizing_mode") and self.digitizing_mode:
            self.digitizing_mode = False
            self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
            self.status_bar.showMessage("Digitizing stopped. Click 'Start Digitizing' to continue.")
            self.update_buttons()
            return

        self.digitizing_mode = True
        self.image_label.setCursor(Qt.CursorShape.CrossCursor)
        self.digitize_btn.setText("Digitizing.  Click to Stop")
        self.status_bar.showMessage("Click on points to digitize data. Right-click or click Stop to stop.")
        
    def add_digitized_point(self, pos: QPoint):
        """Add a digitized point."""
        if not self.calibrated:
            return
            
        # Store the screen coordinates where the user clicked
        screen_x = pos.x()
        screen_y = pos.y()
        
        # Convert screen coordinates to image coordinates for real coordinate calculation
        # We need to account for the QLabel's centering behavior
        # The QLabel centers the pixmap, so we need to calculate the centering offset
        if self.image_label.pixmap():
            pixmap = self.image_label.pixmap()
            label_width = self.image_label.width()
            label_height = self.image_label.height()
            pixmap_width = pixmap.width()
            pixmap_height = pixmap.height()
            
            # Calculate the offset due to centering
            center_offset_x = (label_width - pixmap_width) / 2
            center_offset_y = (label_height - pixmap_height) / 2
            
            # Adjust screen coordinates for centering
            adjusted_x = screen_x - center_offset_x
            adjusted_y = screen_y - center_offset_y
            
            # Convert to image coordinates
            img_x = (adjusted_x - self.offset_x) / self.scale_factor
            img_y = (adjusted_y - self.offset_y) / self.scale_factor
        else:
            # Fallback if no pixmap
            img_x = (screen_x - self.offset_x) / self.scale_factor
            img_y = (screen_y - self.offset_y) / self.scale_factor
        
        # Convert to real coordinates
        real_x, real_y = self.pixel_to_real_coords(img_x, img_y)
        
        # Store both screen coordinates (for display) and image coordinates (for real coords)
        self.digitized_points.append((screen_x, screen_y, img_x, img_y, real_x, real_y))
        self.update_points_table()
        self.update_image_display()
        
        self.status_bar.showMessage(f"Point {len(self.digitized_points)}: ({real_x:.3f}, {real_y:.3f})")
        
    def pixel_to_real_coords(self, pixel_x: float, pixel_y: float) -> Tuple[float, float]:
        """Convert pixel coordinates to real coordinates."""
        if len(self.calibration_points) < 2:
            return 0, 0
            
        # Get calibration points
        p1 = self.calibration_points[0]  # (img_x, img_y, real_x, real_y) - origin
        p2 = self.calibration_points[1]  # (img_x, img_y, real_x, real_y) - max values
        
        # Calculate scaling factors
        scale_x = (p2[2] - p1[2]) / (p2[0] - p1[0])
        scale_y = (p2[3] - p1[3]) / (p2[1] - p1[1])
        
        # Convert coordinates using the calibrated origin
        real_x = p1[2] + (pixel_x - p1[0]) * scale_x
        real_y = p1[3] + (pixel_y - p1[1]) * scale_y
        
        return real_x, real_y
        
    def update_points_table(self):
        """Update the points table display."""
        # Avoid triggering itemChanged while we repopulate the table.
        self.points_table.blockSignals(True)
        self.points_table.setRowCount(len(self.digitized_points))
        
        for i, point in enumerate(self.digitized_points):
            # point structure: (screen_x, screen_y, img_x, img_y, real_x, real_y)
            self.points_table.setItem(i, 0, QTableWidgetItem(f"{point[4]:.6f}"))  # real_x
            self.points_table.setItem(i, 1, QTableWidgetItem(f"{point[5]:.6f}"))  # real_y
            self.points_table.setItem(i, 2, QTableWidgetItem(f"{point[2]:.1f}"))  # img_x
            self.points_table.setItem(i, 3, QTableWidgetItem(f"{point[3]:.1f}"))  # img_y
        self.points_table.blockSignals(False)

    def points_table_item_changed(self, item):
        """
        Sync user edits in the table into `self.digitized_points` for export.

        Columns:
        0 -> X (Real)  (updates point[4])
        1 -> Y (Real)  (updates point[5])
        2/3 -> pixels (not currently used for recalculation/export)
        """
        if item is None:
            return

        row = item.row()
        col = item.column()
        if row < 0 or row >= len(self.digitized_points):
            return
        if col not in (0, 1):
            return

        text = item.text().strip()
        if not text:
            return

        try:
            new_val = float(text)
        except ValueError:
            return

        screen_x, screen_y, img_x, img_y, real_x, real_y = self.digitized_points[row]
        if col == 0:
            real_x = new_val
        else:
            real_y = new_val

        self.digitized_points[row] = (screen_x, screen_y, img_x, img_y, real_x, real_y)
    def update_buttons(self):
        """Update button states based on current mode."""
        has_image = self.original_pixmap is not None
        self.digitize_btn.setEnabled(has_image and self.calibrated)
        if hasattr(self, "digitizing_mode") and self.digitizing_mode:
            self.digitize_btn.setText("Digitizing.  Click to Stop")
        else:
            self.digitize_btn.setText("Start Digitizing")
        
    def clear_points(self):
        """Clear all digitized points."""
        self.digitized_points = []
        self.update_points_table()
        self.update_image_display()
        self.status_bar.showMessage("All points cleared.")
        
    def undo_last_point(self):
        """Remove the last digitized point."""
        if self.digitized_points:
            self.digitized_points.pop()
            self.update_points_table()
            self.update_image_display()
            self.status_bar.showMessage(f"Removed last point. {len(self.digitized_points)} points remaining.")
            
    def zoom_in(self):
        """Zoom in on the image."""
        self.scale_factor *= 1.2
        self.update_image_display()
        
    def zoom_out(self):
        """Zoom out on the image."""
        self.scale_factor /= 1.2
        if self.scale_factor < 0.1:
            self.scale_factor = 0.1
        self.update_image_display()
        
    def reset_view(self):
        """Reset the view to original size and position."""
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update_image_display()
        
    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()  # Return to maximized instead of normal size
        else:
            self.showFullScreen()
        
    def export_csv(self):
        """Export digitized points to CSV file."""
        if not self.digitized_points:
            QMessageBox.warning(self, "Warning", "No points to export.")
            return
            
        default_path = os.path.join(self.last_export_dir, "digitized_data.csv") if self.last_export_dir else "digitized_data.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default_path, "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                # Save the directory for next time
                self.last_export_dir = os.path.dirname(file_path)
                self.save_settings()
                
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['X', 'Y', 'X_Pixel', 'Y_Pixel'])
                    for point in self.digitized_points:
                        # point structure: (screen_x, screen_y, img_x, img_y, real_x, real_y)
                        writer.writerow([point[4], point[5], point[2], point[3]])
                        
                self.status_bar.showMessage(f"Exported {len(self.digitized_points)} points to {file_path}")
                QMessageBox.information(self, "Success", f"Exported {len(self.digitized_points)} points to CSV.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")
                
    def export_txt(self):
        """Export digitized points to TXT file."""
        if not self.digitized_points:
            QMessageBox.warning(self, "Warning", "No points to export.")
            return
            
        default_path = os.path.join(self.last_export_dir, "digitized_data.txt") if self.last_export_dir else "digitized_data.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export TXT", default_path, "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                # Save the directory for next time
                self.last_export_dir = os.path.dirname(file_path)
                self.save_settings()
                
                with open(file_path, 'w') as txtfile:
                    txtfile.write("X\tY\tX_Pixel\tY_Pixel\n")
                    for point in self.digitized_points:
                        # point structure: (screen_x, screen_y, img_x, img_y, real_x, real_y)
                        txtfile.write(f"{point[4]:.6f}\t{point[5]:.6f}\t{point[2]:.1f}\t{point[3]:.1f}\n")
                        
                self.status_bar.showMessage(f"Exported {len(self.digitized_points)} points to {file_path}")
                QMessageBox.information(self, "Success", f"Exported {len(self.digitized_points)} points to TXT.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export TXT: {str(e)}")
                
    def export_swath_coverage_curve(self):
        """Export digitized points to Swath Coverage Curve format."""
        if not self.digitized_points:
            QMessageBox.warning(self, "Warning", "No points to export.")
            return
            
        # Prompt for curve name
        curve_name, ok = QInputDialog.getText(
            self, "Curve Name", "Enter curve name:", 
            text="40 dB theoretical"
        )
        
        if not ok or not curve_name.strip():
            return  # User cancelled or entered empty name
            
        # File save dialog
        default_filename = f"{curve_name.strip()}.txt"
        default_path = os.path.join(self.last_export_dir, default_filename) if self.last_export_dir else default_filename
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Swath Coverage Curve", 
            default_path, 
            "Text Files (*.txt)"
        )
        
        if file_path:
            try:
                # Save the directory for next time
                self.last_export_dir = os.path.dirname(file_path)
                self.save_settings()
                
                with open(file_path, 'w') as txtfile:
                    # Write curve name as first line
                    txtfile.write(f"{curve_name.strip()}\n")
                    
                    # Write data points in format: X,Y*multiplier
                    swath_multiplier = self.swath_multiplier_spin.value()
                    for point in self.digitized_points:
                        # point structure: (screen_x, screen_y, img_x, img_y, real_x, real_y)
                        x_value = point[4]  # real_x
                        y_value = point[5] * swath_multiplier  # real_y * multiplier
                        txtfile.write(f"{x_value:.6f}, {y_value:.6f}\n")
                        
                self.status_bar.showMessage(f"Exported {len(self.digitized_points)} points to {file_path}")
                QMessageBox.information(self, "Success", f"Exported {len(self.digitized_points)} points to Swath Coverage Curve.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export Swath Coverage Curve: {str(e)}")
                
    def export_all_formats(self):
        """Export digitized points to all formats (CSV, TXT, and Swath Coverage Curve)."""
        if not self.digitized_points:
            QMessageBox.warning(self, "Warning", "No points to export.")
            return
            
        # Prompt for curve name for Swath Coverage Curve
        curve_name, ok = QInputDialog.getText(
            self, "Curve Name", "Enter curve name for Swath Coverage Curve:", 
            text="40 dB theoretical"
        )
        
        if not ok or not curve_name.strip():
            return  # User cancelled or entered empty name
            
        curve_name = curve_name.strip()
        successful_exports = []
        failed_exports = []
        
        try:
            # Export CSV
            csv_path, _ = QFileDialog.getSaveFileName(
                self, "Export CSV", 
                os.path.join(self.last_export_dir, "digitized_data.csv") if self.last_export_dir else "digitized_data.csv", 
                "CSV Files (*.csv)"
            )
            
            if csv_path:
                self.last_export_dir = os.path.dirname(csv_path)
                with open(csv_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['X', 'Y', 'X_Pixel', 'Y_Pixel'])
                    for point in self.digitized_points:
                        writer.writerow([point[4], point[5], point[2], point[3]])
                successful_exports.append("CSV")
                
        except Exception as e:
            failed_exports.append(f"CSV: {str(e)}")
            
        try:
            # Export TXT
            txt_path, _ = QFileDialog.getSaveFileName(
                self, "Export TXT", 
                os.path.join(self.last_export_dir, "digitized_data.txt") if self.last_export_dir else "digitized_data.txt", 
                "Text Files (*.txt)"
            )
            
            if txt_path:
                with open(txt_path, 'w') as txtfile:
                    txtfile.write("X\tY\tX_Pixel\tY_Pixel\n")
                    for point in self.digitized_points:
                        txtfile.write(f"{point[4]:.6f}\t{point[5]:.6f}\t{point[2]:.1f}\t{point[3]:.1f}\n")
                successful_exports.append("TXT")
                
        except Exception as e:
            failed_exports.append(f"TXT: {str(e)}")
            
        try:
            # Export Swath Coverage Curve
            # Replace spaces with underscores in curve name for filename
            safe_curve_name = curve_name.replace(" ", "_")
            swath_path, _ = QFileDialog.getSaveFileName(
                self, "Export Swath Coverage Curve", 
                os.path.join(self.last_export_dir, f"{safe_curve_name}.txt") if self.last_export_dir else f"{safe_curve_name}.txt", 
                "Text Files (*.txt)"
            )
            
            if swath_path:
                swath_multiplier = self.swath_multiplier_spin.value()
                with open(swath_path, 'w') as txtfile:
                    txtfile.write(f"{curve_name}\n")
                    for point in self.digitized_points:
                        x_value = point[4]  # real_x
                        y_value = point[5] * swath_multiplier  # real_y * multiplier
                        txtfile.write(f"{x_value:.6f}, {y_value:.6f}\n")
                successful_exports.append("Swath Coverage Curve")
                
        except Exception as e:
            failed_exports.append(f"Swath Coverage Curve: {str(e)}")
            
        # Save settings
        self.save_settings()
        
        # Show results
        if successful_exports:
            success_msg = f"Successfully exported {len(self.digitized_points)} points to: {', '.join(successful_exports)}"
            self.status_bar.showMessage(success_msg)
            
        if failed_exports:
            error_msg = "Failed exports:\n" + "\n".join(failed_exports)
            QMessageBox.warning(self, "Export Errors", error_msg)
        else:
            QMessageBox.information(self, "Success", f"All exports completed successfully!\n\nExported to: {', '.join(successful_exports)}")
                
    def save_session(self):
        """Save the current digitization session."""
        if not self.original_pixmap:
            QMessageBox.warning(self, "Warning", "No session to save.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", self.last_session_dir or "digitization_session.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                # Save the directory for next time
                self.last_session_dir = os.path.dirname(file_path)
                self.save_settings()
                
                session_data = {
                    'image_path': self.image_path,
                    'calibration_points': self.calibration_points,
                    'digitized_points': self.digitized_points,
                    'calibrated': self.calibrated,
                    'x_axis_range': (self.x_min_spin.value(), self.x_max_spin.value()),
                    'y_axis_range': (self.y_min_spin.value(), self.y_max_spin.value())
                }
                
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, indent=2)
                    
                self.status_bar.showMessage(f"Session saved to {file_path}")
                QMessageBox.information(self, "Success", "Session saved successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save session: {str(e)}")
                
    def load_session(self):
        """Load a digitization session."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Session", self.last_session_dir, "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                # Save the directory for next time
                self.last_session_dir = os.path.dirname(file_path)
                self.save_settings()
                
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                    
                # Load image
                if os.path.exists(session_data['image_path']):
                    self.image_path = session_data['image_path']
                    self.original_pixmap = QPixmap(self.image_path)
                    self.current_pixmap = self.original_pixmap
                else:
                    QMessageBox.warning(self, "Warning", f"Image file not found: {session_data['image_path']}")
                    return
                    
                # Restore data
                self.calibration_points = session_data['calibration_points']
                self.digitized_points = session_data['digitized_points']
                self.calibrated = session_data['calibrated']
                
                # Restore axis ranges
                x_range = session_data['x_axis_range']
                y_range = session_data['y_axis_range']
                self.x_min_spin.setValue(x_range[0])
                self.x_max_spin.setValue(x_range[1])
                self.y_min_spin.setValue(y_range[0])
                self.y_max_spin.setValue(y_range[1])
                
                # Update UI
                self.calibration_mode = False
                self.image_label.setCursor(Qt.CursorShape.ArrowCursor)
                self.calibrate_btn.setText("Re-Do Calibration")
                self.update_image_display()
                self.update_points_table()
                self.update_buttons()
                
                self.status_bar.showMessage(f"Session loaded from {file_path}")
                QMessageBox.information(self, "Success", "Session loaded successfully.")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load session: {str(e)}")
                
    def load_settings(self):
        """Load settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.last_image_dir = settings.get('last_image_dir', '')
                    self.last_session_dir = settings.get('last_session_dir', '')
                    self.last_export_dir = settings.get('last_export_dir', '')
        except Exception as e:
            print(f"Failed to load settings: {e}")
            
    def save_settings(self):
        """Save settings to file."""
        try:
            settings = {
                'last_image_dir': self.last_image_dir,
                'last_session_dir': self.last_session_dir,
                'last_export_dir': self.last_export_dir
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Dark Fusion theme (palette + stylesheet).
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#2b2b2b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#dcdcdc"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#353535"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2f2f2f"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#dcdcdc"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#2b2b2b"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#dcdcdc"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#2b2b2b"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#dcdcdc"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#4aa3df"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4aa3df"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1e1e1e"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow, QWidget { background-color: #2b2b2b; color: #dcdcdc; }
        QAbstractScrollArea, QScrollArea { background-color: #2b2b2b; }
        QDialog, QFileDialog, QMessageBox { background-color: #2b2b2b; color: #dcdcdc; }
        QGroupBox { border: 1px solid #5a5a5a; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #dcdcdc; }

        QPushButton, QToolButton {
            background-color: #353535;
            border: 1px solid #5a5a5a;
            padding: 6px;
            border-radius: 2px;
            color: #dcdcdc;
        }
        QPushButton:hover, QToolButton:hover { background-color: #3f3f3f; border: 1px solid #6c6c6c; }
        QPushButton:pressed, QToolButton:pressed { background-color: #2f2f2f; border: 1px solid #6c6c6c; }
        QPushButton:disabled, QToolButton:disabled { background-color: #2b2b2b; color: #7f7f7f; border: 1px solid #3f3f3f; }

        QMessageBox QPushButton {
            background-color: #353535;
            border: 1px solid #5a5a5a;
            color: #dcdcdc;
            padding: 6px;
            border-radius: 2px;
        }

        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #353535;
            border: 1px solid #5a5a5a;
            color: #dcdcdc;
        }
        QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
            color: #7f7f7f;
        }

        QAbstractItemView {
            background-color: #353535;
            color: #dcdcdc;
            selection-background-color: #4aa3df;
            selection-color: #1e1e1e;
        }
        QAbstractItemView::item:selected {
            background-color: #4aa3df;
            color: #1e1e1e;
        }

        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #2b2b2b;
            border: 1px solid #2b2b2b;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #3f3f3f;
            border: 1px solid #6c6c6c;
        }

        QComboBox::drop-down {
            border: 0px;
            background-color: #353535;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #4aa3df;
            color: #1e1e1e;
        }
        QScrollBar:vertical, QScrollBar:horizontal { background: #2b2b2b; }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #3f3f3f; border: 1px solid #5a5a5a; }
        QScrollBar::add-line, QScrollBar::sub-line {
            background: #2b2b2b;
            border: 0px;
        }
        QScrollBar::add-page, QScrollBar::sub-page { background: #2b2b2b; }

        QTableWidget {
            background-color: #2b2b2b;
            border: 1px solid #5a5a5a;
            gridline-color: #404040;
            color: #dcdcdc;
            selection-background-color: #4aa3df;
            selection-color: #1e1e1e;
        }
        QTableWidget::item { color: #dcdcdc; }
        QTableWidget::item:selected { background-color: #4aa3df; color: #1e1e1e; }
        QTableWidget::item:selected:active { background-color: #4aa3df; color: #1e1e1e; }
        QTableWidget::item:hover { background-color: #353535; }
        QHeaderView::section {
            background-color: #353535;
            color: #dcdcdc;
            border: 1px solid #5a5a5a;
            padding: 4px;
        }
        QHeaderView::section:checked { background-color: #3f3f3f; }

        QMenuBar { background-color: #353535; color: #dcdcdc; }
        QMenuBar::item { background: transparent; color: #dcdcdc; padding: 3px 8px; }
        QMenuBar::item:selected { background: #3f3f3f; }
        QMenuBar::item:pressed { background: #2f2f2f; }
        QMenu { background-color: #2b2b2b; color: #dcdcdc; }
        QMenu::item:selected { background-color: #3f3f3f; }

        QStatusBar { background-color: #353535; color: #dcdcdc; }

        QSplitter::handle { background-color: #2f2f2f; width: 6px; margin: 0px; }

        QProgressBar { background-color: #353535; border: 1px solid #5a5a5a; text-align: center; }
        QProgressBar::chunk { background-color: #4aa3df; }

        QToolTip { background-color: #dcdcdc; color: #1e1e1e; border: 1px solid #5a5a5a; }
        """
    )
    
    # Set application properties
    app.setApplicationName("Graph Digitizer")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("MultibeamTools")
    
    # Create and show main window
    window = GraphDigitizer()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
