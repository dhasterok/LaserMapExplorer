import * as Blockly from 'blockly/core';
import * as BlockDynamicConnection from '@blockly/block-dynamic-connection';
import {registerFieldColour, FieldColour} from '@blockly/field-colour';
registerFieldColour();
import { sample_ids,fieldTypeList, baseDir } from './globals';
import {updateFieldDropdown,updateFieldTypeDropdown,addDefaultStylingBlocks,updateStylingChain, updateHistogramOptions, isBlockInChain, listSelectorChanged, updateNDimListDropdown, updateSavePlotPreview,setDefaultSaveDir } from './helper_functions'
var enableSampleIDsBlock = false; // Initially false
window.Blockly = Blockly.Blocks

/*
Summary of Naming Conventions:
Field Names: Camel case (plotType).
Variable Names (js): Camel case (plotType).
Block Type Names: Snake case (set_plot_type).
Block Input Names: Snake case (set_plot_type).
*/


// ---- Display figures (x : top & bottom) ----
const display_figure = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Display figures')
      .appendField(new Blockly.FieldCheckbox('TRUE'), 'SHOW');

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(285);
    this.setTooltip('When enabled, plots open in a modal dialog with Continue/Stop/Skip controls.');
    this.setHelpUrl('');
  }
};
Blockly.common.defineBlocks({ display_figure });


//// File I/O //// 
const load_directory = {
    init: function() {
        this.appendValueInput('DIR')
            .setCheck('String')
            .appendField('load files from directory')
            .appendField(new Blockly.FieldTextInput('directory path'), 'DIR');
        this.setNextStatement(true, null);
        this.setTooltip('Loads files from a directory');
        this.setHelpUrl('');
        this.setColour(60);
    }
};
Blockly.Blocks['load_directory'] = load_directory;

const load_sample = {
    init: function() {
        this.appendValueInput('DIR')
            .setCheck('String')
            .appendField('load sample from directory')
            .appendField(new Blockly.FieldTextInput('file path'), 'DIR');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Loads files from a directory');
        this.setHelpUrl('');
        this.setColour(60);
    }
};
Blockly.Blocks['load_sample'] = load_sample;

/*
const sample_ids_list_block = {
    init: function() {
        this.appendDummyInput().appendField("sample IDs list");
        this.setOutput(true, "Array");  // Outputs an array
        this.setColour(230);
        this.setTooltip('Represents a list of sample IDs');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};
Blockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;
*/

//// Samples and Fields /////

// Function to enable the block
export function enableSampleIDsBlockFunction() {
    let workspace = Blockly.getMainWorkspace()
    enableSampleIDsBlock = true;

    // Re-register the block definition
    //Blockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;
    Blockly.Blocks['select_samples'] = select_samples;
    Blockly.Blocks['loop_over_samples'] = loop_over_samples;
    Blockly.Blocks['loop_over_fields'] = loop_over_fields;
    // Refresh the toolbox
    workspace.updateToolbox(document.getElementById('toolbox'));
}



