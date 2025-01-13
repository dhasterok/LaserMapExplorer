/******************************
 * Helper Functions
 ******************************/
import * as Blockly from 'blockly/core';
import * as BlockDynamicConnection from '@blockly/block-dynamic-connection';
import { sample_ids,fieldTypeList, updateSampleIds, spot_data } from './globals';
import {enableSampleIDsBlockFunction} from './custom_blocks'

// Function: Update Sample Dropdown with IDs
function updateSampleDropdown(sampleIds) {
    // Step 1: Store sample IDs in the global variableaxis_and_labels
    updateSampleIds(sampleIds);
    // Step 2: Enable dependent blocks now that sample_ids is populated
    enableSampleIDsBlockFunction();
    // Step 3: Update the dropdown options in the 'select_samples' block
    const dropdownOptions = sampleIds.map(id => [id, id]);  // Convert sample IDs to dropdown format

    // Iterate through all blocks and update the 'select_samples' block dropdown
    Blockly.getMainWorkspace().getAllBlocks().forEach(function(block) {
        if (block.type === 'select_samples') {
            const dropdownField = block.getField('SAMPLE_IDS');
            if (dropdownField) {
                // Update the dropdown options dynamically
                dropdownField.menuGenerator_ = dropdownOptions;
                dropdownField.setValue(sampleIds.length ? sampleIds[0] : 'NONE');  // Set default value
                block.render();  // Re-render the block to reflect the changes
            }
        }
    });

    console.log("Dropdown updated with sample IDs:", dropdownOptions);
}
window.updateSampleDropdown = updateSampleDropdown;

// Global function to refresh the analyteSavedListsDropdown
function refreshAnalyteSavedListsDropdown() {
    // Iterate through all blocks to find 'select_analytes' blocks
    Blockly.getMainWorkspace().getAllBlocks().forEach(function(block) {
        if (block.type === 'select_analytes') {
            // Get the current selection
            const analyteSelectorValue = block.getFieldValue('analyteSelectorDropdown');
            if (analyteSelectorValue === 'Saved lists') {
                const savedListDropdown = block.getField('analyteSavedListsDropdown');
                const currentSelection = savedListDropdown ? savedListDropdown.getValue() : null;
                // Update the saved lists dropdown while preserving selection
                block.updateSavedListsDropdown(currentSelection);
            }
        }
    });
}

window.refreshAnalyteSavedListsDropdown = refreshAnalyteSavedListsDropdown;


// Global function to refresh the analyteSavedListsDropdown
function refreshCustomFieldListsDropdown() {
    // Iterate through all blocks to find 'select_analytes' blocks
    Blockly.getMainWorkspace().getAllBlocks().forEach(function(block) {
        if (block.type === 'select_custom_lists') {
            // Get the current selection
            const analyteSelectorValue = block.getFieldValue('fieldSelectorDropdown');
            if (analyteSelectorValue === 'Saved lists') {
                const savedListDropdown = block.getField('fieldSavedListsDropdown');
                const currentSelection = savedListDropdown ? savedListDropdown.getValue() : null;
                // Update the saved lists dropdown while preserving selection
                block.updateSavedListsDropdown(currentSelection);
            }
        }
    });
}

window.refreshCustomFieldListsDropdown = refreshCustomFieldListsDropdown;

function updateFieldTypeList(newFieldTypeList) {
    // Clear the existing array
    fieldTypeList.length = 0;

    // Populate with new values
    newFieldTypeList.forEach(item => fieldTypeList.push([item, item]));

    // Update the dropdown options in existing blocks
    const blocks = Blockly.getMainWorkspace().getAllBlocks();
    for (const block of blocks) {
        // If the block has a field named 'fieldType'
        const field = block.getField('fieldType');
        if (field) {
            // Get the currently selected value
            const currentValue = field.getValue();
            // Update the field's options
            //field.setOptions(fieldTypeList); #automatically updated
            // If the current value is still in the options, keep it selected
            const values = fieldTypeList.map(option => option[1]);
            if (values.includes(currentValue)) {
                field.setValue(currentValue);
            } else {
                // Else set to the first option
                field.setValue(values[0]);
            }
        }
    }
}
window.updateFieldTypeList = updateFieldTypeList;

