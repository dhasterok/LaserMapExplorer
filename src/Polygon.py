import os, pickle
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import ( QMessageBox, QTableWidgetItem, QGraphicsPolygonItem, QCheckBox )
from pyqtgraph import ( ScatterPlotItem, PlotDataItem )


# Polygons
# -------------------------------
class Polygon:
    def __init__(self, p_id):
        self.p_id = p_id
        self.points = []  # List to store points as (x, y, scatter)
        self.lines = []  # List to store lines as graphical items

# class PolygonManager:
#     """Operations related to polygon generation and manipulation

#     Polygons can be used to select or exclude regions of maps for analysis.

#     Methods
#     -------
#     increment_pid()
#         creates a new polygon pid for addressing polygon when toolButtonPolyCreate is checked
#     plot_polygon_scatter:

#     distance_to_line_segment:
#     show_polygon_lines:
#     update_table_widget:
#     """
#     def __init__(self, main_window):
#         self.main_window = main_window
#         self.polygons = {}          #dict of polygons
#         self.lines ={}              #temp dict for lines in polygon
#         self.point_index = None             # index for move point
#         self.p_id = None           # polygon ID
#         self.p_id_gen = 0 #Polygon_id generator

#     def add_samples(self):
#         #add sample id to dictionary
#         for sample_id in self.main_window.sample_ids:
#             if sample_id not in self.polygons:
#                 self.polygons[sample_id] = {}

#     # Method to increment p_id_gen
#     def increment_pid(self):
#         """Creates new polygon pid

#         When toolButtonPolyCreate is checked, a new polygon pid is created.
#         """
#         self.main_window.toolButtonPolyCreate.isChecked()
#         self.p_id_gen += 1
#         self.p_id = self.p_id_gen
#         self.main_window.actionClearFilters.setEnabled(True)
#         self.main_window.actionPolygonMask.setEnabled(True)
#         self.main_window.actionPolygonMask.setChecked(True)

#     def plot_polygon_scatter(self, event,k, x, y, x_i, y_i):
#         #create profile dict for this sample if it doesnt exisist
#         if self.main_window.sample_id not in self.polygons:
#             self.polygons[self.main_window.sample_id] = {}
#             self.lines[self.main_window.sample_id] = {}

#         self.array_x = self.main_window.array.shape[1]
#         self.array_y = self.main_window.array.shape[0]
#         # turn off profile (need to suppress context menu on right click)
#         if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyCreate.isChecked():
#             self.main_window.toolButtonPolyCreate.setChecked(False)
#             self.main_window.toolButtonPolyMovePoint.setEnabled(True)

#             # Finalize and draw the polygon
#             self.show_polygon_lines(x,y, complete = True)

#             return
#         elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyMovePoint.isChecked():
#             self.main_window.toolButtonPolyMovePoint.setChecked(False)
#             self.main_window.point_selected = False
#             return

#         elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyAddPoint.isChecked():
#             self.main_window.toolButtonPolyAddPoint.setChecked(False)
#             return

#         elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyRemovePoint.isChecked():
#             self.main_window.toolButtonPolyRemovePoint.setChecked(False)
#             return
#         elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
#             return

#         elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyMovePoint.isChecked():
#             # move point
#             selection_model = self.main_window.tableWidgetPolyPoints.selectionModel()

#             # Check if there is any selection
#             if selection_model.hasSelection():
#                 selected_rows = selection_model.selectedRows()
#                 if selected_rows:
#                     # Assuming you're interested in the first selected row
#                     first_selected_row = selected_rows[0].row()

#                     # Get the item in the first column of this row
#                     item = self.main_window.tableWidgetPolyPoints.item(first_selected_row, 0)

#                     # Check if the item is not None
#                     if item is not None:
#                         self.p_id = int(item.text())  # Get polygon id to move point

