import numpy as np
from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import (
        QWidget, QGroupBox, QFormLayout, QVBoxLayout, QHBoxLayout, QScrollArea,
        QTableWidget, QTableWidgetItem, QHeaderView,
        QComboBox, QCheckBox, QLabel, QPushButton, QSpinBox,
        QMessageBox,
    )
from lame_core.CustomWidgets import CustomDockWidget, CustomLineEdit
from lame_core.UITheme import default_font
from src.common.Logger import auto_log_methods
from src.common import RegressionModel as rm

# Not built (see plan): interactive lasso/rubber-band point selection directly
# on the scatter canvas. Point filtering here is limited to the existing
# global data mask (applied automatically upstream) plus the outlier
# detection/filter controls below.


@auto_log_methods(logger_key='Regression')
class RegressionDock(CustomDockWidget):
    """Regression analysis tool for the currently displayed scatter/heatmap biplot.

    Fits a model (linear, polynomial, exponential, logarithmic) to the (x, y)
    data of whichever biplot is currently shown on ``MainWindow.mpl_canvas``,
    using ordinary least squares or total-least-squares/Deming regression,
    and overlays the fit curve, equation, and stats on that plot.
    """
    MODEL_ITEMS = ['Linear', 'Polynomial', 'Exponential', 'Logarithmic']
    METHOD_ITEMS = ['Least Squares', 'Total Least Squares', 'Deming']
    OUTLIER_ITEMS = ['Z-score', 'IQR', "Cook's Distance"]

    _MODEL_KEY = {'Linear': 'linear', 'Polynomial': 'polynomial', 'Exponential': 'exponential', 'Logarithmic': 'logarithmic'}
    _METHOD_KEY = {'Least Squares': 'ols', 'Total Least Squares': 'tls', 'Deming': 'deming'}
    _OUTLIER_KEY = {'Z-score': 'zscore', 'IQR': 'iqr', "Cook's Distance": 'cooks_distance'}

    FIT_LINE_COLOR = '#d62728'
    OUTLIER_COLOR = '#7f7f7f'

    def __init__(self, parent=None):
        # Set before super().__init__() -- CustomDockWidget.__init__() calls
        # self.show(), which synchronously fires showEvent() (overridden
        # below to read self.main_window) before this constructor resumes.
        self.main_window = parent
        self._overlay_artists = []
        self._last_canvas = None

        super().__init__(parent)

        if parent is None:
            return

        self.logger_key = 'Regression'

        self.setWindowTitle("Regression Analysis")

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        main_layout = QVBoxLayout()
        container.setLayout(main_layout)
        scroll_area.setWidget(container)
        self.setWidget(scroll_area)

        main_layout.addWidget(self._build_model_group())
        main_layout.addWidget(self._build_outlier_group())
        main_layout.addWidget(self._build_cluster_group())
        main_layout.addWidget(self._build_annotation_group())

        self.buttonRunRegression = QPushButton("Run Regression")
        self.buttonRunRegression.setFont(default_font())
        self.buttonRunRegression.clicked.connect(self.run_regression)
        main_layout.addWidget(self.buttonRunRegression)

        self.labelStatus = QLabel("")
        self.labelStatus.setWordWrap(True)
        main_layout.addWidget(self.labelStatus)

        main_layout.addWidget(self._build_leverage_group())

        self.comboBoxRegressionType.currentTextChanged.connect(self._update_control_states)
        self.comboBoxRegressionMethod.currentTextChanged.connect(self._update_control_states)
        self.checkBoxEnableOutlierDetection.toggled.connect(self._update_control_states)
        self.checkBoxFixedSlope.toggled.connect(self._update_control_states)
        self.checkBoxFixedIntercept.toggled.connect(self._update_control_states)
        self._update_control_states()

        self.setGeometry(QRect(0, 0, 300, 640))
        self.setObjectName("RegressionDock")

    # -------------------------------------
    # UI construction
    # -------------------------------------
    def _build_model_group(self):
        regression_group = QGroupBox("Regression Options")
        regression_layout = QFormLayout()
        regression_group.setLayout(regression_layout)

        self.comboBoxRegressionType = QComboBox()
        self.comboBoxRegressionType.setFont(default_font())
        self.comboBoxRegressionType.addItems(self.MODEL_ITEMS)
        regression_layout.addRow(QLabel("Model Type:"), self.comboBoxRegressionType)

        self.spinBoxDegree = QSpinBox()
        self.spinBoxDegree.setRange(2, 8)
        self.spinBoxDegree.setValue(2)
        self.spinBoxDegree.setToolTip("Polynomial degree")
        regression_layout.addRow(QLabel("Degree:"), self.spinBoxDegree)

        self.comboBoxRegressionMethod = QComboBox()
        self.comboBoxRegressionMethod.setFont(default_font())
        self.comboBoxRegressionMethod.addItems(self.METHOD_ITEMS)
        self.comboBoxRegressionMethod.setCurrentText('Total Least Squares')
        regression_layout.addRow(QLabel("Regression Method:"), self.comboBoxRegressionMethod)

        self.lineEditDelta = CustomLineEdit(value=1.0, precision=4)
        self.lineEditDelta.setToolTip(
            "Deming variance ratio sigma_y^2/sigma_x^2, used only when per-point\n"
            "uncertainties are unavailable for the plotted fields (defaults to 1,\n"
            "equivalent to unweighted total least squares)."
        )
        regression_layout.addRow(QLabel("Deming delta:"), self.lineEditDelta)

        self.checkBoxFixedIntercept = QCheckBox("Fix intercept")
        self.lineEditFixedIntercept = CustomLineEdit(value=0.0, precision=6)
        row = QHBoxLayout()
        row.addWidget(self.checkBoxFixedIntercept)
        row.addWidget(self.lineEditFixedIntercept)
        regression_layout.addRow(row)

        self.checkBoxFixedSlope = QCheckBox("Fix slope")
        self.lineEditFixedSlope = CustomLineEdit(value=1.0, precision=6)
        row2 = QHBoxLayout()
        row2.addWidget(self.checkBoxFixedSlope)
        row2.addWidget(self.lineEditFixedSlope)
        regression_layout.addRow(row2)

        return regression_group

    def _build_outlier_group(self):
        outlier_group = QGroupBox("Outlier Detection")
        outlier_layout = QFormLayout()
        outlier_group.setLayout(outlier_layout)

        self.checkBoxEnableOutlierDetection = QCheckBox("Enable Outlier Detection")
        self.checkBoxEnableOutlierDetection.setFont(default_font())
        outlier_layout.addRow(self.checkBoxEnableOutlierDetection)

        self.comboBoxOutlierMethod = QComboBox()
        self.comboBoxOutlierMethod.setFont(default_font())
        self.comboBoxOutlierMethod.addItems(self.OUTLIER_ITEMS)
        outlier_layout.addRow(QLabel("Method:"), self.comboBoxOutlierMethod)

        self.lineEditOutlierThreshold = CustomLineEdit(value=2.0, precision=4)
        self.lineEditOutlierThreshold.setToolTip(
            "Z-score: |z| threshold. IQR: multiplier on the interquartile range.\n"
            "Cook's distance: threshold on D (commonly ~4/n)."
        )
        outlier_layout.addRow(QLabel("Threshold:"), self.lineEditOutlierThreshold)

        self.checkBoxFilterOutliers = QCheckBox("Exclude and refit")
        self.checkBoxFilterOutliers.setFont(default_font())
        outlier_layout.addRow(self.checkBoxFilterOutliers)

        return outlier_group

    def _build_cluster_group(self):
        cluster_group = QGroupBox("Per-Cluster Regression")
        cluster_layout = QVBoxLayout()
        cluster_group.setLayout(cluster_layout)

        self.checkBoxPerCluster = QCheckBox("Fit each cluster separately")
        self.checkBoxPerCluster.setFont(default_font())
        self.checkBoxPerCluster.setEnabled(False)
        self.checkBoxPerCluster.setToolTip(
            "Enabled when the current plot is colored by a cluster field."
        )
        cluster_layout.addWidget(self.checkBoxPerCluster)

        return cluster_group

    def _build_annotation_group(self):
        annotation_group = QGroupBox("Annotations")
        annotation_layout = QVBoxLayout()
        annotation_group.setLayout(annotation_layout)

        self.checkBoxShowEquation = QCheckBox("Show equation")
        self.checkBoxShowEquation.setChecked(True)
        self.checkBoxShowStats = QCheckBox("Show stats (n, R²)")
        self.checkBoxShowStats.setChecked(True)
        annotation_layout.addWidget(self.checkBoxShowEquation)
        annotation_layout.addWidget(self.checkBoxShowStats)

        return annotation_group

    def _build_leverage_group(self):
        leverage_group = QGroupBox("Leverage / Influence")
        leverage_layout = QVBoxLayout()
        leverage_group.setLayout(leverage_layout)

        self.tableLeverage = QTableWidget(0, 4)
        self.tableLeverage.setHorizontalHeaderLabels(['Cluster', 'x', 'y', 'Influence'])
        self.tableLeverage.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableLeverage.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        leverage_layout.addWidget(self.tableLeverage)

        return leverage_group

    # -------------------------------------
    # Control enable/disable logic
    # -------------------------------------
    def _update_control_states(self):
        model = self.comboBoxRegressionType.currentText()
        method = self.comboBoxRegressionMethod.currentText()

        self.spinBoxDegree.setEnabled(model == 'Polynomial')

        two_param_model = model in ('Linear', 'Exponential', 'Logarithmic')
        self.checkBoxFixedIntercept.setEnabled(two_param_model)
        self.checkBoxFixedSlope.setEnabled(two_param_model)
        if not two_param_model:
            self.checkBoxFixedIntercept.setChecked(False)
            self.checkBoxFixedSlope.setChecked(False)
        # mutually exclusive
        if self.checkBoxFixedIntercept.isChecked():
            self.checkBoxFixedSlope.setEnabled(False)
        if self.checkBoxFixedSlope.isChecked():
            self.checkBoxFixedIntercept.setEnabled(False)
        self.lineEditFixedIntercept.setEnabled(self.checkBoxFixedIntercept.isChecked())
        self.lineEditFixedSlope.setEnabled(self.checkBoxFixedSlope.isChecked())

        self.lineEditDelta.setEnabled(method == 'Deming')

        outlier_enabled = self.checkBoxEnableOutlierDetection.isChecked()
        self.comboBoxOutlierMethod.setEnabled(outlier_enabled)
        self.lineEditOutlierThreshold.setEnabled(outlier_enabled)
        self.checkBoxFilterOutliers.setEnabled(outlier_enabled)
        # Cook's distance is only defined for OLS
        cooks_idx = self.comboBoxOutlierMethod.findText("Cook's Distance")
        item = self.comboBoxOutlierMethod.model().item(cooks_idx)
        if item is not None:
            item.setEnabled(method == 'Least Squares')
            if method != 'Least Squares' and self.comboBoxOutlierMethod.currentText() == "Cook's Distance":
                self.comboBoxOutlierMethod.setCurrentText('Z-score')

    def sync_to_active_plot(self):
        """Refreshes controls that depend on the currently displayed plot.

        Call when the dock is shown/raised so the per-cluster option reflects
        whatever plot is active at that moment.
        """
        if not hasattr(self, 'checkBoxPerCluster'):
            # UI not built yet (e.g. showEvent fired during construction
            # with parent=None, before the early return in __init__).
            return
        app_data = getattr(self.main_window, 'app_data', None)
        try:
            # c_field_type looks up style_data.style_dict[style_data.plot_type],
            # which raises KeyError before any plot has ever been selected
            # (plot_type == '') -- no plot means no cluster coloring either way.
            is_cluster_colored = bool(app_data) and app_data.c_field_type == 'cluster'
        except (KeyError, AttributeError):
            is_cluster_colored = False
        self.checkBoxPerCluster.setEnabled(is_cluster_colored)
        if not is_cluster_colored:
            self.checkBoxPerCluster.setChecked(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_to_active_plot()

    # -------------------------------------
    # Regression
    # -------------------------------------
    def _active_biplot(self):
        """Returns (canvas, plot_info, x_field, y_field) for the current plot,
        or ``None`` if the current plot isn't a fittable 2-field biplot.
        """
        mw = self.main_window
        plot_info = getattr(mw, 'plot_info', None)
        if not plot_info or plot_info.get('plot_type') not in ('scatter', 'heatmap'):
            return None

        z_field = plot_info.get('field', ['', '', '', ''])[2]
        if z_field not in (None, '', 'none'):
            # ternary plot -- not a 2-D biplot
            return None

        canvas = plot_info.get('figure')
        data = getattr(canvas, 'data', None)
        if canvas is None or data is None or 'x' not in data.columns or 'y' not in data.columns:
            return None

        x_field, y_field = plot_info['field'][0], plot_info['field'][1]
        return canvas, plot_info, x_field, y_field

    def run_regression(self):
        active = self._active_biplot()
        if active is None:
            QMessageBox.warning(self, 'Regression', 'The current plot is not a scatter/heatmap biplot.')
            return
        canvas, plot_info, x_field, y_field = active

        if canvas is not self._last_canvas:
            self._overlay_artists = []
        self._clear_overlay()
        self._last_canvas = canvas

        df = canvas.data
        model = self._MODEL_KEY[self.comboBoxRegressionType.currentText()]
        method = self._METHOD_KEY[self.comboBoxRegressionMethod.currentText()]
        degree = self.spinBoxDegree.value()
        fixed_intercept = self.lineEditFixedIntercept.value if self.checkBoxFixedIntercept.isChecked() else None
        fixed_slope = self.lineEditFixedSlope.value if self.checkBoxFixedSlope.isChecked() else None
        delta = self.lineEditDelta.value

        data = self.main_window.app_data.current_data
        sx = rm.get_uncertainty_vector(data, x_field) if data is not None else None
        sy = rm.get_uncertainty_vector(data, y_field) if data is not None else None

        self.tableLeverage.setRowCount(0)

        try:
            if self.checkBoxPerCluster.isChecked() and 'cluster_group' in df.columns:
                results = self._run_per_cluster(canvas, df, model, method, degree, fixed_slope, fixed_intercept, delta)
            else:
                results = [self._run_single(canvas, df['x'].values, df['y'].values, sx, sy,
                                             model, method, degree, fixed_slope, fixed_intercept, delta,
                                             color=self.FIT_LINE_COLOR, label=None)]
        except Exception as exc:
            self.labelStatus.setText(f"Fit failed: {exc}")
            canvas.draw_idle()
            return

        n_flagged = sum(r['n_flagged'] for r in results if r is not None)
        n_total = sum(r['n'] for r in results if r is not None)
        self.labelStatus.setText(f"Fit on {n_total} point(s); {n_flagged} flagged as outliers.")

        canvas.draw_idle()

    def _run_single(self, canvas, x, y, sx, sy, model, method, degree,
                     fixed_slope, fixed_intercept, delta, color, label):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        if model == 'logarithmic':
            mask &= x > 0
        if model == 'exponential':
            mask &= y > 0
        x, y = x[mask], y[mask]
        sxm = sx[mask] if sx is not None and len(sx) == len(mask) else None
        sym = sy[mask] if sy is not None and len(sy) == len(mask) else None

        result = rm.fit_regression(x, y, sx=sxm, sy=sym, model=model, method=method,
                                    degree=degree, fixed_slope=fixed_slope,
                                    fixed_intercept=fixed_intercept, delta=delta)

        outlier_mask = np.zeros(len(x), dtype=bool)
        if self.checkBoxEnableOutlierDetection.isChecked():
            outlier_method = self._OUTLIER_KEY[self.comboBoxOutlierMethod.currentText()]
            threshold = self.lineEditOutlierThreshold.value
            if outlier_method == 'cooks_distance' and result.cooks_distance is not None:
                outlier_mask = rm.detect_outliers(result.cooks_distance, method='cooks_distance', threshold=threshold)
            else:
                outlier_mask = rm.detect_outliers(result.residuals, method=outlier_method if outlier_method != 'cooks_distance' else 'zscore', threshold=threshold)

            if self.checkBoxFilterOutliers.isChecked() and outlier_mask.any():
                keep = ~outlier_mask
                x, y = x[keep], y[keep]
                sxm = sxm[keep] if sxm is not None else None
                sym = sym[keep] if sym is not None else None
                result = rm.fit_regression(x, y, sx=sxm, sy=sym, model=model, method=method,
                                            degree=degree, fixed_slope=fixed_slope,
                                            fixed_intercept=fixed_intercept, delta=delta)
                outlier_mask = np.zeros(len(x), dtype=bool)

        self._draw_fit(canvas, x, result, color, label)
        if outlier_mask.any():
            artist = canvas.axes.scatter(x[outlier_mask], y[outlier_mask], facecolors='none',
                                          edgecolors=self.OUTLIER_COLOR, s=80, linewidths=1.2, zorder=6)
            self._overlay_artists.append(artist)

        influence = result.leverage if result.leverage is not None else result.orthogonal_residual
        self._add_leverage_rows(label or '', x, y, influence)

        return {'result': result, 'n': len(x), 'n_flagged': int(outlier_mask.sum())}

    def _run_per_cluster(self, canvas, df, model, method, degree, fixed_slope, fixed_intercept, delta):
        app_data = self.main_window.app_data
        style_data = self.main_window.style_data
        cluster_method = app_data.c_field
        cluster_dict = app_data.cluster_dict.get(cluster_method)
        if not cluster_dict:
            return []

        cluster_color, cluster_label, _ = style_data.get_cluster_colormap(cluster_dict, alpha=style_data.marker_alpha)
        n = cluster_dict['n_clusters']
        color_map = {i: cluster_color[i] for i in range(n)}
        label_map = {i: cluster_label[i] for i in range(n)}
        if 99 in cluster_dict:
            color_map[99] = cluster_color[-1]
            label_map[99] = cluster_label[-1]

        results = []
        for cluster_val in sorted(df['cluster_group'].unique()):
            sub = df[df['cluster_group'] == cluster_val]
            if len(sub) < 3:
                continue
            cluster_key = int(cluster_val)
            color = color_map.get(cluster_key, self.FIT_LINE_COLOR)
            label = label_map.get(cluster_key, str(cluster_key))
            try:
                r = self._run_single(canvas, sub['x'].values, sub['y'].values, None, None,
                                      model, method, degree, fixed_slope, fixed_intercept, delta,
                                      color=color, label=label)
                results.append(r)
            except Exception:
                continue
        return results

    def _draw_fit(self, canvas, x, result, color, label):
        xmin, xmax = float(np.min(x)), float(np.max(x))
        if result.model == 'logarithmic':
            xmin = max(xmin, np.min(x[x > 0]) if np.any(x > 0) else xmin)
        xs = np.linspace(xmin, xmax, 200)
        ys = result.predict(xs)

        line, = canvas.axes.plot(xs, ys, color=color, linewidth=1.8, zorder=5)
        self._overlay_artists.append(line)

        text_lines = []
        if self.checkBoxShowEquation.isChecked():
            text_lines.append(result.equation_str)
        if self.checkBoxShowStats.isChecked():
            text_lines.append(f"n={result.n}, R²={result.r_squared:.4f}")
        if label:
            text_lines.insert(0, label)

        if text_lines:
            # stack successive cluster annotations down the left edge of the axes
            y_pos = 0.95 - 0.10 * sum(1 for a in self._overlay_artists if getattr(a, '_regression_annotation', False))
            txt = canvas.axes.text(0.03, y_pos, "\n".join(text_lines), transform=canvas.axes.transAxes,
                                    fontsize=8, va='top', ha='left', color=color,
                                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.6, edgecolor=color))
            txt._regression_annotation = True
            self._overlay_artists.append(txt)

    def _add_leverage_rows(self, cluster_label, x, y, influence):
        if influence is None or len(influence) == 0:
            return
        threshold = 2 * np.mean(influence) if np.mean(influence) > 0 else np.inf
        flagged = np.where(influence > threshold)[0]
        # cap the table so a bad fit can't flood it
        flagged = flagged[np.argsort(-influence[flagged])][:25]
        for i in flagged:
            row = self.tableLeverage.rowCount()
            self.tableLeverage.insertRow(row)
            self.tableLeverage.setItem(row, 0, QTableWidgetItem(str(cluster_label)))
            self.tableLeverage.setItem(row, 1, QTableWidgetItem(f"{x[i]:.4g}"))
            self.tableLeverage.setItem(row, 2, QTableWidgetItem(f"{y[i]:.4g}"))
            self.tableLeverage.setItem(row, 3, QTableWidgetItem(f"{influence[i]:.4g}"))

    def _clear_overlay(self):
        for artist in self._overlay_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._overlay_artists = []