const select_samples = {
    init: function() {
        this.appendDummyInput().appendField('Select sample ID').appendField(new Blockly.FieldDropdown(this.getOptions), 'SAMPLE_IDS');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Selects a sample ID');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    },
    getOptions: function() {
        if (!sample_ids.length) {
            return [['No sample IDs available', 'NONE']];
        }
        return sample_ids.map(id => [id, id]);
    },
};
Blockly.Blocks['select_samples'] = select_samples;

 // Block: loop over Sample IDs
 const loop_over_samples = {
    init: function() {
        this.appendDummyInput('NAME')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Loop over samples');
        this.appendDummyInput()
            .appendField("for each sample ID in")
            .appendField(new Blockly.FieldVariable("sample_ids"), "SAMPLE_IDS");

        this.appendStatementInput("DO")
            .appendField("do");

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(180);
        this.setTooltip('Loop over each sample in the provided directory');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};
Blockly.common.defineBlocks({ loop_over_samples: loop_over_samples });

// Block: loop over fields
const loop_over_fields = {
    init: function() {
        this.appendDummyInput('NAME')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Loop over fields');
        this.appendDummyInput()
            .appendField("for each field in")
            .appendField('field type')
            .appendField(new Blockly.FieldDropdown(function() {
                return fieldTypeList;
            }), 'fieldType');
        this.appendStatementInput("DO")
            .appendField("do");

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(60);
        this.setTooltip('Loop over each field in the selected field type');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};


Blockly.common.defineBlocks({ loop_over_fields: loop_over_fields });


Blockly.common.defineBlocks({ 
    select_analytes: {
        init: function() {
            this.appendDummyInput('NAME')
                .setAlign(Blockly.inputs.Align.CENTRE)
                .appendField('Select analytes/ratios');

            // Initialize the analyte selector dropdown
            this.appendDummyInput('SELECTOR')
                .appendField(new Blockly.FieldLabelSerializable('Analyte/Ratio list from'), 'NAME')
                .appendField(new Blockly.FieldDropdown(
                    [
                        ['Analyte selector', 'Analyte selector'],
                        ['Current selection', 'Current selection'],
                        ['Saved lists', 'Saved lists']
                    ]
                ), 'analyteSelectorDropdown');

            // Add the analyte saved lists dropdown, initially hidden
            this.appendDummyInput('SAVED_LISTS')
                .appendField('Saved list')
                .appendField(new Blockly.FieldDropdown([['None', 'None']]), 'analyteSavedListsDropdown')
                .setVisible(false);

            this.setPreviousStatement(true, null);
            this.setNextStatement(true, null);
            this.setTooltip('');
            this.setHelpUrl('');
            this.setColour(180);

            // Use the common validator that calls selectorChanged(...)
            const dropdown = this.getField('analyteSelectorDropdown');
            dropdown.setValidator((newValue) => {
                return listSelectorChanged(newValue, this, 'analyte');
            });
        }
    }
});
Blockly.common.defineBlocks({
  select_field_from_type: {
    init: function () {
      this.appendDummyInput('NAME')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Select fields from field type');

      // Field type dropdown
      this.appendDummyInput('FIELD_TYPE')
        .appendField('Field type')
        .appendField(
          new Blockly.FieldDropdown([['Select...', '']]),
          'fieldType'
        );

      // Field dropdown (with All/None defaults)
      this.appendDummyInput('FIELD')
        .appendField('Field')
        .appendField(
          new Blockly.FieldDropdown([
            ['All', '__ALL__'],
            ['None', '__NONE__'],
            ['Select...', '']
          ]),
          'field'
        );

      this.setPreviousStatement(true, 'custom_field');
      this.setNextStatement(true, 'custom_field');
      this.setColour(180);
      this.setTooltip('Select a field type and specific field(s).');
      this.setHelpUrl('');

      if (!this.isInFlyout) {
        // Dynamically update FieldType list

        updateFieldTypeDropdown(this, 'field map', 'c', 'fieldType', 'field');

        const fieldTypeDropdown = this.getField('fieldType');
        fieldTypeDropdown.setValidator((newValue) => {
            this.argDict = this.argDict || {};
            this.argDict['c_field_type'] = newValue;
            updateFieldDropdown(this, newValue, 'field');
            return newValue;
        });
       const fieldDropdown = this.getField('field');
        fieldDropdown.setValidator((newValue) => {
            this.argDict = this.argDict || {};
            this.argDict['c_field'] = newValue;
            return newValue;
        }); 

      }
    }
  }
});


Blockly.common.defineBlocks({
    select_fields_list: {
        init: function() {
            this.appendDummyInput('NAME')
                .setAlign(Blockly.inputs.Align.CENTRE)
                .appendField('Select fields from');

            // Initialize the field selector dropdown
            this.appendDummyInput('SELECTOR')
                .appendField(new Blockly.FieldLabelSerializable('Field list from'), 'NAME')
                .appendField(new Blockly.FieldDropdown(
                    [
                        ['Field selector', 'Field selector'],
                        ['Current selection', 'Current selection'],
                        ['Saved lists', 'Saved lists']
                    ]
                ), 'fieldSelectorDropdown');

            // Add the field saved lists dropdown, initially hidden
            this.appendDummyInput('SAVED_LISTS')
                .appendField('Saved list')
                .appendField(new Blockly.FieldDropdown([['None', 'None']]), 'fieldSavedListsDropdown')
                .setVisible(false);

            // Restrict connections so this block can only connect to custom_field chains
            this.setPreviousStatement(true, 'custom_field');
            this.setNextStatement(true, 'custom_field');
            this.setTooltip('Select a set of fields from different sources.');
            this.setHelpUrl('');
            this.setColour(180);

            // Use the common validator that calls selectorChanged(...)
            const dropdown = this.getField('fieldSelectorDropdown');
            dropdown.setValidator((newValue) => {
                return listSelectorChanged(newValue, this, 'field');
            });
        }
    }
});

Blockly.common.defineBlocks({
  export_table: {
    init: function() {
      this.appendDummyInput()
            .setAlign(Blockly.inputs.Align.CENTRE)
            .appendField('Export Table');

      // Statement input that can hold select_fields_list or select_field_from_type
      this.appendStatementInput('fields')
          .setCheck(['select_fields_list', 'select_field_from_type'])
          .appendField('Fields to export');

      // So it can be attached to the "exportTable" Value Input in correlation_analysis:
      this.setOutput(true, 'export_table');

      this.setColour(60);
      this.setTooltip('Exports selected fields as a table.');
      this.setHelpUrl('');
    }
  }
});


 // Define the select_analytes block
// Define the select_ref_val block
const select_ref_val = {
  init: function () {
    const block = this;

    block.appendDummyInput('NAME')
      .setAlign(Blockly.inputs.Align.CENTRE)
      .appendField('Select Reference value');

    block.appendDummyInput('refValue')
      .appendField('Ref. value')
      .appendField(new Blockly.FieldDropdown([
        ['bulk silicate Earth [MS95] McD', 'bulk_silicate_earth'],
        ['option 2', 'option_2']
      ]), 'refValueDropdown');

    block.setPreviousStatement(true, null);
    block.setNextStatement(true, null);
    block.setColour(180);

    if (!block.workspace || block.workspace.isFlyout) return;

    // Update options from Python
    window.blocklyBridge?.getRefValueList?.().then((response) => {
      const options = response.map(opt => [opt, opt]);
      const dropdown = block.getField('refValueDropdown');
      if (dropdown && options.length) {
        dropdown.menuGenerator_ = options; // update
        dropdown.setValue(options[0][1]);  // default
        dropdown.forceRerender?.();        // refresh
      }
    }).catch(err => console.error('Error fetching reference list:', err));
  }
};

Blockly.common.defineBlocks({ select_ref_val });


// Define the change_pixel_dimensions block
const change_pixel_dimensions= {
    init: function() {
        this.appendDummyInput()
            .appendField("Set Dimensions");
        this.appendDummyInput()
            .appendField("dx")
            .appendField(new Blockly.FieldNumber(0), "dx");
        this.appendDummyInput()
            .appendField("dy")
            .appendField(new Blockly.FieldNumber(0), "dy");
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(180);
        this.setTooltip("Set the dx and dy dimensions");
        this.setHelpUrl("");

        // Update the default values of dx and dy
        this.updateDimensions();
    },

    updateDimensions: function() {
        var block = this;
        // Call the Python function get_current_dimensions through the WebChannel
        window.blocklyBridge.getCurrentDimensions().then(function(dimensions) {
            var dx = dimensions[0];
            var dy = dimensions[1];
            // Round dx and dy to 4 decimal places
            dx = Number(dx.toFixed(4));
            dy = Number(dy.toFixed(4));
            // Set the field values
            block.setFieldValue(dx, 'dx');
            block.setFieldValue(dy, 'dy');
        }).catch(function(error) {
            console.error('Error fetching dimensions:', error);
        });
    }
};

Blockly.common.defineBlocks({change_pixel_dimensions: change_pixel_dimensions});

const swap_pixel_dimensions= {
    init: function() {
      this.appendDummyInput()
          .appendField("Swap Dimensions dx ↔ dy");
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(180);
      this.setTooltip("Swap the values of dx and dy");
      this.setHelpUrl("");
    }
  };

Blockly.common.defineBlocks({swap_pixel_dimensions: swap_pixel_dimensions});

const swap_x_y= {
    init: function() {
      this.appendDummyInput()
          .appendField("Swap x ↔ y");
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setColour(180);
      this.setTooltip("Swap the values of coordinate axes");
      this.setHelpUrl("");
    }
  };

Blockly.common.defineBlocks({swap_x_y: swap_x_y});

const select_outlier_method = {
    init: function() {
        this.appendDummyInput('NAME')
            .setAlign(Blockly.inputs.Align.CENTRE)
            .appendField('Select outlier method');

        // Initialize the analyte selector dropdown
        this.appendDummyInput('SELECTOR')
            .appendField(new Blockly.FieldLabelSerializable('Outlier method'), 'NAME')
            .appendField(new Blockly.FieldDropdown(
                [['none', 'none'],
                 ['quantile criteria', 'quantile criteria'],
                 ['quantile and distance criteria', 'quantile and distance criteria'],
                 ['Chauvenet criterion', 'chauvenet criterion'],
                 ['log(n>x) inflection', 'log(n>x) inflection']]
            ), 'outlierMethodDropdown');

        // Add the quantile bounds, initially hidden
        this.appendDummyInput('QB')
            .appendField("Quantile bounds")
            .appendField(new Blockly.FieldNumber(0.05), "lB")
            .appendField(new Blockly.FieldNumber(99.5), "uB")
            .setVisible(false);
        // Add the difference bounds, initially hidden
        this.appendDummyInput('DB')
            .appendField("Difference bound")
            .appendField(new Blockly.FieldNumber(99), "dLB")
            .appendField(new Blockly.FieldNumber(99), "dUB")
            .setVisible(false);

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(180);

        // Handle the selection change in analyteSelectorDropdown
        const dropdown = this.getField('outlierMethodDropdown');
        dropdown.setValidator(this.outlierMethodChanged.bind(this));
        // Set initial visibility based on the default selection
        const initialValue = this.getFieldValue('outlierMethodDropdown');
        this.outlierMethodChanged(initialValue);
    },

    outlierMethodChanged: function(newValue) {
        const qbInput = this.getInput('QB');
        const dbInput = this.getInput('DB');

        if (newValue === 'quantile criteria') {
            qbInput.setVisible(true);
            dbInput.setVisible(false);
        } else if (newValue === 'quantile and distance criteria') {
            qbInput.setVisible(true);
            dbInput.setVisible(true);
        } else {
            qbInput.setVisible(false);
            dbInput.setVisible(false);
        }

        // Refresh the block to reflect the visibility change
        this.render();

        return newValue;
    }
};

Blockly.common.defineBlocks({ select_outlier_method: select_outlier_method });

const neg_handling_method = {
    init: function() {
        this.appendDummyInput('NAME')
            .setAlign(Blockly.inputs.Align.CENTRE)
            .appendField('Select negative handling method');

        // Initialize the analyte selector dropdown
        this.appendDummyInput('SELECTOR')
            .appendField(new Blockly.FieldLabelSerializable('Neg. handling method'), 'NAME')
            .appendField(new Blockly.FieldDropdown(
                [['ignore negatives', 'ignore negatives'],
                 ['minimum positive', 'minimum positive'],
                 ['gradual shift', 'gradual shift'],
                 ['Yeo-Johnson transform', 'Yeo-Johnson transform']]
            ), 'negMethodDropdown');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(180);
    }
};
Blockly.common.defineBlocks({ neg_handling_method: neg_handling_method });



// Define the field_select block
const field_select = {
    init: function() {
        // Add a header with centered alignment
        this.appendDummyInput('header')
            .setAlign(Blockly.inputs.Align.CENTRE)
            .appendField('Select fields');

        // Create the 'Field type' dropdown with options
        this.appendDummyInput('NAME')
            .appendField('Field type')
            .appendField(new Blockly.FieldDropdown(
                [
                    ['Analyte', 'Analyte'],
                    ['Analyte (Normalised)', 'Analyte (Normalised)'],
                    ['PCA Score', 'PCA Score'],
                    ['Cluster', 'Cluster']
                ],
                this.updateFieldDropdown.bind(this)  // Bind the update function
            ), 'fieldType');

        // Create the 'field' dropdown, initially empty
        this.appendDummyInput('FIELD')
            .appendField('Field')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'field');

        this.setInputsInline(false);
        this.setTooltip('Select fields for analysis');
        this.setHelpUrl('');
        this.setColour(160);  // Adjust color as needed
        this.setOutput(true, null); 

        // Initialize the 'field' dropdown options based on the default 'fieldType' value
        const initialFieldType = this.getFieldValue('fieldType');
        this.updateFieldDropdown(initialFieldType);
    },

    updateFieldDropdown: function(newValue) {
        const fieldTypeValue = newValue || this.getFieldValue('fieldType');

        // Call the Python function getFieldList through the WebChannel, handle as a promise
        window.blocklyBridge.getFieldList(fieldTypeValue).then((response) => {
            // Map the response to the required format for Blockly dropdowns
            const options = response.map(option => [option, option]);

            // Add 'none' and 'all' options at the beginning
            options.unshift(['all', 'all']);
            options.unshift(['none', 'none']);

            const dropdown = this.getField('field');

            // Update the dropdown options
            dropdown.menuGenerator_ = options;

            // Set the default value to 'Select...' or to the first option if options are available
            if (options.length > 0) {
                dropdown.setValue(options[0][1]);
            } else {
                dropdown.setValue('');
            }

            dropdown.forceRerender();  // Refresh dropdown to display updated options
        }).catch(error => {
            console.error('Error fetching field list:', error);
        });
    }
};

// Register the block with Blockly
Blockly.common.defineBlocks({ field_select: field_select });


const properties = {
    init: function() {
        // Header
        this.appendDummyInput('header')
            .appendField('Properties')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // Reference value selection
        this.appendDummyInput('refValue')
            .appendField('Ref. value')
            .appendField(new Blockly.FieldDropdown([
                ['bulk silicate Earth [MS95] McD', 'bulk_silicate_earth'],
                ['option 2', 'option_2']
            ]), 'refValueDropdown');

        // Data scaling selection
        this.appendDummyInput('dataScaling')
            .appendField('Data scaling')
            .appendField(new Blockly.FieldDropdown([
                ['linear', 'linear'],
                ['logarithmic', 'logarithmic']
            ]), 'dataScalingDropdown');

        // Correlation method selection
        this.appendDummyInput('corrMethod')
            .appendField('Corr. Method')
            .appendField(new Blockly.FieldDropdown([
                ['none', 'none'],
                ['method 1', 'method_1']
            ]), 'corrMethodDropdown')
            .appendField(new Blockly.FieldCheckbox('FALSE'), 'corrMethodCheckbox')
            .appendField('C²');

        // Resolution inputs
        this.appendDummyInput('resolution')
            .appendField('Resolution')
            .appendField(new Blockly.FieldNumber(738, 1), 'Nx')
            .appendField('Nx')
            .appendField(new Blockly.FieldNumber(106, 1), 'Ny')
            .appendField('Ny');

        // Dimensions inputs
        this.appendDummyInput('dimensions')
            .appendField('Dimensions')
            .appendField(new Blockly.FieldNumber(0.9986), 'dx')
            .appendField('dx')
            .appendField(new Blockly.FieldNumber(0.9906), 'dy')
            .appendField('dy');

        // Autoscale settings
        this.appendDummyInput('autoscaleHeader')
            .appendField('Autoscale')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // Show with colormap checkbox
        this.appendDummyInput('showColormap')
            .appendField(new Blockly.FieldCheckbox('TRUE'), 'showColormap')
            .appendField('Show with colormap');

        // Quantile bounds
        this.appendDummyInput('quantileBounds')
            .appendField('Quantile bounds')
            .appendField(new Blockly.FieldNumber(0.05), 'quantileLower')
            .appendField('to')
            .appendField(new Blockly.FieldNumber(99.5), 'quantileUpper');

        // Difference bound
        this.appendDummyInput('differenceBound')
            .appendField('Difference bound')
            .appendField(new Blockly.FieldNumber(0.05), 'diffBoundLower')
            .appendField('to')
            .appendField(new Blockly.FieldNumber(99), 'diffBoundUpper');

        // Negative handling dropdown
        this.appendDummyInput('negativeHandling')
            .appendField('Negative handling')
            .appendField(new Blockly.FieldDropdown([
                ['Ignore negatives', 'ignore_negatives'],
                ['Treat as zero', 'treat_as_zero']
            ]), 'negativeHandlingDropdown');

        // Apply to all analytes checkbox
        this.appendDummyInput('applyAll')
            .appendField(new Blockly.FieldCheckbox('FALSE'), 'applyAll')
            .appendField('Apply to all analytes');

        this.setInputsInline(false);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Configure samples and fields settings.');
        this.setHelpUrl('');
        this.setColour(160);
    }
};

Blockly.common.defineBlocks({ properties: properties });


////  Analysis ////

// heatmap and ternary

// const scatter_and_heatmaps = {
//     init: function() {
//         this.appendDummyInput('header')
//             .appendField('Scatter and Heatmaps')
//             .setAlign(Blockly.inputs.Align.CENTRE)

//         // Biplot and ternary section
//         this.appendDummyInput('biplotHeader')
//             .appendField('Biplot and Ternary')
//             .setAlign(Blockly.inputs.Align.CENTRE);

//         this.appendDummyInput('analyteX')
//             .appendField('Analyte X')
//             .appendField(new Blockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCA Score', 'PCA Score'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteX', 'analyteXType')
//         ), 'analyteXType')
//             .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'analyteX');

//         this.appendDummyInput('analyteY')
//             .appendField('Analyte Y')
//             .appendField(new Blockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCA Score', 'PCA Score'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteY', 'analyteYType')), 'analyteYType')
//             .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'analyteY');

//         this.appendDummyInput('analyteZ')
//             .appendField('Analyte Z')
//             .appendField(new Blockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCA Score', 'PCA Score'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteZ', 'analyteZType')), 'analyteZType')
//             .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'analyteZ');

//         this.appendDummyInput('preset')
//             .appendField('Preset')
//             .appendField(new Blockly.FieldDropdown([['Select preset', 'default'], ['Custom preset', 'custom']]), 'preset');

//         this.appendDummyInput('heatmaps')
//             .appendField('Heatmaps')
//             .appendField(new Blockly.FieldDropdown([['counts', 'counts'], ['counts, median', 'counts, median'], ['median', 'median'], ['counts, mean, std', 'counts, mean, std']]), 'heatmapType');

//         // Map from ternary section
//         this.appendDummyInput('mapHeader')
//             .appendField('Map from Ternary')
//             .setAlign(Blockly.inputs.Align.CENTRE);

//         this.appendDummyInput('colormap')
//             .appendField('Colormap')
//             .appendField(new Blockly.FieldDropdown([['yellow-red-blue', 'yellow-red-blue'], ['viridis', 'viridis'], ['plasma', 'plasma']]), 'colormap');

//         // Colors selection
//         this.appendDummyInput('colors')
//             .appendField('Colors')
//             .appendField(new FieldColour('#FFFF00'), 'colorX')
//             .appendField('X')
//             .appendField(new FieldColour('#FF0000'), 'colorY')
//             .appendField('Y')
//             .appendField(new FieldColour('#0000FF'), 'colorZ')
//             .appendField('Z')
//             .appendField(new Blockly.FieldCheckbox('FALSE'), 'colorM')
//             .appendField('M');

//         this.setInputsInline(false);
//         this.setTooltip('Configure scatter and heatmap settings.');
//         this.setHelpUrl('');
//         this.setColour(160);  // Adjust color as needed
//         this.setOutput(true, null);
//     },
//     updateAnalyteDropdown: function(analyteField, analyteTypeField) {
//         const analyteType = this.getFieldValue(analyteTypeField);

//         // Call the Python function getFieldList through the WebChannel, handle as a promise
//         window.blocklyBridge.getFieldList(analyteType).then((response) => {
//             const options = response.map(option => [option, option]);
//             const dropdown = this.getField(analyteField);

//             // Clear existing options and add new ones
//             dropdown.menuGenerator_ = options;
//             dropdown.setValue(options[0][1]);  // Set the first option as the default
//             dropdown.forceRerender();  // Refresh dropdown to display updated options
//         }).catch(error => {
//             console.error('Error fetching field list:', error);
//         });
//     }
// };
// Blockly.common.defineBlocks({ scatter_and_heatmaps: scatter_and_heatmaps });


// // Block: Plot 
// const plot_map = {
//     init: function() {
//         this.appendDummyInput('header')
//         .appendField('Plot Map')
//         .setAlign(Blockly.inputs.Align.CENTRE)
//         // Create the 'Field type' dropdown with options
//         this.appendDummyInput('NAME')
//         .appendField('Field type')
//         .appendField(new Blockly.FieldDropdown(
//             [
//                 ['Analyte', 'Analyte'],
//                 ['Analyte (Normalised)', 'Analyte (Normalised)'],
//                 ['PCA Score', 'PCA Score'],
//                 ['Cluster', 'Cluster']
//             ],
//             this.updateFieldDropdown.bind(this)  // Bind the update function
//         ), 'fieldType');

//         // Create the 'field' dropdown, initially empty
//         this.appendDummyInput('FIELD')
//             .appendField('Field')
//             .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'field');

        
//         // Style and Save inputs
//         this.appendValueInput('style')
//             .appendField('Style');
//         this.appendValueInput('save')
//             .appendField('Save');
        
//         this.setPreviousStatement(true, null);
//         this.setNextStatement(true, null);
//         this.setTooltip('Configure and render a plot with specified type and settings.');
//         this.setHelpUrl('');
//         this.setColour(285);
//         this.setInputsInline(false)
//         // Initialize internal properties
//         this.plotType = null;
//         this.connectedStyleBlocks = {}; // To store references to connected style blocks

//         // Automatically disable the block if sample IDs are not enabled
//         if (!enableSampleIDsBlock) {
//             this.setDisabledReason(true, "no_sample_ids");
//         }
//     },

//     updateFieldDropdown: function(newValue) {
//         const fieldTypeValue = newValue || this.getFieldValue('fieldType');

//         // Call the Python function getFieldList through the WebChannel, handle as a promise
//         window.blocklyBridge.getFieldList(fieldTypeValue).then((response) => {
//             // Map the response to the required format for Blockly dropdowns
//             const options = response.map(option => [option, option]);

//             // Add 'none' and 'all' options at the beginning
//             options.unshift(['all', 'all']);
//             options.unshift(['none', 'none']);

//             const dropdown = this.getField('field');

//             // Update the dropdown options
//             dropdown.menuGenerator_ = options;

//             // Set the default value to 'Select...' or to the first option if options are available
//             if (options.length > 0) {
//                 dropdown.setValue(options[0][1]);
//             } else {
//                 dropdown.setValue('');
//             }

//             dropdown.forceRerender();  // Refresh dropdown to display updated options
//         }).catch(error => {
//             console.error('Error fetching field list:', error);
//         });
//     },
    
//     updateConnectedStyleBlocks: function() {
//         // Get the style block connected to the 'style' input
//         const styleBlock = this.getInputTargetBlock('style');
        
//         if (styleBlock && styleBlock.type === 'styles') {
//             const connectedBlocks = this.getStyleSubBlocks(styleBlock);
//             this.connectedStyleBlocks = connectedBlocks;

//             // Trigger style updates
//             dynamicStyleUpdate(this.plotType, connectedBlocks);
//         }
//         else{
//             this.plotType = null;
//             this.clearConnectedStyleBlocks();
//         }
//     },

//     clearConnectedStyleBlocks: function() {
//         this.connectedStyleBlocks = {};
//     },

//     getStyleSubBlocks: function(styleBlock) {
//         const connectedBlocks = {};

//         ['axisAndLabels', 'annotAndScale', 'marksAndLines', 'coloring'].forEach((type) => {
//             const subBlock = styleBlock.getInputTargetBlock(type);
//             if (subBlock) connectedBlocks[type] = subBlock;
//         });

//         return connectedBlocks;
//     }
// };
// Blockly.common.defineBlocks({ plot_map: plot_map });

const plot_map = {
    init: function () {
        this.appendDummyInput('header')
            .appendField('Plot Map')
            .setAlign(Blockly.inputs.Align.CENTRE);

        
        this.appendDummyInput('NAME')
            .appendField('Field type')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'fieldType');

        this.appendDummyInput('FIELD')
            .appendField('Field')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'field');
        // Add dynamic statement input for styling
        const stylingInput = this.appendStatementInput('styling')
            .setCheck('styling')
            .appendField('Styling');
        
        // Add dynamic statement input for styling
        this.appendStatementInput('Polygons')
            .setCheck('Polygons')
            .appendField('Polygons');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, 'PLOT_OUTPUT');
        this.setTooltip('Configure and render a plot with specified type and settings.');
        this.setHelpUrl('');
        this.setColour(285);

        this.plotType = 'field map'

        this.plotName =  this.getFieldValue('field')|| 'plot';
        // Add default blocks to Styling input only in the toolbox
        if (!this.isInFlyout) {
            const defaultBlocks = ['x_axis', 'y_axis', 'font', 'colormap'];
            addDefaultStylingBlocks(this,this.workspace, defaultBlocks);
            //  Attach validators to fieldType and field
            // Default: axis = 'c' for 'C' axis; adjust as needed
            const axis = 'c';
            updateFieldTypeDropdown(this, this.plotType, axis, 'fieldType', 'field');

            // Attach validators to dropdowns
            const fieldTypeDropdown = this.getField('fieldType');
            fieldTypeDropdown.setValidator((newValue) => {
                this.argDict = this.argDict || {};
                this.argDict['c_field_type'] = newValue;
                updateFieldDropdown(this, newValue, 'field');  // When fieldType changes, update fields
                return newValue;
            });
            const fieldDropdown = this.getField('field');
            fieldDropdown.setValidator((newValue) => {
                this.argDict = this.argDict || {};
                this.argDict['c_field'] = newValue;
                this.argDict['plot_type'] = this.plotType;
                updateStylingChain(this, this.argDict);
                return newValue;
            });
        }
        this.setOnChange(function(event) {
            // 1) If no workspace or block is in the flyout, do nothing
            if (!this.workspace || this.isInFlyout) return;
          
            // 2) Only care about create/move/delete events
            if (
              event.type === Blockly.Events.BLOCK_CREATE ||
              event.type === Blockly.Events.BLOCK_MOVE ||
              event.type === Blockly.Events.BLOCK_DELETE
            ) {
              // 3) Check if the changed block is in the "styling" chain
              //    For instance, we can do:
              if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
                // 4) Call updateStylingChain(...)
                updateStylingChain(this);
              }
            }
        })
    }
};
Blockly.common.defineBlocks({ plot_map: plot_map });

