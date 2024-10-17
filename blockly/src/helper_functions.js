/******************************
 * Helper Functions
 ******************************/
import * as Blockly from 'blockly/core';
// Function: Update Sample Dropdown with IDs
function updateSampleDropdown(sampleIds) {
    storeSampleIdsAsList(sampleIds);  // Store sample IDs as Blockly list

    const dropdownOptions = sampleIds.map(id => [id, id]);
    Blockly.getMainWorkspace().getAllBlocks().forEach(function(block) {
        if (block.type === 'select_samples') {
            block.getField('SAMPLE_IDS').menuGenerator_ = dropdownOptions;  // Update dropdown options dynamically
            block.getField('SAMPLE_IDS').setValue(dropdownOptions[0][0]);  // Set default value
        }
    });
    console.log("Dropdown updated with sample IDs:", dropdownOptions);
}

// Global variable to store sample IDs
let sample_ids = [];

// Function: Update the sample_ids list and refresh the dropdown
function updateSampleIds(sampleIds) {
    // Update the global sample_ids variable
    sample_ids = sampleIds;

    // Refresh all blocks in the workspace that use the select_samples dropdown
    Blockly.getMainWorkspace().getAllBlocks().forEach(function(block) {
        if (block.type === 'select_samples') {
            const dropdownField = block.getField('SAMPLE_IDS');
            if (dropdownField) {
                dropdownField.menuGenerator_ = sampleIds.map(id => [id, id]); // Update dropdown options dynamically
                dropdownField.setValue(sampleIds.length ? sampleIds[0] : 'NONE'); // Set default value
            }
        }
    });

    console.log("Dropdown updated with sample IDs:", sample_ids);
}