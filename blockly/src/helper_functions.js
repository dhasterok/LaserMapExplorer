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

/**
 * Retrieve an array of all blocks connected to the 'Styling' input
 * in a linear chain (via next/previous statements).
 * @param {Blockly.Block} plotBlock - The main block that has a 'Styling' statement input.
 * @return {Blockly.Block[]} Array of connected blocks.
 */
function getStylingBlocks(plotBlock) {
    // 1) Get the 'Styling' input object
    const stylingInput = plotBlock.getInput('Styling');
    if (!stylingInput) {
      // Input not found; perhaps the block doesn't have a 'Styling' input?
      console.warn("No 'Styling' input found on block:", plotBlock);
      return [];
    }
    
    // 2) Get the top-most connected block on this input
    const firstBlock = stylingInput.connection
      ? stylingInput.connection.targetBlock()
      : null;
  
    // 3) Traverse the chain of connected blocks
    const stylingBlocks = [];
    let currentBlock = firstBlock;
    while (currentBlock) {
      stylingBlocks.push(currentBlock);
      currentBlock = currentBlock.getNextBlock();
    }
  
    return stylingBlocks;
}
  


/**
 * Retrieve and update all blocks connected to the "Styling" input.
 * @param {Blockly.Block} plotMapBlock - The plot_map block instance.
 * @param {String} plotType - The dictionary containing styling values.
 */

export function updateStylingChain(plotBlock, plotType) {
    // 1) Get the first block connected to "Styling".
    const stylingBlocks = getStylingBlocks(plotBlock);
    
    // If you want to explicitly set the plotType:
    // this.plotType = 'analyte map';
  
    // 2) Call the style widgets function with the current plotType.
    window.blocklyBridge.invokeSetStyleWidgets(plotType, (styleStr) => {
      // 3a) Check if the style dictionary is empty
      const style = JSON.parse(styleStr);
      if (style.constructor === Object && Object.keys(style).length === 0) {
        console.warn('Style dictionary not provided for plotType:', this.plotType);
        return; // Exit if style is not available
      } else {
        console.log('updating styles');
        
        // Store the style object in styleDict for clarity.
        let styleDict = style;
        
        // 3b) Traverse the chain of styling blocks
        for (const block of stylingBlocks) {
          // 3c) Identify the block by type and update
          switch (block.type) {
            case 'x_axis':
              updateXAxisBlock(block, styleDict);
              break;
            case 'y_axis':
              updateYAxisBlock(block, styleDict);
              break;
            case 'z_axis':
              updateZAxisBlock(block, styleDict);
              break;
            case 'c_axis':
              updateCAxisBlock(block, styleDict);
              break;
            case 'font':
              updateFontBlock(block, styleDict);
              break;
            case 'tick_direction':
              updateTickDirectionBlock(block, styleDict);
              break;
            case 'aspect_ratio':
              updateAspectRatioBlock(block, styleDict);
              break;
            case 'coloring':
              updateColormapBlock(block, styleDict);
              break;
            case 'add_scale':
              updateAddScaleBlock(block, styleDict);
              break;
            case 'marker_properties':
              updateMarkerPropertiesBlock(block, styleDict);
              break;
            case 'line_properties':
              updateLinePropertiesBlock(block, styleDict);
              break;
            case 'color_field':
              updateColorFieldBlock(block, styleDict);
              break;
            case 'colormap':
              updateColormapBlock(block, styleDict);
              break;
            case 'show_mass':
              updateShowMassBlock(block, styleDict);
              break;
            case 'color_by_cluster':
              updateColorByClusterBlock(block, styleDict);
              break;
            default:
              // Optionally handle unsupported block types
              console.warn('Unsupported styling block:', block.type);
          }
        }
      }
    });
}
  
  
function updateXAxisBlock(block, style) {
// e.g. style might contain:
// {
//   "XLabel": "X Axis Title",
//   "XLim": ["0", "100"],   // an array: [min, max]
//   "XScale": "linear"
// }
if (style['XLabel'] !== undefined) {
    block.setFieldValue(style['XLabel'], 'xLabel');
}
if (style['XLim'] && Array.isArray(style['XLim'])) {
    block.setFieldValue(style['XLim'][0], 'xLimMin');
    block.setFieldValue(style['XLim'][1], 'xLimMax');
}
if (style['XScale'] !== undefined) {
    block.setFieldValue(style['XScale'], 'xScaleDropdown');
}
block.render();
}

