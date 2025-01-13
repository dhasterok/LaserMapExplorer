/******************************
 * Python Generators for Custom Blocks
 ******************************/
// Import a generator.
import {pythonGenerator, Order} from 'blockly/python';
import { sample_ids } from './globals';



// Python Generator: Load Directory
pythonGenerator.forBlock['load_directory'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    // self is instance of Workflow class
    var code = (dir_name === "'directory path'")
        ? 'self.main.io.open_directory(ui_update=False)\nself.store_sample_ids()\n'
        : 'self.main.io.open_directory(' + dir_name + ', ui_update=False)\nself.store_sample_ids()\n';
    return code;
};

pythonGenerator.forBlock['load_sample'] = function(block, generator) {
    var dir_name = generator.quote_(block.getFieldValue('DIR'));
    // Generate code with or without directory parameter
    var code = (dir_name === "'file path'")
        ? 'self.main.io.open_sample(ui_update=False)\nself.store_sample_ids()\n'
        : 'self.main.io.open_sample(' + dir_name + 'ui_update=False)\nself.store_sample_ids()\n';
    return code;
};


// Python Generator: Select Samples
pythonGenerator.forBlock['select_samples'] = function(block, generator) {
    var sample_id = generator.quote_(block.getFieldValue('SAMPLE_IDS'));
    var code = 'self.parent.change_sample(self.parent.sample_ids.index(' + sample_id + '))\n';
    return code;
};

pythonGenerator.forBlock['select_analytes'] = function(block) {
    var analyteSelectorValue = block.getFieldValue('analyteSelectorDropdown');
    var code = '';
    
    if (analyteSelectorValue === 'Current selection') {
        code = '';
    } else if (analyteSelectorValue === 'Analyte selector') {
        code = 'self.parent.open_select_analyte_dialog()\n';
        code += 'self.refresh_analyte_saved_lists_dropdown()\n'
    } else if (analyteSelectorValue === 'Saved lists') {''
        var savedListName = block.getFieldValue('analyteSavedListsDropdown');
        var quotedListName = generator.quote_(savedListName);
        code = 'self.parent.update_analyte_selection_from_file(' + quotedListName + ')\n';
    }
    code += 'self.main.update_blockly_field_types(self)'
    return code;
};
  
  
// Python code generator for the select_analytes block
pythonGenerator.forBlock['select_ref_val'] = function(block) {
    const refValue = block.getFieldValue('refValueDropdown'); // Get selected dropdown value
    const code = `self.parent.change_ref_material_BE('${refValue}')\n`; // Python function call
    return code;
};

pythonGenerator.forBlock['change_pixel_dimensions'] = function(block, generator) {
    var dx = block.getFieldValue('dx');
    var dy = block.getFieldValue('dy');
    var code = 'self.parent.data[self.parent.sample_id].update_resolution(dx ='+dx+ ', dy ='+ dy+', ui_update = False)\n';
    return code;
};


pythonGenerator.forBlock['swap_pixel_dimensions'] = function(block) {
    var code = 'self.parent.data[self.parent.sample_id].swap_resolution\n';
    return code;
};

pythonGenerator.forBlock['swap_x_y'] = function(block) {
    var code = 'self.parent.data[self.parent.sample_id].swap_xy\n';
    return code;
};

pythonGenerator.forBlock['select_outlier_method'] = function(block) {
    var method = block.getFieldValue('outlierMethodDropdown');
    var code = '';

    if (method === 'quantile criteria') {
        var uB = block.getFieldValue('uB');
        var lB = block.getFieldValue('lB');
        code += `self.parent.update_bounds(ub=${uB}, lb=${uB})\n`;
    }
    if (method === 'quantile and distance criteria') {
        var uB = block.getFieldValue('uB');
        var lB = block.getFieldValue('lB');
        var dUB = block.getFieldValue('dUB');
        var dLB = block.getFieldValue('dLB');
        code += `self.parent.update_bounds(ub=${uB}, lb=${uB}, d_ub=${dUB}, d_lb=${dLB})\n`;
    }
    
    code += `self.parent.data[self.parent.sample_id].outlier_method='${method}'\n`;
    return code;
};