const plot_correlation = {
    init: function() {
        this.appendDummyInput('VARIABLE1')
            .appendField('Correlation');
        this.appendDummyInput()
            .appendField('Method')
            .appendField(new Blockly.FieldDropdown([
                ['Pearson', 'Pearson'],
                ['Spearman', 'Spearman'],
                ['Kendall', 'Kendall']
            ]), 'method');
        this.appendDummyInput()
            .appendField('R^2')
            .appendField(new Blockly.FieldCheckbox('TRUE'), 'rSquared');
        this.appendValueInput('exportTable')
            .setCheck('export_table')
            .appendField('Export')
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(285);
        this.setTooltip('Performs correlation analysis between two variables.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['plot_correlation'] = plot_correlation;


const plot_histogram = {
    init: function () {
        this.appendDummyInput('header')
            .appendField('Plot Histogram')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // Type dropdown
        this.appendDummyInput('TYPE')
            .appendField('Type')
            .appendField(new Blockly.FieldDropdown([
                ['PDF', 'PDF'],
                ['CDF', 'CDF'],
                ['log-scaling', 'log-scaling'],
            ]), 'histType');

        // Field type dropdown
        this.appendDummyInput('FIELD_TYPE')
            .appendField('Field type')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'fieldType');

        // Field dropdown
        this.appendDummyInput('FIELD')
            .appendField('Field')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'field');

        // Add statement input for histogram options
        this.appendStatementInput('histogramOptions')
            .setCheck('histogramOptions')
            .appendField('Histogram options');

        // Add dynamic statement input for styling
        const stylingInput = this.appendStatementInput('styling')
            .setCheck('styling')
            .appendField('Styling');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Configure and render a histogram plot with specified settings.');
        this.setHelpUrl('');
        this.setColour(285);
        this.plotType = 'histogram'
        this.field = this.getFieldValue('field');
        this.fieldType = this.getFieldValue('fieldType');
        this.histType = this.getFieldValue('histType');
        this.histNumBins = 100;
        // Add default blocks for styling only if not in flyout
        if (!this.isInFlyout) {
            
            const defaultBlocks = [
                'aspect_ratio',
                'tick_direction',
                'x_axis',
                'y_axis',
                'line_properties',
                'transparency',
                'font'
            ];
            
            addDefaultStylingBlocks(this,this.workspace, defaultBlocks);

            const axis = 'x';
            updateFieldTypeDropdown(this, this.plotType, axis, 'fieldType', 'field');
            // const initialFieldType = this.getFieldValue('fieldType');
            // updateFieldDropdown(this,initialFieldType);
            // // update style dictionaries
            // updateHistogramOptions(this);
            // 3) Attach validators to fieldType and field
            const fieldTypeDropdown = this.getField('fieldType');
            fieldTypeDropdown.setValidator((newValue) => {
                this.fieldType = String(newValue);
                this.argDict = this.argDict || {};
                this.argDict['x_field_type'] = newValue;
                updateFieldDropdown(this, newValue, 'field'); // X axis
                // update style dictionaries
                updateHistogramOptions(this);
                
                return newValue;
            });

            const fieldDropdown = this.getField('field');
            fieldDropdown.setValidator((newValue) => {
                this.field = String(newValue);

                this.argDict = {
                    plot_type: this.plotType,
                    x_field: newValue,
                    x_field_type: this.field_type,     
                    hist_plot_type: this.histType,
                    hist_num_bins: this.nBins,
                }
                
                updateHistogramOptions(this);
                updateStylingChain(this, this.argDict);

            return newValue;
        });
        }
        this.setOnChange(function(event) {
            // 1) If no workspace or block is in the flyout, do nothing
            if (!this.workspace || this.isInFlyout) return;
          
            // 2) Only care about create/move/delete events
            if (
              event.type === Blockly.Events.BLOCK_CREATE ||
              event.type === Blockly.Events.BLOCK_MOVE ||
              event.type === Blockly.Events.BLOCK_DELETE
            ) {
              // 3) Check if the changed block is in the "styling" chain
              //    For instance, we can do:
              if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
                // 4) Call updateStylingChain(...)
                updateStylingChain(this);
              }
              if (isBlockInChain(this.getInputTargetBlock('histogramOptions'), event.blockId)) {
                // 4) Call updateStylingChain(...)
                updateHistogramOptions(this);
              }
            }
          });
    }
};
Blockly.common.defineBlocks({ plot_histogram: plot_histogram });

