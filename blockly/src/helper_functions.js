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
