class BaseTableAdapter():
    def data(self, row, col):
        """
        Return cell content
        """
        raise NotImplementedError("data() must be implemented")

    def editData(self, row, col):
        """
        Return data to be edited
        """
        return self.data(row, col)

    def setData(self, row, col, value):
        """
        Accepts the edited value
        """
        pass

    def editable(self, row, col):
        """
        Return whether the cell is editable
        """
        return False

    def columnHeader(self, col):
        """
        Return column header, set to None to hide column header
        """
        return f"Col {col}"

    def rowHeader(self, row):
        """
        Return row header, set to None to hide row header
        """
        return f"Row {row}"

    def rowCount(self):
        """
        Return number of rows
        """
        raise NotImplementedError("rowCount() must be implemented")

    def columnCount(self):
        """
        Return number of columns
        """
        raise NotImplementedError("columnCount() must be implemented")