// Function to dynamically update connected style blocks
export function dynamicStyleUpdate(plotType, connectedBlocks) {
    // Call the backend to get updated styles for the specific plot type
    console.log(connectedBlocks)
    window.blocklyBridge.callSetStyleWidgets(plotType, function(style) {
        if (style.constructor === Object && Object.keys(style).length === 0){
            console.warn("Style dictionary not provided for plotType:", plotType);
            return; // Exit if style is not available
        }
        else{
            console.log('updating styles')
            Object.entries(connectedBlocks).forEach(([blockType, block]) => {
                updateFieldsBasedOnPlotType(plotType, block); // Adjust fields per plot type
                switch (blockType) {
                    case 'styles':
                        updateStylesBlock(block, style);
                        break;
                    case 'axis_and_labels':
                        updateAxisAndLabelsBlock(block, style);
                        break;
                    case 'annot_and_scale':
                        updateAnnotAndScaleBlock(block, style);
                        break;
                    case 'marks_and_lines':
                        updateMarksAndLinesBlock(block, style);
                        break;
                    case 'coloring':
                        updateColoringBlock(block, style);
                        break;
                }
            });
        };
    });
}

// Function to update fields based on plot type in style blocks
function updateFieldsBasedOnPlotType(plotType, block) {
    switch (plotType) {
        case 'analyte map' | 'gradient map':
                // Reset all fields to default visibility and enabled state
            switch (block.type){
                case 'axisAndLabels':
                    block.getField('xLabel').setVisible(false);
                    block.getField('xLimMin').setVisible(true);
                    block.getField('xLimMax').setVisible(true);
                    block.getField('xScaleDropdown').setVisible(false);
                    block.getField('yLabel').setVisible(false);
                    block.getField('yLimMin').setVisible(true);
                    block.getField('yLimMax').setVisible(true);
                    block.getField('yScaleDropdown').setVisible(false);
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(false);
                    block.getField('tickDirectionDropdown').setVisible(false);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(true);
                    block.getField('scaleLocation').setVisible(true);
                    block.getField('scaleLength').setVisible(true);
                    block.getField('overlayColor').setVisible(true);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    if (spot_data){
                        block.getField('symbol').setVisible(true);
                        block.getField('size').setVisible(true);
                        block.getField('symbolColor').setVisible(true);
                        block.getField('transparency').setVisible(true);
                    }
                    else{
                        block.getField('symbol').setVisible(false);
                        block.getField('size').setVisible(false);
                        block.getField('symbolColor').setVisible(false);
                        block.getField('transparency').setVisible(false);
                    }

                    // Line properties
                    block.getField('lineWidth').setVisible(true);
                    block.getField('lineColor').setVisible(true);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    block.getField('colorByField').setVisible(true);
                    block.getField('field').setVisible(true);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(true);
                    block.getField('reverse').setVisible(true);
                    block.getField('cScale').setVisible(true);
                    block.getField('cLimMin').setVisible(true);
                    block.getField('cLimMax').setVisible(true);
                    block.getField('cBarLabel').setVisible(true);
                    block.getField('cBarDirection').setVisible(true);
                    break;
            };
        case 'correlation' | 'vectors':
            switch (block.type){
                case 'axis_and_labels':
                    block.getField('xLabel').setVisible(false);
                    block.getField('xLimMin').setVisible(false);
                    block.getField('xLimMax').setVisible(false);
                    block.getField('xScaleDropdown').setVisible(false);
                    block.getField('yLabel').setVisible(false);
                    block.getField('yLimMin').setVisible(false);
                    block.getField('yLimMax').setVisible(false);
                    block.getField('yScaleDropdown').setVisible(false);
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(false);
                    block.getField('tickDirectionDropdown').setVisible(true);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(false);
                    block.getField('scaleLocation').setVisible(false);
                    block.getField('scaleLength').setVisible(false);
                    block.getField('overlayColor').setVisible(false);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    block.getField('symbol').setVisible(false);
                    block.getField('size').setVisible(false);
                    block.getField('symbolColor').setVisible(false);
                    block.getField('transparency').setVisible(false);
                    // Line properties
                    block.getField('lineWidth').setVisible(false);
                    block.getField('lineColor').setVisible(false);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    if (plotType ==='correlation'){
                        block.getField('colorByField').setVisible(true);
                        if (block.getFieldValue('colorByField') == 'cluster'){
                            block.getField('field').setVisible(true);
                        }
                        else{
                            block.getField('field').setVisible(false);
                        }
                    }
                    else {
                        block.getField('colorByField').setVisible(false);
                        block.getField('field').setVisible(false);
                    }
                    block.getField('colorByField').setVisible(true);
                    block.getField('field').setVisible(false);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(true);
                    block.getField('reverse').setVisible(true);
                    block.getField('cScale').setVisible(false);
                    block.getField('cLimMin').setVisible(true);
                    block.getField('cLimMax').setVisible(true);
                    block.getField('cBarLabel').setVisible(false);
                    block.getField('cBarDirection').setVisible(true);
                    break;
            }
        case 'histogram':
            switch (block.type){
                case 'axis_and_labels':
                    block.getField('xLabel').setVisible(true);
                    block.getField('xLimMin').setVisible(true);
                    block.getField('xLimMax').setVisible(true);
                    block.getField('xScaleDropdown').setVisible(true);
                    block.getField('yLabel').setVisible(true);
                    block.getField('yLimMin').setVisible(true);
                    block.getField('yLimMax').setVisible(true);
                    block.getField('yScaleDropdown').setVisible(false);
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(true);
                    block.getField('tickDirectionDropdown').setVisible(true);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(false);
                    block.getField('scaleLocation').setVisible(false);
                    block.getField('scaleLength').setVisible(false);
                    block.getField('overlayColor').setVisible(false);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    block.getField('symbol').setVisible(false);
                    block.getField('size').setVisible(false);
                    
                    block.getField('transparency').setVisible(true);
                    // Line properties
                    block.getField('lineWidth').setVisible(true);
                    block.getField('lineColor').setVisible(true);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    block.getField('colorByField').setVisible(true);
                    if (block.getFieldValue('colorByField') == 'none'){
                        block.getField('field').setVisible(false);
                        block.getField('cBarDirection').setVisible(false);
                        block.getField('symbolColor').setVisible(false);
                    }
                    else{
                        block.getField('field').setVisible(true);
                        block.getField('cBarDirection').setVisible(true);
                        block.getField('symbolColor').setVisible(true);
                    }
                    block.getField('field').setVisible(false);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(false);
                    block.getField('reverse').setVisible(false);
                    block.getField('cScale').setVisible(false);
                    block.getField('cLimMin').setVisible(false);
                    block.getField('cLimMax').setVisible(false);
                    block.getField('cBarLabel').setVisible(false);
                    block.getField('cBarDirection').setVisible(false);
                    break;
            }
        case 'scatter' | 'PCA scatter':
            switch (block.type){
                case 'axis_and_labels':
                    if (plotType ==='scatter'){
                        block.getField('xLabel').setVisible(true);
                        block.getField('xLimMin').setVisible(true);
                        block.getField('xLimMax').setVisible(true);
                        block.getField('xScaleDropdown').setVisible(true);
                        block.getField('yLabel').setVisible(true);
                        block.getField('yLimMin').setVisible(true);
                        block.getField('yLimMax').setVisible(true);
                        block.getField('yScaleDropdown').setVisible(true);
                    }
                    else{
                        block.getField('xLabel').setVisible(true);
                        block.getField('xLimMin').setVisible(false);
                        block.getField('xLimMax').setVisible(false);
                        block.getField('xScaleDropdown').setVisible(false);
                        block.getField('yLabel').setVisible(true);
                        block.getField('yLimMin').setVisible(false);
                        block.getField('yLimMax').setVisible(false);
                        block.getField('yScaleDropdown').setVisible(false);
                    }
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(false);
                    block.getField('tickDirectionDropdown').setVisible(false);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(true);
                    block.getField('scaleLocation').setVisible(true);
                    block.getField('scaleLength').setVisible(true);
                    block.getField('overlayColor').setVisible(true);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    block.getField('symbol').setVisible(false);
                    block.getField('size').setVisible(false);
                    block.getField('symbolColor').setVisible(false);
                    block.getField('transparency').setVisible(false);
                    // Line properties
                    block.getField('lineWidth').setVisible(true);
                    block.getField('lineColor').setVisible(true);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    block.getField('colorByField').setVisible(true);
                    block.getField('field').setVisible(true);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(true);
                    block.getField('reverse').setVisible(true);
                    block.getField('cScale').setVisible(true);
                    block.getField('cLimMin').setVisible(true);
                    block.getField('cLimMax').setVisible(true);
                    block.getField('cBarLabel').setVisible(true);
                    block.getField('cBarDirection').setVisible(true);
                    break;
            }

        case 'histogram':
            switch (block.type){
                case 'axis_and_labels':
                    block.getField('xLabel').setVisible(false);
                    block.getField('xLimMin').setVisible(true);
                    block.getField('xLimMax').setVisible(true);
                    block.getField('xScaleDropdown').setVisible(false);
                    block.getField('yLabel').setVisible(false);
                    block.getField('yLimMin').setVisible(true);
                    block.getField('yLimMax').setVisible(true);
                    block.getField('yScaleDropdown').setVisible(false);
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(false);
                    block.getField('tickDirectionDropdown').setVisible(false);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(true);
                    block.getField('scaleLocation').setVisible(true);
                    block.getField('scaleLength').setVisible(true);
                    block.getField('overlayColor').setVisible(true);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    block.getField('symbol').setVisible(false);
                    block.getField('size').setVisible(false);
                    block.getField('symbolColor').setVisible(false);
                    block.getField('transparency').setVisible(false);
                    // Line properties
                    block.getField('lineWidth').setVisible(true);
                    block.getField('lineColor').setVisible(true);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    block.getField('colorByField').setVisible(true);
                    block.getField('field').setVisible(true);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(true);
                    block.getField('reverse').setVisible(true);
                    block.getField('cScale').setVisible(true);
                    block.getField('cLimMin').setVisible(true);
                    block.getField('cLimMax').setVisible(true);
                    block.getField('cBarLabel').setVisible(true);
                    block.getField('cBarDirection').setVisible(true);
                    break;
            }

        case 'scatter':
            switch (block.type){
                case 'axis_and_labels':
                    block.getField('xLabel').setVisible(false);
                    block.getField('xLimMin').setVisible(true);
                    block.getField('xLimMax').setVisible(true);
                    block.getField('xScaleDropdown').setVisible(false);
                    block.getField('yLabel').setVisible(false);
                    block.getField('yLimMin').setVisible(true);
                    block.getField('yLimMax').setVisible(true);
                    block.getField('yScaleDropdown').setVisible(false);
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(false);
                    block.getField('tickDirectionDropdown').setVisible(false);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(true);
                    block.getField('scaleLocation').setVisible(true);
                    block.getField('scaleLength').setVisible(true);
                    block.getField('overlayColor').setVisible(true);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    block.getField('symbol').setVisible(false);
                    block.getField('size').setVisible(false);
                    block.getField('symbolColor').setVisible(false);
                    block.getField('transparency').setVisible(false);
                    // Line properties
                    block.getField('lineWidth').setVisible(true);
                    block.getField('lineColor').setVisible(true);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    block.getField('colorByField').setVisible(true);
                    block.getField('field').setVisible(true);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(true);
                    block.getField('reverse').setVisible(true);
                    block.getField('cScale').setVisible(true);
                    block.getField('cLimMin').setVisible(true);
                    block.getField('cLimMax').setVisible(true);
                    block.getField('cBarLabel').setVisible(true);
                    block.getField('cBarDirection').setVisible(true);
                    break;
            }
        case 'pca scatter':
            switch (block.type){
                case 'axis_and_labels':
                    block.getField('xLabel').setVisible(false);
                    block.getField('xLimMin').setVisible(true);
                    block.getField('xLimMax').setVisible(true);
                    block.getField('xScaleDropdown').setVisible(false);
                    block.getField('yLabel').setVisible(false);
                    block.getField('yLimMin').setVisible(true);
                    block.getField('yLimMax').setVisible(true);
                    block.getField('yScaleDropdown').setVisible(false);
                    block.getField('zLabel').setVisible(false);
                    block.getField('aspectRatio').setVisible(false);
                    block.getField('tickDirectionDropdown').setVisible(false);
                    block.render();
                    break;
                case 'annot_and_scale':
                    block.getField('scaleDirection').setVisible(true);
                    block.getField('scaleLocation').setVisible(true);
                    block.getField('scaleLength').setVisible(true);
                    block.getField('overlayColor').setVisible(true);
                    // font 
                    block.getField('font').setVisible(true);
                    block.getField('fontSize').setVisible(true);
                    block.getField('showMass').setVisible(true);
                    break;
                case 'marks_and_lines':
                    block.getField('symbol').setVisible(false);
                    block.getField('size').setVisible(false);
                    block.getField('symbolColor').setVisible(false);
                    block.getField('transparency').setVisible(false);
                    // Line properties
                    block.getField('lineWidth').setVisible(true);
                    block.getField('lineColor').setVisible(true);
                    block.getField('lengthMultiplier').setVisible(false);
                    break;
                case 'coloring':
                    // Color properties
                    block.getField('colorByField').setVisible(true);
                    block.getField('field').setVisible(true);
                    block.getField('resolution').setVisible(false);
                    block.getField('colormap').setVisible(true);
                    block.getField('reverse').setVisible(true);
                    block.getField('cScale').setVisible(true);
                    block.getField('cLimMin').setVisible(true);
                    block.getField('cLimMax').setVisible(true);
                    block.getField('cBarLabel').setVisible(true);
                    block.getField('cBarDirection').setVisible(true);
                    break;
            }

        default:
            // Default settings if plot type doesn't match any case
            break;
    }
}

