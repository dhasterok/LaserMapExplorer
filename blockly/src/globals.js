
export let sample_ids = [];  // Declare and export the global variable
export let spot_data = false;  // Declare and export the global variable

export function updateSampleIds(newIds) {
    sample_ids.length = 0;  // Clear the array
    sample_ids.push(...newIds);  // Add new items to the array
    console.log('Sample IDs updated globally:', sample_ids);
}