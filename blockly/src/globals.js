export let sample_ids = [];  // Declare and export the global variable
export const fieldTypeList = [['Analyte', 'Analyte'], ['Analyte (normalized)', 'Analyte (normalized)']]; // Global variable to store fieldTypeList
export let spot_data = false;  // Declare and export the global variable
export let baseDir = ''; // Define a global variable for baseDir

// Function to set baseDir from Python
export function setBaseDir(dir) {
  baseDir = dir;
}

export function updateSampleIds(newIds) {
    sample_ids.length = 0;  // Clear the array
    sample_ids.push(...newIds);  // Add new items to the array
    console.log('Sample IDs updated globally:', sample_ids);
}