function updateYAxisBlock(block, style) {
// e.g. style might contain:
// {
//   "YLabel": "Y Axis Title",
//   "YLim": ["0", "100"],
//   "YScale": "log"
// }
if (style['YLabel'] !== undefined) {
    block.setFieldValue(style['YLabel'], 'yLabel');
}
if (style['YLim'] && Array.isArray(style['YLim'])) {
    block.setFieldValue(style['YLim'][0], 'yLimMin');
    block.setFieldValue(style['YLim'][1], 'yLimMax');
}
if (style['YScale'] !== undefined) {
    block.setFieldValue(style['YScale'], 'yScaleDropdown');
}
block.render();
}


function updateZAxisBlock(block, style) {
// e.g. style might contain:
// {
//   "ZLabel": "Z Axis Title",
//   "ZLim": ["0", "100"],
//   "ZScale": "linear"
// }
if (style['ZLabel'] !== undefined) {
    block.setFieldValue(style['ZLabel'], 'zLabel');
}
if (style['ZLim'] && Array.isArray(style['ZLim'])) {
    block.setFieldValue(style['ZLim'][0], 'zLimMin');
    block.setFieldValue(style['ZLim'][1], 'zLimMax');
}
if (style['ZScale'] !== undefined) {
    block.setFieldValue(style['ZScale'], 'zScaleDropdown');
}
block.render();
}



function updateCAxisBlock(block, style) {
// e.g. style might contain:
// {
//   "CLabel": "Concentration",
//   "CLim": ["0", "500"],
//   "CScale": "log"
// }
if (style['CLabel'] !== undefined) {
    block.setFieldValue(style['CLabel'], 'cLabel');
}
if (style['CLim'] && Array.isArray(style['CLim'])) {
    block.setFieldValue(style['CLim'][0], 'cLimMin');
    block.setFieldValue(style['CLim'][1], 'cLimMax');
}
if (style['CScale'] !== undefined) {
    block.setFieldValue(style['CScale'], 'cScaleDropdown');
}
block.render();
}


function updateFontBlock(block, style) {
// e.g. style might contain:
// {
//   "FontName": "Arial",
//   "FontSize": 12
// }
if (style['FontName'] !== undefined) {
    block.setFieldValue(style['FontName'], 'font');
}
if (style['FontSize'] !== undefined) {
    block.setFieldValue(String(style['FontSize']), 'fontSize');
}
block.render();
}


function updateTickDirectionBlock(block, style) {
// e.g. style might contain:
// { "TickDir": "out" }
if (style['TickDir'] !== undefined) {
    block.setFieldValue(style['TickDir'], 'tickDirectionDropdown');
}
block.render();
}


function updateAspectRatioBlock(block, style) {
// e.g. style might contain:
// {
//   "AspectRatio": "1.0",
//   "TickDir": "in"
// }
if (style['AspectRatio'] !== undefined) {
    block.setFieldValue(String(style['AspectRatio']), 'aspectRatio');
}
if (style['TickDir'] !== undefined) {
    block.setFieldValue(style['TickDir'], 'tickDirectionDropdown');
}
block.render();
}


