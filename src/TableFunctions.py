# Functions for tables
# -------------------------------
class TableFcn:
    """Common table operations class

    For moving and deleting rows in QTableWidgets
    """
    def __init__(self, parent=None):

        self.parent = parent

    def move_row_up(self, table):
        """Moves a row up one position in a table

        Moves the selected row in a table up one position. If multiple are selected only the top row is moved.

        Parameters
        ----------
        table : QTableWidget
        """

        # Get selected row
        row = table.currentRow()
        if len(table.selectedItems()) > 0:
            return

        if row > 0:
            table.insertRow(row - 1)
            for i in range(table.columnCount()):
                table.setItem(row - 1, i, table.takeItem(row + 1, i))
            table.removeRow(row + 1)
            table.setCurrentCell(row - 1, 0)

            match table.accessibleName():
                case 'Profiling':
                    self.parent.comboBoxProfileSort.setCurrentIndex(0) #set dropdown sort to no

                    # Update self.profiles[self.parent.sample_id] here accordingly
                    for key, profile in self.parent.profiling.profiles[self.parent.sample_id].items():
                        if row >0:
                            profile[row], profile[row -1 ] = profile[row - 1], profile[row]
                    self.parent.profiling.plot_profiles()
                    if self.parent.profiling.parent.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                        self.parent.profiling.clear_interpolation()
                        self.parent.profiling.interpolate_points(interpolation_distance=int(self.parent.lineEditIntDist.text()), radius= int(self.parent.lineEditPointRadius.text()))
                #case 'NDim':
                    # update plot

                #case 'Filters':
                    # update filters
                    # update plots

    def move_row_down(self,table):
        """Moves a row down one position in a table

        Moves the selected row in a table down one position. If multiple are selected only the top row is moved.

        Parameters
        ----------
        table : QTableWidget
        """

        # Similar to move_row_up, but moving the row down
        row = table.currentRow()
        if len(table.selectedItems()) > 0:
            return

        max_row = table.rowCount() - 1
        if row < max_row:
            table.insertRow(row + 2)
            for i in range(table.columnCount()):
                table.setItem(row + 2, i, table.takeItem(row, i))
            table.removeRow(row)
            table.setCurrentCell(row + 1, 0)
            match table.accesibleName():
                case 'Profiling':
                    # update point order of each profile
                    for key, profile in self.parent.profiling.profiles[self.parent.sample_id].items():
                        if row < len(profile) - 1:
                            profile[row], profile[row + 1] = profile[row + 1], profile[row]
                    self.parent.profiling.plot_profiles()
                    if self.parent.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                        self.parent.profiling.clear_interpolation()
                        self.parent.profiling.interpolate_points(interpolation_distance=int(self.parent.lineEditIntDist.text()), radius= int(self.parent.lineEditPointRadius.text()))

    def delete_row(self,table):
        """Deletes selected rows in a table

        Parameters
        ----------
        table : QTableWidget
        """
        rows = [index.row() for index in table.selectionModel().selectedRows()][::-1] #sort descending to pop in order
        match table.accessibleName():
            case 'Profiling':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)
                    # remove point from each profile and its corresponding scatter plot item


                    for key, profile in self.parent.profiling.profiles[self.parent.sample_id].items():
                        if row < len(profile):
                            scatter_item = profile[row][3]  # Access the scatter plot item
                            for _, (_, plot, _) in self.parent.lasermaps.items():
                                plot.removeItem(scatter_item)
                            profile.pop(row) #index starts at 0

                self.parent.profiling.plot_profiles(sort_axis = False)

                if self.parent.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                    self.parent.profiling.clear_interpolation()
                    self.parent.profiling.interpolate_points(interpolation_distance=int(self.parent.lineEditIntDist.text()), radius= int(self.parent.lineEditPointRadius.text()))

            case 'NDim':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)
                    self.parent.ndim_list.pop(row)

            case 'Filters':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)

            case 'Polygon':
                for row in rows:
                    # Get p_id
                    item = self.parent.tableWidgetPolyPoints.item(row, 0)
                    p_id = int(item.text())
                    # Get selected row and delete it
                    table.removeRow(row)
                    if p_id in self.parent.polygon.lines[self.parent.sample_id]:
                        # remove point from each profile and its corresponding scatter plot item
                        for p in self.parent.polygon.polygons[self.parent.sample_id][p_id].points:
                            scatter_item = p[2]  # Access the scatter plot item
                            for _, (_, plot, _) in self.parent.lasermaps.items():
                                plot.removeItem(scatter_item)
                        # Remove existing temporary line(s) if any
                        for line in self.parent.polygon.lines[self.parent.sample_id][p_id].lines:
                            for _, (_, plot, _) in self.parent.lasermaps.items():
                                plot.removeItem(line)
                    

                        
                    # delete polygon from list
                    del self.parent.polygon.polygons[self.parent.sample_id][p_id]
