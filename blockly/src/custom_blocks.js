import * as Blockly from 'blockly/core';
import {registerFieldColour, FieldColour} from '@blockly/field-colour';
registerFieldColour();
import { sample_ids, baseDir } from './globals';
import {dynamicStyleUpdate} from './helper_functions'
var enableSampleIDsBlock = false; // Initially false
window.Blockly = Blockly.Blocks

/*
Summary of Naming Conventions:
Field Names: Camel case (plotType).
Variable Names (js): Camel case (plotType).
Block Type Names: Snake case (set_plot_type).
Block Input Names: Snake case (set_plot_type).
*/

//// I/O //// 
const load_directory = {
    init: function() {
        this.appendValueInput('DIR')
            .setCheck('String')
            .appendField('load files from directory')
            .appendField(new Blockly.FieldTextInput('directory name'), 'DIR');
        this.setNextStatement(true, null);
        this.setTooltip('Loads files from a directory');
        this.setHelpUrl('');
        this.setColour(225);
    }
};
Blockly.Blocks['load_directory'] = load_directory;
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
    Blockly.Blocks['iterate_sample_ids'] = iterate_sample_ids;

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

 // Block: Iterate Through Sample IDs
 const iterate_sample_ids = {
    init: function() {
        this.appendDummyInput()
            .appendField("for each sample ID in")
            .appendField(new Blockly.FieldVariable("sample_ids"), "SAMPLE_IDS");

        this.appendStatementInput("DO")
            .appendField("do");

        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(230);
        this.setTooltip('Iterate through each sample ID in the sample_ids list');
        this.setHelpUrl('');
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};
Blockly.common.defineBlocks({ iterate_sample_ids: iterate_sample_ids });

// Define the select_analytes block
const select_analytes = {
    init: function() {
      this.appendDummyInput('NAME')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Select analytes');
  
      // Initialize with a placeholder dropdown
      this.appendDummyInput('NAME')
        .appendField(new Blockly.FieldLabelSerializable('Analyte list'), 'NAME')
        .appendField(new Blockly.FieldDropdown([['Loading...', '']]), 'ANALYTELISTDROPDOWN')
        .appendField(new Blockly.FieldImage(`${baseDir}/resources/icons/icon-atom-64.svg`, 15, 15, { alt: '*', flipRtl: 'FALSE' }));
  
      this.setPreviousStatement(true, null);
      this.setNextStatement(true, null);
      this.setTooltip('');
      this.setHelpUrl('');
      this.setColour(225);
  
      // Populate dropdown asynchronously
      this.updateAnalyteOptions();
    },
  
    // Function to update the analyte options asynchronously
    updateAnalyteOptions: function() {
      // Call the Python function getAnalyteList through the WebChannel
      window.blocklyBridge.getAnalyteList().then((response) => {
        // Map the response to the required format for Blockly dropdowns
        const options = response.map(option => [option, option]);
        const dropdown = this.getField('ANALYTELISTDROPDOWN');
        if (dropdown){
            // Clear existing options and add new ones
        dropdown.menuGenerator_ = options;
        dropdown.setValue(options[0][1]);  // Set the first option as the default
        dropdown.forceRerender();  // Refresh dropdown to display updated options
        }
        

      }).catch(error => {
        console.error('Error fetching analyte list:', error);
      });
    }
  };
  
  Blockly.common.defineBlocks({ select_analytes: select_analytes });
  
                      

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

const scatter_and_heatmaps = {
    init: function() {
        this.appendDummyInput('header')
            .appendField('Scatter and Heatmaps')
            .setAlign(Blockly.inputs.Align.CENTRE)

        // Biplot and ternary section
        this.appendDummyInput('biplotHeader')
            .appendField('Biplot and Ternary')
            .setAlign(Blockly.inputs.Align.CENTRE);

        this.appendDummyInput('analyteX')
            .appendField('Analyte X')
            .appendField(new Blockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCA Score', 'PCA Score'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteX', 'analyteXType')
        ), 'analyteXType')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'analyteX');

        this.appendDummyInput('analyteY')
            .appendField('Analyte Y')
            .appendField(new Blockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCA Score', 'PCA Score'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteY', 'analyteYType')), 'analyteYType')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'analyteY');

        this.appendDummyInput('analyteZ')
            .appendField('Analyte Z')
            .appendField(new Blockly.FieldDropdown([['Analyte', 'Analyte'], ['Analyte (Normalised)', 'Analyte (Normalised)'],['PCA Score', 'PCA Score'], ['Cluster', 'Cluster']],this.updateAnalyteDropdown.bind(this, 'analyteZ', 'analyteZType')), 'analyteZType')
            .appendField(new Blockly.FieldDropdown([['Select...', '']]), 'analyteZ');

        this.appendDummyInput('preset')
            .appendField('Preset')
            .appendField(new Blockly.FieldDropdown([['Select preset', 'default'], ['Custom preset', 'custom']]), 'preset');

        this.appendDummyInput('heatmaps')
            .appendField('Heatmaps')
            .appendField(new Blockly.FieldDropdown([['counts', 'counts'], ['counts, median', 'counts, median'], ['median', 'median'], ['counts, mean, std', 'counts, mean, std']]), 'heatmapType');

        // Map from ternary section
        this.appendDummyInput('mapHeader')
            .appendField('Map from Ternary')
            .setAlign(Blockly.inputs.Align.CENTRE);

        this.appendDummyInput('colormap')
            .appendField('Colormap')
            .appendField(new Blockly.FieldDropdown([['yellow-red-blue', 'yellow-red-blue'], ['viridis', 'viridis'], ['plasma', 'plasma']]), 'colormap');

        // Colors selection
        this.appendDummyInput('colors')
            .appendField('Colors')
            .appendField(new FieldColour('#FFFF00'), 'colorX')
            .appendField('X')
            .appendField(new FieldColour('#FF0000'), 'colorY')
            .appendField('Y')
            .appendField(new FieldColour('#0000FF'), 'colorZ')
            .appendField('Z')
            .appendField(new Blockly.FieldCheckbox('FALSE'), 'colorM')
            .appendField('M');

        this.setInputsInline(false);
        this.setTooltip('Configure scatter and heatmap settings.');
        this.setHelpUrl('');
        this.setColour(160);  // Adjust color as needed
        this.setOutput(true, null);
    },
    updateAnalyteDropdown: function(analyteField, analyteTypeField) {
        const analyteType = this.getFieldValue(analyteTypeField);

        // Call the Python function getFieldList through the WebChannel, handle as a promise
        window.blocklyBridge.getFieldList(analyteType).then((response) => {
            const options = response.map(option => [option, option]);
            const dropdown = this.getField(analyteField);

            // Clear existing options and add new ones
            dropdown.menuGenerator_ = options;
            dropdown.setValue(options[0][1]);  // Set the first option as the default
            dropdown.forceRerender();  // Refresh dropdown to display updated options
        }).catch(error => {
            console.error('Error fetching field list:', error);
        });
    }
};
Blockly.common.defineBlocks({ scatter_and_heatmaps: scatter_and_heatmaps });