function updateStylesBlock(block, style) {
    
}

/*
style = {
    "Axes": {
        "XLim": [1, 738],
        "XScale": "linear",
        "XLabel": "X",
        "YLim": [1, 106],
        "YScale": "linear",
        "YLabel": "Y",
        "ZLabel": "",
        "AspectRatio": 0.9919100893474309,
        "TickDir": "out"
    },
    "Text": {
        "Font": "Avenir",
        "FontSize": 11.0
    },
    "Scale": {
        "Direction": "none",
        "Location": "northeast",
        "Length": None,
        "OverlayColor": "#ffffff"
    },
    "Markers": {
        "Symbol": "circle",
        "Size": 6,
        "Alpha": 30
    },
    "Lines": {
        "LineWidth": 1.5,
        "Multiplier": 1,
        "Color": "#1c75bc"
    },
    "Colors": {
        "Color": "#1c75bc",
        "ColorByField": "Analyte",
        "Field": "Li7",
        "Colormap": "plasma",
        "Reverse": False,
        "CLim": [-0.00144, 66.7],
        "CScale": "linear",
        "Direction": "vertical",
        "CLabel": "$^{7}$Li (ppm)",
        "Resolution": 10
    }
}

'XLim':
[1, 738]
'XScale':
'linear'
'XLabel':
'X'
'YLim':
[1, 106]
'YScale':
'linear'
'YLabel':
'Y'
'ZLabel':
''
'AspectRatio':
0.9919100893474309
'TickDir':
'out'
'Font':
'Avenir'
'FontSize':
11.0
'ScaleDir':
'none'

    */