#                     else:
#                         QMessageBox.warning(self.main_window, "Selection Error", "No item found in the first column of the selected row.")
#                 else:
#                     QMessageBox.warning(self.main_window, "Selection Error", "No row is selected.")
#             else:
#                 QMessageBox.warning(self.main_window, "Selection Error", "No selection is made in the table.")


#             if self.main_window.point_selected:
#                 #remove selected point
#                 prev_scatter = self.polygons[self.main_window.sample_id][self.p_id][self.point_index][2]
#                 self.main_window.plot.removeItem(prev_scatter)


#                 # Create a scatter plot item at the clicked position
#                 scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
#                 scatter.setZValue(1e9)
#                 self.main_window.plot.addItem(scatter)


#                 #update self.point_index index of self.polygons[self.main_window.sample_id]with new point data

#                 self.polygons[self.main_window.sample_id][self.p_id][self.point_index] = (x,y, scatter)

#                 # Finalize and draw the polygon
#                 self.show_polygon_lines(x,y, complete = True)

#                 self.main_window.point_selected = False
#                 #update plot and table widget
#                 # self.update_table_widget()
#             else:
#                 # find nearest profile point
#                 mindist = 10**12
#                 for i, (x_p,y_p,_) in enumerate(self.polygons[self.main_window.sample_id][self.p_id]):
#                     dist = (x_p - x)**2 + (y_p - y)**2
#                     if mindist > dist:
#                         mindist = dist
#                         self.point_index = i
#                 if (round(mindist*self.array_x/self.main_window.x_range) < 50):
#                     self.main_window.point_selected = True


#         elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyAddPoint.isChecked():
#             # add point
#             # user must first choose line of polygon
#             # choose the vertext points to add point based on line
#             # Find the closest line segment to the click location
#             min_distance = float('inf')
#             insert_after_index = None
#             for i in range(len(self.polygons[self.main_window.sample_id][self.p_id])):
#                 p1 = self.polygons[self.main_window.sample_id][self.p_id][i]
#                 p2 = self.polygons[self.main_window.sample_id][self.p_id][(i + 1) % len(self.polygons[self.main_window.sample_id][self.p_id])]  # Loop back to the start for the last segment
#                 dist = self.distance_to_line_segment(x, y, p1[0], p1[1], p2[0], p2[1])
#                 if dist < min_distance:
#                     min_distance = dist
#                     insert_after_index = i

#             # Insert the new point after the closest line segment
#             if insert_after_index is not None:
#                 scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
#                 scatter.setZValue(1e9)
#                 self.main_window.plot.addItem(scatter)
#                 self.polygons[self.main_window.sample_id][self.p_id].insert(insert_after_index + 1, (x, y, scatter))

#             # Redraw the polygon with the new point
#             self.show_polygon_lines(x, y, complete=True)

#         elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyRemovePoint.isChecked():
#             # remove point
#             # draw polygon without selected point
#             # remove point
#             # Find the closest point to the click location
#             min_distance = float('inf')
#             point_to_remove_index = None
#             for i, (px, py, _) in enumerate(self.polygons[self.main_window.sample_id][self.p_id]):
#                 dist = ((px - x)**2 + (py - y)**2)**0.5
#                 if dist < min_distance:
#                     min_distance = dist
#                     point_to_remove_index = i

#             # Remove the closest point
#             if point_to_remove_index is not None:
#                 _, _, scatter_item = self.polygons[self.main_window.sample_id][self.p_id].pop(point_to_remove_index)
#                 self.main_window.plot.removeItem(scatter_item)

#             # Redraw the polygon without the removed point
#             self.show_polygon_lines(x, y, complete=True)

#             self.main_window.toolButtonPolyRemovePoint.setChecked(False)

#         elif event.button() == QtCore.Qt.LeftButton:
#             # Create a scatter self.main_window.plot item at the clicked position
#             scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
#             scatter.setZValue(1e9)
#             self.main_window.plot.addItem(scatter)

#             # add x and y to self.polygons[self.main_window.sample_id] dict
#             if self.p_id not in self.polygons[self.main_window.sample_id]:
#                 self.polygons[self.main_window.sample_id][self.p_id] = [(x,y, scatter)]