// Block: Plot 
const plot = {
    init: function() {
        // Style and Save inputs
        this.appendValueInput('analysisType')
            .appendField('Analysis type');
        this.appendDummyInput('plot_header')
            .setAlign(Blockly.inputs.Align.CENTRE)
            .appendField('Plot type')
            .appendField(new Blockly.FieldDropdown([
                ['Analyte Map', 'analyte map'],
                ['Histogram', 'histogram'],
                ['Correlation', 'correlation'],
                ['Gradient Map', 'gradient map'],
                ['Scatter', 'scatter'],
                ['Heatmap', 'heatmap'],
                ['Ternary Map', 'ternary map'],
                ['TEC', 'tec'],
                ['Radar', 'radar'],
                ['Variance', 'variance'],
                ['Vectors', 'vectors'],
                ['PCA Scatter', 'pca scatter'],
                ['PCA Heatmap', 'pca heatmap'],
                ['PCA Score', 'pca score'],
                ['Clusters', 'clusters'],
                ['Cluster Score', 'cluster score'],
                ['Profile', 'profile']
            ]), 'plot_type_dropdown');
        
        // Style and Save inputs
        this.appendValueInput('style')
            .appendField('Style');
        this.appendValueInput('save')
            .appendField('Save');
        
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('Configure and render a plot with specified type and settings.');
        this.setHelpUrl('');
        this.setColour(285);
        this.setInputsInline(false)
        // Initialize internal properties
        this.plotType = null;
        this.connectedStyleBlocks = {}; // To store references to connected style blocks

        // Automatically disable the block if sample IDs are not enabled
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    },

    onchange: function() {
        const selectedPlotType = this.getFieldValue('plot_type_dropdown');
        if (selectedPlotType && selectedPlotType !== this.plotType) {
            this.plotType = selectedPlotType;
            console.log()
            this.updateConnectedStyleBlocks();
        } 
    },

    updateConnectedStyleBlocks: function() {
        // Get the style block connected to the 'style' input
        const styleBlock = this.getInputTargetBlock('style');
        
        if (styleBlock && styleBlock.type === 'styles') {
            const connectedBlocks = this.getStyleSubBlocks(styleBlock);
            this.connectedStyleBlocks = connectedBlocks;

            // Trigger style updates
            dynamicStyleUpdate(this.plotType, connectedBlocks);
        }
        else{
            this.plotType = null;
            this.clearConnectedStyleBlocks();
        }
    },

    clearConnectedStyleBlocks: function() {
        this.connectedStyleBlocks = {};
    },

    getStyleSubBlocks: function(styleBlock) {
        const connectedBlocks = {};

        ['axisAndLabels', 'annotAndScale', 'marksAndLines', 'coloring'].forEach((type) => {
            const subBlock = styleBlock.getInputTargetBlock(type);
            if (subBlock) connectedBlocks[type] = subBlock;
        });

        return connectedBlocks;
    }
};
Blockly.common.defineBlocks({ plot: plot });

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
            
