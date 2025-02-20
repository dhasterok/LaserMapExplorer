from src.common.ExtendedDF import AttributeDataFrame

class UIFieldLogic():
    """Methods associated with fields and field type, specifically comboboxes

    Parameters
    ----------
    data : AttributeDataFrame, optional
        Initializes data frame, defaults to None
    """        
    def __init__(self, data=None):
        self.data = data

    def update_data(self, data):
        """Updates the data

        Parameters
        ----------
        data : AttributeDataFrame
            New data frame
        """        
        if not ((data is None) and (not isinstance(data, AttributeDataFrame))):
            raise TypeError("data should be an AttributeDataFrame")
        self.data = data

    # -------------------------------------
    # Field type and field combobox pairs
    # -------------------------------------
    # updates field type comboboxes for analyses and plotting
    def update_field_type_combobox(self, comboBox, addNone=False, plot_type=''):
        """Updates field type combobox
        
        Used to update ``MainWindow.comboBoxHistFieldType``, ``MainWindow.comboBoxFilterFieldType``,
        ``MainWindow.comboBoxFieldTypeX``, ``MainWindow.comboBoxFieldTypeY``,
        ``MainWindow.comboBoxFieldTypeZ``, and ``MainWindow.comboBoxColorByField``

        Parameters
        ----------
        combobox : QComboBox
            The combobox to update.
        addNone : bool
            Adds ``None`` to the top of the ``combobox`` list
        plot_type : str
            The plot type helps to define the set of field types available, by default ``''`` (no change)
        """
        data_type_dict = self.data.get_attribute_dict('data_type')

        match plot_type.lower():
            case 'correlation' | 'histogram' | 'tec':
                if 'cluster' in data_type_dict:
                    field_list = ['cluster']
                else:
                    field_list = []
            case 'cluster score':
                if 'cluster score' in data_type_dict:
                    field_list = ['cluster score']
                else:
                    field_list = []
            case 'cluster':
                if 'cluster' in data_type_dict:
                    field_list = ['cluster']
                else:
                    field_list = ['cluster score']
            case 'cluster performance':
                field_list = []
            case 'pca score':
                if 'pca score' in data_type_dict:
                    field_list = ['PCA score']
                else:
                    field_list = []
            case 'ternary map':
                field_list = []
            case _:
                field_list = ['Analyte', 'Analyte (normalized)']

                # add check for ratios
                if 'ratio' in data_type_dict:
                    field_list.append('Ratio')
                    field_list.append('Ratio (normalized)')

                if 'pca score' in data_type_dict:
                    field_list.append('PCA score')

                if 'cluster' in data_type_dict:
                    field_list.append('Cluster')

                if 'cluster score' in data_type_dict:
                    field_list.append('Cluster score')

        # add None to list?
        if addNone:
            field_list.insert(0, 'None')

        # clear comboBox items
        comboBox.clear()
        # add new items
        comboBox.addItems(field_list)

        # ----start debugging----
        # print('update_field_type_combobox: '+plot_type+',  '+comboBox.currentText())
    # ----end debugging----

    # updates field comboboxes for analysis and plotting
    def update_field_combobox(self, parentBox, childBox):
        """Updates comboBoxes with fields for plots or analysis

        Updates lists of fields in comboBoxes that are used to generate plots or used for analysis.
        Calls ``MainWindow.get_field_list()`` to construct the list.

        Parameters
        ----------
        parentBox : QComboBox, None
            ComboBox used to select field type ('Analyte', 'Analyte (normalized)', 'Ratio', etc.), if None, then 'Analyte'

        childBox : QComboBox
            ComboBox with list of field values
        """
        if self.data is None:
            return

        if parentBox is None:
            fields = self.get_field_list('Analyte')
        else:
            fields = self.get_field_list(set_name=parentBox.currentText())

        childBox.clear()
        childBox.addItems(fields)

        # ----start debugging----
        # if parentBox is not None:
        #     print('update_field_combobox: '+parentBox.currentText())
        # else:
        #     print('update_field_combobox: None')
        # print(fields)
        # ----end debugging----

        # get a named list of current fields for sample

    # gets the set of fields
    def get_field_list(self, set_name='Analyte', filter='all'):
        """Gets the fields associated with a defined set

        Set names are consistent with QComboBox.

        Parameters
        ----------
        set_name : str, optional
            name of set list, options include ``Analyte``, ``Analyte (normalized)``, ``Ratio``, ``Calcualated Field``,
            ``PCA Score``, ``Cluster``, ``Cluster Score``, ``Special``, Defaults to ``Analyte``
        filter : str, optional
            Optionally filters data to columns selected for analysis, options are ``'all'`` and ``'used'``,
            by default `'all'`

        Returns
        -------
        list
            Set_fields, a list of fields within the input set
        """
        if self.data is None:
            return

        if filter not in ['all', 'used']:
            raise ValueError("filter must be 'all' or 'used'.")

        match set_name:
            case 'Analyte' | 'Analyte (normalized)':
                if filter == 'used':
                    set_fields = self.data.match_attributes({'data_type': 'analyte', 'use': True})
                else:
                    set_fields = self.data.match_attribute('data_type', 'analyte')
            case 'Ratio' | 'Ratio (normalized)':
                if filter == 'used':
                    set_fields = self.data.match_attributes({'data_type': 'ratio', 'use': True})
                else:
                    set_fields = self.data.match_attribute('data_type', 'ratio')
            case 'None':
                return []
            case _:
                set_fields = self.data.match_attribute('data_type', set_name.lower())

        return set_fields    