/******************************
 * Python Generators for Custom Blocks
 ******************************/
// Import a generator.
import {pythonGenerator} from 'blockly/python';
import { sample_ids } from './globals';
// Python Generator: Load Directory
pythonGenerator.forBlock['load_directory'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    var code = (dir_name === "'directory name'")
        ? 'self.parent.LameIO.open_directory()\nself.store_sample_ids()\n'
        : 'self.parent.open_directory(' + dir_name + ')\nself.store_sample_ids()\n';
    return code;
};

// Python Generator: Select Samples
pythonGenerator.forBlock['select_samples'] = function(block, generator) {
    var sample_id = generator.quote_(block.getFieldValue('SAMPLE_ID'));
    var code = 'self.parent.change_sample(self.parent.sample_ids.index(' + sample_id + ')\n';
    return code;
};

// Python Generator: Sample IDs List
pythonGenerator.forBlock['sample_ids_list_block'] = function(block, generator) {
    const code = JSON.stringify(sample_ids);  // Generates Python list from global sample_ids variable
    return code;
};

// Python Generator: Iterate Through Sample IDs
pythonGenerator.forBlock['iterate_sample_ids'] = function(block, generator) {
    var variable_sample_ids = JSON.stringify(sample_ids);
    var statements_do = generator.statementToCode(block, 'DO');
    var code = 'for sample_id in ' + variable_sample_ids + ':\n' + statements_do;
    return code;
};

pythonGenerator.forBlock['plot'] = function() {
// TODO: change Order.ATOMIC to the correct operator precedence strength
const value_plot_type = generator.valueToCode(block, 'plot_type', Order.ATOMIC);

// TODO: Assemble python into the code variable.
const code = '...';
return code;
}

pythonGenerator.forBlock['plot_map'] = function() {
// TODO: change Order.ATOMIC to the correct operator precedence strength
const value_style = generator.valueToCode(block, 'style', Order.ATOMIC);

// TODO: change Order.ATOMIC to the correct operator precedence strength
const value_save = generator.valueToCode(block, 'save', Order.ATOMIC);

// TODO: Assemble python into the code variable.
const code = '...';
// TODO: Change Order.NONE to the correct operator precedence strength
return [code, Order.NONE];
}