const plot_biplot = {
    init: function () {
        this.appendDummyInput('header')
            .appendField('Biplot')
            .setAlign(Blockly.inputs.Align.CENTRE);

        this.appendDummyInput('XTYPE')
            .appendField('Field type X')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'fieldTypeX');
        this.appendDummyInput('XFIELD')
            .appendField('Field X')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'fieldX');
        this.appendDummyInput('YTYPE')
            .appendField('Field type Y')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'fieldTypeY');
        this.appendDummyInput('YFIELD')
            .appendField('Field Y')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'fieldY');
        this.appendDummyInput('HEATMAP')
            .appendField('Show Heatmap')
            .appendField(new Blockly.FieldCheckbox('FALSE'), 'SHOW_HEATMAP');
        // Set initial plotType
        this.plotType = 'scatter';

        const heatmapCheckbox = this.getField('SHOW_HEATMAP');
        heatmapCheckbox.setValidator((newValue) => {
            this.plotType = (newValue === 'TRUE') ? 'heatmap' : 'scatter';
            updateStylingChain(this); // If you want to update styling
            return newValue;
        });

        // Styling
        this.appendStatementInput('styling')
            .setCheck('styling')
            .appendField('Styling');
        this.appendStatementInput('extras')
            .setCheck(['Regression', 'PCA'])
            .appendField('Additional Plots');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Plot a biplot (scatter or heatmap) with optional regression/PCA.');
        this.setHelpUrl('');
        this.setColour(285);

        // Add default styling blocks (only if not in flyout)
        if (!this.isInFlyout) {
            const defaultBlocks = ['x_axis', 'y_axis', 'font', 'colormap'];
            addDefaultStylingBlocks(this, this.workspace, defaultBlocks);
            // update fieldType dropdowns for X and Y
            updateFieldTypeDropdown(this, this.plotType, 'x', 'fieldTypeX', 'fieldX');
            updateFieldTypeDropdown(this, this.plotType, 'y', 'fieldTypeY', 'fieldY');

            // Attach validators to fieldType and field for X and Y
            const fieldTypeXDropdown = this.getField('fieldTypeX');
            fieldTypeXDropdown.setValidator((newValue) => {
                updateFieldDropdown(this, newValue, 'fieldX'); // X axis
                return newValue;
            });
            const fieldXDropdown = this.getField('fieldX');
            fieldXDropdown.setValidator((newValue) => {
                this.argDict = {
                    plot_type: this.plotType,
                    x_field: newValue,
                    x_field_type: this.getFieldValue('fieldTypeX'),     
                }
                updateStylingChain(this);
                return newValue;
            });

            const fieldTypeYDropdown = this.getField('fieldTypeY');
            fieldTypeYDropdown.setValidator((newValue) => {
                updateFieldDropdown(this, newValue, 'fieldY'); // Y axis
                return newValue;
            });
            const fieldYDropdown = this.getField('fieldY');
            fieldYDropdown.setValidator((newValue) => {
                this.argDict = {
                    plot_type: this.plotType,
                    y_field: newValue,
                    y_field_type: this.getFieldValue('fieldTypeY'),     
                }
                updateStylingChain(this);
                return newValue;
            });
        }
        // On change, always re-sync the style chain
        this.setOnChange(function(event) {
            if (!this.workspace || this.isInFlyout) return;
            if (
              event.type === Blockly.Events.BLOCK_CREATE ||
              event.type === Blockly.Events.BLOCK_MOVE ||
              event.type === Blockly.Events.BLOCK_DELETE
            ) {
                if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
                    updateStylingChain(this);
                }
            }
        });
    }
};
Blockly.common.defineBlocks({ plot_biplot: plot_biplot });


const plot_ternary = {
    init: function () {
        this.appendDummyInput('header')
            .appendField('Ternary Plot')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // Dynamically add axes fields and types
        ['X','Y','Z'].forEach(axis => {
            this.appendDummyInput(`${axis}TYPE`)
                .appendField(`Field type ${axis}`)
                .appendField(new Blockly.FieldDropdown([['Select...', '']]), `fieldType${axis}`);
            this.appendDummyInput(`${axis}FIELD`)
                .appendField(`Field ${axis}`)
                .appendField(new Blockly.FieldDropdown([['Select...', '']]), `field${axis}`);
        });

        // Now add the heatmap checkbox
        this.appendDummyInput('HEATMAP')
            .appendField('Show Heatmap')
            .appendField(new Blockly.FieldCheckbox('FALSE'), 'SHOW_HEATMAP');

        this.appendStatementInput('styling')
            .setCheck('styling')
            .appendField('Styling');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Ternary diagram (scatter or heatmap).');
        this.setHelpUrl('');
        this.setColour(285);

        // Default plot type
        this.plotType = 'scatter';
        const axisIndexMap = { X: 'x', Y: 'y', Z: 'z' };
        if (!this.isInFlyout) {
            const defaultBlocks = ['x_axis', 'y_axis', 'z_axis', 'colormap'];
            addDefaultStylingBlocks(this, this.workspace, defaultBlocks);

            // Set up validators and chain updates
            ['X','Y','Z'].forEach(axis => {
                const axisVal = axisIndexMap[axis];
                updateFieldTypeDropdown(this, this.plotType, axisVal, `fieldType${axis}`, `field${axis}`);
                    
                const fieldTypeDropdown = this.getField(`fieldType${axis}`);
                fieldTypeDropdown.setValidator((newValue) => {
                    this.argDict = this.argDict || {};
                    this.argDict[`${axis.toLowerCase()}_field_type`] = newValue;
                    updateFieldDropdown(this, newValue, `field${axis}`);
                    // After type changes, update the full chain with all info
                    return newValue;
                });

                const fieldDropdown = this.getField(`field${axis}`);
                fieldDropdown.setValidator((newValue) => {
                    this.argDict =  getTernaryArgDict(this)
                    //update new field value in dict 
                    this.argDict[`${axis.toLowerCase()}_field`]=newValue
                    updateStylingChain(this);
                    return newValue;
                });
            });

            // Heatmap checkbox validator (now field exists!)
            const heatmapCheckbox = this.getField('SHOW_HEATMAP');
            heatmapCheckbox.setValidator((newValue) => {
                this.plotType = (newValue === 'TRUE') ? 'heatmap' : 'scatter';
                updateStylingChain(this);
                return newValue;
            });
        }

        this.setOnChange(function(event) {
            if (!this.workspace || this.isInFlyout) return;
            if (
                event.type === Blockly.Events.BLOCK_CREATE ||
                event.type === Blockly.Events.BLOCK_MOVE ||
                event.type === Blockly.Events.BLOCK_DELETE
            ) {
                if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
                    updateStylingChain(this);
                }
            }
        });

        // Helper function to gather current settings into an argDict
        function getTernaryArgDict(block) {
            return {
                'plot_type': block.plotType,
                'x_field': block.getFieldValue('fieldX'),
                'x_field_type': block.getFieldValue('fieldTypeX'),
                'y_field': block.getFieldValue('fieldY'),
                'y_field_type': block.getFieldValue('fieldTypeY'),
                'z_field': block.getFieldValue('fieldZ'),
                'z_field_type': block.getFieldValue('fieldTypeZ'),
            };
        }
    }
};
Blockly.common.defineBlocks({ plot_ternary: plot_ternary });


const plot_ternary_map = {
    init: function () {
        this.appendDummyInput('header')
            .appendField('Ternary Map')
            .setAlign(Blockly.inputs.Align.CENTRE);

        ['X','Y','Z'].forEach(axis => {
            this.appendDummyInput(`${axis}TYPE`)
                .appendField(`Field type ${axis}`)
                .appendField(new Blockly.FieldDropdown([['Select...', '']]), `fieldType${axis}`);
            this.appendDummyInput(`${axis}FIELD`)
                .appendField(`Field ${axis}`)
                .appendField(new Blockly.FieldDropdown([['Select...', '']]), `field${axis}`);
        });

        this.appendStatementInput('styling')
            .setCheck('styling')
            .appendField('Styling');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Ternary map.');
        this.setHelpUrl('');
        this.setColour(285);
        this.plotType = 'ternary map';
        if (!this.isInFlyout) {
            const defaultBlocks = ['x_axis', 'y_axis', 'font', 'colormap'];
            addDefaultStylingBlocks(this, this.workspace, defaultBlocks);

            ['X','Y','Z'].forEach(axis => {
                const fieldTypeDropdown = this.getField(`fieldType${axis}`);
                fieldTypeDropdown.setValidator((newValue) => {
                    this.argDict = this.argDict || {};
                    this.argDict[`${axis}_field_type`] = newValue;
                    updateFieldDropdown(this, newValue, axis);
                    updateStylingChain(this);
                    return newValue;
                });
                const fieldDropdown = this.getField(`field${axis}`);
                fieldDropdown.setValidator((newValue) => {
                    this.argDict =  getTernaryArgDict(this)
                    //update new field value in dict 
                    this.argDict[`${axis.toLowerCase()}_field`]=newValue
                    updateStylingChain(this);
                    return newValue;
                });
            });
        }
        this.setOnChange(function(event) {
            if (!this.workspace || this.isInFlyout) return;
            if (
              event.type === Blockly.Events.BLOCK_CREATE ||
              event.type === Blockly.Events.BLOCK_MOVE ||
              event.type === Blockly.Events.BLOCK_DELETE
            ) {
                if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
                    updateStylingChain(this);
                }
            }
        });
        // Helper function to gather current settings into an argDict
        function getTernaryArgDict(block) {
            return {
                'plot_type': block.plotType,
                'x_field': block.getFieldValue('fieldX'),
                'x_field_type': block.getFieldValue('fieldTypeX'),
                'y_field': block.getFieldValue('fieldY'),
                'y_field_type': block.getFieldValue('fieldTypeY'),
                'z_field': block.getFieldValue('fieldZ'),
                'z_field_type': block.getFieldValue('fieldTypeZ'),
            };
        }
    }
};
Blockly.common.defineBlocks({ plot_ternary_map: plot_ternary_map });

/* ================================
   Compatibility Diagram (TEC)
   ================================ */
const plot_ndim = {
  init: function () {
    const block = this;

    block.appendDummyInput('header')
      .appendField('Compatibility diagram')
      .setAlign(Blockly.inputs.Align.CENTRE);

    block.appendDummyInput('ASET')
      .appendField('Defined set')
      .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'ndimAnalyteSet');

    block.appendDummyInput('QSEL')
      .appendField('Quantiles')
      .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'ndimQuantiles');

    // Styling chain
    block.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    block.setPreviousStatement(true, null);
    block.setNextStatement(true, null);
    block.setTooltip('TEC (spider) diagram. Requires Reference value to be set.');
    block.setHelpUrl('');
    block.setColour(285);

    block.plotType = 'TEC';
    this.argDict = {
                    plot_type: this.plotType,
                }
    if (!block.workspace || block.workspace.isFlyout) return;

    // Defaults for TEC
    const defaultBlocks = ['font', 'line_properties', 'transparency', 'colormap'];
    addDefaultStylingBlocks(block, block.workspace, defaultBlocks);

    // Populate dropdowns
    updateNDimListDropdown(block, 'ndimList');
    updateAnalyteSetDropdown(block, 'ndimAnalyteSet');
    updateQuantilesDropdown(block, 'ndimQuantiles');

    // // Keep styling args in sync when user changes any selector
    // const refresh = () => updateStylingChain(block);

    // block.getField('ndimList')?.setValidator(() => { refresh(); return null; });
    // block.getField('ndimAnalyteSet')?.setValidator(() => { refresh(); return null; });
    // block.getField('ndimQuantiles')?.setValidator(() => { refresh(); return null; });

    // Keep styles in sync when chain mutates
    block.setOnChange(function (event) {
      if (!this.workspace || this.isInFlyout) return;
      if (event.type === Blockly.Events.BLOCK_CREATE ||
          event.type === Blockly.Events.BLOCK_MOVE ||
          event.type === Blockly.Events.BLOCK_DELETE) {
        if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
          updateStylingChain(this);
        }
      }
    });

    function updateAnalyteSetDropdown(b, fieldName) {
      window.blocklyBridge?.getNDimAnalyteSets?.()
        .then((keys) => {
          const opts = (keys || []).map(k => [k, k]);
          const dd = b.getField(fieldName);
          if (dd && opts.length) {
            dd.menuGenerator_ = opts;           // simple, compatible with your codebase
            const keep = dd.getValue();
            const values = new Set(opts.map(o => o[1]));
            dd.setValue(values.has(keep) ? keep : opts[0][1]);
            dd.forceRerender?.();
          }
        })
        .catch(err => console.error('Analyte sets error:', err));
    }

    function updateQuantilesDropdown(b, fieldName) {
      window.blocklyBridge?.getNDimQuantiles?.()
        .then((items) => {
          // Accept [{label, value}, ...] or strings
          const opts = (items || []).map(it => {
            if (typeof it === 'string') return [it, it];
            const label = String(it.label ?? it.value ?? '');
            const value = String(it.value ?? label);
            return [label, value];
          });
          const dd = b.getField(fieldName);
          if (dd && opts.length) {
            dd.menuGenerator_ = opts;
            const keep = dd.getValue();
            const values = new Set(opts.map(o => o[1]));
            dd.setValue(values.has(keep) ? keep : opts[0][1]);
            dd.forceRerender?.();
          }
        })
        .catch(err => console.error('Quantiles error:', err));
    }
  }
};

Blockly.common.defineBlocks({ plot_ndim });


/* ================================
   Radar Plot
   ================================ */
