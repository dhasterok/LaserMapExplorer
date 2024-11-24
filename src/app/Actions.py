class Actions:
    def __init__(self, parent):
        self.parent = parent

        parent.actionFullMap.triggered.connect(self.reset_to_full_view)
        parent.actionFullMap.triggered.connect(lambda: parent.actionCrop.setChecked(False))
        parent.actionFullMap.setEnabled(False)

    def reset_to_full_view(self):
        """Reset the map to full view (i.e., remove crop)

        Executes on ``MainWindow.actionFullMap`` is clicked.
        """

        sample_id = self.parent.sample_id
        #set original bounds
        
        #remove crop overlays
        self.crop_tool.remove_overlays()

        self.data[sample_id].reset_crop()
        
        # reapply existing filters
        if self.parent.actionFilterToggle.isChecked():
            self.parent.apply_field_filters(update_plot=False)
            # should look for filters built on computed fields and remove them
        if self.parent.actionPolygonMask.isChecked():
            self.parent.apply_polygon_mask(update_plot=False)

        # reset cluster mask (no valid clustering exists)
        self.parent.actionClusterMask.setEnabled(False)
        self.parent.actionClusterMask.setChecked(False)
        self.parent.data[sample_id].cluster_mask = np.ones_like(self.parent.data[sample_id].mask, dtype=bool)

        self.apply_filters(fullmap=False)

        self.parent.data[self.sample_id].crop = False