function updateAxisAndLabelsBlock(block, style) {
    // Update X, Y, and Z Labels
    block.setFieldValue(style['XLabel'], 'xLabel');
    block.setFieldValue(style['YLabel'], 'yLabel');
    block.setFieldValue(style['ZLabel'], 'zLabel');
    
    // Update X and Y Limits
    block.setFieldValue(style['XLim'][0], 'xLimMin');
    block.setFieldValue(style['XLim'][1], 'xLimMax');
    block.setFieldValue(style['YLim'][0], 'yLimMin');
    block.setFieldValue(style['YLim'][1], 'yLimMax');
    
    // Update X and Y Scales
    block.setFieldValue(style['XScale'], 'xScaleDropdown');
    block.setFieldValue(style['YScale'], 'yScaleDropdown');

    // Update tick direction
    block.setFieldValue(style['TickDir'], 'tickDirectionDropdown');

    // Update aspect Ratio
    block.setFieldValue(style['AspectRatio'], 'aspectRatio');
    
    // Render the updated block
    block.render();
}

function updateAnnotAndScaleBlock(block, style) {
    // Update Scale direction and location
    block.setFieldValue(style['ScaleDir'], 'scaleDirection');
    block.setFieldValue(style['ScaleLocation'], 'scaleLocation');
    
    // Update Scale length and overlay color
    block.setFieldValue(style['ScaleLength'], 'scaleLength');

    block.setFieldValue(style['OverlayColor'], 'overlayColor');
    
    // Render the updated block
    block.render();
}

