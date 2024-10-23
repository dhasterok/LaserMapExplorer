import * as Blockly from 'blockly/core';
import {registerFieldColour, FieldColour} from '@blockly/field-colour';
registerFieldColour();
import { sample_ids } from './globals';

var enableSampleIDsBlock = false; // Initially false
window.Blockly = Blockly.Blocks
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


// Function to enable the block
export function enableSampleIDsBlockFunction() {
    let workspace = Blockly.getMainWorkspace()
    enableSampleIDsBlock = true;

    // Re-register the block definition
    Blockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;
    Blockly.Blocks['select_samples'] = select_samples;
    Blockly.Blocks['analyte_map'] = analyte_map;
    Blockly.Blocks['iterate_sample_ids'] = iterate_sample_ids;
    Blockly.Blocks['sample_ids_list_block'] = sample_ids_list_block;

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

// Block: Plot 
const plot = {
    init: function() {
        this.appendDummyInput('plot_header')
        .setAlign(Blockly.inputs.Align.CENTRE)
        .appendField('Plot ');
        this.appendValueInput('plot_type')
        .appendField('Plot type');
        this.setPreviousStatement(true, null);
        this.setNextStatement(true, null);
        this.setTooltip('add plot type block');
        this.setHelpUrl('');
        this.setColour(285);
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    },
    onchange: function() {
        // Get the block attached to the 'plot_type' input
        const connectedBlock = this.getInputTargetBlock('plot_type');

        // Check if a block is connected
        if (connectedBlock) {
            // Get the type of the connected block and store it in a variable
            const plotType = connectedBlock.type;
            console.log('Connected plot type block:', plotType);  // Debugging log

            // Store the connected block's type in a Blockly variable 'PLOT_TYPE'
            const workspace = this.workspace;
            const variable = workspace.getVariable('PLOT_TYPE');
            if (variable) {
                // Update the variable with the connected block's type
                workspace.getVariableMap().getVariable('PLOT_TYPE').name = plotType;
            } else {
                // Create the variable if it doesn't exist yet
                workspace.createVariable('PLOT_TYPE', null, plotType);
            }
        } else {
            console.log('No block connected to plot_type');
        }
    }
};
Blockly.common.defineBlocks({plot: plot});
          
const analyte_map = {
    init: function() {
        this.appendDummyInput('plot_map_header')
        .appendField('Plot Map');
        this.appendValueInput('style')
        .appendField('Style');
        this.appendValueInput('save')
        .appendField('Save '); 
        this.setOutput(true, null);
        this.setTooltip('plot 2d image of analyte');
        this.setHelpUrl('');
        this.setColour(285);
        if (!enableSampleIDsBlock) {
            this.setDisabledReason(true, "no_sample_ids");
        }
    }
};
Blockly.common.defineBlocks({analyte_map: analyte_map});

// Style Blocks
const axisAndLabels = {
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
        .appendField(new Blockly.FieldTextInput(''), 'xLimMin');
        this.appendDummyInput('xScaleHeader')
        .appendField('X Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['option', 'OPTIONNAME']
            ]), 'xAxisDropdown');
        this.appendDummyInput('yLabelHeader')
        .appendField('Y Label')
        .appendField(new Blockly.FieldTextInput(''), 'yLabel');
        this.appendDummyInput('yLimitsHeader')
        .appendField('Y Limits')
        .appendField(new Blockly.FieldTextInput(''), 'yLimMin')
        .appendField(new Blockly.FieldTextInput(''), 'yLimMin');
        this.appendDummyInput('xScaleHeader')
        .appendField('Y Scale')
        .appendField(new Blockly.FieldDropdown([
            ['Linear', 'linear'],
            ['Log', 'log'],
            ['Logit', 'logit'],
            ['option', 'OPTIONNAME']
            ]), 'yAxisDropdown');
        this.appendDummyInput('zLabelHeader')
        .appendField('Z Label')
        .appendField(new Blockly.FieldTextInput(''), 'zLabel');
        this.appendDummyInput('zLabelHeader')
        .appendField('Tick Direction')
        .appendField(new Blockly.FieldDropdown([
            ['out', 'out'],
            ['in', 'in'],
            ['inout', 'inout'],
            ['none', 'none']
            ]), 'yAxisDropdown');
        this.setInputsInline(false)
        this.setOutput(true, null);
        this.setTooltip('Adjust axis and labels of a plot');
        this.setHelpUrl('');
        this.setColour(285);
    }
};
Blockly.common.defineBlocks({axisAndLabels: axisAndLabels});
                        
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
        this.appendValueInput('axisAndLabelInput')
        .appendField('Axis and Labels');
        this.appendValueInput('annotAndScaleInput')
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
    }
};
Blockly.common.defineBlocks({styles: styles});

const annotAndScale = {
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
        .appendField(new Blockly.FieldNumber(11, 4, 100), 'NAME');
        this.appendDummyInput('showMass')
        .appendField('Show mass')
        .appendField(new Blockly.FieldCheckbox('FALSE'), 'showMass');
        this.setOutput(true, null);
        this.setTooltip('');
        this.setHelpUrl('');
        this.setColour(285);
    }
};
Blockly.common.defineBlocks({annotAndScale: annotAndScale});

const marksAndLines = {
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
        this.appendDummyInput('transparency')
        .appendField('Transparency')
        .appendField(new Blockly.FieldNumber(100, 0, 100), 'size');
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
Blockly.common.defineBlocks({marksAndLines: marksAndLines});
            
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
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME'],
            ['option', 'OPTIONNAME']
            ]), 'scale');
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