#             else:
#                 self.polygons[self.main_window.sample_id][self.p_id].append((x,y, scatter))

#     def distance_to_line_segment(self, px, py, x1, y1, x2, y2):
#         """Computes distance to the line segment of a polygon

#         Determines the minimum distance from a point (px,py) to a line segment defined by
#         the points (x1,y1) and (x2,y2).

#         Parameters
#         ----------
#         px, py : float
#             Point used to determine minimum distance
#         x1, y1 : float
#             Point 1 on a line
#         x2, y2 : float
#             Point 2 on a line

#         Returns
#         -------
#         float
#             Minimum distance from point to a line
#         """        
#         # Calculate the distance from point (px, py) to the line segment defined by points (x1, y1) and (x2, y2)
#         # This is a simplified version; you might need a more accurate calculation based on your coordinate system
#         return min(((px - x1)**2 + (py - y1)**2)**0.5, ((px - x2)**2 + (py - y2)**2)**0.5)

#     def show_polygon_lines(self, x,y, complete = False):
#         if self.main_window.sample_id in self.polygons:
#             if self.p_id in self.polygons[self.main_window.sample_id]:
#                 # Remove existing temporary line(s) if any
#                 if self.p_id in self.lines[self.main_window.sample_id]:
#                     for line in self.lines[self.main_window.sample_id][self.p_id]:
#                         self.main_window.plot.removeItem(line)
#                 self.lines[self.main_window.sample_id][self.p_id] = []

#                 points = self.polygons[self.main_window.sample_id][self.p_id]
#                 if len(points) == 1:
#                     # Draw line from the first point to cursor
#                     line = PlotDataItem([points[0][0], x], [points[0][1], y], pen='r')
#                     self.main_window.plot.addItem(line)
#                     self.lines[self.main_window.sample_id][self.p_id].append(line)
#                 elif not complete and len(points) > 1:

#                     if self.main_window.point_selected:
#                         # self.point_index is the index of the pont that needs to be moved

#                         # create polygon with moved point
#                         x_points = [p[0] for p in points[:self.point_index]] + [x]+ [p[0] for p in points[(self.point_index+1):]]
#                         y_points = [p[1] for p in points[:self.point_index]] + [y]+ [p[1] for p in points[(self.point_index+1):]]

#                     else:

#                         # create polygon with new point
#                         x_points = [p[0] for p in points] + [x, points[0][0]]
#                         y_points = [p[1] for p in points] + [y, points[0][1]]
#                     # Draw shaded polygon + lines to cursor
#                     poly_item = QGraphicsPolygonItem(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in zip(x_points, y_points)]))
#                     poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
#                     self.main_window.plot.addItem(poly_item)
#                     self.lines[self.main_window.sample_id][self.p_id].append(poly_item)

#                     # Draw line from last point to cursor
#                     # line = PlotDataItem([points[-1][0], x], [points[-1][1], y], pen='r')
#                     # self.main_window.plot.addItem(line)
#                     # self.lines[self.main_window.sample_id][self.p_id].append(line)

#                 elif complete and len(points) > 2:
#                     points = [QtCore.QPointF(x, y) for x, y, _ in self.polygons[self.main_window.sample_id][self.p_id]]
#                     polygon = QtGui.QPolygonF(points)
#                     poly_item = QGraphicsPolygonItem(polygon)
#                     poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
#                     self.main_window.plot.addItem(poly_item)
#                     self.lines[self.main_window.sample_id][self.p_id].append(poly_item)

#                     self.update_table_widget()
#                     # Find the row where the first column matches self.p_id and select it
#                     for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
#                         item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
#                         if item and int(item.text()) == self.p_id:
#                             self.main_window.tableWidgetPolyPoints.selectRow(row)
#                             break

#     def update_table_widget(self):
#         """Update polygon table

#         Updates ``MainWindow.tableWidgetPolyPoints`` with 
#         """        
#         if self.main_window.sample_id in self.polygons: #if polygons for that sample if exists