const plot_radar = {
    init: function () {
        this.appendDummyInput('header')
            .appendField('Radar plot')
            .setAlign(Blockly.inputs.Align.CENTRE);

        // N-dim list selector (dynamic)
        this.appendDummyInput('NDIM')
            .appendField('N-dim list')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'ndimList');

        // Styling chain
        this.appendStatementInput('styling')
            .setCheck('styling')
            .appendField('Styling');

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Radar plot. Requires Reference value to be set.');
        this.setHelpUrl('');
        this.setColour(285);

        this.plotType = 'Radar';
        this.argDict = {
                    plot_type: this.plotType,
                }
        if (!this.isInFlyout) {
            // Defaults for Radar
            const defaultBlocks = ['font', 'line_properties', 'transparency', 'colormap'];
            addDefaultStylingBlocks(this, this.workspace, defaultBlocks);

            // Populate N-dim dropdown dynamically
            updateNDimListDropdown(this, 'ndimList');

            const ndimDropdown = this.getField('ndimList');
            ndimDropdown.setValidator((newValue) => {
                updateStylingChain(this, getNDimArgDict(this));
                return newValue;
            });
        }

        this.setOnChange(function (event) {
            if (!this.workspace || this.isInFlyout) return;
            if (event.type === Blockly.Events.BLOCK_CREATE ||
                event.type === Blockly.Events.BLOCK_MOVE ||
                event.type === Blockly.Events.BLOCK_DELETE) {
                if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
                    updateStylingChain(this, getNDimArgDict(this));
                }
            }
        });

        function getNDimArgDict(block) {
            return {
                plot_type: block.plotType,          // 'Radar'
                ndim_list_key: block.getFieldValue('ndimList')
            };
        }
    }
};
Blockly.common.defineBlocks({ plot_radar: plot_radar });
/* ================================
   Clustering & Dimensionality Reduction — custom_blocks.js (updated)
   ================================ */