pythonGenerator.forBlock['neg_handling_method'] = function(block) {
    var method = block.getFieldValue('negMethodDropdown');
    
     var code = `self.parent.data[self.parent.sample_id].negative_method='${method}'\n`;
    return code;
};

pythonGenerator.forBlock['select_custom_lists'] = function(block) {
    var analyteSelectorValue = block.getFieldValue('fieldSelectorDropdown');
    var code = '';
    
    if (analyteSelectorValue === 'Current selection') {
        code = '';
    } else if (analyteSelectorValue === 'Field selector') {
        code = 'self.parent.open_select_custom_field_dialog()\n';
    } else if (analyteSelectorValue === 'Saved lists') {
        var savedListName = block.getFieldValue('fieldSavedListsDropdown');
        var quotedListName = generator.quote_(savedListName);
        code = 'self.parent.update_analyte_selection_from_file(' + quotedListName + ')\n';
    }
    return code;
};



/*
// Python Generator: Sample IDs List
pythonGenerator.forBlock['sample_ids_list_block'] = function(block, generator) {
    const code = JSON.stringify(sample_ids);  // Generates Python list from global sample_ids variable
    return code;
};
*/
// Python Generator: Iterate Through Sample IDs
pythonGenerator.forBlock['loop_over_samples'] = function(block, generator) {
    var variable_sample_ids = JSON.stringify(sample_ids);
    var statements_do = generator.statementToCode(block, 'DO');
    var code = 'for field in ' + variable_sample_ids + ':\n' +
        generator.INDENT + 'self.parent.change_sample(self.parent.sample_ids.index(sample_id), save_analysis= False)\n' +
        statements_do;
    return code;
};


// Python Generator: Iterate Through Sample IDs
pythonGenerator.forBlock['loop_over_fields'] = function(block, generator) {
    var field_type = block.plotType ? generator.quote_(block.fieldType) : 'Analyte';
    var statements_do = generator.statementToCode(block, 'DO');
    var code = 'for field in get_field_list(' + field_type + '):\n' +
        statements_do;
    return code;
};

pythonGenerator.forBlock['plot'] = function(block, generator) {
    // Retrieve the stored plotType from the block
    var plot_type = block.plotType ? generator.quote_(block.plotType) : 'None';

    // Initialize an empty code string
    var code = '';

    // Check if a `style` block is connected
    var styleCode = generator.valueToCode(block, 'style', Order.NONE);
    if (styleCode && styleCode !== '{}') {
        code += `
self.parent.style.style_dict[${plot_type}] = {**self.parent.style.style_dict[${plot_type}], **${styleCode}}
self.parent.style.set_style_widgets(${plot_type})
`;
    }

    // Update the visualization regardless of the style connection
    code += `self.parent.update_SV(${plot_type})\n`;
    return code;
};


pythonGenerator.forBlock['styles'] = function(block, generator) {
    // Retrieve code for each connected sub-block, default to an empty object if not connected
    var axisAndLabelsCode = generator.valueToCode(block, 'axis_and_labels', Order.NONE);
    var annotAndScaleCode = generator.valueToCode(block, 'annot_and_scale', Order.NONE);
    var marksAndLinesCode = generator.valueToCode(block, 'markers_and_lines', Order.NONE);
    var coloringCode = generator.valueToCode(block, 'coloring', Order.NONE);

    // Construct the style dictionary with only non-empty entries
    var styleDict = [];
    if (axisAndLabelsCode && axisAndLabelsCode !== '{}') styleDict.push(`"Axes": ${axisAndLabelsCode}`);
    if (annotAndScaleCode && annotAndScaleCode !== '{}') styleDict.push(`"Text": ${annotAndScaleCode}`);
    if (marksAndLinesCode && marksAndLinesCode !== '{}') styleDict.push(`"Markers": ${marksAndLinesCode}`);
    if (coloringCode && coloringCode !== '{}') styleDict.push(`"Colors": ${coloringCode}`);

    // Assemble the dictionary as a string, ensuring only non-empty values are included
    var code = `{${styleDict.join(', ')}}`;
    
    return [code, Order.ATOMIC];
};