function updateAddScaleBlock(block, style) {
// e.g. style might contain:
// {
//   "ScaleColor": "#FF0000",
//   "ScaleUnits": "m",
//   "ScaleLength": "50",
//   "ScaleDirection": "horizontal"
// }
if (style['ScaleColor'] !== undefined) {
    block.setFieldValue(style['ScaleColor'], 'scaleColor');
}
if (style['ScaleUnits'] !== undefined) {
    block.setFieldValue(style['ScaleUnits'], 'scaleUnits');
}
if (style['ScaleLength'] !== undefined) {
    block.setFieldValue(style['ScaleLength'], 'scaleLength');
}
if (style['ScaleDirection'] !== undefined) {
    block.setFieldValue(style['ScaleDirection'], 'scaleDirection');
}
block.render();
}


function updateMarkerPropertiesBlock(block, style) {
// e.g. style might contain:
// {
//   "MarkerSymbol": "circle",
//   "MarkerSize": 8,
//   "MarkerColor": "#FFFF00",
//   "MarkerAlpha": 0.5  // if you want transparency
// }
if (style['MarkerSymbol'] !== undefined) {
    block.setFieldValue(style['MarkerSymbol'], 'markerSymbol');
}
if (style['MarkerSize'] !== undefined) {
    block.setFieldValue(String(style['MarkerSize']), 'markerSize');
}
if (style['MarkerColor'] !== undefined) {
    block.setFieldValue(style['MarkerColor'], 'markerColor');
}
// If you handle marker alpha:
// block.setFieldValue(String(style['MarkerAlpha']), 'transparency');
block.render();
}


function updateLinePropertiesBlock(block, style) {
// e.g. style might contain:
// {
//   "LineWidth": 2,
//   "LineColor": "#00FF00"
// }
if (style['LineWidth'] !== undefined) {
    block.setFieldValue(String(style['LineWidth']), 'lineWidth');
}
if (style['LineColor'] !== undefined) {
    block.setFieldValue(style['LineColor'], 'lineColor');
}
block.render();
}


function updateColorFieldBlock(block, style) {
// e.g. style might contain:
// {
//   "ColorFieldType": "typeA",
//   "ColorFieldOption": "option1"
// }
if (style['ColorFieldType'] !== undefined) {
    block.setFieldValue(style['ColorFieldType'], 'fieldType');
}
if (style['ColorFieldOption'] !== undefined) {
    block.setFieldValue(style['ColorFieldOption'], 'field');
}
block.render();
}


function updateColormapBlock(block, style) {
// e.g. style might contain:
// {
//   "ColormapName": "viridis",
//   "Reverse": true,
//   "Direction": "vertical"
// }
if (style['ColormapName'] !== undefined) {
    block.setFieldValue(style['ColormapName'], 'colormap');
}
if (style['Reverse'] !== undefined) {
    // FieldCheckbox expects "TRUE" or "FALSE"
    const checkboxVal = style['Reverse'] ? 'TRUE' : 'FALSE';
    block.setFieldValue(checkboxVal, 'reverse');
}
if (style['Direction'] !== undefined) {
    block.setFieldValue(style['Direction'], 'direction');
}
block.render();
}


function updateShowMassBlock(block, style) {
// e.g. style might contain:
// {
//   "ShowMass": true
// }
if (style['ShowMass'] !== undefined) {
    const checkboxVal = style['ShowMass'] ? 'TRUE' : 'FALSE';
    block.setFieldValue(checkboxVal, 'showMass');
}
block.render();
}

function updateColorByClusterBlock(block, style) {
// e.g. style might contain:
// {
//   "ClusterType": "cluster1"
// }
if (style['ClusterType'] !== undefined) {
    block.setFieldValue(style['ClusterType'], 'clusterType');
}
block.render();
}


/**
 * A helper function to gather all blocks under the "Styling" statement,
 * categorize them into "Axes", "Text", "Markers", "Colors", and merge
 * them into a single dictionary string for Python code.
 * @param {Blockly.Block} plotBlock - The main block (e.g. "plot_map") that has a "Styling" input.
 * @param {Object} generator - The Python generator object (e.g. pythonGenerator).
 * @return {String} - The final merged JSON string, e.g. '{"Axes": {...}, "Text": {...}, ...}'.
 */