/***** Helpers *****/
const DICE_SVG = 'data:image/svg+xml;utf8,' +
  encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="6" y="6" width="52" height="52" rx="10" fill="#eaeaea" stroke="#999"/>
  <circle cx="20" cy="20" r="4" fill="#666"/><circle cx="44" cy="20" r="4" fill="#666"/>
  <circle cx="32" cy="32" r="4" fill="#666"/>
  <circle cx="20" cy="44" r="4" fill="#666"/><circle cx="44" cy="44" r="4" fill="#666"/></svg>`);

/* Small utility to walk statement input and return first block in the chain */
function _firstInChain(block, inputName) {
  if (!block) return null;
  const head = block.getInputTargetBlock(inputName);
  return head || null;
}

/* Toggle visibility of a DummyInput by name, if it exists */
function _setInputVisible(block, inputName, visible) {
  const inp = block && block.getInput(inputName);
  if (inp) {
    inp.setVisible(visible);
    block.render();
  }
}

/* ================================
   PCA — Basis variance (x: top & bottom)
   ================================ */
const plot_basis_variance = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Basis variance')
      .setAlign(Blockly.inputs.Align.CENTRE);

    this.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(210);
    this.setTooltip('Explained and cumulative variance of PCA.');
    this.setHelpUrl('');
    this.plotType = 'variance';
    this.argDict = {
                    plot_type: this.plotType 
                }
    if (!this.isInFlyout) {
      // Default styling: marker properties, line properties, font
      const defaultBlocks = ['marker_properties', 'line_properties', 'font'];
      addDefaultStylingBlocks(this, this.workspace, defaultBlocks);
    }

    this.setOnChange(function (event) {
      if (!this.workspace || this.isInFlyout) return;
      if ([Blockly.Events.BLOCK_CREATE, Blockly.Events.BLOCK_MOVE, Blockly.Events.BLOCK_DELETE].includes(event.type)) {
        if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
          updateStylingChain(this);
        }
      }
    });
  }
};
Blockly.common.defineBlocks({ plot_basis_variance });

/* ================================
   PCA — Basis vectors plot (x: top & bottom)
   ================================ */
const plot_basis_vectors_plot = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Basis vectors plot')
      .setAlign(Blockly.inputs.Align.CENTRE);

    this.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(210);
    this.setTooltip('Heatmap/plot of PCA basis vectors.');
    this.setHelpUrl('');
    this.plotType = 'basis vectors';
    this.argDict = {
                    plot_type: this.plotType  
                }
    if (!this.isInFlyout) {
      // Default styling: colormap, font
      const defaultBlocks = ['colormap', 'font'];
      addDefaultStylingBlocks(this, this.workspace, defaultBlocks);
    }

    this.setOnChange(function (event) {
      if (!this.workspace || this.isInFlyout) return;
      if ([Blockly.Events.BLOCK_CREATE, Blockly.Events.BLOCK_MOVE, Blockly.Events.BLOCK_DELETE].includes(event.type)) {
        if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId)) {
          updateStylingChain(this);
        }
      }
    });
  }
};
Blockly.common.defineBlocks({ plot_basis_vectors_plot });

/* ================================
   PCA — Basis vectors (styling block) (<: left into styling chain)
   ================================ */
const style_basis_vectors = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Basis vectors')
      .setAlign(Blockly.inputs.Align.CENTRE);

    this.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    this.setPreviousStatement(true, 'styling');
    this.setNextStatement(true, 'styling');
    this.setColour(120);
    this.setTooltip('Styling for PCA basis vectors overlay.');
    this.setHelpUrl('');
    
    this.plotType = 'basis vectors';
    this.argDict = {
                    plot_type: this.plotType     
                }
    if (!this.isInFlyout) {
      // Default styling: line properties, transparency
      const defaultBlocks = ['line_properties', 'transparency'];
      addDefaultStylingBlocks(this, this.workspace, defaultBlocks);
    }
  }
};
Blockly.common.defineBlocks({ style_basis_vectors });

/* ================================
   Seed block (<: left) — with RNG button (uses bridge RNG if available)
   ================================ */
const cfg_seed = {
  init: function () {
    const block = this;  // capture block reference
    const seedField = new Blockly.FieldTextInput('');

    const dice = new Blockly.FieldImage(DICE_SVG, 16, 16, 'randomize', () => {
      const rng = window.blocklyBridge?.randomClusterSeed;
      const applySeed = (val) => {
        seedField.setValue(String(val));
        // force the field to visually refresh
        seedField.forceRerender?.();
      };

      if (typeof rng === 'function') {
        Promise.resolve(rng()).then(applySeed).catch(() => {
          applySeed(Math.floor(Math.random() * 1e9));
        });
      } else {
        applySeed(Math.floor(Math.random() * 1e9));
      }
    });

    block.appendDummyInput('ROW')
      .appendField('Seed')
      .appendField(dice, 'rng')
      .appendField(seedField, 'seed');

    seedField.setValidator((nv) => nv);
    block.setPreviousStatement(true, 'seed');
    block.setNextStatement(true, 'seed');
    block.setColour(15);
    block.setTooltip('Random seed for reproducibility.');
    block.setHelpUrl('');
  }
};
Blockly.common.defineBlocks({ cfg_seed });

/* ================================
   Cluster options (<: left; mutator-ready stub)
   ================================ */
const cfg_cluster_options = {
  init: function () {
    this.appendDummyInput('METHOD')
      .appendField('Cluster options')
      .setAlign(Blockly.inputs.Align.CENTRE);

    this.appendDummyInput('EXP')
      .appendField('Exponent')
      .appendField(new Blockly.FieldNumber(2.0, 1, 10, 0.1), 'exponent');

    this.appendDummyInput('DIST')
      .appendField('Distance')
      .appendField(new Blockly.FieldDropdown([
        ['euclidean', 'euclidean'],
        ['manhattan', 'manhattan'],
        ['cosine', 'cosine']
      ]), 'distance');

    // New: Custom field list input
    this.appendStatementInput('customFields')
      .setCheck('custom_field')
      .appendField('Custom field list');

    this.appendDummyInput('PCA')
      .appendField('PCA')
      .appendField(new Blockly.FieldCheckbox('FALSE'), 'pca');

    this.setPreviousStatement(true, 'cluster_options');
    this.setNextStatement(true, 'cluster_options');
    this.setColour(20);
    this.setTooltip('Advanced clustering options (ready for mutator extension).');
    this.setHelpUrl('');

    if (!this.isInFlyout) {
      // Optionally, populate distance list from bridge if available
      const distDD = this.getField('distance');
      const loader = window.blocklyBridge?.getClusterDistanceOptions;
      if (typeof loader === 'function') {
        loader().then((opts) => {
          const items = (opts || []).map(s => [s, s]);
          if (items.length) {
            distDD.menuGenerator_ = items;
            const cur = distDD.getValue();
            const vals = new Set(items.map(o => o[1]));
            if (!vals.has(cur)) distDD.setValue(items[0][1]);
            distDD.forceRerender?.();
          }
        }).catch(console.error);
      }
    }
  }
};
Blockly.common.defineBlocks({ cfg_cluster_options });

/* ================================
   PCA preconditioning (<: left)
   ================================ */
const cfg_pca_preconditioning = {
  init: function () {
    this.appendDummyInput('NB')
      .appendField('PCA preconditioning: No. basis')
      .appendField(new Blockly.FieldNumber(0, 0), 'nBasis');

    this.setPreviousStatement(true, 'pca_preconditioning');
    this.setNextStatement(true, 'pca_preconditioning');
    this.setColour(20);
    this.setTooltip('Number of basis vectors for PCA preconditioning.');
    this.setHelpUrl('');
  }
};
Blockly.common.defineBlocks({ cfg_pca_preconditioning });



/* ================================
   Multidimensional — Clustering (x: top & bottom) with dynamic defaults
   ================================ */
const plot_clustering = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Clustering')
      .setAlign(Blockly.inputs.Align.CENTRE);

    // Method dropdown is populated dynamically from AppData via bridge
    this.appendDummyInput('METHOD')
      .appendField('Method')
      .appendField(new Blockly.FieldDropdown([['Loading…', '']]), 'method');

    // Chain: Seed > Cluster options > Custom field list
    this.appendStatementInput('seed')
      .setCheck('seed')
      .appendField('Seed');

    this.appendStatementInput('options')
      .setCheck('cluster_options')
      .appendField('Cluster options');

    this.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(200);
    this.setTooltip('Clustering entry point (method + seed + options + custom field list).');
    this.setHelpUrl('');
    this.plotType = 'cluster map'
    this.argDict = {
                    plot_type: this.plotType    
                }
    if (!this.isInFlyout) {
      // Default styling: marker, line width, font (use *_nc if you have “no color” variants)
      const defaultBlocks = ['marker_properties', 'line_properties', 'font'];
      addDefaultStylingBlocks(this, this.workspace, defaultBlocks);

      const methodDD = this.getField('method');

      // Load methods dynamically
      const loadMethods = () => {
        const lister = window.blocklyBridge?.getClusterMethodList;
        if (typeof lister !== 'function') return;
        lister().then((methods) => {
          const opts = (methods || []).map(m => [m, m]);
          if (!opts.length) return;
          methodDD.menuGenerator_ = opts;
          // choose previously set value or first
          const cur = methodDD.getValue();
          const vals = new Set(opts.map(o => o[1]));
          methodDD.setValue(vals.has(cur) ? cur : opts[0][1]);
          methodDD.forceRerender?.();
          applyDefaults(methodDD.getValue());
        }).catch(console.error);
      };

      // Apply defaults for selected method into child blocks
      const applyDefaults = (method) => {
        const getter = window.blocklyBridge?.getClusterDefaults;
        const specer = window.blocklyBridge?.getClusterOptionSpec;
        if (typeof getter !== 'function') return;

        getter(method).then((json) => {
          const d = typeof json === 'string' ? JSON.parse(json) : (json || {});
          // Seed
          const seedBlk = _firstInChain(this, 'seed');
          if (seedBlk && seedBlk.getField('seed')) {
            seedBlk.getField('seed').setValue(d.seed != null ? String(d.seed) : '');
          }
          // Options
          const optBlk = _firstInChain(this, 'options');
          if (optBlk) {
            if (optBlk.getField('exponent') && d.exponent != null) {
              optBlk.getField('exponent').setValue(Number(d.exponent));
            }
            if (optBlk.getField('distance') && d.distance) {
              // ensure distance is in dropdown; if not, keep current
              const dd = optBlk.getField('distance');
              const items = (dd.menuGenerator_ || []).map(o => o[1]);
              if (items.includes(d.distance)) dd.setValue(d.distance);
            }
            if (optBlk.getField('pca')) {
              optBlk.getField('pca').setValue(d.precondition ? 'TRUE' : 'FALSE');
            }
          }
          updateStylingChain(this);
        }).catch(console.error);

        // Toggle visible/hidden fields based on option spec
        if (typeof specer === 'function') {
          specer(method).then((json) => {
            const s = typeof json === 'string' ? JSON.parse(json) : (json || {});
            const optBlk = _firstInChain(this, 'options');
            if (optBlk) {
              _setInputVisible(optBlk, 'EXP', !!s.supports_exponent);
              _setInputVisible(optBlk, 'DIST', !!s.supports_distance);
              optBlk.render();
            }
          }).catch(console.error);
        }
      };

      // Validator: when method changes, re-apply defaults
      methodDD.setValidator((nv) => {
        applyDefaults(nv);
        return nv;
      });

      // Load data now
      loadMethods();
    }

    this.setOnChange(function (event) {
      if (!this.workspace || this.isInFlyout) return;
      if ([Blockly.Events.BLOCK_CREATE, Blockly.Events.BLOCK_MOVE, Blockly.Events.BLOCK_DELETE].includes(event.type)) {
        const inStyling = isBlockInChain(this.getInputTargetBlock('styling'), event.blockId);
        const inSeed = isBlockInChain(this.getInputTargetBlock('seed'), event.blockId);
        const inOpt = isBlockInChain(this.getInputTargetBlock('options'), event.blockId);
        if (inStyling || inSeed || inOpt) updateStylingChain(this);
      }
    });
  }
};
Blockly.common.defineBlocks({ plot_clustering });

/* ================================
   Cluster performance (x: top & bottom) with dynamic defaults
   ================================ */
/* ================================
   Cluster performance (x: top & bottom) with dynamic defaults + Max Clusters
   ================================ */
const plot_cluster_performance = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Cluster performance')
      .setAlign(Blockly.inputs.Align.CENTRE);

    // Method dropdown populated dynamically
    this.appendDummyInput('METHOD')
      .appendField('Method')
      .appendField(new Blockly.FieldDropdown([['Loading…', '']]), 'method');

    // Max clusters (defaults to AppData.max_clusters via bridge)
    this.appendDummyInput('MAXK')
      .appendField('Max clusters')
      .appendField(new Blockly.FieldNumber(10, 2, 1000, 1), 'maxClusters');

    this.appendStatementInput('seed')
      .setCheck('seed')
      .appendField('Seed');

    this.appendStatementInput('options')
      .setCheck('cluster_options')
      .appendField('Cluster options');

    this.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(200);
    this.setTooltip('Plots for choosing optimal number of clusters (elbow, silhouette, etc.).');
    this.setHelpUrl('');
    this.plotType = 'cluster performance'
    this.argDict = {
                    plot_type: this.plotType
                }
    if (!this.isInFlyout) {
      // Default styling: marker, line width, font
      const defaultBlocks = ['marker_properties', 'line_properties', 'font'];
      addDefaultStylingBlocks(this, this.workspace, defaultBlocks);

      const methodDD = this.getField('method');
      const maxKField = this.getField('maxClusters');

      const loadMethods = () => {
        const lister = window.blocklyBridge?.getClusterMethodList;
        if (typeof lister !== 'function') return;
        lister().then((methods) => {
          const opts = (methods || []).map(m => [m, m]);
          if (!opts.length) return;
          methodDD.menuGenerator_ = opts;
          const cur = methodDD.getValue();
          const vals = new Set(opts.map(o => o[1]));
          methodDD.setValue(vals.has(cur) ? cur : opts[0][1]);
          methodDD.forceRerender?.();
          applyDefaults(methodDD.getValue());
        }).catch(console.error);
      };

      const applyDefaults = (method) => {
        const getter = window.blocklyBridge?.getClusterDefaults;
        const specer = window.blocklyBridge?.getClusterOptionSpec;
        if (typeof getter !== 'function') return;

        getter(method).then((json) => {
          const d = typeof json === 'string' ? JSON.parse(json) : (json || {});
          // Seed
          const seedBlk = _firstInChain(this, 'seed');
          if (seedBlk && seedBlk.getField('seed')) {
            seedBlk.getField('seed').setValue(d.seed != null ? String(d.seed) : '');
          }
          // Options
          const optBlk = _firstInChain(this, 'options');
          if (optBlk) {
            if (optBlk.getField('exponent') && d.exponent != null) {
              optBlk.getField('exponent').setValue(Number(d.exponent));
            }
            if (optBlk.getField('distance') && d.distance) {
              const dd = optBlk.getField('distance');
              const items = (dd.menuGenerator_ || []).map(o => o[1]);
              if (items.includes(d.distance)) dd.setValue(d.distance);
            }
            if (optBlk.getField('pca')) {
              optBlk.getField('pca').setValue(d.precondition ? 'TRUE' : 'FALSE');
            }
          }
          // Max clusters default
          if (maxKField && Number.isFinite(Number(d.max_clusters))) {
            maxKField.setValue(Number(d.max_clusters));
          }
          updateStylingChain(this);
        }).catch(console.error);

        if (typeof specer === 'function') {
          specer(method).then((json) => {
            const s = typeof json === 'string' ? JSON.parse(json) : (json || {});
            const optBlk = _firstInChain(this, 'options');
            if (optBlk) {
              _setInputVisible(optBlk, 'EXP', !!s.supports_exponent);
              _setInputVisible(optBlk, 'DIST', !!s.supports_distance);
              optBlk.render();
            }
          }).catch(console.error);
        }
      };

      methodDD.setValidator((nv) => { applyDefaults(nv); return nv; });
      if (maxKField) {
        maxKField.setValidator((nv) => { updateStylingChain(this); return nv; });
      }

      loadMethods();
    }

    this.setOnChange(function (event) {
      if (!this.workspace || this.isInFlyout) return;
      if ([Blockly.Events.BLOCK_CREATE, Blockly.Events.BLOCK_MOVE, Blockly.Events.BLOCK_DELETE].includes(event.type)) {
        const inStyling = isBlockInChain(this.getInputTargetBlock('styling'), event.blockId);
        const inSeed = isBlockInChain(this.getInputTargetBlock('seed'), event.blockId);
        const inOpt = isBlockInChain(this.getInputTargetBlock('options'), event.blockId);
        if (inStyling || inSeed || inOpt) updateStylingChain(this);
      }
    });
  }
};
Blockly.common.defineBlocks({ plot_cluster_performance });

/* ================================
   Dimentionality Reduction Plots
   ================================ */   
/* ================================
   Multidimensional — Dimensional reduction (x: top & bottom)
   ================================ */
const dimensional_reduction = {
  init: function () {
    this.appendDummyInput('HEADER')
      .appendField('Dimensional Reduction')
      .setAlign(Blockly.inputs.Align.CENTRE);

    this.appendDummyInput('METHOD')
      .appendField('Method')
      .appendField(new Blockly.FieldDropdown([
        ['PCA: Principal component analysis', 'PCA: Principal component analysis']
      ]), 'method');

    this.appendStatementInput('styling')
      .setCheck('styling')
      .appendField('Styling');

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(285);
    this.setTooltip('Dimensionality reduction entry point (method + custom field selection).');
    this.setHelpUrl('');
    this.plotType = 'basis vectors';
    this.argDict = {
                    plot_type: this.plotType   
                }
    if (!this.isInFlyout) {
      // Choose defaults for DR maps: colormap, font
      const defaultBlocks = ['colormap', 'font'];
      addDefaultStylingBlocks(this, this.workspace, defaultBlocks);
    }

    this.setOnChange(function (event) {
      if (!this.workspace || this.isInFlyout) return;
      if ([Blockly.Events.BLOCK_CREATE, Blockly.Events.BLOCK_MOVE, Blockly.Events.BLOCK_DELETE].includes(event.type)) {
        if (isBlockInChain(this.getInputTargetBlock('styling'), event.blockId) ) {
          updateStylingChain(this);
        }
      }
    });
  }
};
Blockly.common.defineBlocks({ dimensional_reduction });


/* ================================
    Styling Blocks
   ================================ */
Blockly.Blocks['modify_styles'] = {
    init: function () {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Modify style');
        this.appendStatementInput('STACK')
            .setCheck('styling_item');
        this.setColour(300);
        this.setTooltip('Container for styling items.');
        this.contextMenu = false; // Hide from regular workspace context menu
    }
};

Blockly.Blocks['x_axis'] = {
    init: function () {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('X Axis');
        this.appendDummyInput('xLabelHeader')
        .appendField('X Label')
        .appendField(new Blockly.FieldTextInput(''), 'xLabel');
        this.appendDummyInput('xLimitsHeader')
        .appendField('X Limits')
        .appendField(new Blockly.FieldTextInput(''), 'xLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'xLimMax');
        this.appendDummyInput('xScaleHeader')
        .appendField('X Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['Symlog', 'symlog'],
            ]), 'xScaleDropdown');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set X axis properties');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['y_axis'] = {
    init: function () {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Y Axis');
        this.appendDummyInput('yLabelHeader')
        .appendField('Y Label')
        .appendField(new Blockly.FieldTextInput(''), 'yLabel');
        this.appendDummyInput('yLimitsHeader')
        .appendField('Y Limits')
        .appendField(new Blockly.FieldTextInput(''), 'yLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'yLimMax');
        this.appendDummyInput('yScaleHeader')
        .appendField('Y Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['Symlog', 'symlog'],
            ]), 'yScaleDropdown');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set Y axis properties');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['z_axis'] = {
    init: function () {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Z Axis');
        this.appendDummyInput('zLabelHeader')
        .appendField('Z Label')
        .appendField(new Blockly.FieldTextInput(''), 'zLabel');
        this.appendDummyInput('zLimitsHeader')
        .appendField('Z Limits')
        .appendField(new Blockly.FieldTextInput(''), 'zLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'zLimMax');
        this.appendDummyInput('zScaleHeader')
        .appendField('Z Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['Symlog', 'symlog'],
            ]), 'zScaleDropdown');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set Z axis properties');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['c_axis'] = {
    init: function () {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('C Axis');
        this.appendDummyInput('cLabelHeader')
        .appendField('C Label')
        .appendField(new Blockly.FieldTextInput(''), 'cLabel');
        this.appendDummyInput('cLimitsHeader')
        .appendField('C Limits')
        .appendField(new Blockly.FieldTextInput(''), 'cLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'cLimMax');
        this.appendDummyInput('cScaleHeader')
        .appendField('c Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['Symlog', 'symlog'],
            ]), 'cScaleDropdown');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set C axis properties');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['font'] = {
    init: function () {
        this.appendDummyInput('font')
        .appendField('Font')
        .appendField(new Blockly.FieldDropdown([
            ['none', 'none'],
            ]), 'font');
        this.appendDummyInput('fontSize')
        .appendField('Font size')
        .appendField(new Blockly.FieldNumber(11, 4, 100), 'fontSize');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set axis label/annotation font');
        this.setHelpUrl('');
    },
};


Blockly.Blocks['tick_direction'] = {
    init: function () {
        this.appendDummyInput('tickDirectionHeader')
        .appendField('Tick direction')
        .appendField(new Blockly.FieldDropdown([
            ['out', 'out'],
            ['in', 'in'],
            ['inout', 'inout'],
            ['none', 'none']
            ]), 'tickDirectionDropdown');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set tick direction');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['aspect_ratio'] = {
    init: function () {
        this.appendDummyInput('aspectRatioHeader')
        .appendField('Aspect ratio')
        .appendField(new Blockly.FieldTextInput(''), 'aspectRatio');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(300);
        this.setTooltip('Set aspect ratio');
        this.setHelpUrl('');
    },
};


Blockly.Blocks['add_scale'] = {
    init: function () {
        this.appendDummyInput('scaleHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Add Scale');
        this.appendDummyInput('colorSelect')
        .appendField('Color')
        .appendField(new FieldColour('#ff0000'), 'scaleColor');
        this.appendDummyInput('unitsHeader')
        .appendField('Units')
        .appendField(new Blockly.FieldTextInput(''), 'scaleUnits');
        this.appendDummyInput('lengthHeader')
        .appendField('Length')
        .appendField(new Blockly.FieldTextInput(''), 'scaleLength');
        this.appendDummyInput('directionHeader')
        .appendField('Direction')
        .appendField(new Blockly.FieldDropdown([
            ['Horizontal', 'horizontal'],
            ['Vertical', 'vertical']
            ]), 'scaleDirection');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(220);
        this.setTooltip('Add a scale to the plot.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['marker_properties'] = {
    init: function () {
        this.appendDummyInput('markerHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Marker Properties');
        this.appendDummyInput('symbolHeader')
        .appendField('Symbol')
        .appendField(new Blockly.FieldDropdown([
            ['Circle', 'circle'],
            ['Square', 'square'],
            ['Diamond', 'diamond'],
            ['Triangle (Up)', 'triangleUp'],
            ['Triangle (Down)', 'triangleDown']
            ]), 'markerSymbol');
        this.appendDummyInput('sizeHeader')
        .appendField('Size')
        .appendField(new Blockly.FieldNumber(6, 1, 50), 'markerSize');
        this.appendDummyInput('colorSelect')
        .appendField('Color')
        .appendField(new FieldColour('#ff0000'), 'markerColor');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(230);
        this.setTooltip('Set marker properties for the plot.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['transparency'] = {
    init: function () {
        this.appendDummyInput('transparency')
        .appendField('Transparency')
        .appendField(new Blockly.FieldNumber(100, 0, 100), 'transparency');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(255);
        this.setTooltip('Adjust transparency of plot');
        this.setHelpUrl('');
    },
};


Blockly.Blocks['line_properties'] = {
    init: function () {
        this.appendDummyInput('lineHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Line Properties');
        this.appendDummyInput('lineWidthHeader')
        .appendField('Width')
        .appendField(new Blockly.FieldNumber(1, 0.1, 10, 0.1), 'lineWidth');
        this.appendDummyInput('lineColorHeader')
        .appendField('Color')
        .appendField(new FieldColour('#000000'), 'lineColor');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(230);
        this.setTooltip('Set line properties for the plot.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['color_select'] = {
    init: function () {
        this.appendDummyInput('colorHeader')
        .appendField('Color Select')
        .appendField(new FieldColour('#ff0000'), 'colorPicker');
        this.setOutput(true, null);
        this.setColour(240);
        this.setTooltip('Select a color.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['color_field'] = {
    init: function () {
        this.appendDummyInput('colorFieldHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Color Field');
        this.appendDummyInput('fieldTypeHeader')
        .appendField('Field Type')
        .appendField(new Blockly.FieldDropdown([
            ['Type A', 'typeA'],
            ['Type B', 'typeB']
            ]), 'fieldType');
        this.appendDummyInput('fieldHeader')
        .appendField('Field')
        .appendField(new Blockly.FieldDropdown([
            ['Option 1', 'option1'],
            ['Option 2', 'option2']
            ]), 'field');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(245);
        this.setTooltip('Select a field for coloring.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['colormap'] = {
    init: function () {
        this.appendDummyInput('colormapHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Colormap');
        this.appendDummyInput('mapHeader')
        .appendField('Colormap')
        .appendField(new Blockly.FieldDropdown([
            ['Jet', 'jet'],
            ['Viridis', 'viridis'],
            ['Plasma', 'plasma']
            ]), 'colormap');
        this.appendDummyInput('reverseHeader')
        .appendField('Reverse')
        .appendField(new Blockly.FieldCheckbox('FALSE'), 'reverse');
        this.appendDummyInput('directionHeader')
        .appendField('Direction')
        .appendField(new Blockly.FieldDropdown([
            ['Horizontal', 'horizontal'],
            ['Vertical', 'vertical']
            ]), 'direction');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(250);
        this.setTooltip('Set colormap properties.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['show_mass'] = {
    init: function () {
        this.appendDummyInput('massHeader')
        .appendField('Show Mass')
        .appendField(new Blockly.FieldCheckbox('FALSE'), 'showMass');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(255);
        this.setTooltip('Toggle visibility of mass in the plot.');
        this.setHelpUrl('');
    },
};

Blockly.Blocks['color_by_cluster'] = {
    init: function () {
        this.appendDummyInput('clusterHeader')
        .appendField('Color by Cluster');
        this.appendDummyInput('clusterOptions')
        .appendField(new Blockly.FieldDropdown([
            ['Cluster 1', 'cluster1'],
            ['Cluster 2', 'cluster2']
            ]), 'clusterType');
        this.setPreviousStatement(true, 'styling');
        this.setNextStatement(true, 'styling');
        this.setColour(255);
        this.setTooltip('Color plot based on cluster classification.');
        this.setHelpUrl('');
    },
};





///// histogram options ////////

Blockly.Blocks['histogram_options'] = {
    init: function () {
      // 1) Fields
      this.appendDummyInput()
        .appendField('Bin Width')
        .appendField(
          new Blockly.FieldNumber(1, 0, Infinity, 1),
          "binWidth"
        );
      this.appendDummyInput()
        .appendField('Num. bins')
        .appendField(
          new Blockly.FieldNumber(10, 1, 500, 1),
          "nBins"
        );
  
      // 2) Statement-chaining
      this.setPreviousStatement(true, 'histogramOptions');
      this.setNextStatement(true, 'histogramOptions');
  
      this.setTooltip('Specify bin width / num. bins for the histogram.');
      this.setHelpUrl('');
      this.setColour(285);
  
      // 3) We store a property for the histogram range
      //    If updateHistogramOptions fetches [min,max], we can store it here
      //    so that onChange can do the math.
      this.histRange = 1; // default, will be overwritten
  
      // 4) Track old values so we see which field changed
      this.oldBinWidth = this.getFieldValue('binWidth');
      this.oldNBins    = this.getFieldValue('nBins');
  
      // 5) OnChange
      this.setOnChange(function(event) {
        // If not on workspace or is in flyout, ignore
        if (!this.workspace || this.isInFlyout) return;
  
        // We only care about changes to *this* block's fields
        if (event.type === Blockly.Events.CHANGE && event.blockId === this.id && event.element === 'field') {
          // Which field was changed?
          const fieldName = event.name; // e.g. "binWidth" or "nBins"
          const newValue = this.getFieldValue(fieldName);
  
          const totalRange = this.histRange;
          if (totalRange <= 0) {
            console.warn("Histogram range is invalid or zero in size:", this.histRange);
            return;
          }
  
          if (fieldName === 'binWidth') {
            // user typed a new binWidth => recalc nBins
            // nBins = totalRange / binWidth
            const binWidthNum = parseFloat(newValue);
            if (binWidthNum > 0) {
              const computedNBins = Math.round(totalRange / binWidthNum);
              this.setFieldValue(computedNBins, 'nBins');
            }
          } else if (fieldName === 'nBins') {
            // user typed a new nBins => recalc binWidth
            const nBinsNum = parseFloat(newValue);
            if (nBinsNum > 0) {
              const computedBinWidth = totalRange / nBinsNum;
              // optionally round to some decimal
              this.setFieldValue(String(computedBinWidth), 'binWidth');
            }
          }
  
          // Finally, update old values
          this.oldBinWidth = this.getFieldValue('binWidth');
          this.oldNBins    = this.getFieldValue('nBins');
        }
      });
    }
  };
  


const styles = {
    init: function() {
        this.appendDummyInput('stylesHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Styles');
        this.appendDummyInput('themeHeader')
        .appendField('Theme')
        .appendField(new Blockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'NAME');
        this.appendValueInput('axisAndLabels')
        .appendField('Axis and Labels');
        this.appendValueInput('annotAndScale')
        .appendField('Annotations and Scale');
        this.appendValueInput('markersAndLines')
        .appendField('Markers and Lines');
        this.appendValueInput('coloring')
        .appendField('Coloring');
        this.appendValueInput('clusters')
        .appendField('Clusters');
        this.setInputsInline(true)
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(285);
    },
    onchange: function(event) {
        // Check if the event is a BLOCK_MOVE event and involves this block as the parent
        if (event.type === Blockly.Events.BLOCK_MOVE && event.newParentId === this.id) {
            // Only proceed if a new block is added to the 'styles' block
            const plotBlock = this.getSurroundParent();
            if (plotBlock && plotBlock.type === 'plot') {
                plotBlock.updateConnectedStyleBlocks();
            }
        }
    }
};
Blockly.common.defineBlocks({ styles: styles });

// Style Blocks
const axis_and_labels = {
    init: function() {
        this.appendDummyInput('axisHeader')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Axis and Labels');
        this.appendDummyInput('xLabelHeader')
        .appendField('X Label')
        .appendField(new Blockly.FieldTextInput(''), 'xLabel');
        this.appendDummyInput('xLimitsHeader')
        .appendField('X Limits')
        .appendField(new Blockly.FieldTextInput(''), 'xLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'xLimMax');
        this.appendDummyInput('xScaleHeader')
        .appendField('X Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['Symlog', 'symlog'],
            ]), 'xScaleDropdown');
        this.appendDummyInput('yLabelHeader')
        .appendField('Y Label')
        .appendField(new Blockly.FieldTextInput(''), 'yLabel');
        this.appendDummyInput('yLimitsHeader')
        .appendField('Y Limits')
        .appendField(new Blockly.FieldTextInput(''), 'yLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'yLimMax');
        this.appendDummyInput('yScaleHeader')
        .appendField('Y Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['Symlog', 'symlog'],
            ]), 'yScaleDropdown');
        this.appendDummyInput('zLabelHeader')
        .appendField('Z Label')
        .appendField(new Blockly.FieldTextInput(''), 'zLabel');
        this.appendDummyInput('axisRatioHeader')
        .appendField('Aspect Ratio')
        .appendField(new Blockly.FieldTextInput(''), 'aspectRatio');
        this.appendDummyInput('tickDirectionHeader')
        .appendField('Tick Direction')
        .appendField(new Blockly.FieldDropdown([
            ['out', 'out'],
            ['in', 'in'],
            ['inout', 'inout'],
            ['none', 'none']
            ]), 'tickDirectionDropdown');
        this.setInputsInline(false)
        this.setOutput(true, null);
        this.setTooltip('Adjust axis and labels of a plot');
        this.setHelpUrl('');
        this.setColour(285);
    }
};
Blockly.common.defineBlocks({axis_and_labels: axis_and_labels});
                        

const annot_and_scale = {
    init: function() {
        this.appendDummyInput('scaleDirection')
        .appendField('Scale direction')
        .appendField(new Blockly.FieldDropdown([
            ['none', 'none'],
            ['horizontal', 'horizontal']
            ]), 'scaleDirection');
        this.appendDummyInput('scaleLocation')
        .appendField('Scale location')
        .appendField(new Blockly.FieldDropdown([
            ['northeast', 'northeast'],
            ['northwest', 'northwest'],
            ['southwest', 'southwest'],
            ['southeast', 'southeast']
            ]), 'scaleLocation');
        this.appendDummyInput('scaleLength')
        .appendField('scale Length')
        .appendField(new Blockly.FieldTextInput(''), 'scaleLength');
        this.appendDummyInput('overlayColor')
        .appendField('Overlay color')
        .appendField(new FieldColour('#ff0000'), 'overlayColor');
        this.appendDummyInput('font')
        .appendField('Font')
        .appendField(new Blockly.FieldDropdown([
            ['none', 'none'],
            ['horizontal', 'horizontal']
            ]), 'font');
        this.appendDummyInput('fontSize')
        .appendField('Font size')
        .appendField(new Blockly.FieldNumber(11, 4, 100), 'fontSize');
        this.appendDummyInput('showMass')
        .appendField('Show mass')
        .appendField(new Blockly.FieldCheckbox('FALSE'), 'showMass');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(285);
    }
};
Blockly.common.defineBlocks({annot_and_scale: annot_and_scale});

const marks_and_lines = {
    init: function() {
        this.appendDummyInput('symbol')
        .appendField('Symbol')
        .appendField(new Blockly.FieldDropdown([
            ['circle', 'circle'],
            ['square', 'square'],
            ['diamond', 'diamond'],
            ['triangle (up)', 'triangleUp'],
            ['triangle (down)', 'triangleDown'],
            ['hexagon', 'hexagon'],
            ['pentagon', 'pentagon'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'symbol');
        this.appendDummyInput('size')
        .appendField('Size')
        .appendField(new Blockly.FieldNumber(6, 1, 50), 'size');
        this.appendDummyInput('symbolColorHeader')
        .appendField('Symbol Color')
        .appendField(new FieldColour('#ff0000'), 'symbolColor');
        this.appendDummyInput('transparency')
        .appendField('Transparency')
        .appendField(new Blockly.FieldNumber(100, 0, 100), 'transparency');
        this.appendDummyInput('lineWidth')
        .appendField('Line Width')
        .appendField(new Blockly.FieldDropdown([
            ['0', '0'],
            ['0.1', '0.1'],
            ['0.25', '0.25'],
            ['0.5', '0.5'],
            ['0.75', '0.75'],
            ['1', '1'],
            ['1.5', '1.5'],
            ['2', '2'],
            ['2.5', '2.5'],
            ['3', '3'],
            ['4', '4'],
            ['5', '5'],
            ['6', '6']
            ]), 'lineWidth');
        this.appendDummyInput('lineColor')
        .appendField('Line Color')
        .appendField(new FieldColour('#ff0000'), 'lineColor');
        this.appendDummyInput('lengthMultiplier')
        .appendField('Length multiplier')
        .appendField(new Blockly.FieldTextInput('1'), 'lengthMultiplier');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(225);
    }
};
Blockly.common.defineBlocks({marks_and_lines: marks_and_lines});
            
// const coloring = {
//     init: function() {
//         this.appendDummyInput('Coloring')
//         .setAlign(Blockly.inputs.Align.CENTRE)
//         .appendField('Coloring');
//         this.appendDummyInput('colorByField')
//         .appendField('Color by Field')
//         .appendField(new Blockly.FieldDropdown([
//             ['option', 'OPTIONNAME'],
//             ['option', 'OPTIONNAME'],
//             ['option', 'OPTIONNAME']
//             ]), 'colorByField');
//         this.appendDummyInput('field')
//         .appendField('Field')
//         .appendField(new Blockly.FieldDropdown([
//             ['option', 'OPTIONNAME'],
//             ['option', 'OPTIONNAME'],
//             ['option', 'OPTIONNAME']
//             ]), 'field');
//         this.appendDummyInput('resolution')
//         .appendField('Resolution')
//         .appendField(new Blockly.FieldNumber(10, 0), 'resolution');
//         this.appendDummyInput('colormap')
//         .appendField('Colormap')
//         .appendField(new Blockly.FieldDropdown([
//             ['option', 'OPTIONNAME'],
//             ['option', 'OPTIONNAME'],
//             ['option', 'OPTIONNAME']
//             ]), 'colormap');
//         this.appendDummyInput('reverse')
//         .appendField('Reverse')
//         .appendField(new Blockly.FieldCheckbox('FALSE'), 'reverse');
//         this.appendDummyInput('scale')
//         .appendField('Scale')
//         .appendField(new Blockly.FieldDropdown([
//             ['linear', 'linear'],
//             ['log', 'log'],
//             ]), 'cScale');
//         this.appendDummyInput('cLim')
//         .appendField('Clim')
//         .appendField(new Blockly.FieldTextInput(''), 'cLimMin')
//         .appendField(new Blockly.FieldTextInput(''), 'cLimMax');
//         this.appendDummyInput('cBarLabel')
//         .appendField('Cbar label')
//         .appendField(new Blockly.FieldTextInput(''), 'cBarLabel');
//         this.appendDummyInput('cBarDirection')
//         .appendField('Cbar direction')
//         .appendField(new Blockly.FieldDropdown([
//             ['none', 'none'],
//             ['Horizontal', 'horizontal'],
//             ['Vertical', 'vertical']
//             ]), 'cBarDirection');
//         this.setOutput(true, null);
//         this.setTooltip('');
//         this.setHelpUrl('');
//         this.setColour(225);
//     }
// };
// Blockly.common.defineBlocks({coloring: coloring});


/* alternatives */

const properties_v1 = {
    init: function() {
        // Reference Value Section
        this.appendDummyInput('refValueSection')
            .appendField('Reference Value')
            .appendField(new Blockly.FieldDropdown([
                ['Bulk Silicate Earth [MS95] McD', 'bulk_silicate_earth'],
                ['Option 2', 'option_2']
            ]), 'refValueDropdown');

        // Data Scaling Section
        this.appendDummyInput('dataScalingSection')
            .appendField('Data Scaling')
            .appendField(new Blockly.FieldDropdown([
                ['Linear', 'linear'],
                ['Logarithmic', 'logarithmic']
            ]), 'dataScalingDropdown');

        // Other sections grouped similarly...
        
        this.setInputsInline(false);
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Configure sample properties with grouped sections.');
        this.setHelpUrl('');
        this.setColour(160);
    }
};
Blockly.Blocks['properties_v1'] = properties_v1;

const data_scaling = {
    init: function() {
        this.appendDummyInput()
            .appendField('Data Scaling')
            .appendField(new Blockly.FieldDropdown([
                ['Linear', 'linear'],
                ['Logarithmic', 'logarithmic']
            ]), 'SCALING');
        this.setOutput(true, 'DataScaling');
        this.setColour(160);
        this.setTooltip('Selects data scaling method');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['data_scaling'] = data_scaling;

const autoscale_settings = {
    init: function() {
        this.appendDummyInput()
            .appendField('Autoscale Settings');
        // Add fields related to autoscaling
        this.setOutput(true, 'AutoscaleSettings');
        this.setColour(160);
        this.setTooltip('Configure autoscale settings');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['autoscale_settings'] = autoscale_settings;

const specify_plot_type = {
    init: function() {
        this.appendDummyInput()
            .appendField('Plot Type')
            .appendField(new Blockly.FieldDropdown([
                ['Field Map', 'field_map'],
                ['Histogram', 'histogram'],
                // ... other plot types
            ]), 'PLOT_TYPE');
        this.setOutput(true, 'PlotType');
        this.setColour(285);
        this.setTooltip('Specifies the plot type');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['specify_plot_type'] = specify_plot_type;


const plot_configuration = {
    init: function() {
        this.appendValueInput('PLOT_TYPE')
            .setCheck('PlotType')
            .appendField('Plot');
        this.appendValueInput('STYLE')
            .setCheck('Style')
            .appendField('With Style');
        this.appendValueInput('SAVE')
            .setCheck('SaveOptions')
            .appendField('And Save Options');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(285);
        this.setTooltip('Configures and renders the plot with specified settings.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['plot_configuration'] = plot_configuration;


const x_axis_settings = {
    init: function() {
        this.appendDummyInput()
            .appendField('X Axis Settings');
        this.appendDummyInput()
            .appendField('Label')
            .appendField(new Blockly.FieldTextInput('X-Axis'), 'X_LABEL');
        this.appendDummyInput()
            .appendField('Scale')
            .appendField(new Blockly.FieldDropdown([
                ['Linear', 'linear'],
                ['Log', 'log']
            ]), 'X_SCALE');
        this.appendDummyInput()
            .appendField('Limits')
            .appendField('Min')
            .appendField(new Blockly.FieldNumber(0), 'X_MIN')
            .appendField('Max')
            .appendField(new Blockly.FieldNumber(100), 'X_MAX');
        this.setOutput(true, 'XAxisSettings');
        this.setColour(285);
        this.setTooltip('Settings for X axis');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['x_axis_settings'] = x_axis_settings;


const y_axis_settings = {
    init: function() {
        this.appendDummyInput()
            .appendField('Y Axis Settings');
        this.appendDummyInput()
            .appendField('Label')
            .appendField(new Blockly.FieldTextInput('Y-Axis'), 'Y_LABEL');
        this.appendDummyInput()
            .appendField('Scale')
            .appendField(new Blockly.FieldDropdown([
                ['Linear', 'linear'],
                ['Log', 'log']
            ]), 'Y_SCALE');
        this.appendDummyInput()
            .appendField('Limits')
            .appendField('Min')
            .appendField(new Blockly.FieldNumber(0), 'Y_MIN')
            .appendField('Max')
            .appendField(new Blockly.FieldNumber(100), 'Y_MAX');
        this.setOutput(true, 'YAxisSettings');
        this.setColour(285);
        this.setTooltip('Settings for Y axis');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['y_axis_settings'] = y_axis_settings;

const data_filtering = {
    init: function() {
        this.appendValueInput('FIELD')
            .setCheck('String')
            .appendField('Filter Data where');
        this.appendDummyInput()
            .appendField(new Blockly.FieldDropdown([
                ['>', '>'],
                ['<', '<'],
                ['=', '='],
                ['≠', '!='],
                ['≥', '>='],
                ['≤', '<=']
            ]), 'OPERATOR');
        this.appendValueInput('VALUE')
            .setCheck('Number')
            .appendField('Value');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(300);
        this.setTooltip('Filters data based on the specified condition.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['data_filtering'] = data_filtering;

Blockly.Blocks['save_plot'] = {
  init: function() {
    this.appendDummyInput().appendField("save plot");

     // Minimal change-dir dropdown used as a button
    const changeDir = new Blockly.FieldDropdown([["current path","IDLE"], ["change…","CHANGE"]], (v) => {
      if (v !== "CHANGE") return v;           // only act on explicit select
      const f = this.getField('DIRECTORY');
      const cur = (f ? f.getValue() : "") || "";
      const r = window.blocklyBridge.selectDirectory(cur);
      (r && typeof r.then === 'function') ? r.then(p => { if (p) f.setValue(p); updateSavePlotPreview(this); this.getField('CHANGE_DIR')?.setValue('IDLE'); })
                                    : (r && f.setValue(r));
      this.getField('CHANGE_DIR')?.setValue('IDLE');  // reset to neutral
      updateSavePlotPreview(this);
      return 'IDLE';
    });
    
    this.appendDummyInput()
        .appendField("directory")
        .appendField(new Blockly.FieldTextInput("path/to/folder"), "DIRECTORY")
        .appendField(changeDir, "CHANGE_DIR");
    changeDir.setValue('IDLE');  // neutral default

    this.appendDummyInput()
        .appendField("basename")
        .appendField(new Blockly.FieldTextInput(""), "BASENAME");

    this.appendDummyInput()
        .appendField(new Blockly.FieldCheckbox("TRUE"), "SAVE_FIGURE")
        .appendField("save figure as")
        .appendField(new Blockly.FieldDropdown([
          ["png","png"], ["jpg","jpg"], ["svg","svg"], ["pdf","pdf"]
        ]), "FIG_TYPE");

    this.appendDummyInput()
        .appendField(new Blockly.FieldCheckbox("TRUE"), "SAVE_DATA")
        .appendField("save data as")
        .appendField(new Blockly.FieldDropdown([
          ["csv","csv"], ["xlsx","xlsx"], ["parquet","parquet"]
        ]), "DATA_TYPE");

    // Live preview labels (use Serializable so we can update text)
    this.appendDummyInput()
        .appendField("figure path:")
        .appendField(new Blockly.FieldLabelSerializable("—"), "FIG_PREVIEW");

    this.appendDummyInput()
        .appendField("data path:")
        .appendField(new Blockly.FieldLabelSerializable("—"), "DATA_PREVIEW");

    this.setPreviousStatement(true, null);
    this.setNextStatement(true, null);
    this.setColour(230);
    this.setTooltip("Save current canvas figure and/or data to disk.");
    this.setHelpUrl("");

    // Fetch default dir once the block is created
    setDefaultSaveDir(this);

    // Live updates when any relevant field changes
    const block = this;
    this.setOnChange(function(e) {
      // Only recompute on field changes to our block
      if (!e || e.blockId !== block.id) return;
      updateSavePlotPreview(block);
    });
  }
};



const profiling = {
    init: function() {
        this.appendDummyInput()
            .appendField('Profiling');
        this.appendDummyInput()
            .appendField('Profile Name')
            .appendField(new Blockly.FieldTextInput('Profile1'), 'PROFILE_NAME');
        this.appendDummyInput()
            .appendField('Sort Axis')
            .appendField(new Blockly.FieldDropdown([
                ['X', 'x'],
                ['Y', 'y']
            ]), 'SORT_AXIS');
        this.appendDummyInput()
            .appendField('Radius')
            .appendField(new Blockly.FieldNumber(10, 0), 'RADIUS');
        this.appendDummyInput()
            .appendField('Threshold')
            .appendField(new Blockly.FieldNumber(0), 'THRESHOLD');
        this.appendDummyInput()
            .appendField('Interpolation Distance')
            .appendField(new Blockly.FieldNumber(1, 0), 'INT_DISTANCE');
        this.appendDummyInput()
            .appendField('Point Error')
            .appendField(new Blockly.FieldDropdown([
                ['Median + IQR', 'median'],
                ['Mean + Standard Error', 'mean']
            ]), 'POINT_ERROR');
        this.appendValueInput('FIELDS')
            .setCheck('Array')
            .appendField('Fields');
        this.appendDummyInput()
            .appendField('Number of Subplots')
            .appendField(new Blockly.FieldNumber(1, 1), 'NUM_SUBPLOTS');
        this.appendDummyInput()
            .appendField('Interpolate Points')
            .appendField(new Blockly.FieldCheckbox('FALSE'), 'INTERPOLATE');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(160);
        this.setTooltip('Performs profiling with specified settings.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['profiling'] = profiling;
