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


export function dynamicStyleUpdate(plotType) {
    // Assume set_style_widgets is available from Python backend
    window.blocklyBridge.callSetStyleWidgets(plotType, function(style) {
        // The 'style' object contains the updated style properties
        // Now, update the 'styles', 'axisAndLabels', etc. blocks with the new values

        Blockly.getMainWorkspace().getAllBlocks().forEach(function(block) {
            switch (block.type) {
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
    });
}

function updateStylesBlock(block, style) {
    
}

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
    block.setFieldValue(style['Axes']['XScale'], 'xAxisDropdown');
    block.setFieldValue(style['Axes']['YScale'], 'yAxisDropdown');
    
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