#             self.main_window.tableWidgetPolyPoints.clearContents()  # Clear existing rows
#             self.main_window.tableWidgetPolyPoints.setRowCount(0)

#             for pid, val in self.polygons[self.main_window.sample_id].items():
#                 row_position = self.main_window.tableWidgetPolyPoints.rowCount()
#                 self.main_window.tableWidgetPolyPoints.insertRow(row_position)

#                 # Fill in the data
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 0, QTableWidgetItem(str(pid)))
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 1, QTableWidgetItem(f'poly {pid}'))
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 2, QTableWidgetItem(str('')))
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 3, QTableWidgetItem(str('In')))

#                 # Create a QCheckBox
#                 checkBox = QCheckBox()
#                 checkBox.setChecked(True) # Set its checked state

#                 # Connect the stateChanged signal
#                 checkBox.stateChanged.connect(lambda: self.main_window.apply_polygon_mask(update_plot=True))

#                 # Add the checkbox to the table
#                 self.main_window.tableWidgetPolyPoints.setCellWidget(row_position, 4, checkBox)

#         # update polygon mask
#         self.main_window.apply_polygon_mask(update_plot=True)

#     def clear_lines(self):
#         if self.p_id in self.polygons[self.main_window.sample_id]:
#             # Remove existing temporary line(s) if any
#             if self.p_id in self.lines[self.main_window.sample_id]:
#                 for line in self.lines[self.main_window.sample_id][self.p_id]:
#                     self.main_window.plot.removeItem(line)
#             self.lines[self.main_window.sample_id][self.p_id] = []

#     def clear_polygons(self):
#         if self.main_window.sample_id in self.polygons:
#             self.main_window.tableWidgetPolyPoints.clearContents()
#             self.main_window.tableWidgetPolyPoints.setRowCount(0)
#             self.clear_lines()
#             self.lines[self.main_window.sample_id] ={}              #temp dict for lines in polygon
#             self.point_index = None             # index for move point
#             self.p_id = None           # polygon ID
#             self.p_id_gen = 0 #Polygon_id generator