const coloring = {
    init: function() {
        this.appendDummyInput('Coloring')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Coloring');
        this.appendDummyInput('colorByField')
        .appendField('Color by Field')
        .appendField(new Blockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'colorByField');
        this.appendDummyInput('field')
        .appendField('Field')
        .appendField(new Blockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'field');
        this.appendDummyInput('resolution')
        .appendField('Resolution')
        .appendField(new Blockly.FieldNumber(10, 0), 'resolution');
        this.appendDummyInput('colormap')
        .appendField('Colormap')
        .appendField(new Blockly.FieldDropdown([
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'colormap');
        this.appendDummyInput('reverse')
        .appendField('Reverse')
        .appendField(new Blockly.FieldCheckbox('FALSE'), 'reverse');
        this.appendDummyInput('scale')
        .appendField('Scale')
        .appendField(new Blockly.FieldDropdown([
            ['linear', 'linear'],
            ['log', 'log'],
            ]), 'cScale');
        this.appendDummyInput('cLim')
        .appendField('Clim')
        .appendField(new Blockly.FieldTextInput(''), 'cLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'cLimMax');
        this.appendDummyInput('cBarLabel')
        .appendField('Cbar label')
        .appendField(new Blockly.FieldTextInput(''), 'cBarLabel');
        this.appendDummyInput('cBarDirection')
        .appendField('Cbar direction')
        .appendField(new Blockly.FieldDropdown([
            ['none', 'none'],
            ['Horizontal', 'horizontal'],
            ['Vertical', 'vertical']
            ]), 'cBarDirection');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(225);
    }
};
Blockly.common.defineBlocks({coloring: coloring});


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

const reference_value = {
    init: function() {
        this.appendDummyInput()
            .appendField('Reference Value')
            .appendField(new Blockly.FieldDropdown([
                ['Bulk Silicate Earth [MS95] McD', 'bulk_silicate_earth'],
                ['Option 2', 'option_2']
            ]), 'REF_VALUE');
        this.setOutput(true, 'ReferenceValue');
        this.setColour(160);
        this.setTooltip('Selects a reference value');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['reference_value'] = reference_value;

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
                ['Analyte Map', 'analyte_map'],
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
        this.setColour(200);
        this.setTooltip('Filters data based on the specified condition.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['data_filtering'] = data_filtering;

const correlation_analysis = {
    init: function() {
        this.appendDummyInput()
            .setCheck('String')
            .appendField('Correlation');
        this.appendDummyInput()
            .appendField('Method')
            .appendField(new Blockly.FieldDropdown([
                ['Pearson', 'pearson'],
                ['Spearman', 'spearman'],
                ['Kendall', 'kendall']
            ]), 'METHOD');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(210);
        this.setTooltip('Performs correlation analysis between two variables.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['correlation_analysis'] = correlation_analysis;

const clustering = {
    init: function() {
        this.appendDummyInput()
            .appendField('Perform Clustering using')
            .appendField(new Blockly.FieldDropdown([
                ['K-Means', 'k_means'],
                ['Hierarchical', 'hierarchical'],
                ['DBSCAN', 'dbscan'],
                ['Gaussian Mixture', 'gmm']
            ]), 'CLUSTERING_METHOD');
        this.appendValueInput('PARAMETERS')
            .setCheck('ClusterParameters')
            .appendField('Parameters');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(230);
        this.setTooltip('Clusters the data using the selected method.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['clustering'] = clustering;

const export_data = {
    init: function() {
        this.appendDummyInput()
            .appendField('Export Data as')
            .appendField(new Blockly.FieldDropdown([
                ['CSV', 'csv'],
                ['Excel', 'excel'],
                ['JSON', 'json'],
                ['XML', 'xml']
            ]), 'FILE_TYPE');
        this.appendDummyInput()
            .appendField('File Name')
            .appendField(new Blockly.FieldTextInput('data_export'), 'FILE_NAME');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setColour(60);
        this.setTooltip('Exports data to the specified file type.');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['export_data'] = export_data;

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

const scatter_plot_settings = {
    init: function() {
        this.appendDummyInput()
            .appendField('Scatter Plot Settings');
        // Fields for Analyte X, Y, Z
        this.setOutput(true, 'ScatterSettings');
        this.setColour(160);
        this.setTooltip('Settings for scatter plots');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['scatter_plot_settings'] = scatter_plot_settings;


const heatmap_settings = {
    init: function() {
        this.appendDummyInput()
            .appendField('Heatmap Settings');
        // Fields for heatmap types and options
        this.setOutput(true, 'HeatmapSettings');
        this.setColour(160);
        this.setTooltip('Settings for heatmaps');
        this.setHelpUrl('');
    }
};
Blockly.Blocks['heatmap_settings'] = heatmap_settings;
