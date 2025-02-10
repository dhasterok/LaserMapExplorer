        # empty action command
        self.action_ = QAction("", toolbar)
        icon_ = QIcon(":/resources/icons/icon--64.svg")
        self.action_.setIcon(icon_)
        self.action_.setToolTip("")
        self.action_.triggered.connect(self.)