class PolygonManager:
    """Operations related to polygon generation and manipulation

    Polygons can be used to select or exclude regions of maps for analysis.

    Methods
    -------
    increment_pid()
        creates a new polygon pid for addressing polygon when toolButtonPolyCreate is checked
    plot_polygon_scatter:

    distance_to_line_segment:
    show_polygon_lines:
    update_table_widget:
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.polygons = {}  # Dict to store polygons for each sample
        self.p_id = None  # Current polygon ID
        self.p_id_gen = 0  # Polygon ID generator
        self.point_index = None             # index for move point
        # plot selected polygon from table
        self.main_window.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(lambda: self.view_selected_polygon)

    def add_samples(self):
        for sample_id in self.main_window.sample_ids:
            if sample_id not in self.polygons:
                self.polygons[sample_id] = {}

    def increment_pid(self):
        """Creates a new polygon ID"""
        self.p_id_gen += 1
        self.p_id = self.p_id_gen
        # Create new polygon instance
        self.polygons[self.main_window.sample_id][self.p_id] = Polygon(self.p_id)


    def save_polygons(self, project_dir, sample_id):
        """Save polygons to a file"""
        if sample_id in self.polygons:
            for p_id, polygon in self.polygons[sample_id].items():
                file_name = os.path.join(project_dir, sample_id, f'polygon_{p_id}.poly')
                serializable_polygon = self.transform_polygon_for_pickling(polygon)
                with open(file_name, 'wb') as file:
                    pickle.dump(serializable_polygon, file)
            print("Polygons saved successfully.")

    def load_polygons(self, project_dir, sample_id):
        """Load polygons from a file"""
        directory = os.path.join(project_dir, sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".poly"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    serializable_polygon = pickle.load(file)
                    polygon = self.reconstruct_polygon(serializable_polygon)
                    p_id = polygon.p_id
                    self.polygons[sample_id][p_id] = polygon
        self.update_table_widget()
        print("Polygons loaded successfully.")

    def transform_polygon_for_pickling(self, polygon):
        """Transform the polygon into a serializable format"""
        serializable_polygon = {
            'p_id': polygon.p_id,
            'points': [],
            'polygon_points': [],  # To store points of QGraphicsPolygonItem
            'lines':[]
        }

        for point in polygon.points:
            x, y, scatter = point
            scatter_state = self.extract_scatter_plot_state(scatter)
            serializable_polygon['points'].append((x, y, scatter_state))

        for line in polygon.lines:
            if isinstance(line, QGraphicsPolygonItem):
                polygon_points = [line.polygon() for line in polygon.lines]
                serializable_polygon['polygon_points'] = [[(point.x(), point.y()) for point in poly] for poly in polygon_points]
            else:
                # Assuming lines are stored as tuples of data points (x1, y1, x2, y2)
                serializable_polygon['lines'].append(line.getData())
        return serializable_polygon

    def extract_scatter_plot_state(self, scatter):
        """Extract the state of a scatter plot item"""
        data = scatter.getData()
        symbol = scatter.opts['symbol']
        size = scatter.opts['size']
        z_value = scatter.zValue()
        return {'data': data, 'symbol': symbol, 'size': size, 'z_value': z_value}

    def reconstruct_polygon(self, serializable_polygon):
        """Reconstruct a polygon from a serializable format"""
        polygon = Polygon(serializable_polygon['p_id'])
        for point in serializable_polygon['points']:
            x, y, scatter_state = point
            scatter = self.recreate_scatter_plot(scatter_state)
            polygon.points.append((x, y, scatter))

        for line_data in serializable_polygon['lines']:
            line = PlotDataItem(line_data[0], line_data[1], pen='r')
            polygon.lines.append(line)

        # Reconstruct the QGraphicsPolygonItem using the saved points
        for polygon_points in serializable_polygon['polygon_points']:
            polygon_item = QGraphicsPolygonItem()
            polygon_path = QtGui.QPainterPath()
            if polygon_points:
                polygon_path.moveTo(polygon_points[0][0], polygon_points[0][1])
                for point in polygon_points[1:]:
                    polygon_path.lineTo(point[0], point[1])
                polygon_item.setPolygon(QtGui.QPolygonF(polygon_path.toFillPolygon()))
                polygon_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                polygon.lines.append(polygon_item)
            return polygon

    def recreate_scatter_plot(self, state):
        """Recreate a scatter plot item from a saved state"""
        scatter = ScatterPlotItem(state['data'][0], state['data'][1], symbol=state['symbol'], size=state['size'])
        scatter.setZValue(state['z_value'])
        return scatter

    def plot_polygon_scatter(self, event,k, x, y, x_i, y_i):
        if self.p_id in self.polygons[self.main_window.sample_id]:
            points = self.polygons[self.main_window.sample_id][self.p_id].points
            print('p')
        self.array_x = self.main_window.array.shape[1]
        self.array_y = self.main_window.array.shape[0]
        # turn off profile (need to suppress context menu on right click)
        if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyCreate.isChecked():
            self.main_window.toolButtonPolyCreate.setChecked(False)
            self.main_window.toolButtonPolyMovePoint.setEnabled(True)

            # Finalize and draw the polygon
            self.show_polygon_lines(x,y, complete = True)
            # Enable filter and polygon actions
            self.main_window.actionClearFilters.setEnabled(True)
            self.main_window.actionPolygonMask.setEnabled(True)
            self.main_window.actionPolygonMask.setChecked(True)
            # apply polygon filter
            self.main_window.apply_filters(fullmap=False)
            return
        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyMovePoint.isChecked():
            self.main_window.toolButtonPolyMovePoint.setChecked(False)
            self.main_window.point_selected = False
            return

        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyAddPoint.isChecked():
            self.main_window.toolButtonPolyAddPoint.setChecked(False)
            return

        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyRemovePoint.isChecked():
            self.main_window.toolButtonPolyRemovePoint.setChecked(False)
            return
        elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
            return

        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyMovePoint.isChecked():
            # move point
            selection_model = self.main_window.tableWidgetPolyPoints.selectionModel()

            # Check if there is any selection
            if selection_model.hasSelection():
                selected_rows = selection_model.selectedRows()
                if selected_rows:
                    # Assuming you're interested in the first selected row
                    first_selected_row = selected_rows[0].row()

                    # Get the item in the first column of this row
                    item = self.main_window.tableWidgetPolyPoints.item(first_selected_row, 0)

                    # Check if the item is not None
                    if item is not None:
                        self.p_id = int(item.text())  # Get polygon id to move point

                    else:
                        QMessageBox.warning(self.main_window, "Selection Error", "No item found in the first column of the selected row.")
                else:
                    QMessageBox.warning(self.main_window, "Selection Error", "No row is selected.")
            else:
                QMessageBox.warning(self.main_window, "Selection Error", "No selection is made in the table.")


            if self.main_window.point_selected:
                #remove selected point
                prev_scatter = points[self.point_index][2]
                self.main_window.plot.removeItem(prev_scatter)


                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                self.main_window.plot.addItem(scatter)


                #update self.point_index index of self.polygons[self.main_window.sample_id]with new point data

                points[self.point_index] = (x,y, scatter)

                # Finalize and draw the polygon
                self.show_polygon_lines(x,y, complete = True)

                self.main_window.point_selected = False
                #update plot and table widget
                # self.update_table_widget()
            else:
                # find nearest profile point
                mindist = 10**12
                for i, (x_p,y_p,_) in enumerate(points):
                    dist = (x_p - x)**2 + (y_p - y)**2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if (round(mindist*self.array_x/self.main_window.x_range) < 50):
                    self.main_window.point_selected = True


        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyAddPoint.isChecked():
            # add point
            # user must first choose line of polygon
            # choose the vertext points to add point based on line
            # Find the closest line segment to the click location
            min_distance = float('inf')
            insert_after_index = None
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]  # Loop back to the start for the last segment
                dist = self.distance_to_line_segment(x, y, p1[0], p1[1], p2[0], p2[1])
                if dist < min_distance:
                    min_distance = dist
                    insert_after_index = i

            # Insert the new point after the closest line segment
            if insert_after_index is not None:
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                self.main_window.plot.addItem(scatter)
                points.insert(insert_after_index + 1, (x, y, scatter))

            # Redraw the polygon with the new point
            self.show_polygon_lines(x, y, complete=True)

        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyRemovePoint.isChecked():
            # remove point
            # draw polygon without selected point
            # remove point
            # Find the closest point to the click location
            min_distance = float('inf')
            point_to_remove_index = None
            for i, (px, py, _) in enumerate(points.points):
                dist = ((px - x)**2 + (py - y)**2)**0.5
                if dist < min_distance:
                    min_distance = dist
                    point_to_remove_index = i

            # Remove the closest point
            if point_to_remove_index is not None:
                _, _, scatter_item = points.pop(point_to_remove_index)
                self.main_window.plot.removeItem(scatter_item)

            # Redraw the polygon without the removed point
            self.show_polygon_lines(x, y, complete=True)

            self.main_window.toolButtonPolyRemovePoint.setChecked(False)

        elif event.button() == QtCore.Qt.LeftButton:
            # Create a scatter self.main_window.plot item at the clicked position
            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
            scatter.setZValue(1e9)
            self.main_window.plot.addItem(scatter)

            # add x and y to self.polygons[self.main_window.sample_id] dict
            if self.p_id not in self.polygons[self.main_window.sample_id]:
                points = [(x,y, scatter)]

            else:
                points.append((x,y, scatter))

    def distance_to_line_segment(self, px, py, x1, y1, x2, y2):
        """Computes distance to the line segment of a polygon

        Determines the minimum distance from a point (px,py) to a line segment defined by
        the points (x1,y1) and (x2,y2).

        Parameters
        ----------
        px, py : float
            Point used to determine minimum distance
        x1, y1 : float
            Point 1 on a line
        x2, y2 : float
            Point 2 on a line

        Returns
        -------
        float
            Minimum distance from point to a line
        """        
        # Calculate the distance from point (px, py) to the line segment defined by points (x1, y1) and (x2, y2)
        # This is a simplified version; you might need a more accurate calculation based on your coordinate system
        return min(((px - x1)**2 + (py - y1)**2)**0.5, ((px - x2)**2 + (py - y2)**2)**0.5)

    def show_polygon_lines(self, x,y, complete = False):
        
        if self.p_id in self.polygons[self.main_window.sample_id]:
            lines = self.polygons[self.main_window.sample_id][self.p_id].lines
            # Remove existing temporary line(s) if any
            for line in lines:
                self.main_window.plot.removeItem(line)
            lines.clear()
            points = self.polygons[self.main_window.sample_id][self.p_id].points
            if len(points) == 1:
                # Draw line from the first point to cursor
                line = PlotDataItem([points[0][0], x], [points[0][1], y], pen='r')
                self.main_window.plot.addItem(line)
                lines.append(line)
            elif not complete and len(points) > 1:

                if self.main_window.point_selected:
                    # self.point_index is the index of the pont that needs to be moved

                    # create polygon with moved point
                    x_points = [p[0] for p in points[:self.point_index]] + [x]+ [p[0] for p in points[(self.point_index+1):]]
                    y_points = [p[1] for p in points[:self.point_index]] + [y]+ [p[1] for p in points[(self.point_index+1):]]

                else:

                    # create polygon with new point
                    x_points = [p[0] for p in points] + [x, points[0][0]]
                    y_points = [p[1] for p in points] + [y, points[0][1]]
                # Draw shaded polygon + lines to cursor
                poly_item = QGraphicsPolygonItem(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in zip(x_points, y_points)]))
                poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                self.main_window.plot.addItem(poly_item)
                lines.append(poly_item)

                # Draw line from last point to cursor
                # line = PlotDataItem([points[-1][0], x], [points[-1][1], y], pen='r')
                # self.main_window.plot.addItem(line)
                # lines.append(line)

            elif complete and len(points) > 2:
                points = [QtCore.QPointF(x, y) for x, y, _ in points]
                polygon = QtGui.QPolygonF(points)
                poly_item = QGraphicsPolygonItem(polygon)
                poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                self.main_window.plot.addItem(poly_item)
                lines.append(poly_item)

                self.update_table_widget()
                # Find the row where the first column matches self.p_id and select it
                for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
                    if item and int(item.text()) == self.p_id:
                        self.main_window.tableWidgetPolyPoints.selectRow(row)
                        break


    def update_table_widget(self):
        """Update the polygon table"""
        if self.main_window.sample_id in self.polygons:
            self.main_window.tableWidgetPolyPoints.clearContents()
            self.main_window.tableWidgetPolyPoints.setRowCount(0)

            for p_id, polygon in self.polygons[self.main_window.sample_id].items():
                row_position = self.main_window.tableWidgetPolyPoints.rowCount()
                self.main_window.tableWidgetPolyPoints.insertRow(row_position)

                self.main_window.tableWidgetPolyPoints.setItem(row_position, 0, QTableWidgetItem(str(p_id)))
                self.main_window.tableWidgetPolyPoints.setItem(row_position, 1, QTableWidgetItem(f'Polygon {p_id}'))
                self.main_window.tableWidgetPolyPoints.setItem(row_position, 2, QTableWidgetItem(str('')))
                self.main_window.tableWidgetPolyPoints.setItem(row_position, 3, QTableWidgetItem('In'))

                checkBox = QCheckBox()
                checkBox.setChecked(True)
                checkBox.stateChanged.connect(lambda: self.main_window.apply_polygon_mask(update_plot=True))
                self.main_window.tableWidgetPolyPoints.setCellWidget(row_position, 4, checkBox)

        self.main_window.apply_polygon_mask(update_plot=False)

    def clear_lines(self):
            if self.p_id in self.polygons[self.main_window.sample_id]:
                # Remove existing temporary line(s) if any
                for line in self.polygons[self.main_window.sample_id][self.p_id].lines:
                    self.main_window.plot.removeItem(line)

    def clear_polygons(self):
        if self.main_window.sample_id in self.polygons:
            self.main_window.tableWidgetPolyPoints.clearContents()
            self.main_window.tableWidgetPolyPoints.setRowCount(0)

            for polygon in self.polygons[self.main_window.sample_id].values():
                for point in polygon.points:
                    _, _, scatter_item = point
                    self.main_window.plot.removeItem(scatter_item)
                for line in polygon.lines:
                    self.main_window.plot.removeItem(line)

            self.polygons[self.main_window.sample_id] = {}
            self.point_index = None             # index for move point
            self.p_id = None           # polygon ID
            self.p_id_gen = 0 #Polygon_id generator

    def plot_existing_polygon(self, plot, p_id= None):
        """Plot the first existing polygon for the current sample ID.

        If there are polygons for the sample ID, select the row in the table widget
        and plot the first polygon with its points and lines.
        """
        sample_id = self.main_window.sample_id

        if sample_id in self.polygons:
            if len(self.polygons[sample_id])>0: #if polygons exist
                if not p_id:
                    # Get the first polygon ID and its corresponding polygon object
                    p_id = next(iter(self.polygons[sample_id]))
                
                polygon = self.polygons[sample_id][p_id]
                

                # Clear any existing selections in the table
                self.main_window.tableWidgetPolyPoints.clearSelection()

                # Find the row where the first column matches the first polygon ID and select it
                for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
                    if item and int(item.text()) == p_id:
                        self.main_window.tableWidgetPolyPoints.selectRow(row)
                        break

                # Plot the points for the polygon
                for x, y, scatter in polygon.points:
                    scatter.setParentItem(None)  # Ensure the scatter is removed from any previous plots
                    scatter.setZValue(1e9)  # Ensure it is drawn on top
                    plot.addItem(scatter)

                # Plot the lines for the polygon
                for line_data in polygon.lines:
                    if isinstance(line_data, QGraphicsPolygonItem):
                        # Re-add the polygon shape to the plot
                        plot.addItem(line_data)
                    else:
                        # Assume line_data is from PlotDataItem or similar and contains (x, y) data
                        line_data = PlotDataItem(line_data[0], line_data[1], pen='r')
                        line_data.setParentItem(None)  # Ensure the line is removed from any previous plots
                        plot.addItem(line_data)

    def view_selected_polygon(self):
        """View the selected polygon when a selection is made in the table widget."""
        sample_id = self.main_window.sample_id

        if sample_id in self.polygons:
            # Get the selected rows in the table widget
            selected_rows = self.main_window.tableWidgetPolyPoints.selectionModel().selectedRows()

            if selected_rows:
                # Assume only one row can be selected at a time for simplicity
                selected_row = selected_rows[0]
                polygon_id_item = self.main_window.tableWidgetPolyPoints.item(selected_row.row(), 0)

                if polygon_id_item:
                    polygon_id = int(polygon_id_item.text())

                    if polygon_id in self.polygons[sample_id]:
                        # Clear the plot before adding the new polygon
                        self.clear_plot()

                        # Plot the selected polygon
                        self.plot_existing_polygon( self.main_window.plot, polygon_id)

    def clear_plot(self):
        """Clear all existing polygons from the plot."""
        for sample_id, polygons in self.polygons.items():
            for polygon in polygons.values():
                for _, _, scatter in polygon.points:
                    self.main_window.plot.removeItem(scatter)
                for line in polygon.lines:
                    self.main_window.plot.removeItem(line)