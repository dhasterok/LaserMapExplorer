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

function updateStylesBlock(block, style) {
    
}

///style = {"Axes": {"XLim": [1, 738], "XScale": "linear", "XLabel": "X", "YLim": [1, 106], "YScale": "linear", "YLabel": "Y", "ZLabel": "", "AspectRatio": 0.9919100893474309, "TickDir": "out"}, "Text": {"Font": "Avenir", "FontSize": 11.0}, "Scale": {"Direction": "none", "Location": "northeast", "Length": null, "OverlayColor": "#ffffff"}, "Markers": {"Symbol": "circle", "Size": 6, "Alpha": 30}, "Lines": {"LineWidth": 1.5, "Multiplier": 1, "Color": "#1c75bc"}, "Colors": {"Color": "#1c75bc", "ColorByField": "Analyte", "Field": "Li7", "Colormap": "plasma", "Reverse": false, "CLim": [-0.00144, 66.7], "CScale": "linear", "Direction": "vertical", "CLabel": "$^{7}$Li (ppm)", "Resolution": 10}}
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
    
    // Update Line Color
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
    
    // Render the updated block
    block.render();
}