function updateMarksAndLinesBlock(block, style) {
    // Update Marker Symbol and Size and transparency
    block.setFieldValue(style['Marker'], 'symbol');
    block.setFieldValue(style['MarkerSize'], 'size');
    block.setFieldValue(style['MarkerColor'], 'symbolColor');
    block.setFieldValue(style['MarkerAlpha'], 'transparency');
    // Update Transparency and Line Width
    
    block.setFieldValue(style['LineWidth'], 'lineWidth');
    
    // Update Line Color and symbol Color
    block.setFieldValue(style['LineColor'], 'lineColor');
    block.setFieldValue(style['Multiplier'], 'lengthMultiplier');
    
    // Render the updated block
    block.render();
}

function updateColoringBlock(block, style) {
    // Update Colormap, Scale, and CLim
    block.setFieldValue(style['Colormap'], 'colormap');
    block.setFieldValue(style['CScale'], 'cScale');
    
    block.setFieldValue(style['CLim'][0], 'cLimMin');
    block.setFieldValue(style['CLim'][1], 'cLimMax');
    
    // Update the Cbar label and direction
    block.setFieldValue(style['CLabel'], 'cBarLabel');
    block.setFieldValue(style['CbarDir'], 'cBarDirection');

    block.setFieldValue(style['Resolution'], 'resolution');

    block.setFieldValue(style['CbarReverse'], 'reverse');
    
    // Render the updated block
    block.render();
}

