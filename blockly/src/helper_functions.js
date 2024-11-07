/******************************
 * Helper Functions
 ******************************/
import * as Blockly from 'blockly/core';
import { sample_ids, updateSampleIds } from './globals';
import {enableSampleIDsBlockFunction} from './custom_blocks'
// Function: Update Sample Dropdown with IDs
function updateSampleDropdown(sampleIds) {
    // Step 1: Store sample IDs in the global variable
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
                    case 'axisAndLabels':
                        updateAxisAndLabelsBlock(block, style);
                        break;
                    case 'annotAndScale':
                        updateAnnotAndScaleBlock(block, style);
                        break;
                    case 'marksAndLines':
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
    // Reset all fields to default visibility and enabled state
    block.getField('xLabel').setEnabled(true);
    block.getField('xLimMin').setEnabled(true);
    block.getField('xScaleDropdown').setEnabled(true);
    block.getField('yLabel').setEnabled(true);
    block.getField('yLimMin').setEnabled(true);
    block.getField('yScaleDropdown').setEnabled(true);
    block.getField('zLabel').setEnabled(true);
    block.getField('aspectRatio').setEnabled(true);
    block.getField('tickDirectionDropdown').setEnabled(true);
    
    // Adjust fields based on plot type
    switch (plotType) {
        case 'analyte map':
                // Reset all fields to default visibility and enabled state
            block.getField('xLabel').setEnabled(true);
            block.getField('xLimMin').setEnabled(true);
            block.getField('xScaleDropdown').setEnabled(true);
            block.getField('yLabel').setEnabled(true);
            block.getField('yLimMin').setEnabled(true);
            block.getField('yScaleDropdown').setEnabled(true);
            block.getField('zLabel').setEnabled(true);
            block.getField('aspectRatio').setEnabled(true);
            block.getField('tickDirectionDropdown').setEnabled(true);
        case 'gradient map':
            // Axes properties
            block.getField('xLabel').setEnabled(false);
            block.getField('xLimMin').setEnabled(true);
            block.getField('xScaleDropdown').setEnabled(false);
            block.getField('yLabel').setEnabled(false);
            block.getField('yLimMin').setEnabled(true);
            block.getField('yScaleDropdown').setEnabled(false);
            block.getField('zLabel').setEnabled(false);
            block.getField('aspectRatio').setEnabled(false);
            block.getField('tickDirectionDropdown').setEnabled(false);
            // Scalebar properties
            block.getField('scaleDirection').setEnabled(true);
            block.getField('scaleLocation').setEnabled(true);
            block.getField('scaleLength').setEnabled(true);
            block.getField('overlayColor').setEnabled(true);
            // Marker properties
            block.getField('symbol').setEnabled(true);
            block.getField('size').setEnabled(true);
            block.getField('transparency').setEnabled(true);
            block.getField('symbolColor').setEnabled(true);
            // Line properties
            block.getField('lineWidth').setEnabled(true);
            block.getField('lineColor').setEnabled(true);
            block.getField('lengthMultiplier').setEnabled(false);
            // Color properties
            block.getField('colorByField').setEnabled(true);
            block.getField('field').setEnabled(true);
            block.getField('colormap').setEnabled(true);
            block.getField('cLimMin').setEnabled(true);
            block.getField('cLimMax').setEnabled(true);
            block.getField('cScale').setEnabled(true);
            block.getField('cBarDirection').setEnabled(true);
            block.getField('cBarLabel').setEnabled(true);
            block.getField('resolution').setEnabled(false);
            break;

        case 'correlation':
        case 'vectors':
            // Axes properties
            block.getField('xLabel').setEnabled(false);
            block.getField('xLimMin').setEnabled(false);
            block.getField('xScaleDropdown').setEnabled(false);
            block.getField('yLabel').setEnabled(false);
            block.getField('yLimMin').setEnabled(false);
            block.getField('yScaleDropdown').setEnabled(false);
            block.getField('zLabel').setEnabled(false);
            block.getField('aspectRatio').setEnabled(false);
            block.getField('tickDirectionDropdown').setEnabled(true);
            // Scalebar properties
            block.getField('scaleDirection').setEnabled(false);
            block.getField('scaleLocation').setEnabled(false);
            block.getField('scaleLength').setEnabled(false);
            block.getField('overlayColor').setEnabled(false);
            // Marker properties
            block.getField('symbol').setEnabled(false);
            block.getField('size').setEnabled(false);
            block.getField('transparency').setEnabled(false);
            block.getField('symbolColor').setEnabled(false);
            // Line properties
            block.getField('lineWidth').setEnabled(false);
            block.getField('lineColor').setEnabled(false);
            block.getField('lengthMultiplier').setEnabled(false);
            // Color properties
            block.getField('colormap').setEnabled(true);
            block.getField('cScale').setEnabled(false);
            block.getField('cLimMin').setEnabled(true);
            block.getField('cLimMax').setEnabled(true);
            block.getField('cBarDirection').setEnabled(true);
            block.getField('cBarLabel').setEnabled(false);
            block.getField('colorByField').setEnabled(plotType === 'correlation');
            block.getField('field').setEnabled(block.getField('colorByField').getValue() === 'cluster');
            block.getField('resolution').setEnabled(false);
            break;

        case 'histogram':
            // Axes properties
            block.getField('xLabel').setEnabled(true);
            block.getField('xLimMin').setEnabled(true);
            block.getField('xScaleDropdown').setEnabled(true);
            block.getField('yLabel').setEnabled(true);
            block.getField('yLimMin').setEnabled(true);
            block.getField('yScaleDropdown').setEnabled(false);
            block.getField('zLabel').setEnabled(false);
            block.getField('aspectRatio').setEnabled(true);
            block.getField('tickDirectionDropdown').setEnabled(true);
            // Scalebar properties
            block.getField('scaleDirection').setEnabled(false);
            block.getField('scaleLocation').setEnabled(false);
            block.getField('scaleLength').setEnabled(false);
            block.getField('overlayColor').setEnabled(false);
            // Marker properties
            block.getField('symbol').setEnabled(false);
            block.getField('size').setEnabled(false);
            block.getField('transparency').setEnabled(true);
            // Line properties
            block.getField('lineWidth').setEnabled(true);
            block.getField('lineColor').setEnabled(true);
            block.getField('lengthMultiplier').setEnabled(false);
            // Color properties
            block.getField('colorByField').setEnabled(true);
            block.getField('colormap').setEnabled(false);
            block.getField('cBarDirection').setEnabled(block.getField('colorByField').getValue() !== 'none');
            block.getField('field').setEnabled(block.getField('colorByField').getValue() !== 'none');
            block.getField('symbolColor').setEnabled(block.getField('colorByField').getValue() === 'none');
            break;

        case 'scatter':
        case 'pca scatter':
            // Axes properties
            const isScatter = block.getField('zLabel').getValue() === '';
            block.getField('xLimMin').setEnabled(isScatter);
            block.getField('xScaleDropdown').setEnabled(isScatter);
            block.getField('yLimMin').setEnabled(isScatter);
            block.getField('yScaleDropdown').setEnabled(isScatter);
            block.getField('zLabel').setEnabled(!isScatter);
            // Other properties similar to Python code logic...
            break;

        // Add additional cases for each plot type as needed

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
    */
function updateAxisAndLabelsBlock(block, style) {
    // Update X, Y, and Z Labels
    block.setFieldValue(style['Axes']['XLabel'], 'xLabel');
    block.setFieldValue(style['Axes']['YLabel'], 'yLabel');
    block.setFieldValue(style['Axes']['ZLabel'], 'zLabel');
    
    // Update X and Y Limits
    block.setFieldValue(style['Axes']['XLim'][0], 'xLimMin');
    block.setFieldValue(style['Axes']['XLim'][1], 'xLimMax');
    block.setFieldValue(style['Axes']['YLim'][0], 'yLimMin');
    block.setFieldValue(style['Axes']['YLim'][1], 'yLimMax');
    
    // Update X and Y Scales
    block.setFieldValue(style['Axes']['XScale'], 'xScaleDropdown');
    block.setFieldValue(style['Axes']['YScale'], 'yScaleDropdown');

    // Update tick direction
    block.setFieldValue(style['Axes']['TickDir'], 'tickDirectionDropdown');

    // Update aspect Ratio
    block.setFieldValue(style['Axes']['AspectRatio'], 'aspectRatio');
    
    // Render the updated block
    block.render();
}

function updateAnnotAndScaleBlock(block, style) {
    // Update Scale direction and location
    block.setFieldValue(style['Scale']['Direction'], 'scaleDirection');
    block.setFieldValue(style['Scale']['Location'], 'scaleLocation');
    
    // Update Scale length and overlay color
    if (style['Scale']['Length'] !== null) {
        block.setFieldValue(style['Scale']['Length'], 'scaleLength');
    }
    block.setFieldValue(style['Scale']['OverlayColor'], 'overlayColor');
    
    // Render the updated block
    block.render();
}

function updateMarksAndLinesBlock(block, style) {
    // Update Symbol and Size
    block.setFieldValue(style['Markers']['Symbol'], 'symbol');
    block.setFieldValue(style['Markers']['Size'], 'size');
    
    // Update Transparency and Line Width
    block.setFieldValue(style['Markers']['Alpha'], 'transparency');
    block.setFieldValue(style['Lines']['LineWidth'], 'lineWidth');
    
    // Update Line Color and symbol Color
    block.setFieldValue(style['Lines']['Color'], 'lineColor');
    block.setFieldValue(style['Lines']['Color'], 'lineColor');
    
    // Render the updated block
    block.render();
}

function updateColoringBlock(block, style) {
    // Update Colormap, Scale, and CLim
    block.setFieldValue(style['Colors']['Colormap'], 'colormap');
    block.setFieldValue(style['Colors']['CScale'], 'scale');
    
    block.setFieldValue(style['Colors']['CLim'][0], 'cLimMin');
    block.setFieldValue(style['Colors']['CLim'][1], 'cLimMax');
    
    // Update the Cbar label and direction
    block.setFieldValue(style['Colors']['CLabel'], 'cBarLabel');
    block.setFieldValue(style['Colors']['Direction'], 'cBarDirection');

    block.setFieldValue(style['Colors']['CScale'], 'cScale');
    
    // Render the updated block
    block.render();
}

