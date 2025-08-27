import numpy as np
import pandas as pd

class Geochronology():
    def __init__(self, parent=None):

        if parent is None:
            return
        self.parent = parent

    def callback_dating_ratios(self):
        self.callback_dating_method()

    def callback_dating_method(self):
        """Updates isotopes and decay constants when dating method changes.

        Default decay constants are as follows:
        - **Lu-Hf**: :math:`1.867 \\pm 0.008 \\times 10^{-5}` Ma (Sonderlund et al., EPSL, 2004, https://doi.org/10.1016/S0012-821X(04)00012-3)

        - **Re-Os**: :math:`1.666 \\pm 0.005 \\times 10^{-5}` Ma (Selby et al., GCA, 2007, https://doi.org/10.1016/j.gca.2007.01.008)
        """
        data = self.parent.data[self.parent.sample_id].processed

        match self.parent.comboBoxDatingMethod.currentText():
            case "Lu-Hf":
                if self.parent.checkBoxComputeRatios.isChecked():
                    # get list of analytes
                    analyte_list = data.get_attribute('data_type','Analyte')

                    self.parent.labelIsotope1.setText("Lu175")
                    self.parent.comboBoxIsotopeAgeFieldType1.setCurrentText("Analyte")
                    if ("Lu175" in analyte_list) and (self.parent.parent.comboBoxIsotopeAgeFieldType1.currentText() == "Analyte"):
                        self.parent.comboBoxIsotopeAgeField1.setCurrentText("Lu175")

                    self.parent.labelIsotope2.setText("Hf176")
                    self.parent.comboBoxIsotopeAgeFieldType2.setCurrentText("Analyte")
                    if ("Hf176" in analyte_list) and (self.parent.comboBoxIsotopeAgeFieldType2.currentText() == "Analyte"):
                        self.parent.comboBoxIsotopeAgeField2.setCurrentText("Hf176")

                    self.parent.labelIsotope3.setEnabled(True)
                    self.parent.comboBoxIsotopeAgeField3.setEnabled(True)
                    self.parent.labelIsotope3.setText("Hf178")
                    self.parent.comboBoxIsotopeAgeFieldType3.setCurrentText("Analyte")
                    if ("Hf178" in analyte_list) and (self.parent.comboBoxIsotopeAgeFieldType3.currentText() == "Analyte"):
                        self.parent.comboBoxIsotopeAgeField3.setCurrentText("Hf178")
                else:
                    # get list of ratios
                    ratio_list = data.get_attribute('data_type','ratio')

                    self.parent.labelIsotope1.setText("Hf176/Hf178")
                    self.parent.comboBoxIsotopeAgeFieldType1.setCurrentText("Ratio")
                    if ("Hf176/Hf178" in ratio_list) and (self.parent.comboBoxIsotopeAgeFieldType1.currentText() == "Ratio"):
                        self.parent.comboBoxIsotopeAgeField1.setCurrentText("Hf176/Hf178")

                    self.parent.labelIsotope2.setText("Lu175/Hf178")
                    self.parent.comboBoxIsotopeAgeFieldType2.currentText("Ratio")
                    if ("Lu175/Hf178" in ratio_list) and (self.parent.comboBoxIsotopeAgeFieldType2.currentText() == "Ratio"):
                        self.parent.comboBoxIsotopeAgeField2.setCurrentText("Lu175/Hf178")

                    self.parent.labelIsotope3.setText("")
                    self.parent.comboBoxIsotopeAgeFieldType3.currentText("Ratio")
                    self.parent.labelIsotope3.setEnabled(False)
                    self.parent.comboBoxIsotopeAgeFieldType3.setEnabled(False)
                    self.parent.comboBoxIsotopeAgeField3.setEnabled(False)
                    

                # Sonderlund et al., EPSL, 2004, https://doi.org/10.1016/S0012-821X(04)00012-3
                self.parent.lineEditDecayConstant.value = 1.867e-5 # Ma
                self.parent.lineEditDecayConstantUncertainty.value = 0.008e-5 # Ma
            case "Re-Os":
                self.parent.labelIsotope1.setText("Re187")
                if "Re187" in self.parent.analyte_list and self.parent.comboBoxIsotopeAgeFieldType1.currentText() == "Analyte":
                    self.parent.comboBoxIsotopeAgeField1.setCurrentText("Re187")
                self.parent.labelIsotope2.setText("Os187")
                if "Os187" in self.parent.analyte_list and self.parent.comboBoxIsotopeAgeFieldType2.currentText() == "Analyte":
                    self.parent.comboBoxIsotopeAgeField2.setCurrentText("Os187")
                self.parent.labelIsotope3.setText("Os188")
                if "Os188" in self.parent.analyte_list and self.parent.comboBoxIsotopeAgeFieldType3.currentText() == "Analyte":
                    self.parent.comboBoxIsotopeAgeField3.setCurrentText("Os188")

                # Selby et al., GCA, 2007, https://doi.org/10.1016/j.gca.2007.01.008
                self.parent.lineEditDecayConstant.value = 1.666e-5 # Ma
                self.parent.lineEditDecayConstantUncertainty.value = 0.005e-5 # Ma
            case "Sm-Nd":
                pass
            case "Rb-Sr":
                pass
            case "U-Pb":
                pass
            case "Th-Pb":
                pass
            case "Pb-Pb":
                pass

    def scatter_date(self, x, y, y0):

        def slope_only(b):
            def model(A,x):
                return A[0]*x + b
            return model

        linear = odr.Model(slope_only(y0))
        data = odr.RealData(x,y)
        myodr = odr.ODR(data, linear, beta0=[1])
        myoutput = myodr.run()
        myoutput.pprint()


    def compute_date_map(self):
        """Compute one of several date maps"""
        decay_constant = self.parent.lineEditDecayConstant.value
        method = self.parent.comboBoxDatingMethod.currentText()
        match method:
            case "Lu-Hf":
                if self.parent.checkBoxComputeRatios.isChecked():
                    try:
                        Lu175 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField1.currentText(), self.parent.comboBoxIsotopeAgeFieldType1.currentText())
                        Hf176 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField2.currentText(), self.parent.comboBoxIsotopeAgeFieldType2.currentText())
                        Hf178 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField3.currentText(), self.parent.comboBoxIsotopeAgeFieldType3.currentText())

                        Hf176_Hf178 = Hf176['array'].values / Hf178['array'].values
                        Lu175_Hf178 = Lu175['array'].values / Hf178['array'].values
                    except:
                        QMessageBox.warning(self.parent,'Warning','Could not compute ratios, check selected fields.')
                        return
                else:
                    try:
                        Hf176_Hf178 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField1.currentText(), self.parent.comboBoxIsotopeAgeFieldType1.currentText())
                        Lu175_Hf178 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField2.currentText(), self.parent.comboBoxIsotopeAgeFieldType2.currentText())
                    except:
                        QMessageBox.warning(self.parent,'Warning','Could not locate ratios, check selected fields.')
                        return

                if self.parent.data[self.parent.sample_id]['computed_data']['Calculated'].empty:
                    self.parent.data[self.parent.sample_id]['computed_data']['Calculated'][['X','Y']] = self.parent.data[self.parent.sample_id]['cropped_raw_data'][['X','Y']]

                try:
                    date_map = np.log((Hf176_Hf178 - 3.55)/Lu175_Hf178 + 1) / decay_constant 
                except:
                    QMessageBox.warning(self.parent,'Error','Something went wrong. Could not compute date map.')

            case "Re-Os":
                pass

        # save date_map to Calculated dataframe
        self.parent.data[self.parent.sample_id]['computed_data']['Calculated'].loc[self.parent.data[self.parent.sample_id]['mask'],method] = date_map
        
        # update styles and plot
        self.parent.comboBoxColorByField.setCurrentText('Calculated')
        self.parent.color_by_field_callback()
        self.parent.comboBoxColorField.setCurrentText(method)
        self.parent.color_field_callback()
        #self.set_style_widgets(plot_type='field map')

        #self.update_SV()

    def add_ree(self, sample_df):
        """Adds predefined sums of rare earth elements to calculated fields

        Computes four separate sums, LREE, MREE, HREE, and REE.  Elements not analyzed are igorned by the sum.

        * ``lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']``
        * ``mree = ['sm', 'eu', 'gd']``
        * ``hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']``

        Parameters
        ----------
        sample_df : pandas.DataFrame
            Sample data
        
        Returns
        -------
        pandas.DataFrame
            REE dataframe
        """

        lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']
        mree = ['sm', 'eu', 'gd']
        hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']

        # Convert column names to lowercase and filter based on lree, hree, etc. lists
        lree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in lree])]
        hree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in hree])]
        mree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in mree])]
        ree_cols = lree_cols + hree_cols

        # Sum up the values for each row
        ree_df = pd.DataFrame(index=sample_df.index)
        ree_df['LREE'] = sample_df[lree_cols].sum(axis=1)
        ree_df['HREE'] = sample_df[hree_cols].sum(axis=1)
        ree_df['MREE'] = sample_df[mree_cols].sum(axis=1)
        ree_df['REE'] = sample_df[ree_cols].sum(axis=1)

        return ree_df