pythonGenerator.forBlock['axis_and_labels'] = function(block, generator) {
    const xLabel = generator.quote_(block.getFieldValue('xLabel'));
    const xLimMin = block.getFieldValue('xLimMin');
    const xLimMax = block.getFieldValue('xLimMax');
    const xScale = generator.quote_(block.getFieldValue('xScaleDropdown'));
    const yLabel = generator.quote_(block.getFieldValue('yLabel'));
    const yLimMin = block.getFieldValue('yLimMin');
    const yLimMax = block.getFieldValue('yLimMax');
    const yScale = generator.quote_(block.getFieldValue('yScaleDropdown'));
    const zLabel = generator.quote_(block.getFieldValue('zLabel'));
    const tickDirection = generator.quote_(block.getFieldValue('tickDirectionDropdown'));

    const code = `
{
    "XLabel": ${xLabel},
    "XLim": [${xLimMin}, ${xLimMax}],
    "XScale": ${xScale},
    "YLabel": ${yLabel},
    "YLim": [${yLimMin}, ${yLimMax}],
    "YScale": ${yScale},
    "ZLabel": ${zLabel},
    "TickDir": ${tickDirection}
}`;
    return [code, Order.ATOMIC];
};

pythonGenerator.forBlock['annot_and_scale'] = function(block, generator) {
    const scaleDirection = generator.quote_(block.getFieldValue('scaleDirection'));
    const scaleLocation = generator.quote_(block.getFieldValue('scaleLocation'));
    const scaleLength = block.getFieldValue('scaleLength') || 'None';
    const overlayColor = generator.quote_(block.getFieldValue('overlayColor'));
    const font = generator.quote_(block.getFieldValue('font'));
    const fontSize = block.getFieldValue('fontSize');
    const showMass = block.getFieldValue('showMass') === 'TRUE';

    const code = `
{
    "Direction": ${scaleDirection},
    "Location": ${scaleLocation},
    "Length": ${scaleLength},
    "OverlayColor": ${overlayColor},
    "Font": ${font},
    "FontSize": ${fontSize},
    "ShowMass": ${showMass}
}`;
    return [code,Order.ATOMIC];
};

pythonGenerator.forBlock['marks_and_lines'] = function(block, generator) {
    const symbol = generator.quote_(block.getFieldValue('symbol'));
    const size = block.getFieldValue('size');
    const transparency = block.getFieldValue('transparency');
    const lineWidth = generator.quote_(block.getFieldValue('lineWidth'));
    const lineColor = generator.quote_(block.getFieldValue('lineColor'));
    const lengthMultiplier = block.getFieldValue('lengthMultiplier');

    const code = `
{
    "Symbol": ${symbol},
    "Size": ${size},
    "Alpha": ${transparency},
    "LineWidth": ${lineWidth},
    "Color": ${lineColor},
    "Multiplier": ${lengthMultiplier}
}`;
    return [code, Order.ATOMIC];
};

pythonGenerator.forBlock['coloring'] = function(block, generator) {
    const colorByField = generator.quote_(block.getFieldValue('colorByField'));
    const field = generator.quote_(block.getFieldValue('field'));
    const resolution = block.getFieldValue('resolution');
    const colormap = generator.quote_(block.getFieldValue('colormap'));
    const reverse = block.getFieldValue('reverse') === 'TRUE';
    const scale = generator.quote_(block.getFieldValue('scale'));
    const cLimMin = block.getFieldValue('cLimMin');
    const cLimMax = block.getFieldValue('cLimMax');
    const cBarLabel = generator.quote_(block.getFieldValue('cBarLabel'));
    const cBarDirection = generator.quote_(block.getFieldValue('cBarDirection'));

    const code = `
{
    "ColorByField": ${colorByField},
    "Field": ${field},
    "Resolution": ${resolution},
    "Colormap": ${colormap},
    "Reverse": ${reverse},
    "Scale": ${scale},
    "CLim": [${cLimMin}, ${cLimMax}],
    "CBarLabel": ${cBarLabel},
    "CBarDirection": ${cBarDirection}
}`;
    return [code, Order.ATOMIC];
};

