from __future__ import annotations
from . import _typing as _t
class BaseTableAdapter():
    def data(self, row: int, col: int) -> _t.Any:
        """
        Return cell content
        """
        raise NotImplementedError("data() must be implemented")

    def editData(self, row: int, col: int) -> _t.Any:
        """
        Return data to be edited
        """
        return self.data(row, col)

    def setData(self, row: int, col: int, value: _t.Any) -> None:
        """
        Accepts the edited value
        """
        pass

    def editable(self, row: int, col: int) -> bool:
        """
        Return whether the cell is editable
        """
        return False

    def columnHeader(self, col: int) -> str | None:
        """
        Return column header, set to None to hide column header
        """
        return f"Col {col}"

    def rowHeader(self, row: int) -> str | None:
        """
        Return row header, set to None to hide row header
        """
        return f"Row {row}"

    def rowCount(self) -> int:
        """
        Return number of rows
        """
        raise NotImplementedError("rowCount() must be implemented")

    def columnCount(self) -> int:
        """
        Return number of columns
        """
        raise NotImplementedError("columnCount() must be implemented")

    def clicked(self, row: int, col: int) -> None:
        """
        Called when a node is clicked
        """
        pass

    def dblclicked(self, row: int, col: int) -> None:
        """
        Called when a node is double clicked
        """
        pass

class BaseTreeAdapter():
    def parent(self, node: _t.Any) -> _t.Any:
        """
        Return parent node
        """
        raise NotImplementedError("parent() must be implemented")

    def child(self, parent: _t.Any, index: int) -> _t.Any:
        """
        Return child node
        """
        raise NotImplementedError("child() must be implemented")

    def data(self, node: _t.Any) -> _t.Any:
        """
        Return node data
        """
        raise NotImplementedError("data() must be implemented")

    def rowCount(self, parent: _t.Any) -> int:
        """
        Return number of rows
        """
        raise NotImplementedError("rowCount() must be implemented")

    def clicked(self, node: _t.Any) -> None:
        """
        Called when a node is clicked
        """
        pass

    def dblclicked(self, node: _t.Any) -> None:
        """
        Called when a node is double clicked
        """
        pass

    def expanded(self, node: _t.Any) -> None:
        """
        Called when a node is expanded
        """
        pass

    def collapsed(self, node: _t.Any) -> None:
        """
        Called when a node is collapsed
        """
        pass