export function getCategorizedStyleDictCode(plotBlock, generator) {
    // 1) Provide a category mapping function or inline switch
    function getCategoryForType(blockType) {
      switch (blockType) {
        // Axes
        case 'x_axis':
        case 'y_axis':
        case 'z_axis':
        case 'c_axis':
        case 'tick_direction':
        case 'aspect_ratio':
          return 'Axes';
  
        // Text
        case 'font':
        case 'add_scale':
          return 'Text';
  
        // Markers
        case 'marker_properties':
        case 'line_properties':
          return 'Markers';
  
        // Colors
        case 'coloring':
        case 'colormap':
        case 'color_field':
        case 'show_mass':
        case 'color_by_cluster':
          return 'Colors';
  
        default:
          console.warn('No category mapping for block type:', blockType);
          return null;
      }
    }
  
    // 2) Prepare an object to hold arrays of dictionary strings
    const subBlocksCode = {
      Axes: [],
      Text: [],
      Markers: [],
      Colors: []
    };
  
    // 3) Traverse the chain of blocks connected to "Styling"
    let currentBlock = plotBlock.getInputTargetBlock('Styling');
    while (currentBlock) {
      const bType = currentBlock.type;
      // Generate code for this sub-block
      const tuple = generator.blockToCode(currentBlock, true); 
      let dictString = Array.isArray(tuple) ? tuple[0] : tuple; 
      if (!dictString) dictString = '{}';
  
      // Determine category
      const cat = getCategoryForType(bType);
      if (cat && dictString !== '{}' && dictString.trim() !== '{}') {
        subBlocksCode[cat].push(dictString);
      }
  
      currentBlock = currentBlock.getNextBlock();
    }
  
    // 4) Merge all sub-blocks in each category into a single dict
    const mergedCategories = {};
    for (let cat of ['Axes','Text','Markers','Colors']) {
      const dicts = subBlocksCode[cat]; // array of strings like '{ "XLabel": "Foo" }'
      if (dicts.length > 0) {
        let mergedKeyVals = [];
        for (let dStr of dicts) {
          const trimmed = dStr.trim();
          if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
            const content = trimmed.slice(1, -1).trim(); // remove outer braces
            if (content) mergedKeyVals.push(content);
          }
        }
        mergedCategories[cat] = mergedKeyVals.length > 0
          ? `{${mergedKeyVals.join(', ')}}`
          : '{}';
      } else {
        mergedCategories[cat] = '{}';
      }
    }
  
    // 5) Now build the final big dictionary, ignoring empty '{}'
    const styleDictParts = [];
    if (mergedCategories['Axes'] !== '{}') {
      styleDictParts.push(`"Axes": ${mergedCategories['Axes']}`);
    }
    if (mergedCategories['Text'] !== '{}') {
      styleDictParts.push(`"Text": ${mergedCategories['Text']}`);
    }
    if (mergedCategories['Markers'] !== '{}') {
      styleDictParts.push(`"Markers": ${mergedCategories['Markers']}`);
    }
    if (mergedCategories['Colors'] !== '{}') {
      styleDictParts.push(`"Colors": ${mergedCategories['Colors']}`);
    }
  
    // 6) Join them into one dictionary string
    const styleDictCode = `{${styleDictParts.join(', ')}}`;
    return styleDictCode;
  }
  

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

// function updateColoringBlock(block, style) {
//     // Update Colormap, Scale, and CLim
//     block.setFieldValue(style['Colormap'], 'colormap');
//     block.setFieldValue(style['CScale'], 'cScale');
    
//     block.setFieldValue(style['CLim'][0], 'cLimMin');
//     block.setFieldValue(style['CLim'][1], 'cLimMax');
    
//     // Update the Cbar label and direction
//     block.setFieldValue(style['CLabel'], 'cBarLabel');
//     block.setFieldValue(style['CbarDir'], 'cBarDirection');

//     block.setFieldValue(style['Resolution'], 'resolution');

//     block.setFieldValue(style['CbarReverse'], 'reverse');
    
//     // Render the updated block
//     block.render();
// }

